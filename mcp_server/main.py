import asyncio
import logging
import sys

from mcp.server import ServerRequestContext
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequestParams,
    CallToolResult,
    ListToolsResult,
    PaginatedRequestParams,
)

from mcp_server.config import SERVER_NAME
from mcp_server.registry import call_tool, list_tools
from mcp_server.tools.database import close_db_pool


logger = logging.getLogger(__name__)

APP_NAME = SERVER_NAME
VERSION = "1.0.0"


async def handle_list_tools(ctx: ServerRequestContext, params: PaginatedRequestParams | None) -> ListToolsResult:
    """Handle the MCP ``list_tools`` request.

    Args:
        ctx: The MCP server request context.
        params: Pagination parameters, if any.

    Returns:
        ListToolsResult: The aggregated tool definitions.
    """
    return ListToolsResult(tools=await list_tools())


async def handle_call_tool(ctx: ServerRequestContext, params: CallToolRequestParams) -> CallToolResult:
    """Handle the MCP ``call_tool`` request.

    Args:
        ctx: The MCP server request context.
        params: The tool name and arguments to invoke.

    Returns:
        CallToolResult: The tool call outcome.
    """
    result = await call_tool(params.name, params.arguments)
    return CallToolResult(content=result.content, is_error=result.is_error)


mcp_server = Server(
    APP_NAME,
    version=VERSION,
    on_list_tools=handle_list_tools,
    on_call_tool=handle_call_tool,
)


async def main() -> None:
    """Run the MCP server over stdio until the transport closes."""
    async with stdio_server() as (read_stream, write_stream):
        try:
            await mcp_server.run(
                read_stream,
                write_stream,
                mcp_server.create_initialization_options(),
            )
        finally:
            await close_db_pool()


if __name__ == "__main__":
    # stdout carries the JSON-RPC stream, so all logging must go to stderr.
    logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    print(f"Starting {APP_NAME} v{VERSION}", file=sys.stderr)
    asyncio.run(main())
