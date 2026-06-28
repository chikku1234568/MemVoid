from __future__ import annotations

from unittest.mock import MagicMock, patch

from mem_void.graph.client import Neo4jClient
from mem_void.models.fact import Fact
from mem_void.resolution.fact_resolver import FactResolver


class TestFactResolverUnit:
    """Unit tests for FactResolver — all Neo4j calls mocked."""

    def test_exclusive_predicate_closes_old_facts(self) -> None:
        client = MagicMock(spec=Neo4jClient)
        fact = Fact(subject="Alice", predicate="WORKS_AT", object="OpenAI")

        with (
            patch("mem_void.resolution.fact_resolver.close_active_facts") as mock_close,
            patch("mem_void.resolution.fact_resolver.create_fact") as mock_create,
        ):
            resolver = FactResolver(client)
            result = resolver.resolve(fact)

        assert result is fact
        mock_close.assert_called_once_with(client, "Alice", "WORKS_AT", fact.valid_from)
        mock_create.assert_called_once_with(client, fact)

    def test_additive_predicate_does_not_close_old_facts(self) -> None:
        client = MagicMock(spec=Neo4jClient)
        fact = Fact(subject="Alice", predicate="WORKS_ON", object="Titan")

        with (
            patch("mem_void.resolution.fact_resolver.close_active_facts") as mock_close,
            patch("mem_void.resolution.fact_resolver.create_fact") as mock_create,
        ):
            resolver = FactResolver(client)
            result = resolver.resolve(fact)

        assert result is fact
        mock_close.assert_not_called()
        mock_create.assert_called_once_with(client, fact)

    def test_unknown_predicate_treated_as_additive(self) -> None:
        client = MagicMock(spec=Neo4jClient)
        fact = Fact(subject="Alice", predicate="CUSTOM_PRED", object="Something")

        with (
            patch("mem_void.resolution.fact_resolver.close_active_facts") as mock_close,
            patch("mem_void.resolution.fact_resolver.create_fact") as mock_create,
        ):
            resolver = FactResolver(client)
            resolver.resolve(fact)

        mock_close.assert_not_called()
        mock_create.assert_called_once_with(client, fact)

    def test_multiple_exclusive_facts_close_previous(self) -> None:
        client = MagicMock(spec=Neo4jClient)
        fact1 = Fact(subject="Alice", predicate="LIVES_IN", object="SF")
        fact2 = Fact(subject="Alice", predicate="LIVES_IN", object="NYC")

        with (
            patch("mem_void.resolution.fact_resolver.close_active_facts") as mock_close,
            patch("mem_void.resolution.fact_resolver.create_fact") as mock_create,
        ):
            resolver = FactResolver(client)
            resolver.resolve(fact1)
            resolver.resolve(fact2)

        assert mock_close.call_count == 2
        assert mock_create.call_count == 2

    def test_all_exclusive_predicates_trigger_close(self) -> None:
        client = MagicMock(spec=Neo4jClient)
        exclusive = ["WORKS_AT", "LIVES_IN", "LOCATED_IN", "REPORTS_TO", "HAS_TITLE", "HEADQUARTERED_IN"]

        for pred in exclusive:
            with (
                patch("mem_void.resolution.fact_resolver.close_active_facts") as mock_close,
                patch("mem_void.resolution.fact_resolver.create_fact") as mock_create,
            ):
                resolver = FactResolver(client)
                fact = Fact(subject="X", predicate=pred, object="Y")
                resolver.resolve(fact)

            mock_close.assert_called_once()

    def test_all_additive_predicates_do_not_close(self) -> None:
        client = MagicMock(spec=Neo4jClient)
        additive = ["WORKS_ON", "KNOWS", "USES", "LIKES", "HAS_SKILL", "ATTENDED"]

        for pred in additive:
            with (
                patch("mem_void.resolution.fact_resolver.close_active_facts") as mock_close,
                patch("mem_void.resolution.fact_resolver.create_fact") as mock_create,
            ):
                resolver = FactResolver(client)
                fact = Fact(subject="X", predicate=pred, object="Y")
                resolver.resolve(fact)

            mock_close.assert_not_called()
