from __future__ import annotations

from unittest.mock import MagicMock, patch

from mem_void.graph.client import Neo4jClient
from mem_void.graph.repository import entity_by_name, upsert_entity
from mem_void.graph.schema import ensure_schema
from mem_void.models.entity import Entity
from mem_void.resolution.entity_resolver import EntityResolver


class TestEntityResolverUnit:
    """Unit tests with mocked repository functions — no Neo4j needed."""

    def test_resolve_by_exact_name_match(self) -> None:
        client = MagicMock(spec=Neo4jClient)
        existing = Entity(name="Microsoft", entity_type="ORG")

        with (
            patch("mem_void.resolution.entity_resolver.entity_by_name", return_value=existing) as mock_by_name,
            patch("mem_void.resolution.entity_resolver.entity_by_alias") as mock_by_alias,
            patch("mem_void.resolution.entity_resolver.upsert_entity") as mock_upsert,
        ):
            resolver = EntityResolver(client)
            result = resolver.resolve("Microsoft")

        assert result is existing
        assert result.name == "Microsoft"
        mock_by_name.assert_called_once_with(client, "Microsoft")
        mock_by_alias.assert_not_called()
        mock_upsert.assert_not_called()

    def test_resolve_by_alias_match(self) -> None:
        client = MagicMock(spec=Neo4jClient)
        canonical = Entity(name="Microsoft Corp", entity_type="ORG", aliases=["Microsoft", "MSFT"])

        with (
            patch("mem_void.resolution.entity_resolver.entity_by_name", return_value=None) as mock_by_name,
            patch("mem_void.resolution.entity_resolver.entity_by_alias", return_value=canonical) as mock_by_alias,
            patch("mem_void.resolution.entity_resolver.upsert_entity") as mock_upsert,
        ):
            resolver = EntityResolver(client)
            result = resolver.resolve("Microsoft")

        assert result is canonical
        assert result.name == "Microsoft Corp"
        mock_by_name.assert_called_once_with(client, "Microsoft")
        mock_by_alias.assert_called_once_with(client, "Microsoft")
        mock_upsert.assert_not_called()

    def test_resolve_creates_new_entity(self) -> None:
        client = MagicMock(spec=Neo4jClient)
        new_entity = Entity(name="OpenAI", entity_type="ORG")

        with (
            patch("mem_void.resolution.entity_resolver.entity_by_name", return_value=None) as mock_by_name,
            patch("mem_void.resolution.entity_resolver.entity_by_alias", return_value=None) as mock_by_alias,
            patch("mem_void.resolution.entity_resolver.upsert_entity", return_value=new_entity) as mock_upsert,
        ):
            resolver = EntityResolver(client)
            result = resolver.resolve("OpenAI", entity_type="ORG")

        assert result is new_entity
        assert result.name == "OpenAI"
        mock_by_name.assert_called_once_with(client, "OpenAI")
        mock_by_alias.assert_called_once_with(client, "OpenAI")
        mock_upsert.assert_called_once()
        upserted = mock_upsert.call_args[0][1]
        assert upserted.name == "OpenAI"
        assert upserted.entity_type == "ORG"

    def test_resolve_passes_correct_entity_type_on_create(self) -> None:
        client = MagicMock(spec=Neo4jClient)
        new_entity = Entity(name="Alice", entity_type="PERSON")

        with (
            patch("mem_void.resolution.entity_resolver.entity_by_name", return_value=None),
            patch("mem_void.resolution.entity_resolver.entity_by_alias", return_value=None),
            patch("mem_void.resolution.entity_resolver.upsert_entity", return_value=new_entity) as mock_upsert,
        ):
            resolver = EntityResolver(client)
            resolver.resolve("Alice", entity_type="PERSON")

        upserted = mock_upsert.call_args[0][1]
        assert upserted.entity_type == "PERSON"

    def test_resolve_default_entity_type_is_unknown(self) -> None:
        client = MagicMock(spec=Neo4jClient)
        new_entity = Entity(name="Thing", entity_type="UNKNOWN")

        with (
            patch("mem_void.resolution.entity_resolver.entity_by_name", return_value=None),
            patch("mem_void.resolution.entity_resolver.entity_by_alias", return_value=None),
            patch("mem_void.resolution.entity_resolver.upsert_entity", return_value=new_entity) as mock_upsert,
        ):
            resolver = EntityResolver(client)
            resolver.resolve("Thing")

        upserted = mock_upsert.call_args[0][1]
        assert upserted.entity_type == "UNKNOWN"

    def test_exact_name_takes_priority_over_alias(self) -> None:
        """An exact name match on a different entity beats an alias match."""
        client = MagicMock(spec=Neo4jClient)
        exact_match = Entity(name="Microsoft", entity_type="PRODUCT")
        alias_match = Entity(name="Microsoft Corp", entity_type="ORG", aliases=["Microsoft"])

        with (
            patch("mem_void.resolution.entity_resolver.entity_by_name", return_value=exact_match) as mock_by_name,
            patch("mem_void.resolution.entity_resolver.entity_by_alias", return_value=alias_match) as mock_by_alias,
            patch("mem_void.resolution.entity_resolver.upsert_entity") as mock_upsert,
        ):
            resolver = EntityResolver(client)
            result = resolver.resolve("Microsoft")

        assert result is exact_match
        assert result.entity_type == "PRODUCT"
        mock_by_name.assert_called_once()
        mock_by_alias.assert_not_called()
        mock_upsert.assert_not_called()


