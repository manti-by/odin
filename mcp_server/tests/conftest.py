import pytest

from mcp_server.tools import docstrings, wiki


@pytest.fixture(autouse=True)
def reset_caches():
    """Clear the parsed-corpus caches between tests.

    ``docstrings`` and ``wiki`` each hold one cached corpus keyed by a root
    path plus a file fingerprint. Tests that build a throwaway corpus would
    otherwise leak it into the next test.
    """
    wiki.PAGES.clear()
    docstrings.FUNCTIONS.clear()
    yield


@pytest.fixture
def log_root(tmp_path, monkeypatch):
    """Point the log tools at a throwaway directory."""
    root = tmp_path / "logs"
    root.mkdir()
    monkeypatch.setattr("mcp_server.tools.logs.LOG_ROOT_RESOLVED", root)
    return root


@pytest.fixture
def pages_root(tmp_path, monkeypatch):
    """Point the wiki tools at a throwaway pages directory."""
    root = tmp_path / "pages"
    root.mkdir()
    monkeypatch.setattr("mcp_server.tools.wiki.PAGES_ROOT", root)
    return root
