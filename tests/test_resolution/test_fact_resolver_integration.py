from __future__ import annotations

from datetime import datetime, timezone

from mem_void.graph.client import Neo4jClient
from mem_void.graph.repository import current_facts, fact_history, upsert_entity
from mem_void.graph.schema import ensure_schema
from mem_void.models import Entity, Fact
from mem_void.resolution.fact_resolver import FactResolver


class TestFactResolverIntegration:
    def test_exclusive_predicate_closes_previous(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        upsert_entity(neo4j_client, Entity(name="Alice", entity_type="PERSON"))
        upsert_entity(neo4j_client, Entity(name="Acme", entity_type="ORG"))
        upsert_entity(neo4j_client, Entity(name="OpenAI", entity_type="ORG"))

        resolver = FactResolver(neo4j_client)

        resolver.resolve(Fact(subject="Alice", predicate="WORKS_AT", object="Acme"))
        resolver.resolve(Fact(subject="Alice", predicate="WORKS_AT", object="OpenAI"))

        facts = current_facts(neo4j_client, "Alice")
        works_at = [f for f in facts if f.predicate == "WORKS_AT"]
        assert len(works_at) == 1
        assert works_at[0].object == "OpenAI"
        assert works_at[0].is_active is True

    def test_closed_fact_has_valid_to_set(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        upsert_entity(neo4j_client, Entity(name="Alice", entity_type="PERSON"))
        upsert_entity(neo4j_client, Entity(name="Acme", entity_type="ORG"))
        upsert_entity(neo4j_client, Entity(name="OpenAI", entity_type="ORG"))

        resolver = FactResolver(neo4j_client)

        start = datetime(2024, 1, 15, tzinfo=timezone.utc)
        resolver.resolve(Fact(
            subject="Alice", predicate="WORKS_AT", object="Acme",
            valid_from=start,
        ))
        resolver.resolve(Fact(subject="Alice", predicate="WORKS_AT", object="OpenAI"))

        history = fact_history(neo4j_client, "Alice", predicate="WORKS_AT")
        assert len(history) == 2

        closed = [f for f in history if f.object == "Acme"][0]
        active = [f for f in history if f.object == "OpenAI"][0]

        assert closed.valid_to is not None
        assert closed.is_active is False
        assert active.valid_to is None
        assert active.is_active is True

        assert closed.valid_from == start

    def test_additive_predicate_does_not_close(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        upsert_entity(neo4j_client, Entity(name="Alice", entity_type="PERSON"))
        upsert_entity(neo4j_client, Entity(name="Phoenix", entity_type="PROJECT"))
        upsert_entity(neo4j_client, Entity(name="Titan", entity_type="PROJECT"))

        resolver = FactResolver(neo4j_client)

        resolver.resolve(Fact(subject="Alice", predicate="WORKS_ON", object="Phoenix"))
        resolver.resolve(Fact(subject="Alice", predicate="WORKS_ON", object="Titan"))

        facts = current_facts(neo4j_client, "Alice", predicate="WORKS_ON")
        assert len(facts) == 2
        objects = {f.object for f in facts}
        assert objects == {"Phoenix", "Titan"}
        assert all(f.is_active for f in facts)

    def test_mixed_exclusive_and_additive(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        upsert_entity(neo4j_client, Entity(name="Alice", entity_type="PERSON"))
        upsert_entity(neo4j_client, Entity(name="Acme", entity_type="ORG"))
        upsert_entity(neo4j_client, Entity(name="OpenAI", entity_type="ORG"))
        upsert_entity(neo4j_client, Entity(name="Phoenix", entity_type="PROJECT"))

        resolver = FactResolver(neo4j_client)

        resolver.resolve(Fact(subject="Alice", predicate="WORKS_AT", object="Acme"))
        resolver.resolve(Fact(subject="Alice", predicate="WORKS_ON", object="Phoenix"))
        resolver.resolve(Fact(subject="Alice", predicate="WORKS_AT", object="OpenAI"))

        facts = current_facts(neo4j_client, "Alice")
        predicates = {(f.predicate, f.object) for f in facts}

        assert ("WORKS_AT", "OpenAI") in predicates
        assert ("WORKS_AT", "Acme") not in predicates
        assert ("WORKS_ON", "Phoenix") in predicates

    def test_close_all_active_facts_for_predicate(self, neo4j_client: Neo4jClient) -> None:
        """If multiple active facts exist for an exclusive predicate (pre-M5 state),
        they should all be closed."""
        ensure_schema(neo4j_client)
        upsert_entity(neo4j_client, Entity(name="Alice", entity_type="PERSON"))
        upsert_entity(neo4j_client, Entity(name="A", entity_type="ORG"))
        upsert_entity(neo4j_client, Entity(name="B", entity_type="ORG"))
        upsert_entity(neo4j_client, Entity(name="C", entity_type="ORG"))

        # Use create_fact directly (bypassing resolver) to create multiple active
        from mem_void.graph.repository import create_fact

        create_fact(neo4j_client, Fact(subject="Alice", predicate="WORKS_AT", object="A"))
        create_fact(neo4j_client, Fact(subject="Alice", predicate="WORKS_AT", object="B"))

        # Now resolve a new one via the resolver
        resolver = FactResolver(neo4j_client)
        resolver.resolve(Fact(subject="Alice", predicate="WORKS_AT", object="C"))

        # Only C should be active
        facts = current_facts(neo4j_client, "Alice", predicate="WORKS_AT")
        assert len(facts) == 1
        assert facts[0].object == "C"

    def test_exclusive_predicate_does_not_affect_other_subjects(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        upsert_entity(neo4j_client, Entity(name="Alice", entity_type="PERSON"))
        upsert_entity(neo4j_client, Entity(name="Bob", entity_type="PERSON"))
        upsert_entity(neo4j_client, Entity(name="Acme", entity_type="ORG"))
        upsert_entity(neo4j_client, Entity(name="OpenAI", entity_type="ORG"))

        resolver = FactResolver(neo4j_client)

        resolver.resolve(Fact(subject="Alice", predicate="WORKS_AT", object="Acme"))
        resolver.resolve(Fact(subject="Bob", predicate="WORKS_AT", object="Acme"))
        resolver.resolve(Fact(subject="Alice", predicate="WORKS_AT", object="OpenAI"))

        # Alice's Acme fact should be closed
        alice_facts = current_facts(neo4j_client, "Alice", predicate="WORKS_AT")
        assert len(alice_facts) == 1
        assert alice_facts[0].object == "OpenAI"

        # Bob's Acme fact should still be active
        bob_facts = current_facts(neo4j_client, "Bob", predicate="WORKS_AT")
        assert len(bob_facts) == 1
        assert bob_facts[0].object == "Acme"
        assert bob_facts[0].is_active is True

    def test_close_only_closes_same_predicate(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        upsert_entity(neo4j_client, Entity(name="Alice", entity_type="PERSON"))
        upsert_entity(neo4j_client, Entity(name="SF", entity_type="LOCATION"))
        upsert_entity(neo4j_client, Entity(name="NYC", entity_type="LOCATION"))
        upsert_entity(neo4j_client, Entity(name="Acme", entity_type="ORG"))

        resolver = FactResolver(neo4j_client)

        resolver.resolve(Fact(subject="Alice", predicate="LIVES_IN", object="SF"))
        resolver.resolve(Fact(subject="Alice", predicate="WORKS_AT", object="Acme"))
        resolver.resolve(Fact(subject="Alice", predicate="LIVES_IN", object="NYC"))

        # LIVES_IN for SF should be closed
        lives = fact_history(neo4j_client, "Alice", predicate="LIVES_IN")
        assert len(lives) == 2  # SF (closed) + NYC (active)

        # WORKS_AT for Acme should still be active (different predicate)
        works = current_facts(neo4j_client, "Alice", predicate="WORKS_AT")
        assert len(works) == 1
        assert works[0].object == "Acme"
        assert works[0].is_active is True
