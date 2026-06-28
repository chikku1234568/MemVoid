from __future__ import annotations

from mem_void.graph.client import Neo4jClient
from mem_void.graph.repository import current_facts, fact_history
from mem_void.models.fact import Fact


def related_entities(
    client: Neo4jClient,
    entity_name: str,
    *,
    active_only: bool = True,
) -> list[dict[str, str]]:
    """Return entities directly connected to the given entity.

    Args:
        entity_name: The entity to start from.
        active_only: If True, only returns connections with valid_to IS NULL.

    Returns:
        List of dicts with keys: 'entity' (connected entity name) and
        'predicate' (relationship type).
    """
    where_clause = "WHERE r.valid_to IS NULL" if active_only else ""

    with client.session() as session:
        query = (
            f"MATCH (a:Entity {{name: $entity_name}})-[r]->(e:Entity) "
            f"{where_clause} "
            "RETURN e.name AS entity, type(r) AS predicate "
            "ORDER BY predicate, entity"
        )
        records = session.run(query, entity_name=entity_name).data()

    return [{"entity": r["entity"], "predicate": r["predicate"]} for r in records]


__all__ = [
    "current_facts",
    "fact_history",
    "related_entities",
]
