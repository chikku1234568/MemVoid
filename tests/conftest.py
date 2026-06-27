from __future__ import annotations

import pytest
from testcontainers.neo4j import Neo4jContainer

from mem_void.config import Settings
from mem_void.graph.client import Neo4jClient


@pytest.fixture(scope="session")
def neo4j_container() -> Neo4jContainer:
    """Session-scoped Neo4j 5.x Community Edition container."""
    container = Neo4jContainer(
        image="neo4j:5-community",
        username="neo4j",
        password="password",
    )
    container.with_exposed_ports(7687, 7474)
    container.start()
    yield container
    container.stop()


@pytest.fixture(scope="session")
def settings(neo4j_container: Neo4jContainer) -> Settings:
    """Settings pointing at the test Neo4j container."""
    return Settings(
        neo4j_uri=neo4j_container.get_connection_url(),
        neo4j_user="neo4j",
        neo4j_password="password",
    )


@pytest.fixture(scope="session")
def neo4j_client(settings: Settings) -> Neo4jClient:
    """Session-scoped client connected to the test container."""
    client = Neo4jClient(settings)
    yield client
    client.close()
