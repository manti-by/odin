import pytest

from mcp_server.models import DocumentedFunction
from mcp_server.tools.docstrings import (
    FunctionCollector,
    files_fingerprint,
    function_fields,
    list_source_files,
    load_functions,
    resolve_module_name,
    search_functions,
)
from mcp_server.tools.docstrings import call_tool as docstrings_call_tool


SOURCE = '''
def documented(value):
    """Return the value.

    Args:
        value: the input.
    """
    return value


def undocumented(value):
    return value


class Thing:
    """A thing."""

    def method(self):
        """Do the thing."""
        return None
'''


@pytest.fixture
def source_root(tmp_path):
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "pkg" / "core.py").write_text(SOURCE, encoding="utf-8")
    (tmp_path / "pkg" / "__pycache__").mkdir()
    (tmp_path / "pkg" / "__pycache__" / "core.cpython-314.pyc").write_bytes(b"\x00")
    return tmp_path / "pkg"


class TestListSourceFiles:
    def test_list_source_files__is_sorted_and_excludes_pycache(self, source_root):
        assert [path.name for path in list_source_files(source_root)] == ["__init__.py", "core.py"]


class TestFilesFingerprint:
    def test_files_fingerprint__changes_with_content(self, source_root):
        files = list_source_files(source_root)
        before = files_fingerprint(files, source_root)
        (source_root / "core.py").write_text(SOURCE + "\n# changed\n", encoding="utf-8")
        assert files_fingerprint(files, source_root) != before

    def test_files_fingerprint__is_stable_without_changes(self, source_root):
        files = list_source_files(source_root)
        assert files_fingerprint(files, source_root) == files_fingerprint(files, source_root)


class TestResolveModuleName:
    def test_resolve_module_name__plain_module(self, source_root):
        assert resolve_module_name(source_root / "core.py", source_root) == "pkg.core"

    def test_resolve_module_name__package_init_drops_the_init_segment(self, source_root):
        assert resolve_module_name(source_root / "__init__.py", source_root) == "pkg"


class TestFunctionCollector:
    def test_collector__records_only_documented_functions(self):
        import ast

        collector = FunctionCollector(module_name="pkg.core", path="pkg/core.py")
        collector.visit(ast.parse(SOURCE))
        names = [function.qualified_name for function in collector.functions]
        assert names == ["pkg.core.documented", "pkg.core.Thing.method"]

    def test_collector__records_the_line_number(self):
        import ast

        collector = FunctionCollector(module_name="pkg.core", path="pkg/core.py")
        collector.visit(ast.parse(SOURCE))
        first = collector.functions[0]
        assert first.line == SOURCE.splitlines().index("def documented(value):") + 1


class TestLoadFunctions:
    def test_load_functions__indexes_the_source_tree(self, source_root):
        functions = load_functions(source_root)
        assert [f.qualified_name for f in functions] == ["pkg.core.documented", "pkg.core.Thing.method"]

    def test_load_functions__skips_unparseable_files(self, source_root):
        (source_root / "broken.py").write_text("def (:\n", encoding="utf-8")
        functions = load_functions(source_root)
        assert all("broken" not in f.qualified_name for f in functions)

    def test_load_functions__second_call_uses_the_cache(self, source_root):
        first = load_functions(source_root)
        assert load_functions(source_root) == first


class TestFunctionFields:
    def test_function_fields__a_dotted_name_stays_searchable_by_its_parts(self):
        """The name field is the highest-weighted one; a bare name must reach it."""
        function = DocumentedFunction(
            qualified_name="odin.apps.relays.models.Relay.get_target_state",
            path="odin/apps/relays/models.py",
            line=1,
            docstring="Compute it.",
        )
        counts = function_fields(function)[0].counts
        assert counts.get("get_target_state") == 1
        assert counts.get("relay") == 1
        assert counts.get("models") == 1
        assert "odin.apps.relays.models.relay.get_target_state" not in counts


class TestSearchFunctions:
    def test_search_functions__finds_a_documented_function(self, source_root):
        load_functions(source_root)
        results = search_functions(source_root=source_root, query="documented", limit=5)
        assert results[0][0].qualified_name == "pkg.core.documented"

    def test_search_functions__finds_a_function_by_its_bare_name(self, source_root):
        load_functions(source_root)
        results = search_functions(source_root=source_root, query="Thing.method", limit=5)
        assert [f.qualified_name for f, _, _ in results] == ["pkg.core.Thing.method"]

    def test_search_functions__stop_words_only_matches_nothing(self, source_root):
        load_functions(source_root)
        assert search_functions(source_root=source_root, query="the of and", limit=5) == []

    def test_search_functions__respects_the_limit(self, source_root):
        load_functions(source_root)
        assert len(search_functions(source_root=source_root, query="value", limit=1)) == 1


