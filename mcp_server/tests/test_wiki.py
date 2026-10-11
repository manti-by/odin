import pytest

from mcp_server.tools.wiki import call_tool as wiki_call_tool
from mcp_server.tools.wiki import (
    extract_snippets,
    load_pages,
    metadata_text,
    page_title,
    parse_page_file,
    resolve_page,
    search_pages,
    summarize_meta,
)


class TestParsePageFile:
    def test_parse_page_file__splits_frontmatter_from_body(self, tmp_path):
        path = tmp_path / "page.md"
        path.write_text("---\ntitle: Relay mode\ntype: implementation\n---\n# Body\n", encoding="utf-8")
        page = parse_page_file(path)
        assert page == {
            "name": "page.md",
            "meta": {"title": "Relay mode", "type": "implementation"},
            "body": "# Body\n",
        }

    def test_parse_page_file__page_without_frontmatter_is_all_body(self, tmp_path):
        path = tmp_path / "page.md"
        path.write_text("just a body", encoding="utf-8")
        assert parse_page_file(path) == {"name": "page.md", "meta": {}, "body": "just a body"}

    def test_parse_page_file__empty_frontmatter_yields_empty_meta(self, tmp_path):
        path = tmp_path / "page.md"
        path.write_text("---\n---\nbody", encoding="utf-8")
        assert parse_page_file(path)["meta"] == {}

    def test_parse_page_file__invalid_yaml_is_skipped(self, tmp_path):
        path = tmp_path / "page.md"
        path.write_text("---\ntitle: [unclosed\n---\nbody", encoding="utf-8")
        assert parse_page_file(path) is None

    def test_parse_page_file__non_mapping_frontmatter_is_skipped(self, tmp_path):
        path = tmp_path / "page.md"
        path.write_text("---\n- one\n- two\n---\nbody", encoding="utf-8")
        assert parse_page_file(path) is None

    def test_parse_page_file__bare_dash_value_is_preserved_as_string(self, tmp_path):
        """``branch: -`` is valid YAML for None, not for the string "-"."""
        path = tmp_path / "page.md"
        path.write_text("---\nbranch: -\n---\nbody", encoding="utf-8")
        assert parse_page_file(path)["meta"] == {"branch": "-"}

    def test_parse_page_file__missing_file_is_skipped(self, tmp_path):
        assert parse_page_file(tmp_path / "absent.md") is None


class TestResolvePage:
    def test_resolve_page__resolves_a_bare_name(self, pages_root):
        (pages_root / "page.md").write_text("body", encoding="utf-8")
        assert resolve_page(pages_root, "page.md") == (pages_root / "page.md").resolve()

    def test_resolve_page__appends_the_md_suffix(self, pages_root):
        (pages_root / "page.md").write_text("body", encoding="utf-8")
        assert resolve_page(pages_root, "page") is not None

    def test_resolve_page__strips_a_pages_prefix(self, pages_root):
        (pages_root / "page.md").write_text("body", encoding="utf-8")
        assert resolve_page(pages_root, "pages/page.md") is not None

    @pytest.mark.parametrize("name", ["../secret.md", "../../etc/passwd", "sub/../../escape.md"])
    def test_resolve_page__rejects_traversal(self, pages_root, name):
        assert resolve_page(pages_root, name) is None

    def test_resolve_page__missing_page_is_none(self, pages_root):
        assert resolve_page(pages_root, "absent.md") is None


class TestMetadata:
    def test_metadata_text__flattens_list_and_scalar_fields(self):
        text = metadata_text({"tags": ["relays", "mode"], "services": ["api"], "type": "implementation"})
        assert text == "relays mode api implementation"

    def test_metadata_text__ignores_unknown_and_empty_fields(self):
        assert metadata_text({"title": "ignored", "tickets": [], "areas": None}) == ""

    def test_summarize_meta__always_leads_with_type_date_status(self):
        summary = summarize_meta({})
        assert summary.startswith("type: -, date: -, status: -")

    def test_summarize_meta__joins_list_fields(self):
        assert "tags: a, b" in summarize_meta({"tags": ["a", "b"]})

    def test_page_title__falls_back_to_the_file_name(self):
        assert page_title({"name": "page.md", "meta": {}}) == "page.md"

    def test_page_title__prefers_the_frontmatter_title(self):
        assert page_title({"name": "page.md", "meta": {"title": "T"}}) == "T"


class TestExtractSnippets:
    def test_extract_snippets__prefixes_the_line_number(self):
        assert extract_snippets("alpha\nrelay here\nbeta", ["relay"]) == ["L2: relay here"]

    def test_extract_snippets__skips_blank_lines(self):
        assert extract_snippets("\n\nrelay\n\n", ["relay"]) == ["L3: relay"]

    def test_extract_snippets__no_match_gives_nothing(self):
        assert extract_snippets("nothing to see", ["relay"]) == []


