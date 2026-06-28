# mem-void

Temporal Knowledge Graph Memory System — a persistent memory layer for AI agents.

```
Text Events → Entities → Temporal Facts → Neo4j → Retrieval
```

**Status:** V1 complete (Milestones 1–8 of 8).

## Quick Start

### 1. Prerequisites

- Python 3.10+
- Neo4j 5.x (Community Edition)
- OpenAI API key (or Ollama)

### 2. Setup

```bash
python -m venv .venv
source .venv/bin/activate      # Linux/macOS
.\.venv\Scripts\Activate.ps1   # Windows

pip install -e ".[dev]"
cp .env.example .env            # edit with your credentials
```

### 3. Start Neo4j

```bash
docker run -d --name memvoid-neo4j \
  -p 7687:7687 -p 7474:7474 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:5-community
```

### 4. Run the Demo

```bash
python examples/alice_demo.py
```

## Architecture

```
src/mem_void/
├── config/          # Settings (pydantic-settings, .env)
├── graph/           # Neo4j client, schema, repository (CRUD)
├── models/          # Episode, Entity, Fact (Pydantic v2)
├── resolution/      # EntityResolver, FactResolver, PredicateRegistry
├── ingestion/       # Entity + Fact extraction (LLM)
├── retrieval/       # Graph traversal + temporal queries
├── utils/           # LLM client (OpenAI/Ollama)
└── memory.py        # Public API: Memory class
```

### Component Flow

```
memory.ingest("Alice joined Acme")
    │
    ├─ Episode created (Neo4j node)
    ├─ Entity extraction (LLM → Alice:PERSON, Acme:ORG)
    ├─ Entity resolution (exact name → alias → create)
    ├─ Fact extraction (LLM → WORKS_AT:Alice→Acme)
    └─ Fact resolution (exclusive: close old, additive: preserve)
           │
           ▼
        Neo4j Graph
           │
    ┌──────┴──────┐
    ▼              ▼
current_facts  fact_history  related_entities
```

## Usage

```python
from mem_void import Memory, Settings

memory = Memory(Settings())

# Ingest events
memory.ingest("Alice joined Acme")
memory.ingest("Alice works on Project Phoenix")
memory.ingest("Alice joined OpenAI")

# Query
from mem_void.retrieval import current_facts, fact_history, related_entities

facts = current_facts(memory._client, "Alice")
# → WORKS_AT OpenAI, WORKS_ON Project Phoenix

history = fact_history(memory._client, "Alice", predicate="WORKS_AT")
# → OpenAI (active), Acme (closed)

entities = related_entities(memory._client, "Alice")
# → OpenAI, Project Phoenix

memory.close()
```

## Current Capabilities

- **Temporal facts** — every fact has `valid_from`/`valid_to`
- **Predicate-aware invalidation** — EXCLUSIVE (WORKS_AT, LIVES_IN) auto-close old facts; ADDITIVE (WORKS_ON, KNOWS) coexist
- **Deterministic entity resolution** — exact name → alias → create
- **LLM extraction** — entities and facts from free text (OpenAI/Ollama)
- **Graph-native retrieval** — Cypher queries, no embeddings, no vector search
- **Time travel** — `facts_at_time()`, `facts_in_range()`

## Current Limitations

- No embeddings or semantic search
- No fuzzy entity matching (exact + alias only)
- No explicit fact negation ("Alice left Acme" without new employer)
- No REST API (library only)
- No streaming/batch ingestion optimization
- Single-agent memory only

## Testing

```bash
# Unit tests (no Docker)
pytest tests/test_config/ tests/test_models/ tests/test_resolution/test_predicate_registry.py tests/test_resolution/test_fact_resolver.py tests/test_ingestion/test_extractors.py -v

# All tests (requires Docker)
pytest -v
```

## Repository Structure

```
mem-void/
├── src/mem_void/       # Package source
├── tests/              # Unit + integration tests
├── examples/           # Runnable demos
├── planning/           # Milestone logs
├── deepseek/           # Architecture documents
├── pyproject.toml
└── README.md
```
