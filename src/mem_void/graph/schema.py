from __future__ import annotations

from neo4j.exceptions import ClientError, Neo4jError

from mem_void.graph.client import Neo4jClient

_CONSTRAINTS: list[str] = [
    "CREATE CONSTRAINT episode_uuid_unique IF NOT EXISTS "
    "FOR (e:Episode) REQUIRE e.uuid IS UNIQUE",
    "CREATE CONSTRAINT entity_uuid_unique IF NOT EXISTS "
    "FOR (e:Entity) REQUIRE e.uuid IS UNIQUE",
    "CREATE CONSTRAINT entity_name_unique IF NOT EXISTS "
    "FOR (e:Entity) REQUIRE e.name IS UNIQUE",
]

_INDEXES: list[str] = [
    "CREATE INDEX entity_type_idx IF NOT EXISTS "
    "FOR (e:Entity) ON (e.entity_type)",
    "CREATE INDEX episode_timestamp_idx IF NOT EXISTS "
    "FOR (e:Episode) ON (e.timestamp)",
]

_ALL_STATEMENTS: list[str] = _CONSTRAINTS + _INDEXES


def ensure_schema(client: Neo4jClient) -> None:
    """Idempotently create all constraints and indexes.

    Safe to call multiple times — already-existing constraints/indexes
    are skipped via IF NOT EXISTS (Neo4j 5.7+) or caught as ClientError
    (Neo4j 5.0-5.6).
    """
    with client.session() as session:
        for statement in _ALL_STATEMENTS:
            try:
                session.run(statement)
            except (ClientError, Neo4jError) as exc:
                _handle_schema_error(exc)


def _handle_schema_error(exc: ClientError | Neo4jError) -> None:
    message = str(exc).lower()
    if "already existing" in message or "already exists" in message:
        return
    raise exc
