from __future__ import annotations

from mem_void.graph.client import Neo4jClient
from mem_void.graph.repository import entity_by_alias, entity_by_name, upsert_entity
from mem_void.models.entity import Entity


class EntityResolver:
    """Deterministic entity resolution via exact name, alias, or creation.

    Resolution strategy (in order):
    1. Exact canonical name match — returns the existing Entity.
    2. Alias lookup — searches all Entity.alias lists; returns the
       canonical Entity whose aliases contain the given name.
    3. Creation — creates a new Entity node via upsert.

    The resolver is deterministic: given the same name and database
    state, it always produces the same result. No embeddings, no
    similarity thresholds, no fuzzy matching.

    Usage:
        resolver = EntityResolver(client)
        entity = resolver.resolve("Microsoft")
        # Returns existing Entity for "Microsoft", or creates one.
    """

    def __init__(self, client: Neo4jClient) -> None:
        self._client = client

    def resolve(self, name: str, entity_type: str = "UNKNOWN") -> Entity:
        """Resolve an entity name to an Entity node.

        Args:
            name: The entity name to resolve.
            entity_type: Used only when creating a new entity.
                         Ignored if the entity already exists.

        Returns:
            The resolved Entity (existing or newly created).
        """
        existing = entity_by_name(self._client, name)
        if existing is not None:
            return existing

        existing = entity_by_alias(self._client, name)
        if existing is not None:
            return existing

        entity = Entity(name=name, entity_type=entity_type)
        return upsert_entity(self._client, entity)
