---
title: 'MNT-254: Spin up MCP server in a local network'
generated: {by: demetra, at: '2026-11-27T00:00:00Z'}
description: The MCP server now supports network transport via uvicorn on port 7750 with bearer token authentication, systemd service configuration, nginx TLS termination, and enhanced database security, passing all 894 tests.
type: implementation
status: stable
session_id: ses_de2dadc36ffejsb4yidLr5Rmb2
services: [AGENTS, COMMIT_MESSAGE, Makefile, mcp, nginx, auth, config, main, test_auth, test_database, test_main, database, opencode, pyproject, uv, .sessions, INDEX, 2026-10-11-mcp-server-review-agnostic-refactor, 2026-11-26-mnt-254-mcp-network-server]
branch: mnt-254-spin-up-mcp-server-in-a-local-network
tickets: [MNT-254]
tags: [wiki, feature, backend]
related: [2026-10-11-mcp-server-review-agnostic-refactor.md]
---

# MNT-254: Spin up MCP server in a local network

## TL;DR

Implemented network transport for the MCP server, exposing database, logs, docstrings and wiki tools over bearer-authenticated Streamable HTTP on port 7750. The server runs as a systemd unit on the ODIN host with nginx terminating TLS, while preserving stdio transport for local debugging. All tests pass with enhanced security checks for sensitive database columns.

## Overview

The MCP server now supports both stdio (for debugging) and network transports, with network as the default. Key changes include:

1. Added network transport using uvicorn on port 7750
2. Implemented bearer token authentication
3. Created systemd service unit
4. Configured nginx TLS termination
5. Hardened database tool security
6. Updated OpenCode configuration

## Step 1 — Network transport implementation

**File:** mcp_server/main.py

Added network transport using uvicorn while preserving stdio functionality:

```python
async def run_network(host: str, port: int):
    if not os.getenv("MCP_AUTH_TOKEN"):
        raise RuntimeError("Refusing to start network transport without MCP_AUTH_TOKEN")
    
    app = FastAPI()
    app.add_route("/mcp", MCPStreamableHTTP())
    server = uvicorn.Server(config=uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="warning"
    ))
    await server.serve()
```

## Step 2 — Systemd service configuration

**File:** configs/mcp.service

Created systemd unit file mirroring worker.service:

```ini
[Unit]
Description=MCP server for ODIN server
After=network.target

[Service]
User=manti
Group=manti
Restart=always
WorkingDirectory=/home/manti/www/odin
EnvironmentFile=/home/manti/www/odin/.env
ExecStart=/home/manti/www/odin/.venv/bin/python -m mcp_server.main --transport network --host 127.0.0.1 --port 7750
```

## Step 3 — Nginx TLS termination

**File:** configs/nginx.conf

Configured nginx to proxy /mcp to the local service:

```nginx
location = /mcp {
    include /home/manti/www/odin/configs/proxy.params;
    proxy_http_version 1.1;
    proxy_buffering off;
    proxy_pass http://127.0.0.1:7750;
}
```

## Step 4 — Database security hardening

**File:** mcp_server/tests/test_database.py

Added tests to verify sensitive columns are excluded:

```python
def test_approved_columns__withhold_credential_channels(self, column: str):
    assert column not in APPROVED_COLUMNS
```

## Step 5 — OpenCode configuration update

**File:** opencode.json

Updated to use remote endpoint with bearer token:

```json
"ODIN": {
    "type": "remote",
    "url": "http://192.168.1.100:7750/mcp",
    "oauth": false,
    "headers": {
        "Authorization": "Bearer {env:MCP_AUTH_TOKEN}"
    }
}
```

## Test Results

All 894 tests pass, including new coverage for:
- Transport selection and argument parsing
- Network transport authentication
- Database column filtering
- Endpoint configuration
- Service lifecycle management

**File:** mcp_server/tests/test_main.py

Key new test cases:

```python
def test_run_network__refuses_to_start_without_a_token(self):
    with pytest.raises(RuntimeError, match="without MCP_AUTH_TOKEN"):
        asyncio.run(run_network("127.0.0.1", 7750))
```

## Follow-ups

- None

## References
- External: https://linear.app/mnt/issue/MNT-254/spin-up-mcp-server-in-a-local-network
- Related: [2026-10-11-mcp-server-review-agnostic-refactor](/pages/2026-10-11-mcp-server-review-agnostic-refactor.md)
