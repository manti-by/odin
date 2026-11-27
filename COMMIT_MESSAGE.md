# MNT-254 — prepared commit and PR handoff

This records step 8 (Git Flow) of the plan. The commit and PR are deliberately left to the
orchestrator; no commit or push is performed here.

## Commit subject

`feat(mcp): serve MCP tools over bearer-authenticated Streamable HTTP on the LAN`

## Commit body

- Run the database, log, source, wiki and docstring MCP tools on the ODIN host as the
  `mcp.service` systemd unit, bound to `127.0.0.1:7750`.
- Expose them through nginx's existing TLS vhost at `https://192.168.1.100/mcp`, so the
  bearer token never crosses the LAN in cleartext.
- Keep stdio available with `--transport stdio`; network is the default and fails closed
  without `MCP_AUTH_TOKEN`.
- Point the project's `opencode.json` at the remote HTTPS endpoint with the same token.
- Drop Django session keys, expiry and blobs from the database tool's column allow-list.
- Add transport, auth and column-hardening tests; document the change in the wiki.

## PR

- Title: same as the commit subject.
- Target branch: `master`.
- Source branch: `mnt-254-spin-up-mcp-server-in-a-local-network`.
- MNT-254 state: In Progress (verified 2026-11-27); move to In Review when the PR opens,
  to Done after approval and merge.

See `wiki/pages/2026-11-26-mnt-254-mcp-network-server.md` for the full implementation record.
