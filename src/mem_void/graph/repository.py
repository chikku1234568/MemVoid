from __future__ import annotations

from datetime import datetime
from uuid import UUID

from mem_void.graph.client import Neo4jClient
from mem_void.models.entity import Entity
from mem_void.models.episode import Episode
from mem_void.models.fact import Fact


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


def create_fact(client: Neo4jClient, fact: Fact) -> None:
    """Persist a Fact as a Neo4j relationship between two Entity nodes.

    The predicate becomes the relationship type. Both subject and object
    must already exist as Entity nodes in the graph.

    No invalidation logic — purely creates the relationship.
    """
    Fact.validate_predicate(fact.predicate)

    with client.session() as session:
        session.run(
            f"""
            MATCH (s:Entity {{name: $subject}})
            MATCH (o:Entity {{name: $object}})
            CREATE (s)-[r:{fact.predicate} {{
                uuid: $uuid,
                valid_from: $valid_from,
                valid_to: $valid_to,
                episode_uuid: $episode_uuid,
                confidence: $confidence,
                created_at: $created_at
            }}]->(o)
            """,
            subject=fact.subject,
            object=fact.object,
            uuid=str(fact.uuid),
            valid_from=fact.valid_from,
            valid_to=fact.valid_to,
            episode_uuid=str(fact.episode_uuid) if fact.episode_uuid else None,
            confidence=fact.confidence,
            created_at=fact.created_at,
        )


def close_active_facts(
    client: Neo4jClient,
    subject: str,
    predicate: str,
    closed_at: object,
) -> None:
    """Close all currently active facts for a (subject, predicate) pair.

    Sets valid_to = closed_at on every matching relationship
    where valid_to IS NULL. Used by FactResolver for exclusive predicates.
    """
    Fact.validate_predicate(predicate)

    with client.session() as session:
        session.run(
            f"""
            MATCH (s:Entity {{name: $subject}})-[r:{predicate}]->(:Entity)
            WHERE r.valid_to IS NULL
            SET r.valid_to = $closed_at
            """,
            subject=subject,
            closed_at=closed_at,
        )


def current_facts(
    client: Neo4jClient,
    entity_name: str,
    predicate: str | None = None,
) -> list[Fact]:
    """Return all currently active facts (valid_to IS NULL) for an entity.

    Args:
        entity_name: The subject entity name.
        predicate: Optional predicate filter. If None, returns all predicates.
    """
    predicate_clause = _predicate_match_clause(predicate) if predicate else ""

    with client.session() as session:
        query = (
            f"MATCH (a:Entity {{name: $entity_name}})"
            f"-[r{predicate_clause}]->(e:Entity) "
            "WHERE r.valid_to IS NULL "
            "RETURN r.uuid AS uuid, "
            "       a.name AS subject, "
            "       type(r) AS predicate, "
            "       e.name AS object, "
            "       r.valid_from AS valid_from, "
            "       r.valid_to AS valid_to, "
            "       r.episode_uuid AS episode_uuid, "
            "       r.confidence AS confidence, "
            "       r.created_at AS created_at "
            "ORDER BY r.valid_from DESC"
        )
        records = session.run(query, entity_name=entity_name).data()

    return [_record_to_fact(r) for r in records]


def fact_history(
    client: Neo4jClient,
    entity_name: str,
    predicate: str | None = None,
) -> list[Fact]:
    """Return all facts for an entity — both active and closed.

    Ordered by valid_from descending (most recent first).
    """
    predicate_clause = _predicate_match_clause(predicate) if predicate else ""

    with client.session() as session:
        query = (
            f"MATCH (a:Entity {{name: $entity_name}})"
            f"-[r{predicate_clause}]->(e:Entity) "
            "RETURN r.uuid AS uuid, "
            "       a.name AS subject, "
            "       type(r) AS predicate, "
            "       e.name AS object, "
            "       r.valid_from AS valid_from, "
            "       r.valid_to AS valid_to, "
            "       r.episode_uuid AS episode_uuid, "
            "       r.confidence AS confidence, "
            "       r.created_at AS created_at "
            "ORDER BY r.valid_from DESC"
        )
        records = session.run(query, entity_name=entity_name).data()

    return [_record_to_fact(r) for r in records]


def _predicate_match_clause(predicate: str) -> str:
    """Build a safe relationship type clause for Cypher interpolation.

    Validates the predicate name then returns the colon-prefixed type
    for use in MATCH patterns: ':WORKS_AT'.
    """
    Fact.validate_predicate(predicate)
    return f":{predicate}"


def _record_to_fact(data: dict) -> Fact:
    return Fact(
        uuid=UUID(data["uuid"]),
        subject=data["subject"],
        predicate=data["predicate"],
        object=data["object"],
        valid_from=_to_datetime(data["valid_from"]),
        valid_to=_to_datetime(data["valid_to"]) if data.get("valid_to") else None,
        episode_uuid=UUID(data["episode_uuid"]) if data.get("episode_uuid") else None,
        confidence=data.get("confidence"),
        created_at=_to_datetime(data["created_at"]),
    )


def _to_datetime(value: object) -> datetime:
    """Convert a Neo4j DateTime or Python datetime to datetime."""
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value))
