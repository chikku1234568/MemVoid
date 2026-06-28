from __future__ import annotations

from mem_void.graph.client import Neo4jClient
from mem_void.graph.repository import close_active_facts, create_fact
from mem_void.models.fact import Fact
from mem_void.resolution.predicate_registry import is_exclusive


class FactResolver:
    """Resolves facts using the Predicate Registry for temporal consistency.

    For EXCLUSIVE predicates (e.g. WORKS_AT): closes all active facts
    for the same (subject, predicate) before creating the new fact.

    For ADDITIVE predicates (e.g. WORKS_ON): creates the new fact
    without affecting existing active facts.

    Usage:
        resolver = FactResolver(client)
        fact = Fact(subject="Alice", predicate="WORKS_AT", object="OpenAI")
        resolver.resolve(fact)
    """

    def __init__(self, client: Neo4jClient) -> None:
        self._client = client

    def resolve(self, fact: Fact) -> Fact:
        """Resolve a fact: close old exclusive facts, then persist.

        Returns the same Fact object after it has been stored.
        """
        if is_exclusive(fact.predicate):
            close_active_facts(
                self._client,
                fact.subject,
                fact.predicate,
                fact.valid_from,
            )

        create_fact(self._client, fact)
        return fact
