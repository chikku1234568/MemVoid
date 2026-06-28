from __future__ import annotations

from datetime import datetime, timezone

from mem_void.config import Settings
from mem_void.graph.client import Neo4jClient
from mem_void.graph.repository import create_episode
from mem_void.graph.schema import ensure_schema
from mem_void.ingestion.entity_extractor import extract_entities
from mem_void.ingestion.fact_extractor import extract_facts
from mem_void.models.episode import Episode
from mem_void.models.fact import Fact
from mem_void.resolution.entity_resolver import EntityResolver
from mem_void.resolution.fact_resolver import FactResolver


class IngestResult:
    def __init__(self) -> None:
        self.entities_resolved: int = 0
        self.entities_created: int = 0
        self.facts_created: int = 0
        self.facts_closed: int = 0


class Memory:
    """Public API for mem-void. Ingests text and retrieves facts."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = Neo4jClient(settings)
        self._schema_ensured = False

    def ingest(self, text: str, *, timestamp: datetime | None = None) -> IngestResult:
        """Ingest raw text into the temporal knowledge graph.

        Pipeline: text → episode → entities → resolve → facts → resolve → Neo4j
        """
        self._ensure_schema()
        result = IngestResult()

        ts = timestamp or datetime.now(timezone.utc)
        episode = Episode(content=text, timestamp=ts)
        create_episode(self._client, episode)

        entity_spans = extract_entities(self._settings, text)
        entity_resolver = EntityResolver(self._client)

        entity_map: dict[str, str] = {}
        for span in entity_spans:
            existing = entity_resolver.resolve(span.name, span.entity_type)
            if existing.name not in entity_map:
                entity_map[existing.name] = existing.name

        result.entities_resolved = len(entity_map)

        triples = extract_facts(self._settings, text, list(entity_map.keys()))
        fact_resolver = FactResolver(self._client)

        for triple in triples:
            if triple.subject not in entity_map or triple.object not in entity_map:
                continue

            fact = Fact(
                subject=triple.subject,
                predicate=triple.predicate,
                object=triple.object,
                valid_from=ts,
                episode_uuid=episode.uuid,
            )
            fact_resolver.resolve(fact)
            result.facts_created += 1

        return result

    def close(self) -> None:
        self._client.close()

    def _ensure_schema(self) -> None:
        if not self._schema_ensured:
            ensure_schema(self._client)
            self._schema_ensured = True
