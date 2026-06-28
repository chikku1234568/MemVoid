from __future__ import annotations

from datetime import datetime, timezone

from mem_void.graph.client import Neo4jClient
from mem_void.graph.repository import upsert_entity
from mem_void.graph.schema import ensure_schema
from mem_void.models import Entity, Fact
from mem_void.resolution.fact_resolver import FactResolver
from mem_void.retrieval.graph_traversal import related_entities
from mem_void.retrieval.temporal import facts_at_time, facts_in_range


class TestRelatedEntities:
    def test_returns_connected_entities(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        upsert_entity(neo4j_client, Entity(name="Alice", entity_type="PERSON"))
        upsert_entity(neo4j_client, Entity(name="Acme", entity_type="ORG"))
        upsert_entity(neo4j_client, Entity(name="Phoenix", entity_type="PROJECT"))

        resolver = FactResolver(neo4j_client)
        resolver.resolve(Fact(subject="Alice", predicate="WORKS_AT", object="Acme"))
        resolver.resolve(Fact(subject="Alice", predicate="WORKS_ON", object="Phoenix"))

        result = related_entities(neo4j_client, "Alice")

        assert len(result) == 2
        entities = {(r["entity"], r["predicate"]) for r in result}
        assert ("Acme", "WORKS_AT") in entities
        assert ("Phoenix", "WORKS_ON") in entities

    def test_excludes_closed_facts_when_active_only(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        upsert_entity(neo4j_client, Entity(name="Alice", entity_type="PERSON"))
        upsert_entity(neo4j_client, Entity(name="Acme", entity_type="ORG"))
        upsert_entity(neo4j_client, Entity(name="OpenAI", entity_type="ORG"))

        resolver = FactResolver(neo4j_client)
        resolver.resolve(Fact(subject="Alice", predicate="WORKS_AT", object="Acme"))
        resolver.resolve(Fact(subject="Alice", predicate="WORKS_AT", object="OpenAI"))

        result = related_entities(neo4j_client, "Alice", active_only=True)

        assert len(result) == 1
        assert result[0]["entity"] == "OpenAI"

    def test_includes_closed_facts_when_active_only_false(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        upsert_entity(neo4j_client, Entity(name="Alice", entity_type="PERSON"))
        upsert_entity(neo4j_client, Entity(name="Acme", entity_type="ORG"))
        upsert_entity(neo4j_client, Entity(name="OpenAI", entity_type="ORG"))

        resolver = FactResolver(neo4j_client)
        resolver.resolve(Fact(subject="Alice", predicate="WORKS_AT", object="Acme"))
        resolver.resolve(Fact(subject="Alice", predicate="WORKS_AT", object="OpenAI"))

        result = related_entities(neo4j_client, "Alice", active_only=False)

        assert len(result) == 2
        entities = {r["entity"] for r in result}
        assert entities == {"Acme", "OpenAI"}

    def test_returns_empty_for_unknown_entity(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        result = related_entities(neo4j_client, "NoSuchEntity")
        assert result == []


class TestFactsAtTime:
    def test_returns_facts_active_at_point(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        upsert_entity(neo4j_client, Entity(name="Alice", entity_type="PERSON"))
        upsert_entity(neo4j_client, Entity(name="Acme", entity_type="ORG"))
        upsert_entity(neo4j_client, Entity(name="OpenAI", entity_type="ORG"))

        resolver = FactResolver(neo4j_client)
        resolver.resolve(Fact(
            subject="Alice", predicate="WORKS_AT", object="Acme",
            valid_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
        ))
        resolver.resolve(Fact(
            subject="Alice", predicate="WORKS_AT", object="OpenAI",
            valid_from=datetime(2024, 6, 1, tzinfo=timezone.utc),
        ))

        # February 2024: Alice was at Acme
        feb = datetime(2024, 2, 15, tzinfo=timezone.utc)
        result = facts_at_time(neo4j_client, "Alice", feb, predicate="WORKS_AT")
        assert len(result) == 1
        assert result[0].object == "Acme"

        # July 2024: Alice is at OpenAI
        jul = datetime(2024, 7, 15, tzinfo=timezone.utc)
        result = facts_at_time(neo4j_client, "Alice", jul, predicate="WORKS_AT")
        assert len(result) == 1
        assert result[0].object == "OpenAI"

    def test_returns_empty_when_no_facts_at_time(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        upsert_entity(neo4j_client, Entity(name="Alice", entity_type="PERSON"))

        dt = datetime(2020, 1, 1, tzinfo=timezone.utc)
        result = facts_at_time(neo4j_client, "Alice", dt)
        assert result == []


class TestFactsInRange:
    def test_returns_facts_overlapping_range(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        upsert_entity(neo4j_client, Entity(name="Alice", entity_type="PERSON"))
        upsert_entity(neo4j_client, Entity(name="Acme", entity_type="ORG"))
        upsert_entity(neo4j_client, Entity(name="OpenAI", entity_type="ORG"))

        resolver = FactResolver(neo4j_client)
        resolver.resolve(Fact(
            subject="Alice", predicate="WORKS_AT", object="Acme",
            valid_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
        ))
        resolver.resolve(Fact(
            subject="Alice", predicate="WORKS_AT", object="OpenAI",
            valid_from=datetime(2024, 6, 1, tzinfo=timezone.utc),
        ))

        # Q1 2024: only Acme was active
        result = facts_in_range(
            neo4j_client, "Alice",
            datetime(2024, 1, 1, tzinfo=timezone.utc),
            datetime(2024, 3, 31, tzinfo=timezone.utc),
            predicate="WORKS_AT",
        )
        assert len(result) == 1
        assert result[0].object == "Acme"

        # Full year 2024: both Acme and OpenAI overlap
        result = facts_in_range(
            neo4j_client, "Alice",
            datetime(2024, 1, 1, tzinfo=timezone.utc),
            datetime(2024, 12, 31, tzinfo=timezone.utc),
            predicate="WORKS_AT",
        )
        assert len(result) == 2
        objects = {f.object for f in result}
        assert objects == {"Acme", "OpenAI"}
