from __future__ import annotations

from datetime import datetime

from mem_void.graph.client import Neo4jClient
from mem_void.graph.repository import _predicate_match_clause, _record_to_fact
from mem_void.models.fact import Fact


def facts_in_range(
    client: Neo4jClient,
    entity_name: str,
    from_dt: datetime,
    to_dt: datetime,
    *,
    predicate: str | None = None,
) -> list[Fact]:
    """Return facts that were active at any point during the time range.

    A fact overlaps the range if:
        fact.valid_from <= to_dt
        AND (fact.valid_to >= from_dt OR fact.valid_to IS NULL)
    """
    predicate_clause = _predicate_match_clause(predicate) if predicate else ""

    with client.session() as session:
        query = (
            f"MATCH (a:Entity {{name: $entity_name}})"
            f"-[r{predicate_clause}]->(e:Entity) "
            "WHERE r.valid_from <= $to_dt "
            "  AND (r.valid_to >= $from_dt OR r.valid_to IS NULL) "
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
        records = session.run(
            query,
            entity_name=entity_name,
            from_dt=from_dt,
            to_dt=to_dt,
        ).data()

    return [_record_to_fact(r) for r in records]


def facts_at_time(
    client: Neo4jClient,
    entity_name: str,
    point_dt: datetime,
    *,
    predicate: str | None = None,
) -> list[Fact]:
    """Return facts that were active at a specific point in time.

    A fact is active at `point_dt` if:
        fact.valid_from <= point_dt
        AND (fact.valid_to >= point_dt OR fact.valid_to IS NULL)
    """
    predicate_clause = _predicate_match_clause(predicate) if predicate else ""

    with client.session() as session:
        query = (
            f"MATCH (a:Entity {{name: $entity_name}})"
            f"-[r{predicate_clause}]->(e:Entity) "
            "WHERE r.valid_from <= $point_dt "
            "  AND (r.valid_to >= $point_dt OR r.valid_to IS NULL) "
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
        records = session.run(
            query,
            entity_name=entity_name,
            point_dt=point_dt,
        ).data()

    return [_record_to_fact(r) for r in records]


__all__ = ["facts_at_time", "facts_in_range"]
