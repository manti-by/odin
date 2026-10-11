"""Guard the roots the tools resolve their data from.

These paths used to be computed with ``Path(__file__).resolve().parents[N]``
inside each tool, so moving a module one directory up or down silently
repointed the wiki tools at another repository and shrank the docstring index.
They now come from ``mcp_server.config``. A wrong value still resolves to a
directory that *exists*, so nothing crashes -- the tools just answer from the
wrong corpus. Assert on the resolved location, not on "is a directory".
"""

from pathlib import Path

from mcp_server.config import PAGES_ROOT, PROJECT_ROOT, SOURCE_ROOT


REPO_ROOT = Path(__file__).resolve().parents[2]


class TestProjectRoot:
    def test_project_root__is_the_repository(self):
        assert PROJECT_ROOT == REPO_ROOT

    def test_project_root__contains_the_server_package(self):
        assert (PROJECT_ROOT / "mcp_server" / "config.py").is_file()


class TestRootsAreLocal:
    """A wrong ``parents[N]`` used to escape into the parent checkout."""

    def test_pages_root__lives_under_the_project_root(self):
        assert PROJECT_ROOT in PAGES_ROOT.parents

    def test_pages_root__is_not_a_sibling_checkout(self):
        assert PAGES_ROOT != REPO_ROOT.parent / "wiki" / "pages"

    def test_source_root__lives_under_the_project_root(self):
        assert PROJECT_ROOT in SOURCE_ROOT.parents


class TestRootsPointAtRealData:
    def test_pages_root__exists_and_holds_pages(self):
        assert PAGES_ROOT.is_dir()
        assert any(PAGES_ROOT.glob("*.md"))

    def test_source_root__is_the_importable_application_package(self):
        assert SOURCE_ROOT.name == "odin"
        assert (SOURCE_ROOT / "apps").is_dir()
        assert (SOURCE_ROOT / "api").is_dir()

    def test_source_root__is_not_the_mcp_server_itself(self):
        """Indexing ``mcp_server`` would only describe the MCP server."""
        assert SOURCE_ROOT != REPO_ROOT / "mcp_server"

    def test_source_root__name_prefixes_qualified_function_names(self):
        """``resolve_module_name`` prefixes with the root's directory name."""
        from mcp_server.tools.docstrings import resolve_module_name

        assert resolve_module_name(SOURCE_ROOT / "apps" / "core" / "models.py", SOURCE_ROOT) == "odin.apps.core.models"
