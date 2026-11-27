import argparse
import asyncio
import logging
import sys

import uvicorn
from mcp.server import ServerRequestContext
from mcp.server.auth.settings import AuthSettings
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import (
    CallToolRequestParams,
    CallToolResult,
    ListToolsResult,
    PaginatedRequestParams,
)

from mcp_server.auth import StaticTokenVerifier
from mcp_server.config import (
    DEFAULT_TRANSPORT,
    MCP_AUTH_TOKEN,
    MCP_HOST,
    MCP_PATH,
    MCP_PORT,
    MCP_URL,
    SERVER_NAME,
)
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse the transport and network listener options.

    Args:
        argv: Arguments to parse; defaults to the process arguments.

    Returns:
        argparse.Namespace: The selected transport, host and port.
    """
    parser = argparse.ArgumentParser(description=f"Run {APP_NAME}.")
    parser.add_argument(
        "--transport",
        choices=("network", "stdio"),
        default=DEFAULT_TRANSPORT,
        help="Transport to serve over (default: network).",
    )
    parser.add_argument("--host", default=MCP_HOST, help=f"Network bind host (default: {MCP_HOST}).")
    parser.add_argument("--port", type=int, default=MCP_PORT, help=f"Network bind port (default: {MCP_PORT}).")
    return parser.parse_args(argv)


async def run_stdio() -> None:
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


async def run_network(host: str, port: int) -> None:
    """Serve the authenticated MCP tools over Streamable HTTP until it stops.

    Args:
        host: Address to bind the HTTP listener to.
        port: TCP port to listen on.

    Raises:
        RuntimeError: If no bearer token is configured for the network listener.
    """
    if not MCP_AUTH_TOKEN:
        raise RuntimeError("MCP_AUTH_TOKEN must be set to serve the MCP server over the network")

    # The SDK requires an issuer even for token-only auth; no OAuth endpoints are
    # advertised because no auth server provider is installed. The issuer is the
    # public HTTPS URL, not the loopback bind address.
    auth = AuthSettings(
        issuer_url=MCP_URL,
        resource_server_url=None,
        validate_token_resource=False,
    )
    # nginx is the only LAN-facing ingress and already validates the TLS
    # certificate; the SDK's loopback-only Host/Origin guard would reject the
    # proxied public host. Content-Type checks remain active.
    transport_security = TransportSecuritySettings(enable_dns_rebinding_protection=False)
    app = mcp_server.streamable_http_app(
        streamable_http_path=MCP_PATH,
        host=host,
        transport_security=transport_security,
        auth=auth,
        token_verifier=StaticTokenVerifier(MCP_AUTH_TOKEN),
    )
    server = uvicorn.Server(uvicorn.Config(app, host=host, port=port))
    try:
        await server.serve()
    finally:
        await close_db_pool()


async def main(argv: list[str] | None = None) -> None:
    """Run the MCP server over the requested transport.

    Args:
        argv: Arguments to parse; defaults to the process arguments.
    """
    args = parse_args(argv)
    if args.transport == "stdio":
        await run_stdio()
    else:
        await run_network(args.host, args.port)


if __name__ == "__main__":
    # stdout carries the JSON-RPC stream, so all logging must go to stderr.
    logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    print(f"Starting {APP_NAME} v{VERSION}", file=sys.stderr)
    asyncio.run(main(sys.argv[1:]))
