from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypedDict

from mcp.types import TextContent


@dataclass
class ToolResult:
    content: list[TextContent]
    is_error: bool = False


@dataclass(frozen=True)
class DocumentedFunction:
    qualified_name: str
    path: str
    line: int
    docstring: str


@dataclass(frozen=True)
class Field:
    """Describe one searchable zone of a document and how BM25 scores it.

    Attributes:
        weight: Boost applied to the field's term frequency before saturation.
        length_norm: Strength of length normalization, from 0 (off) to 1 (full).
    """

    weight: float
    length_norm: float


@dataclass(frozen=True)
class FieldCounts:
    """Hold per-term token counts and the token length of one document field.

    Attributes:
        counts: Mapping of term to its occurrence count in the field.
        length: Total token count, retained so scoring never re-walks the text.
    """

    counts: Mapping[str, int]
    length: int


@dataclass(frozen=True)
class CorpusStats:
    """Hold corpus-wide BM25 statistics shared by every document.

    Attributes:
        document_count: Number of documents in the corpus.
        average_lengths: Mean token length per field, aligned with the field
            order the caller scores in.
        document_frequency: Mapping of term to the number of documents
            containing it.
    """

    document_count: int
    average_lengths: tuple[float, ...]
    document_frequency: Mapping[str, int]


class SearchConfig(TypedDict):
    """Tunables for the BM25F analyzer shared by the docstring and wiki tools."""

    default_limit: int
    max_results: int
    max_query_length: int
    max_snippets: int
    snippet_length: int
    min_term_length: int
    term_pattern: str
    bm25_k1: float
    wiki_title_boost: float
    wiki_title_length_norm: float
    wiki_metadata_boost: float
    wiki_metadata_length_norm: float
    wiki_body_boost: float
    wiki_body_length_norm: float
    docstring_name_boost: float
    docstring_name_length_norm: float
    docstring_path_boost: float
    docstring_path_length_norm: float
    docstring_text_boost: float
    docstring_text_length_norm: float