class TestCallTool:
    async def test_call_tool__list(self, source_root, monkeypatch):
        monkeypatch.setattr("mcp_server.tools.docstrings.DOCSTRING_ROOT", source_root)
        result = await docstrings_call_tool("docstring_list", {})
        assert result.is_error is False
        assert "pkg.core.documented" in result.content[0].text

    async def test_call_tool__search(self, source_root, monkeypatch):
        monkeypatch.setattr("mcp_server.tools.docstrings.DOCSTRING_ROOT", source_root)
        result = await docstrings_call_tool("docstring_search", {"query": "documented"})
        assert result.is_error is False
        assert "pkg.core.documented" in result.content[0].text

    async def test_call_tool__search_with_no_match_is_not_an_error(self, source_root, monkeypatch):
        monkeypatch.setattr("mcp_server.tools.docstrings.DOCSTRING_ROOT", source_root)
        result = await docstrings_call_tool("docstring_search", {"query": "kubernetes"})
        assert result.is_error is False
        assert "No matching documented functions" in result.content[0].text

    @pytest.mark.parametrize("arguments", [{}, {"query": ""}])
    async def test_call_tool__search_requires_a_query(self, source_root, monkeypatch, arguments):
        monkeypatch.setattr("mcp_server.tools.docstrings.DOCSTRING_ROOT", source_root)
        result = await docstrings_call_tool("docstring_search", arguments)
        assert result.is_error is True
        assert "query is required" in result.content[0].text

    async def test_call_tool__search_rejects_a_non_string_query(self, source_root, monkeypatch):
        monkeypatch.setattr("mcp_server.tools.docstrings.DOCSTRING_ROOT", source_root)
        result = await docstrings_call_tool("docstring_search", {"query": 42})
        assert result.is_error is True
        assert "must be a string" in result.content[0].text

    async def test_call_tool__search_rejects_an_overlong_query(self, source_root, monkeypatch):
        monkeypatch.setattr("mcp_server.tools.docstrings.DOCSTRING_ROOT", source_root)
        result = await docstrings_call_tool("docstring_search", {"query": "x" * 501})
        assert result.is_error is True
        assert "exceeds maximum length" in result.content[0].text

    async def test_call_tool__get_returns_the_full_docstring(self, source_root, monkeypatch):
        monkeypatch.setattr("mcp_server.tools.docstrings.DOCSTRING_ROOT", source_root)
        result = await docstrings_call_tool("docstring_get", {"name": "pkg.core.documented"})
        assert result.is_error is False
        assert "Return the value." in result.content[0].text

    async def test_call_tool__get_unknown_name(self, source_root, monkeypatch):
        monkeypatch.setattr("mcp_server.tools.docstrings.DOCSTRING_ROOT", source_root)
        result = await docstrings_call_tool("docstring_get", {"name": "pkg.core.absent"})
        assert result.is_error is True
        assert "not found" in result.content[0].text

    @pytest.mark.parametrize("arguments", [{}, {"name": ""}])
    async def test_call_tool__get_requires_a_name(self, source_root, monkeypatch, arguments):
        monkeypatch.setattr("mcp_server.tools.docstrings.DOCSTRING_ROOT", source_root)
        result = await docstrings_call_tool("docstring_get", arguments)
        assert result.is_error is True
        assert "name is required" in result.content[0].text

    async def test_call_tool__unknown_tool(self, source_root, monkeypatch):
        monkeypatch.setattr("mcp_server.tools.docstrings.DOCSTRING_ROOT", source_root)
        result = await docstrings_call_tool("docstrings_nope", {})
        assert result.is_error is True
        assert "Unknown tool" in result.content[0].text

    async def test_call_tool__missing_source_directory(self, tmp_path, monkeypatch):
        monkeypatch.setattr("mcp_server.tools.docstrings.DOCSTRING_ROOT", tmp_path / "absent")
        result = await docstrings_call_tool("docstring_list", {})
        assert result.is_error is True
        assert "not found" in result.content[0].text
