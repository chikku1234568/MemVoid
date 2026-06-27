from __future__ import annotations

from datetime import datetime
from uuid import UUID

from mem_void.graph.client import Neo4jClient
from mem_void.models.entity import Entity
from mem_void.models.episode import Episode


def create_episode(client: Neo4jClient, episode: Episode) -> None:
    """Persist an Episode node in Neo4j. Idempotent by UUID."""
    with client.session() as session:
        session.run(
            """
            MERGE (e:Episode {uuid: $uuid})
            SET e.content = $content,
                e.timestamp = $timestamp,
                e.source = $source,
                e.created_at = $created_at
            """,
            uuid=str(episode.uuid),
            content=episode.content,
            timestamp=episode.timestamp,
            source=episode.source,
            created_at=episode.created_at,
        )


def upsert_entity(client: Neo4jClient, entity: Entity) -> Entity:
    """Insert or match an Entity node by name. Returns the resolved Entity.

    Creates the node if no entity with this name exists.
    Returns the existing node if one already matches.
    """
    with client.session() as session:
        record = session.run(
            """
            MERGE (e:Entity {name: $name})
            ON CREATE SET e.uuid = $uuid,
                          e.entity_type = $entity_type,
                          e.aliases = $aliases,
                          e.created_at = $created_at
            RETURN e.uuid AS uuid,
                   e.name AS name,
                   e.entity_type AS entity_type,
                   e.aliases AS aliases,
                   e.created_at AS created_at
            """,
            name=entity.name,
            uuid=str(entity.uuid),
            entity_type=entity.entity_type,
            aliases=entity.aliases,
            created_at=entity.created_at,
        ).single()

        record_data = dict(record)
        return _row_to_entity(record_data)


def entity_by_name(client: Neo4jClient, name: str) -> Entity | None:
    """Look up an Entity node by exact canonical name. Returns None if not found."""
    with client.session() as session:
        record = session.run(
            """
            MATCH (e:Entity {name: $name})
            RETURN e.uuid AS uuid,
                   e.name AS name,
                   e.entity_type AS entity_type,
                   e.aliases AS aliases,
                   e.created_at AS created_at
            """,
            name=name,
        ).single()

    if record is None:
        return None

    return _row_to_entity(dict(record))


def entity_by_alias(client: Neo4jClient, name: str) -> Entity | None:
    """Look up an Entity by searching all alias lists. Returns None if not found.

    Note: This performs a full scan of Entity nodes. Acceptable for V1
    entity counts. A fulltext index on aliases can be added in V2.
    """
    with client.session() as session:
        record = session.run(
            """
            MATCH (e:Entity)
            WHERE $name IN e.aliases
            RETURN e.uuid AS uuid,
                   e.name AS name,
                   e.entity_type AS entity_type,
                   e.aliases AS aliases,
                   e.created_at AS created_at
            """,
            name=name,
        ).single()

    if record is None:
        return None

    return _row_to_entity(dict(record))


def _row_to_entity(data: dict) -> Entity:
    return Entity(
        uuid=UUID(data["uuid"]),
        name=data["name"],
        entity_type=data["entity_type"],
        aliases=data["aliases"],
        created_at=_to_datetime(data["created_at"]),
    )


def _to_datetime(value: object) -> datetime:
    """Convert a Neo4j DateTime or Python datetime to datetime."""
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))
