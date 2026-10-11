import pytest

from mcp_server.tools.search import (
    Field,
    build_stats,
    count_field,
    extract_terms,
    inverse_document_frequency,
    line_hits,
    score_document,
    tokenize,
)


FIELDS = (Field(weight=1.0, length_norm=0.0), Field(weight=1.0, length_norm=0.75))


class TestTokenize:
    def test_extract_terms__lowercases_and_splits(self):
        assert extract_terms("Relay MODE Compute") == ["relay", "mode", "compute"]

    def test_extract_terms__drops_stop_words(self):
        assert extract_terms("what is the relay mode") == ["relay", "mode"]

    def test_extract_terms__drops_short_tokens(self):
        assert extract_terms("a bc relay") == ["bc", "relay"]

    def test_extract_terms__keeps_dots_and_underscores(self):
        assert extract_terms("Relay.get_target_state") == ["relay.get_target_state"]

    def test_tokenize__empty_input_yields_no_terms(self):
        assert tokenize("") == []
        assert tokenize("the of and") == []


class TestCountField:
    def test_count_field__counts_occurrences_and_total_length(self):
        counts = count_field("relay relay mode")
        assert counts.counts["relay"] == 2
        assert counts.length == 3

    def test_count_field__empty_text_is_zero_length(self):
        assert count_field("").length == 0


class TestScoring:
    @staticmethod
    def _corpus(documents):
        return build_stats(fields=FIELDS, documents=documents)

    def test_build_stats__empty_corpus_has_zero_document_count(self):
        stats = self._corpus([])
        assert stats.document_count == 0
        assert stats.average_lengths == (0.0, 0.0)

    def test_build_stats__averages_field_lengths(self):
        stats = self._corpus(
            [(count_field("relay mode"), count_field("relay")), (count_field("pump"), count_field("pump mode"))]
        )
        assert stats.document_count == 2
        assert stats.average_lengths == (1.5, 1.5)

    def test_build_stats__a_term_counts_once_per_document(self):
        stats = self._corpus(
            [(count_field("relay"), count_field("relay")), (count_field("relay"), count_field("pump"))]
        )
        assert stats.document_frequency["relay"] == 2
        assert stats.document_frequency["pump"] == 1

    def test_inverse_document_frequency__is_positive_for_a_universal_term(self):
        assert inverse_document_frequency(document_frequency=5, document_count=5) > 0

    def test_inverse_document_frequency__rarer_terms_score_higher(self):
        rare = inverse_document_frequency(document_frequency=1, document_count=10)
        common = inverse_document_frequency(document_frequency=9, document_count=10)
        assert rare > common

    def test_score_document__empty_corpus_scores_zero(self):
        stats = self._corpus([])
        assert (
            score_document(
                fields=FIELDS, document=(count_field("relay"), count_field("relay")), stats=stats, terms=["relay"]
            )
            == 0.0
        )

    def test_score_document__matching_document_outscores_non_matching(self):
        documents = [
            (count_field("relay mode"), count_field("relay mode")),
            (count_field("weather"), count_field("weather")),
        ]
        stats = self._corpus(documents)
        match = score_document(fields=FIELDS, document=documents[0], stats=stats, terms=["relay"])
        miss = score_document(fields=FIELDS, document=documents[1], stats=stats, terms=["relay"])
        assert match > 0
        assert miss == 0.0

    def test_score_document__repeated_terms_in_one_term_do_not_double_count(self):
        documents = [(count_field("relay relay"), count_field("relay"))]
        stats = self._corpus(documents)
        once = score_document(fields=FIELDS, document=documents[0], stats=stats, terms=["relay"])
        twice = score_document(fields=FIELDS, document=documents[0], stats=stats, terms=["relay", "relay"])
        assert once == twice


class TestLineHits:
    def test_line_hits__counts_distinct_matching_terms(self):
        assert line_hits("relay mode compute", ["relay", "mode"]) == 2

    def test_line_hits__matches_whole_tokens_only(self):
        assert line_hits("relayed", ["relay"]) == 0

    def test_line_hits__no_terms_no_hits(self):
        assert line_hits("relay", []) == 0


class TestFieldStats:
    @pytest.mark.parametrize("weight,length_norm", [(10.0, 0.0), (1.0, 0.75), (5.0, 1.0)])
    def test_field__stores_its_scoring_parameters(self, weight, length_norm):
        field = Field(weight=weight, length_norm=length_norm)
        assert (field.weight, field.length_norm) == (weight, length_norm)
