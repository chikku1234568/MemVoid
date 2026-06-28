from __future__ import annotations

from unittest.mock import patch

from mem_void.config import Settings
from mem_void.graph.client import Neo4jClient
from mem_void.graph.repository import current_facts, fact_history, upsert_entity
from mem_void.graph.schema import ensure_schema
from mem_void.models import Entity
from mem_void.memory import Memory


class TestMemoryPipeline:
    """Integration test for the full ingestion pipeline with mocked LLM."""

    def test_ingest_creates_entities_and_facts(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        settings = Settings(
            neo4j_uri="bolt://localhost:7687",
            _env_file=None,
        )

        entity_json = '[{"name": "Alice", "entity_type": "PERSON"}, {"name": "Acme", "entity_type": "ORG"}]'
        fact_json = '[{"subject": "Alice", "predicate": "WORKS_AT", "object": "Acme"}]'

        with (
            patch("mem_void.memory.Neo4jClient", return_value=neo4j_client),
            patch("mem_void.ingestion.entity_extractor.generate", return_value=entity_json),
            patch("mem_void.ingestion.fact_extractor.generate", return_value=fact_json),
        ):
            memory = Memory(settings)
            result = memory.ingest("Alice joined Acme")

        assert result.facts_created == 1

        facts = current_facts(neo4j_client, "Alice")
        assert len(facts) == 1
        assert facts[0].predicate == "WORKS_AT"
        assert facts[0].object == "Acme"

    def test_ingest_closes_exclusive_fact(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        upsert_entity(neo4j_client, Entity(name="Alice", entity_type="PERSON"))
        upsert_entity(neo4j_client, Entity(name="Acme", entity_type="ORG"))
        upsert_entity(neo4j_client, Entity(name="OpenAI", entity_type="ORG"))

        settings = Settings(_env_file=None)

        e1 = '[{"name": "Alice", "entity_type": "PERSON"}, {"name": "Acme", "entity_type": "ORG"}]'
        f1 = '[{"subject": "Alice", "predicate": "WORKS_AT", "object": "Acme"}]'
        e2 = '[{"name": "Alice", "entity_type": "PERSON"}, {"name": "OpenAI", "entity_type": "ORG"}]'
        f2 = '[{"subject": "Alice", "predicate": "WORKS_AT", "object": "OpenAI"}]'

        with (
            patch("mem_void.memory.Neo4jClient", return_value=neo4j_client),
            patch("mem_void.ingestion.entity_extractor.generate", side_effect=[e1, e2]),
            patch("mem_void.ingestion.fact_extractor.generate", side_effect=[f1, f2]),
        ):
            memory = Memory(settings)
            memory.ingest("Alice joined Acme")
            memory.ingest("Alice joined OpenAI")

        facts = current_facts(neo4j_client, "Alice")
        works_at = [f for f in facts if f.predicate == "WORKS_AT"]
        assert len(works_at) == 1
        assert works_at[0].object == "OpenAI"

        history = fact_history(neo4j_client, "Alice", predicate="WORKS_AT")
        assert len(history) == 2

    def test_ingest_additive_predicate_does_not_close(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        upsert_entity(neo4j_client, Entity(name="Alice", entity_type="PERSON"))
        upsert_entity(neo4j_client, Entity(name="Phoenix", entity_type="PROJECT"))
        upsert_entity(neo4j_client, Entity(name="Titan", entity_type="PROJECT"))

        settings = Settings(_env_file=None)

        e1 = '[{"name": "Alice", "entity_type": "PERSON"}, {"name": "Phoenix", "entity_type": "PROJECT"}]'
        f1 = '[{"subject": "Alice", "predicate": "WORKS_ON", "object": "Phoenix"}]'
        e2 = '[{"name": "Alice", "entity_type": "PERSON"}, {"name": "Titan", "entity_type": "PROJECT"}]'
        f2 = '[{"subject": "Alice", "predicate": "WORKS_ON", "object": "Titan"}]'

        with (
            patch("mem_void.memory.Neo4jClient", return_value=neo4j_client),
            patch("mem_void.ingestion.entity_extractor.generate", side_effect=[e1, e2]),
            patch("mem_void.ingestion.fact_extractor.generate", side_effect=[f1, f2]),
        ):
            memory = Memory(settings)
            memory.ingest("Alice works on Project Phoenix")
            memory.ingest("Alice works on Titan")

        facts = current_facts(neo4j_client, "Alice", predicate="WORKS_ON")
        assert len(facts) == 2
        objects = {f.object for f in facts}
        assert objects == {"Phoenix", "Titan"}
