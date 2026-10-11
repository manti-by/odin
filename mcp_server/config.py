import os
from importlib import import_module
from pathlib import Path

from mcp_server.models import SearchConfig


PROJECT_NAME = os.getenv("MCP_PROJECT_NAME", "odin")
SERVER_NAME = os.getenv("MCP_SERVER_NAME", f"{PROJECT_NAME.upper()} MCP Server")

# Django settings module consulted for database credentials. Importing it here,
# rather than in the database tool, keeps every project-specific import in this
# one module.
DJANGO_SETTINGS_MODULE = os.getenv("MCP_DJANGO_SETTINGS", f"{PROJECT_NAME}.settings.base")

# Repository root: this file lives at <repo>/mcp_server/config.py, so the repo
# is two levels up. Every other root below hangs off it.
PROJECT_ROOT = Path(__file__).resolve().parents[1]

# The importable package the docstring tool indexes, and the wiki corpus.
# Both default to this repository's layout; override to point the server at a
# different project without touching the tools.
SOURCE_ROOT = Path(os.getenv("MCP_SOURCE_ROOT", PROJECT_ROOT / PROJECT_NAME))
PAGES_ROOT = Path(os.getenv("MCP_PAGES_ROOT", PROJECT_ROOT / "wiki" / "pages"))

LOG_ROOT = Path(os.getenv("MCP_LOG_ROOT", f"/var/log/{PROJECT_NAME}"))
LOG_ROOT_DISPLAY = str(LOG_ROOT)

# Resolved separately: on macOS /var is a symlink to /private/var, and the
# path-containment checks require a fully resolved root on both sides.
LOG_ROOT_RESOLVED = LOG_ROOT.resolve()

SEARCH_IGNORE_WORDS: frozenset[str] = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "be",
        "been",
        "did",
        "do",
        "does",
        "for",
        "how",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "that",
        "the",
        "this",
        "to",
        "was",
        "were",
        "what",
        "why",
        "with",
    }
)


SEARCH: SearchConfig = {
    "default_limit": 5,
    "max_results": 20,
    "max_query_length": 500,
    "max_snippets": 3,
    "snippet_length": 200,
    "min_term_length": 2,
    "term_pattern": r"[a-z0-9][a-z0-9_.\-]*",
    "bm25_k1": 1.2,
    "wiki_title_boost": 10.0,
    "wiki_title_length_norm": 0.0,
    "wiki_metadata_boost": 5.0,
    "wiki_metadata_length_norm": 0.0,
    "wiki_body_boost": 1.0,
    "wiki_body_length_norm": 0.75,
    "docstring_name_boost": 10.0,
    "docstring_name_length_norm": 0.0,
    "docstring_path_boost": 5.0,
    "docstring_path_length_norm": 0.0,
    "docstring_text_boost": 1.0,
    "docstring_text_length_norm": 0.75,
}


def database_config() -> dict[str, object]:
    """Return asyncpg connection kwargs from the project's Django settings.

    The settings module is imported here rather than in the database tool so
    that every project-specific import stays in this one module.

    Returns:
        dict[str, object]: Keyword arguments for ``asyncpg.create_pool``.

    Raises:
        ImportError: If the configured Django settings module cannot be
            imported.
    """
    default = import_module(DJANGO_SETTINGS_MODULE).DATABASES["default"]
    return {
        "host": default["HOST"],
        "port": default["PORT"],
        "user": default["USER"],
        "password": default["PASSWORD"],
        "database": default["NAME"],
    }
