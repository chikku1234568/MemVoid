from __future__ import annotations

from mem_void.graph.client import Neo4jClient
from mem_void.graph.schema import ensure_schema


class TestEnsureSchema:
    def test_creates_constraints(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)

        with neo4j_client.session() as session:
            result = session.run("SHOW CONSTRAINTS")
            constraint_names = {record["name"] for record in result}

        assert "episode_uuid_unique" in constraint_names
        assert "entity_uuid_unique" in constraint_names
        assert "entity_name_unique" in constraint_names

    def test_idempotent(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        ensure_schema(neo4j_client)
        ensure_schema(neo4j_client)

        # Should have the same constraints after three calls
        with neo4j_client.session() as session:
            result = session.run("SHOW CONSTRAINTS")
            count = len(list(result))
        assert count >= 3

    def test_creates_indexes(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)

        with neo4j_client.session() as session:
            result = session.run("SHOW INDEXES")
            index_names = {record["name"] for record in result}

        assert "entity_type_idx" in index_names
        assert "episode_timestamp_idx" in index_names
