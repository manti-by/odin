"""Tests for the MCP request handlers.

The handlers are what the low-level server calls for ``tools/list`` and
``tools/call``; they only translate between MCP types and the registry, so they
are tested without a transport.
"""

from types import SimpleNamespace

from mcp_server.config import PROJECT_NAME, SERVER_NAME
from mcp_server.main import APP_NAME, VERSION, handle_call_tool, handle_list_tools


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
