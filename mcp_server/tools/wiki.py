import logging
import re
from pathlib import Path
from typing import Any

import yaml
from mcp.types import TextContent, Tool

from mcp_server.config import PAGES_ROOT, SEARCH
from mcp_server.corpus import CorpusCache, rank
from mcp_server.models import Field, FieldCounts, ToolResult
from mcp_server.tools.search import count_field, line_hits, tokenize
from mcp_server.utils import resolve_limit


logger = logging.getLogger(__name__)

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
BARE_DASH_RE = re.compile(r"^(\s*[A-Za-z_][\w]*\s*:\s*)-$", re.MULTILINE)

WIKI_FIELDS = (
    Field(weight=SEARCH["wiki_title_boost"], length_norm=SEARCH["wiki_title_length_norm"]),
    Field(weight=SEARCH["wiki_metadata_boost"], length_norm=SEARCH["wiki_metadata_length_norm"]),
    Field(weight=SEARCH["wiki_body_boost"], length_norm=SEARCH["wiki_body_length_norm"]),
)


def parse_page_file(path: Path) -> dict | None:
    """Parse a wiki page file into metadata and body content.

    Reads YAML frontmatter delimited by ``---`` lines; pages with invalid or
    non-mapping frontmatter are skipped with a warning.

    Args:
        path: Path of the ``.md`` page file.

    Returns:
        dict | None: A mapping with ``name``, ``meta`` and ``body`` keys, or
            None when the file cannot be read or its frontmatter parsed.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        logger.warning(f"Skipping unreadable page: {path.name}")
        return None

    meta: dict = {}
    body = text
    match = FRONTMATTER_RE.match(text)

    if match:
        block = BARE_DASH_RE.sub(r'\1"-"', match.group(1))
        try:
            parsed = yaml.safe_load(block)
        except yaml.YAMLError:
            logger.warning(f"Skipping page with invalid frontmatter: {path.name}")
            return None

        if parsed is not None and not isinstance(parsed, dict):
            logger.warning(f"Skipping page with non-mapping frontmatter: {path.name}")
            return None

        meta = parsed or {}
        body = text[match.end() :]

    return {"name": path.name, "meta": meta, "body": body}


def page_fields(page: dict[str, Any]) -> tuple[FieldCounts, ...]:
    """Count searchable tokens in a page's title, metadata and body zones.

    Args:
        page: The parsed wiki page.

    Returns:
        tuple[FieldCounts, ...]: Field counts aligned to ``WIKI_FIELDS``.
    """
    return (
        count_field(text=str(page["meta"].get("title") or "")),
        count_field(text=metadata_text(meta=page["meta"])),
        count_field(text=page["body"]),
    )


def _parse_pages(pages_root: Path) -> tuple[list[dict[str, Any]], list[tuple[FieldCounts, ...]]]:
    """Read and parse every wiki page in a directory, sorted by name.

    Args:
        pages_root: Directory containing ``*.md`` wiki page files.

    Returns:
        tuple: The parsed pages and their BM25 field counts, aligned by
            position.
    """
    paths = sorted(pages_root.glob("*.md")) if pages_root.is_dir() else []
    pages = [page for path in paths if (page := parse_page_file(path=path)) is not None]
    return pages, [page_fields(page=page) for page in pages]


PAGES = CorpusCache(WIKI_FIELDS, _parse_pages)


def load_pages(pages_root: Path) -> tuple[dict[str, Any], ...]:
    """Load all valid wiki pages from a directory, sorted by name.

    The parsed pages and their BM25 field counts are cached and rebuilt only
    when a page file is added, removed or otherwise changes its modification
    time or size, so repeated searches skip re-reading and re-tokenizing every
    page in the corpus.

    Args:
        pages_root: Directory containing ``*.md`` wiki page files.

    Returns:
        tuple[dict[str, Any], ...]: The parsed pages in sorted filename order.
    """
    return PAGES.get(pages_root).items


def resolve_page(pages_root: Path, name: str) -> Path | None:
    """Resolve a page name to a file path confined to the pages directory.

    Appends the ``.md`` suffix when needed and rejects any path that escapes
    the pages root.

    Args:
        pages_root: Directory containing the wiki page files.
        name: Page file name, with or without the ``.md`` suffix.

    Returns:
        Path | None: The resolved file path if the page exists, otherwise
            None.
    """
    slug = name.strip().removeprefix("pages/")
    if not slug.endswith(".md"):
        slug = f"{slug}.md"
    target = (pages_root / slug).resolve()

    try:
        target.relative_to(pages_root)
    except ValueError:
        return None
    return target if target.is_file() else None


def metadata_text(meta: dict[str, Any]) -> str:
    """Flatten searchable frontmatter fields into a lowercase string.

    Combines tags, services, areas, tickets and type values for scoring.

    Args:
        meta: The page frontmatter mapping.

    Returns:
        str: A space-joined lowercase string of metadata values.
    """
    parts = []
    for key in ("tags", "services", "areas", "tickets", "type"):
        value = meta.get(key)
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif value:
            parts.append(str(value))
    return " ".join(parts).lower()


def extract_snippets(body: str, terms: list[str]) -> list[str]:
    """Pick the most relevant line snippets from a page body.

    Lines are scored by how many distinct query terms they contain as whole
    tokens, capped at the configured maximum, and returned in line-number order
    with a length cap per snippet.

    Args:
        body: The page body text.
        terms: The search terms to match against lines.

    Returns:
        list[str]: Snippet lines prefixed with their line number.
    """
    scored: list[tuple[int, int, str]] = []
    for lineno, line in enumerate(body.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        hits = line_hits(line=stripped, terms=terms)
        if hits:
            scored.append((-hits, lineno, stripped))

    scored.sort(key=lambda item: item[0])
    top = scored[: SEARCH["max_snippets"]]
    top.sort(key=lambda item: item[1])
    return [f"L{lineno}: {text[: SEARCH['snippet_length']]}" for _, lineno, text in top]


def search_pages(pages_root: Path, query: str, limit: int) -> list[dict[str, Any]]:
    """Search the wiki pages and return the top matches for a query.

    Pages are ranked with BM25F across the title, metadata and body fields, so
    rare terms outweigh common ones and a long page cannot win on bulk alone.

    Args:
        pages_root: Directory containing the wiki page files.
        query: The raw search query.
        limit: Maximum number of results to return.

    Returns:
        list[dict[str, Any]]: Ranked results, each holding ``page``, ``score``
            and ``terms``, or an empty list when the query has no terms.
    """
    terms = tokenize(query=query)
    if not terms:
        return []

    corpus = PAGES.get(pages_root)
    hits = rank(corpus, fields=WIKI_FIELDS, terms=terms)
    hits.sort(key=lambda hit: (-hit.score, hit.item["name"]))
    return [{"page": hit.item, "score": hit.score, "terms": list(hit.terms)} for hit in hits[:limit]]


def summarize_meta(meta: dict[str, Any]) -> str:
    """Render the key frontmatter fields of a page as a readable summary.

    Args:
        meta: The page frontmatter mapping.

    Returns:
        str: A comma-joined summary of type, date, status and list fields.
    """
    parts = [
        f"type: {meta.get('type') or '-'}",
        f"date: {meta.get('date') or '-'}",
        f"status: {meta.get('status') or '-'}",
    ]
    for key in ("services", "areas", "tags", "tickets"):
        value = meta.get(key)
        if isinstance(value, list) and value:
            parts.append(f"{key}: {', '.join(str(item) for item in value)}")
        elif value:
            parts.append(f"{key}: {value}")
    return ", ".join(parts)


def page_title(page: dict[str, Any]) -> str:
    """Return the display title of a page, falling back to its filename.

    Args:
        page: The parsed wiki page.

    Returns:
        str: The frontmatter title, or the page file name when absent.
    """
    return str(page["meta"].get("title") or page["name"])


AVAILABLE_TOOLS = [
    Tool(
        name="wiki_search",
        description=(
            "Search the project wiki of past debugging sessions, investigations, code reviews, and "
            "implementation notes. Consult this BEFORE answering questions about why something works "
            "the way it does, past decisions, or prior incidents. Returns ranked page names with "
            "snippets; fetch a full page with wiki_get_page."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query (keywords or a question)"},
                "limit": {
                    "type": "integer",
                    "description": (f"Max results (default {SEARCH['default_limit']}, max {SEARCH['max_results']})"),
                },
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="wiki_get_page",
        description=(
            "Get the full Markdown content of a single wiki page by its file name, as returned by "
            "wiki_search or wiki_list_pages."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Page file name, e.g. 2026-08-03-fix-mcp-server-2.0-api.md",
                },
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="wiki_list_pages",
        description=(
            "List all project wiki pages with their metadata (title, type, date, status, services, "
            "areas, tags, tickets) without reading page bodies."
        ),
        input_schema={
            "type": "object",
            "properties": {},
        },
    ),
]


async def list_tools() -> list[Tool]:
    """Return the wiki MCP tool definitions.

    Returns:
        list[Tool]: The static list of available wiki tools.
    """
    return AVAILABLE_TOOLS


def _format_search_results(results: list[dict[str, Any]]) -> str:
    """Format ranked search results into a readable text block.

    Args:
        results: The ranked search results from ``_search_pages``.

    Returns:
        str: A numbered, snippet-bearing summary of each result.
    """
    blocks = []
    for position, result in enumerate(results, start=1):
        page = result["page"]
        snippets = extract_snippets(page["body"], result["terms"])
        snippet_lines = "\n".join(f"   > {snippet}" for snippet in snippets)
        blocks.append(
            f"{position}. {page['name']} (score {result['score']:.3f})\n"
            f"   {page_title(page)} — {summarize_meta(page['meta'])}\n"
            f"{snippet_lines}"
        )
    return "\n\n".join(blocks)


async def call_tool(name: str, arguments: dict | None) -> ToolResult:
    """Dispatch a wiki MCP tool call by name.

    Supports listing, searching and fetching wiki pages, wrapping both
    results and errors into a ToolResult.

    Args:
        name: The name of the wiki tool to invoke.
        arguments: Optional tool arguments as a mapping.

    Returns:
        ToolResult: The tool output, or an error result on failure.
    """
    args = arguments or {}
    try:
        if not PAGES_ROOT.is_dir():
            return ToolResult(
                content=[TextContent(type="text", text="Wiki pages directory not found")],
                is_error=True,
            )

        if name == "wiki_list_pages":
            pages = load_pages(PAGES_ROOT)
            if not pages:
                return ToolResult(content=[TextContent(type="text", text="No wiki pages found")])
            lines = [f"{page['name']} — {page_title(page)} ({summarize_meta(page['meta'])})" for page in pages]
            return ToolResult(content=[TextContent(type="text", text="\n".join(lines))])

        if name == "wiki_search":
            query = args.get("query")
            if not query:
                return ToolResult(
                    content=[TextContent(type="text", text="Error: query is required")],
                    is_error=True,
                )
            if not isinstance(query, str):
                return ToolResult(
                    content=[TextContent(type="text", text="Error: query must be a string")],
                    is_error=True,
                )
            if len(query) > SEARCH["max_query_length"]:
                return ToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"Error: query exceeds maximum length of {SEARCH['max_query_length']} characters",
                        )
                    ],
                    is_error=True,
                )
            limit = resolve_limit(args)
            results = search_pages(pages_root=PAGES_ROOT, query=query, limit=limit)
            if not results:
                return ToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text="No matching wiki pages. Try wiki_list_pages to browse the catalog.",
                        )
                    ]
                )
            return ToolResult(content=[TextContent(type="text", text=_format_search_results(results))])

        if name == "wiki_get_page":
            page_name = args.get("name")
            if not page_name:
                return ToolResult(
                    content=[TextContent(type="text", text="Error: name is required")],
                    is_error=True,
                )
            resolved = resolve_page(pages_root=PAGES_ROOT, name=page_name)
            if resolved is None:
                return ToolResult(
                    content=[
                        TextContent(
                            type="text",
                            text=f"Error: page not found or path outside wiki directory: {page_name}",
                        )
                    ],
                    is_error=True,
                )
            return ToolResult(content=[TextContent(type="text", text=resolved.read_text(encoding="utf-8"))])

        return ToolResult(
            content=[TextContent(type="text", text=f"Error: Unknown tool {name}")],
            is_error=True,
        )
    except Exception:
        logger.exception(f"Error executing tool {name}")
        return ToolResult(
            content=[TextContent(type="text", text="Error: Wiki operation failed")],
            is_error=True,
        )
