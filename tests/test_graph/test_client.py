from __future__ import annotations

from mem_void.config import Settings
from mem_void.graph.client import Neo4jClient


class TestNeo4jClient:
    def test_health_check_passes(self, neo4j_client: Neo4jClient) -> None:
        assert neo4j_client.health_check() is True

    def test_session_executes_cypher(self, neo4j_client: Neo4jClient) -> None:
        with neo4j_client.session() as session:
            result = session.run("RETURN 1 AS n")
            record = result.single()
            assert record is not None
            assert record["n"] == 1

    def test_context_manager(self, settings: Settings) -> None:
        with Neo4jClient(settings) as client:
            assert client.health_check() is True

    def test_database_property(self, neo4j_client: Neo4jClient) -> None:
        assert neo4j_client.database == "neo4j"
