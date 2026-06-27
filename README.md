# mem-void

Temporal Knowledge Graph Memory System — a persistent memory layer for AI agents.

Text events → entities → temporal facts → Neo4j → retrieval.

**Status:** V1 in progress (Milestones 1-3 of 6 complete).

## Quick Start

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # Windows
pip install -e ".[dev]"
cp .env.example .env           # edit with your Neo4j credentials
```

Requires Neo4j 5.x. Start with Docker:

```bash
docker run -d --name memvoid-neo4j \
  -p 7687:7687 -p 7474:7474 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:5-community
```

## What Works Now (M1-M3)

```python
from mem_void.config import Settings
from mem_void.graph import Neo4jClient, ensure_schema
from mem_void.resolution import EntityResolver
from mem_void.models import Episode, Entity

client = Neo4jClient(Settings())
ensure_schema(client)

# Deterministic entity resolution
resolver = EntityResolver(client)
alice = resolver.resolve("Alice", entity_type="PERSON")
acme = resolver.resolve("Acme", entity_type="ORG")

# Re-resolve: exact name match returns existing entity
alice2 = resolver.resolve("Alice")
assert alice2.uuid == alice.uuid  # same entity

# Entity aliases work
ms = Entity(name="Microsoft Corp", aliases=["Microsoft", "MSFT"])
# resolver.resolve("Microsoft") → returns "Microsoft Corp"

client.close()
```

## Running Tests

```bash
# Unit tests (no Docker needed)
pytest tests/test_config/ tests/test_models/ tests/test_resolution/ -v

# All tests (requires Docker for Neo4j integration tests)
pytest -v
```

## Architecture

See `deepseek/` for full architecture docs. See `planning/` for milestone logs.
