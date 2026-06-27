from __future__ import annotations

from datetime import datetime, timezone

from mem_void.graph.client import Neo4jClient
from mem_void.graph.repository import create_episode, entity_by_name, upsert_entity
from mem_void.graph.schema import ensure_schema
from mem_void.models import Entity, Episode


class TestCreateEpisode:
    def test_persists_episode(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        ts = datetime(2024, 1, 15, tzinfo=timezone.utc)
        ep = Episode(content="Alice joined Acme", timestamp=ts)

        create_episode(neo4j_client, ep)

        with neo4j_client.session() as session:
            result = session.run(
                "MATCH (e:Episode {uuid: $uuid}) RETURN e.content AS content",
                uuid=str(ep.uuid),
            )
            record = result.single()
        assert record is not None
        assert record["content"] == "Alice joined Acme"

    def test_idempotent(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        ep = Episode(content="Test event")

        create_episode(neo4j_client, ep)
        create_episode(neo4j_client, ep)

        with neo4j_client.session() as session:
            result = session.run(
                "MATCH (e:Episode) RETURN count(e) AS count"
            )
            record = result.single()
        assert record is not None
        assert record["count"] == 1

    def test_stores_source(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        ep = Episode(content="Slack message", source="slack")

        create_episode(neo4j_client, ep)

        with neo4j_client.session() as session:
            result = session.run(
                "MATCH (e:Episode {uuid: $uuid}) RETURN e.source AS source",
                uuid=str(ep.uuid),
            )
            record = result.single()
        assert record is not None
        assert record["source"] == "slack"


class TestUpsertEntity:
    def test_creates_new_entity(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        entity = Entity(name="Alice", entity_type="PERSON")

        result = upsert_entity(neo4j_client, entity)

        assert result.name == "Alice"
        assert result.entity_type == "PERSON"
        assert result.uuid is not None

    def test_returns_existing_entity(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        entity = Entity(name="Acme", entity_type="ORG", aliases=["ACME Inc"])

        first = upsert_entity(neo4j_client, entity)
        second = upsert_entity(neo4j_client, Entity(name="Acme"))

        assert second.uuid == first.uuid
        assert second.name == "Acme"
        assert second.entity_type == "ORG"

    def test_preserves_existing_aliases(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        upsert_entity(neo4j_client, Entity(name="MSFT", aliases=["Microsoft"]))

        existing = entity_by_name(neo4j_client, "MSFT")
        assert existing is not None
        assert "Microsoft" in existing.aliases


class TestEntityByName:
    def test_returns_none_for_missing(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        result = entity_by_name(neo4j_client, "NoSuchEntity")
        assert result is None

    def test_finds_existing_entity(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        entity = Entity(name="OpenAI", entity_type="ORG")
        upsert_entity(neo4j_client, entity)

        result = entity_by_name(neo4j_client, "OpenAI")
        assert result is not None
        assert result.name == "OpenAI"
        assert result.entity_type == "ORG"
        assert result.uuid == entity.uuid
