"""Tests for the MCP request handlers.

The handlers are what the low-level server calls for ``tools/list`` and
``tools/call``; they only translate between MCP types and the registry, so they
are tested without a transport.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from mcp_server.config import (
    DEFAULT_TRANSPORT,
    MCP_HOST,
    MCP_PATH,
    MCP_PORT,
    MCP_URL,
    PROJECT_NAME,
    SERVER_NAME,
)
from mcp_server.main import APP_NAME, VERSION, handle_call_tool, handle_list_tools, main, parse_args, run_network


class TestHandleListTools:
    async def test_handle_list_tools__returns_every_tool(self):
        result = await handle_list_tools(None, None)
        assert result.tools
        assert all(tool.name for tool in result.tools)

    async def test_handle_list_tools__works_without_pagination_params(self):
        assert (await handle_list_tools(None, None)).tools == (
            await handle_list_tools(None, SimpleNamespace(cursor=None))
        ).tools


class TestHandleCallTool:
    async def test_handle_call_tool__maps_content_and_error_flag(self):
        result = await handle_call_tool(None, SimpleNamespace(name="no_such_tool", arguments={}))
        assert result.is_error is True
        assert "Unknown tool no_such_tool" in result.content[0].text

    async def test_handle_call_tool__succeeds_for_a_real_tool(self):
        result = await handle_call_tool(None, SimpleNamespace(name="wiki_list_pages", arguments={}))
        assert result.is_error is False
        assert result.content


class TestServerMetadata:
    def test_server__is_named_for_this_project(self):
        assert APP_NAME == SERVER_NAME

    def test_server__name_mentions_the_project(self):
        assert PROJECT_NAME in APP_NAME.lower()

    def test_server__name_has_no_leftover_project_reference(self):
        assert "demetra" not in APP_NAME.lower()

    def test_server__exposes_a_version(self):
        assert VERSION


class TestParseArgs:
    def test_parse_args__defaults_to_network_on_the_configured_endpoint(self):
        args = parse_args([])
        assert args.transport == DEFAULT_TRANSPORT
        assert DEFAULT_TRANSPORT == "network"
        assert (args.host, args.port) == (MCP_HOST, MCP_PORT)
        assert MCP_HOST == "127.0.0.1"

    def test_parse_args__keeps_stdio_as_an_option(self):
        assert parse_args(["--transport", "stdio"]).transport == "stdio"

    def test_parse_args__accepts_a_custom_endpoint(self):
        args = parse_args(["--host", "127.0.0.1", "--port", "9000"])
        assert args.host == "127.0.0.1"
        assert args.port == 9000

    def test_parse_args__rejects_an_unknown_transport(self):
        with pytest.raises(SystemExit):
            parse_args(["--transport", "websocket"])

    def test_parse_args__help_lists_the_transport_options(self, capsys):
        with pytest.raises(SystemExit) as exc:
            parse_args(["--help"])
        assert exc.value.code == 0
        output = capsys.readouterr().out
        assert "--transport" in output
        assert "--host" in output
        assert "--port" in output


class TestMainDispatch:
    async def test_main__uses_the_network_transport_by_default(self, monkeypatch):
        network, stdio = AsyncMock(), AsyncMock()
        monkeypatch.setattr("mcp_server.main.run_network", network)
        monkeypatch.setattr("mcp_server.main.run_stdio", stdio)

        await main([])

        network.assert_awaited_once_with(MCP_HOST, MCP_PORT)
        stdio.assert_not_awaited()

    async def test_main__uses_stdio_when_requested(self, monkeypatch):
        network, stdio = AsyncMock(), AsyncMock()
        monkeypatch.setattr("mcp_server.main.run_network", network)
        monkeypatch.setattr("mcp_server.main.run_stdio", stdio)

        await main(["--transport", "stdio"])

        stdio.assert_awaited_once_with()
        network.assert_not_awaited()

    async def test_main__passes_a_custom_endpoint_to_the_network_transport(self, monkeypatch):
        network = AsyncMock()
        monkeypatch.setattr("mcp_server.main.run_network", network)

        await main(["--host", "127.0.0.1", "--port", "9000"])

        network.assert_awaited_once_with("127.0.0.1", 9000)


class TestNetworkTransport:
    @pytest.fixture(autouse=True)
    def auth_token(self, monkeypatch):
        monkeypatch.setattr("mcp_server.main.MCP_AUTH_TOKEN", "test-token")

    async def test_run_network__refuses_to_start_without_a_token(self, monkeypatch):
        monkeypatch.setattr("mcp_server.main.MCP_AUTH_TOKEN", "")

        with pytest.raises(RuntimeError, match="MCP_AUTH_TOKEN must be set"):
            await run_network(MCP_HOST, MCP_PORT)

    async def test_run_network__serves_the_configured_path_on_the_requested_endpoint(self, monkeypatch):
        calls: dict[str, object] = {}
        app = object()

        def make_app(**kwargs):
            calls["app_kwargs"] = kwargs
            return app

        class FakeConfig:
            def __init__(self, loaded_app, **kwargs):
                calls["config"] = (loaded_app, kwargs)

        class FakeServer:
            def __init__(self, config):
                calls["server_config"] = config

            async def serve(self):
                calls["served"] = True

        monkeypatch.setattr("mcp_server.main.mcp_server.streamable_http_app", make_app)
        monkeypatch.setattr("mcp_server.main.uvicorn.Config", FakeConfig)
        monkeypatch.setattr("mcp_server.main.uvicorn.Server", FakeServer)
        close_pool = AsyncMock()
        monkeypatch.setattr("mcp_server.main.close_db_pool", close_pool)

        await run_network(MCP_HOST, MCP_PORT)

        app_kwargs = calls["app_kwargs"]
        assert app_kwargs["streamable_http_path"] == MCP_PATH
        assert app_kwargs["host"] == MCP_HOST
        assert app_kwargs["transport_security"].enable_dns_rebinding_protection is False
        assert str(app_kwargs["auth"].issuer_url) == MCP_URL
        assert MCP_URL.startswith("https://")
        verifier = app_kwargs["token_verifier"]
        assert (await verifier.verify_token("test-token")) is not None
        assert await verifier.verify_token("wrong-token") is None
        loaded_app, config_kwargs = calls["config"]
        assert loaded_app is app
        assert (config_kwargs["host"], config_kwargs["port"]) == (MCP_HOST, MCP_PORT)
        assert calls["served"] is True
        close_pool.assert_awaited_once_with()

    async def test_run_network__closes_the_pool_when_serving_fails(self, monkeypatch):
        class FakeServer:
            def __init__(self, config):
                pass

            async def serve(self):
                raise RuntimeError("uvicorn failed")

        monkeypatch.setattr("mcp_server.main.uvicorn.Server", FakeServer)
        close_pool = AsyncMock()
        monkeypatch.setattr("mcp_server.main.close_db_pool", close_pool)

        with pytest.raises(RuntimeError, match="uvicorn failed"):
            await run_network(MCP_HOST, MCP_PORT)

        close_pool.assert_awaited_once_with()
