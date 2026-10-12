import pytest

from mcp_server.registry import HANDLERS, call_tool, list_tools
from mcp_server.tools import database, docstrings, logs, wiki


class TestListTools:
    async def test_list_tools__returns_every_registered_tool(self):
        tools = await list_tools()
        assert {tool.name for tool in tools} == set(HANDLERS)

    async def test_list_tools__names_are_unique(self):
        names = [tool.name for tool in await list_tools()]
        assert len(names) == len(set(names))

    async def test_list_tools__every_tool_declares_an_object_schema(self):
        for tool in await list_tools():
            assert tool.input_schema["type"] == "object", tool.name

    @pytest.mark.parametrize(
        "module",
        [database, docstrings, logs, wiki],
        ids=lambda module: module.__name__.rsplit(".", 1)[-1],
    )
    async def test_list_tools__module_listers_match_registered_names(self, module):
        for tool in await module.list_tools():
            assert HANDLERS[tool.name] is module.call_tool


class TestCallTool:
    async def test_call_tool__dispatches_to_owning_module(self):
        result = await call_tool("docstring_list", {})
        assert result.is_error is False
        assert result.content

    async def test_call_tool__unknown_tool_is_an_error_not_a_crash(self):
        result = await call_tool("no_such_tool", {})
        assert result.is_error is True
        assert "Unknown tool no_such_tool" in result.content[0].text

    async def test_call_tool__missing_arguments_are_tolerated(self):
        result = await call_tool("wiki_list_pages", None)
        assert result.is_error is False

    async def test_call_tool__every_registered_handler_is_reachable(self):
        for name in HANDLERS:
            result = await call_tool(name, {})
            assert isinstance(result.content, list), name
