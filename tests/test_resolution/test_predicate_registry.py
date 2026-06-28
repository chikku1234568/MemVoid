from __future__ import annotations

from mem_void.resolution.predicate_registry import (
    EXCLUSIVE_PREDICATES,
    ADDITIVE_PREDICATES,
    is_additive,
    is_exclusive,
)


class TestPredicateRegistry:
    def test_exclusive_predicates(self) -> None:
        for pred in ["WORKS_AT", "LIVES_IN", "LOCATED_IN", "REPORTS_TO", "HAS_TITLE", "HEADQUARTERED_IN"]:
            assert is_exclusive(pred) is True
            assert is_additive(pred) is False

    def test_additive_predicates(self) -> None:
        for pred in ["WORKS_ON", "KNOWS", "USES", "LIKES", "HAS_SKILL", "ATTENDED"]:
            assert is_exclusive(pred) is False
            assert is_additive(pred) is True

    def test_unknown_predicate_defaults_to_additive(self) -> None:
        assert is_exclusive("CUSTOM_PREDICATE") is False
        assert is_additive("CUSTOM_PREDICATE") is True

    def test_no_overlap_between_sets(self) -> None:
        overlap = EXCLUSIVE_PREDICATES & ADDITIVE_PREDICATES
        assert overlap == set()