class TestEntityResolverIntegration:
    """Integration tests using real Neo4j via testcontainers."""

    def test_resolve_creates_new_entity(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        resolver = EntityResolver(neo4j_client)

        result = resolver.resolve("Alice", entity_type="PERSON")

        assert result.name == "Alice"
        assert result.entity_type == "PERSON"
        assert result.uuid is not None
        assert result.aliases == []

    def test_resolve_returns_existing_by_exact_name(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        resolver = EntityResolver(neo4j_client)

        first = resolver.resolve("Acme", entity_type="ORG")
        second = resolver.resolve("Acme", entity_type="SHOULD_BE_IGNORED")

        assert second.uuid == first.uuid
        assert second.name == "Acme"
        assert second.entity_type == "ORG"

    def test_resolve_returns_existing_by_alias(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)

        upsert_entity(neo4j_client, Entity(
            name="Microsoft Corp",
            entity_type="ORG",
            aliases=["Microsoft", "MSFT"],
        ))

        resolver = EntityResolver(neo4j_client)
        result = resolver.resolve("Microsoft")

        assert result.name == "Microsoft Corp"
        assert result.entity_type == "ORG"

    def test_resolve_different_entities_with_same_type(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        resolver = EntityResolver(neo4j_client)

        alice = resolver.resolve("Alice", entity_type="PERSON")
        bob = resolver.resolve("Bob", entity_type="PERSON")

        assert alice.uuid != bob.uuid
        assert alice.name == "Alice"
        assert bob.name == "Bob"

    def test_idempotent_resolve(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        resolver = EntityResolver(neo4j_client)

        a = resolver.resolve("OpenAI", entity_type="ORG")
        b = resolver.resolve("OpenAI")
        c = resolver.resolve("OpenAI", entity_type="SHOULD_NOT_CHANGE")

        assert a.uuid == b.uuid == c.uuid
        assert a.entity_type == "ORG"
        assert b.entity_type == "ORG"
        assert c.entity_type == "ORG"

    def test_entity_count_stays_stable(self, neo4j_client: Neo4jClient) -> None:
        ensure_schema(neo4j_client)
        resolver = EntityResolver(neo4j_client)

        resolver.resolve("Google")
        resolver.resolve("Google")
        resolver.resolve("Google")

        found = entity_by_name(neo4j_client, "Google")
        assert found is not None

        with neo4j_client.session() as session:
            count = session.run("MATCH (e:Entity) RETURN count(e) AS c").single()
        assert count is not None
        assert count["c"] == 1
