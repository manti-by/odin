from mcp_server.auth import StaticTokenVerifier


class TestStaticTokenVerifier:
    async def test_verify_token__accepts_the_configured_token(self):
        result = await StaticTokenVerifier("secret").verify_token("secret")
        assert result is not None
        assert result.token == "secret"
        assert result.scopes == []

    async def test_verify_token__rejects_a_different_token(self):
        assert await StaticTokenVerifier("secret").verify_token("wrong") is None

    async def test_verify_token__rejects_non_ascii_input_without_raising(self):
        assert await StaticTokenVerifier("secret").verify_token("sécret") is None

    async def test_verify_token__rejects_an_empty_token(self):
        verifier = StaticTokenVerifier("")
        assert await verifier.verify_token("") is None
        assert await verifier.verify_token("secret") is None
