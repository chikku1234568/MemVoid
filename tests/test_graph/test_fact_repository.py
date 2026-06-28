from __future__ import annotations

from datetime import datetime, timezone

import pytest

from mem_void.graph.client import Neo4jClient
from mem_void.graph.repository import (
    create_fact,
    current_facts,
    fact_history,
    upsert_entity,
)
from mem_void.graph.schema import ensure_schema
from mem_void.models import Entity, Fact


class TestCreateFact:
    def test_creates_relationship(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        upsert_entity(neo4j_client, Entity(name="Alice", entity_type="PERSON"))
        upsert_entity(neo4j_client, Entity(name="Acme", entity_type="ORG"))

        fact = Fact(subject="Alice", predicate="WORKS_AT", object="Acme")
        create_fact(neo4j_client, fact)

        # Verify relationship exists in Neo4j
        with neo4j_client.session() as session:
            result = session.run(
                """
                MATCH (a:Entity {name: 'Alice'})-[r:WORKS_AT]->(e:Entity {name: 'Acme'})
                RETURN r.uuid AS uuid, r.valid_from AS valid_from, r.valid_to AS valid_to
                """
            )
            record = result.single()
        assert record is not None
        assert record["valid_to"] is None

    def test_creates_multiple_facts_same_subject(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        upsert_entity(neo4j_client, Entity(name="Alice", entity_type="PERSON"))
        upsert_entity(neo4j_client, Entity(name="Acme", entity_type="ORG"))
        upsert_entity(neo4j_client, Entity(name="Phoenix", entity_type="PROJECT"))

        create_fact(neo4j_client, Fact(subject="Alice", predicate="WORKS_AT", object="Acme"))
        create_fact(neo4j_client, Fact(subject="Alice", predicate="WORKS_ON", object="Phoenix"))

        facts = current_facts(neo4j_client, "Alice")
        predicates = {f.predicate: f.object for f in facts}
        assert predicates == {"WORKS_AT": "Acme", "WORKS_ON": "Phoenix"}

    def test_creates_multiple_facts_additive_predicate(self, neo4j_client: Neo4jClient) -> None:
        """No invalidation yet — both facts for same predicate coexist."""
        ensure_schema(neo4j_client)
        upsert_entity(neo4j_client, Entity(name="Alice", entity_type="PERSON"))
        upsert_entity(neo4j_client, Entity(name="Bob", entity_type="PERSON"))
        upsert_entity(neo4j_client, Entity(name="Carol", entity_type="PERSON"))

        create_fact(neo4j_client, Fact(subject="Alice", predicate="KNOWS", object="Bob"))
        create_fact(neo4j_client, Fact(subject="Alice", predicate="KNOWS", object="Carol"))

        facts = current_facts(neo4j_client, "Alice", predicate="KNOWS")
        assert len(facts) == 2
        objects = {f.object for f in facts}
        assert objects == {"Bob", "Carol"}

    def test_fails_if_subject_missing(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        upsert_entity(neo4j_client, Entity(name="Acme", entity_type="ORG"))

        fact = Fact(subject="NoSuchPerson", predicate="WORKS_AT", object="Acme")
        create_fact(neo4j_client, fact)

        # MATCH fails silently — no relationship created
        facts = current_facts(neo4j_client, "NoSuchPerson")
        assert facts == []

    def test_fails_if_object_missing(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        upsert_entity(neo4j_client, Entity(name="Alice", entity_type="PERSON"))

        fact = Fact(subject="Alice", predicate="WORKS_AT", object="NoSuchOrg")
        create_fact(neo4j_client, fact)

        facts = current_facts(neo4j_client, "Alice")
        assert facts == []


class TestCurrentFacts:
    def test_returns_active_facts_only(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        upsert_entity(neo4j_client, Entity(name="Alice", entity_type="PERSON"))
        upsert_entity(neo4j_client, Entity(name="Acme", entity_type="ORG"))
        upsert_entity(neo4j_client, Entity(name="OpenAI", entity_type="ORG"))

        start = datetime(2024, 1, 15, tzinfo=timezone.utc)
        end = datetime(2024, 6, 1, tzinfo=timezone.utc)

        create_fact(neo4j_client, Fact(subject="Alice", predicate="WORKS_AT", object="Acme", valid_from=start, valid_to=end))
        create_fact(neo4j_client, Fact(subject="Alice", predicate="WORKS_AT", object="OpenAI"))

        facts = current_facts(neo4j_client, "Alice")
        assert len(facts) == 1
        assert facts[0].object == "OpenAI"
        assert facts[0].is_active is True

    def test_returns_empty_for_no_facts(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        upsert_entity(neo4j_client, Entity(name="Alice", entity_type="PERSON"))

        facts = current_facts(neo4j_client, "Alice")
        assert facts == []

    def test_filters_by_predicate(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        upsert_entity(neo4j_client, Entity(name="Alice", entity_type="PERSON"))
        upsert_entity(neo4j_client, Entity(name="Acme", entity_type="ORG"))
        upsert_entity(neo4j_client, Entity(name="Phoenix", entity_type="PROJECT"))

        create_fact(neo4j_client, Fact(subject="Alice", predicate="WORKS_AT", object="Acme"))
        create_fact(neo4j_client, Fact(subject="Alice", predicate="WORKS_ON", object="Phoenix"))

        facts = current_facts(neo4j_client, "Alice", predicate="WORKS_AT")
        assert len(facts) == 1
        assert facts[0].predicate == "WORKS_AT"
        assert facts[0].object == "Acme"

    def test_filters_predicate_returns_empty_for_no_match(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        upsert_entity(neo4j_client, Entity(name="Alice", entity_type="PERSON"))
        upsert_entity(neo4j_client, Entity(name="Acme", entity_type="ORG"))

        create_fact(neo4j_client, Fact(subject="Alice", predicate="WORKS_AT", object="Acme"))

        facts = current_facts(neo4j_client, "Alice", predicate="KNOWS")
        assert facts == []


class TestFactHistory:
    def test_returns_all_facts_active_and_closed(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        upsert_entity(neo4j_client, Entity(name="Alice", entity_type="PERSON"))
        upsert_entity(neo4j_client, Entity(name="Acme", entity_type="ORG"))
        upsert_entity(neo4j_client, Entity(name="OpenAI", entity_type="ORG"))

        start = datetime(2024, 1, 15, tzinfo=timezone.utc)
        end = datetime(2024, 6, 1, tzinfo=timezone.utc)

        create_fact(neo4j_client, Fact(subject="Alice", predicate="WORKS_AT", object="Acme", valid_from=start, valid_to=end))
        create_fact(neo4j_client, Fact(subject="Alice", predicate="WORKS_AT", object="OpenAI"))

        history = fact_history(neo4j_client, "Alice")
        assert len(history) == 2

        objects = [(f.object, f.is_active) for f in history]
        assert ("OpenAI", True) in objects
        assert ("Acme", False) in objects

    def test_ordered_most_recent_first(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        upsert_entity(neo4j_client, Entity(name="Alice", entity_type="PERSON"))
        upsert_entity(neo4j_client, Entity(name="A", entity_type="ORG"))
        upsert_entity(neo4j_client, Entity(name="B", entity_type="ORG"))
        upsert_entity(neo4j_client, Entity(name="C", entity_type="ORG"))

        create_fact(neo4j_client, Fact(subject="Alice", predicate="WORKS_AT", object="A",
                     valid_from=datetime(2020, 1, 1, tzinfo=timezone.utc)))
        create_fact(neo4j_client, Fact(subject="Alice", predicate="WORKS_AT", object="B",
                     valid_from=datetime(2022, 1, 1, tzinfo=timezone.utc)))
        create_fact(neo4j_client, Fact(subject="Alice", predicate="WORKS_AT", object="C",
                     valid_from=datetime(2024, 1, 1, tzinfo=timezone.utc)))

        history = fact_history(neo4j_client, "Alice")
        assert len(history) == 3
        assert [f.object for f in history] == ["C", "B", "A"]

    def test_filters_by_predicate(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        upsert_entity(neo4j_client, Entity(name="Alice", entity_type="PERSON"))
        upsert_entity(neo4j_client, Entity(name="Acme", entity_type="ORG"))
        upsert_entity(neo4j_client, Entity(name="Phoenix", entity_type="PROJECT"))

        create_fact(neo4j_client, Fact(subject="Alice", predicate="WORKS_AT", object="Acme"))
        create_fact(neo4j_client, Fact(subject="Alice", predicate="WORKS_ON", object="Phoenix"))

        history = fact_history(neo4j_client, "Alice", predicate="WORKS_ON")
        assert len(history) == 1
        assert history[0].predicate == "WORKS_ON"
        assert history[0].object == "Phoenix"

    def test_invalid_predicate_raises(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        with pytest.raises(ValueError, match="Invalid predicate"):
            current_facts(neo4j_client, "Alice", predicate="bad predicate")

    def test_unknown_entity_returns_empty(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        history = fact_history(neo4j_client, "NoSuchEntity")
        assert history == []
