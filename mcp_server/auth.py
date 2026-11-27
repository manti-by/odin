import hmac

from mcp.server.auth.provider import AccessToken, TokenVerifier


class StaticTokenVerifier(TokenVerifier):
    """Accept one shared bearer token, configured on the server."""

    def __init__(self, token: str) -> None:
        self._token = token

    async def verify_token(self, token: str) -> AccessToken | None:
        """Return access info only when the bearer token matches.

        Args:
            token: The bearer token supplied by the client.

        Returns:
            AccessToken | None: Access info for a valid token, otherwise None.
        """
        if not token or not self._token or not hmac.compare_digest(token.encode(), self._token.encode()):
            return None
        return AccessToken(token=token, client_id="mcp-client", scopes=[])
