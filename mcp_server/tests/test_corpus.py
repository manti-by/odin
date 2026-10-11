"""Tests for the corpus snapshot and its cache.

The cache replaced five loosely-coupled module globals. These tests pin the two
properties that motivated the change: a caller cannot write through what it was
handed, and a reader can never observe a corpus whose items, field counts and
statistics come from different generations of files.
"""

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from mcp_server.corpus import CorpusCache, fingerprint_directory, fingerprint_pages, rank
from mcp_server.models import Field
from mcp_server.tools.search import count_field


FIELDS = (Field(weight=1.0, length_norm=0.0), Field(weight=1.0, length_norm=0.75))


def _parse(root: Path):
    """Fake parser: one entry per ``*.md`` file, two field counts each."""
    items = sorted(p.name for p in root.glob("*.md")) if root.is_dir() else []
    return items, [(count_field(item), count_field(item)) for item in items]


@pytest.fixture
def corpus_root(tmp_path):
    root = tmp_path / "pages"
    root.mkdir()
    for name in ("a.md", "b.md"):
        (root / name).write_text(f"---\ntitle: {name}\n---\nbody of {name}", encoding="utf-8")
    return root


class TestFingerprints:
    def test_fingerprint_pages__describes_each_file(self, corpus_root):
        fingerprint = fingerprint_pages(corpus_root)
        assert [name for name, _, _ in fingerprint] == ["a.md", "b.md"]

    def test_fingerprint_pages__changes_when_a_file_changes(self, corpus_root):
        before = fingerprint_pages(corpus_root)
        (corpus_root / "a.md").write_text("changed content", encoding="utf-8")
        assert fingerprint_pages(corpus_root) != before

    def test_fingerprint_pages__missing_directory_is_empty(self, tmp_path):
        assert fingerprint_pages(tmp_path / "absent") == ()

    def test_fingerprint_directory__is_recursive_and_skips_pycache(self, tmp_path):
        (tmp_path / "pkg" / "__pycache__").mkdir(parents=True)
        (tmp_path / "pkg" / "core.py").write_text("x = 1", encoding="utf-8")
        (tmp_path / "pkg" / "__pycache__" / "core.pyc").write_bytes(b"\x00")
        assert [name for name, _, _ in fingerprint_directory(tmp_path)] == ["pkg/core.py"]


class TestCorpusImmutability:
    def test_corpus__is_frozen(self, corpus_root):
        corpus = CorpusCache(FIELDS, _parse).get(corpus_root)
        with pytest.raises(FrozenInstanceError):
            corpus.items = ()

    def test_corpus__items_are_a_tuple_so_callers_cannot_mutate_it(self, corpus_root):
        cache = CorpusCache(FIELDS, _parse)
        corpus = cache.get(corpus_root)
        assert isinstance(corpus.items, tuple)

    def test_corpus__caller_mutation_does_not_persist(self, corpus_root):
        """The old cache handed out the live list; a caller could poison it."""
        cache = CorpusCache(FIELDS, _parse)
        first = cache.get(corpus_root)
        assert first.items == ("a.md", "b.md")
        # Anything a caller can reach through the snapshot is immutable.
        with pytest.raises(AttributeError):
            first.items.append("ghost.md")
        assert cache.get(corpus_root).items == ("a.md", "b.md")


class TestCorpusCache:
    def test_cache__parses_on_first_read(self, corpus_root):
        cache = CorpusCache(FIELDS, _parse)
        assert cache.get(corpus_root).items == ("a.md", "b.md")

    def test_cache__reuses_the_snapshot_while_files_are_unchanged(self, corpus_root):
        cache = CorpusCache(FIELDS, _parse)
        assert cache.get(corpus_root) is cache.get(corpus_root)

    def test_cache__rebuilds_when_a_file_changes(self, corpus_root):
        cache = CorpusCache(FIELDS, _parse)
        first = cache.get(corpus_root)
        (corpus_root / "c.md").write_text("---\ntitle: c\n---\nbody", encoding="utf-8")
        assert cache.get(corpus_root).items != first.items

    def test_cache__rebuilds_when_a_file_is_removed(self, corpus_root):
        cache = CorpusCache(FIELDS, _parse)
        cache.get(corpus_root)
        (corpus_root / "a.md").unlink()
        assert cache.get(corpus_root).items == ("b.md",)

    def test_cache__different_roots_do_not_share_a_snapshot(self, corpus_root, tmp_path):
        other = tmp_path / "other"
        other.mkdir()
        (other / "z.md").write_text("---\ntitle: z\n---\nbody", encoding="utf-8")

        cache = CorpusCache(FIELDS, _parse)
        assert cache.get(corpus_root).items == ("a.md", "b.md")
        assert cache.get(other).items == ("z.md",)

    def test_cache__clear_forces_a_rebuild(self, corpus_root):
        cache = CorpusCache(FIELDS, _parse)
        first = cache.get(corpus_root)
        cache.clear()
        assert cache.get(corpus_root) is not first

    def test_cache__missing_root_yields_an_empty_corpus(self, tmp_path):
        corpus = CorpusCache(FIELDS, _parse).get(tmp_path / "absent")
        assert corpus.items == ()
        assert corpus.stats.document_count == 0


class TestConsistency:
    def test_corpus__items_documents_and_stats_agree(self, corpus_root):
        """The property that the five separate globals could not guarantee."""
        corpus = CorpusCache(FIELDS, _parse).get(corpus_root)
        assert len(corpus.items) == len(corpus.documents)
        assert corpus.stats.document_count == len(corpus.items)
        assert corpus.stats.average_lengths == (1.0, 1.0)

    def test_corpus__a_stale_snapshot_is_never_returned_after_a_change(self, corpus_root):
        cache = CorpusCache(FIELDS, _parse)
        stale = cache.get(corpus_root)
        (corpus_root / "a.md").write_text("---\ntitle: new\n---\nnew body", encoding="utf-8")

        fresh = cache.get(corpus_root)
        assert fresh is not stale
        assert len(fresh.items) == len(fresh.documents)
        assert fresh.stats.document_count == len(fresh.items)


class TestRank:
    def test_rank__scores_matching_entries(self, corpus_root):
        corpus = CorpusCache(FIELDS, _parse).get(corpus_root)
        assert [hit.item for hit in rank(corpus, FIELDS, ["a.md"])] == ["a.md"]

    def test_rank__no_terms_yields_nothing(self, corpus_root):
        corpus = CorpusCache(FIELDS, _parse).get(corpus_root)
        assert rank(corpus, FIELDS, []) == []

    def test_rank__empty_corpus_yields_nothing(self, tmp_path):
        corpus = CorpusCache(FIELDS, _parse).get(tmp_path / "absent")
        assert rank(corpus, FIELDS, ["relay"]) == []

    def test_rank__results_carry_the_query_terms(self, corpus_root):
        corpus = CorpusCache(FIELDS, _parse).get(corpus_root)
        assert rank(corpus, FIELDS, ["a.md", "b.md"])[0].terms == ("a.md", "b.md")

    def test_rank__orders_by_descending_score(self, corpus_root):
        corpus = CorpusCache(FIELDS, _parse).get(corpus_root)
        scores = [hit.score for hit in rank(corpus, FIELDS, ["a.md", "b.md"])]
        assert scores == sorted(scores, reverse=True)