class TestLoadPages:
    def test_load_pages__sorts_by_filename(self, pages_root):
        for name in ("b.md", "a.md"):
            (pages_root / name).write_text(f"---\ntitle: {name}\n---\nbody", encoding="utf-8")
        assert [page["name"] for page in load_pages(pages_root)] == ["a.md", "b.md"]

    def test_load_pages__skips_unparseable_pages(self, pages_root):
        (pages_root / "good.md").write_text("---\ntitle: G\n---\nbody", encoding="utf-8")
        (pages_root / "bad.md").write_text("---\ntitle: [unclosed\n---\nbody", encoding="utf-8")
        assert [page["name"] for page in load_pages(pages_root)] == ["good.md"]

    def test_load_pages__missing_directory_is_empty(self, tmp_path):
        assert load_pages(tmp_path / "absent") == ()


class TestSearchPages:
    @pytest.fixture(autouse=True)
    def corpus(self, pages_root):
        (pages_root / "relay.md").write_text(
            "---\ntitle: Relay mode compute\ntags: [relays]\n---\nThe relay mode is computed on read.\n",
            encoding="utf-8",
        )
        (pages_root / "weather.md").write_text(
            "---\ntitle: Weather polling\ntags: [weather]\n---\nThe weather provider polls every thirty minutes.\n",
            encoding="utf-8",
        )

    def test_search_pages__ranks_the_relevant_page_first(self, pages_root):
        results = search_pages(pages_root=pages_root, query="relay mode", limit=5)
        assert results[0]["page"]["name"] == "relay.md"

    def test_search_pages__respects_the_limit(self, pages_root):
        assert len(search_pages(pages_root=pages_root, query="relay weather mode polling", limit=1)) == 1

    def test_search_pages__stop_word_only_query_matches_nothing(self, pages_root):
        assert search_pages(pages_root=pages_root, query="the of and", limit=5) == []

    def test_search_pages__unmatched_query_returns_empty(self, pages_root):
        assert search_pages(pages_root=pages_root, query="kubernetes", limit=5) == []

    def test_search_pages__results_carry_score_and_terms(self, pages_root):
        result = search_pages(pages_root=pages_root, query="relay", limit=1)[0]
        assert result["score"] > 0
        assert result["terms"] == ["relay"]


class TestCallTool:
    async def test_call_tool__list_pages(self, pages_root):
        (pages_root / "page.md").write_text("---\ntitle: T\n---\nbody", encoding="utf-8")
        result = await wiki_call_tool("wiki_list_pages", {})
        assert result.is_error is False
        assert "page.md" in result.content[0].text

    async def test_call_tool__list_pages_when_empty(self, pages_root):
        result = await wiki_call_tool("wiki_list_pages", {})
        assert result.content[0].text == "No wiki pages found"

    async def test_call_tool__get_page_returns_markdown(self, pages_root):
        (pages_root / "page.md").write_text("---\ntitle: T\n---\n# Heading", encoding="utf-8")
        result = await wiki_call_tool("wiki_get_page", {"name": "page.md"})
        assert result.is_error is False
        assert "# Heading" in result.content[0].text

    @pytest.mark.parametrize("arguments", [{"name": ""}, {"name": None}, {}])
    async def test_call_tool__get_page_requires_a_name(self, pages_root, arguments):
        result = await wiki_call_tool("wiki_get_page", arguments)
        assert result.is_error is True
        assert "name is required" in result.content[0].text

    async def test_call_tool__get_page_rejects_traversal(self, pages_root):
        result = await wiki_call_tool("wiki_get_page", {"name": "../../../etc/passwd"})
        assert result.is_error is True
        assert "outside wiki directory" in result.content[0].text

    @pytest.mark.parametrize("arguments", [{}, {"query": ""}])
    async def test_call_tool__search_requires_a_query(self, pages_root, arguments):
        result = await wiki_call_tool("wiki_search", arguments)
        assert result.is_error is True
        assert "query is required" in result.content[0].text

    async def test_call_tool__search_rejects_a_non_string_query(self, pages_root):
        result = await wiki_call_tool("wiki_search", {"query": 42})
        assert result.is_error is True
        assert "must be a string" in result.content[0].text

    async def test_call_tool__search_rejects_an_overlong_query(self, pages_root):
        result = await wiki_call_tool("wiki_search", {"query": "x" * 501})
        assert result.is_error is True
        assert "exceeds maximum length" in result.content[0].text

    async def test_call_tool__search_with_no_match_is_not_an_error(self, pages_root):
        result = await wiki_call_tool("wiki_search", {"query": "kubernetes"})
        assert result.is_error is False
        assert "No matching wiki pages" in result.content[0].text

    async def test_call_tool__unknown_tool(self, pages_root):
        result = await wiki_call_tool("wiki_nope", {})
        assert result.is_error is True
        assert "Unknown tool" in result.content[0].text

    async def test_call_tool__missing_pages_directory(self, tmp_path, monkeypatch):
        monkeypatch.setattr("mcp_server.tools.wiki.PAGES_ROOT", tmp_path / "absent")
        result = await wiki_call_tool("wiki_list_pages", {})
        assert result.is_error is True
        assert "not found" in result.content[0].text
