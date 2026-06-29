# mem-void

**Temporal Knowledge Graph Memory System** — a persistent, queryable memory layer for AI agents.

```
Raw Text → Entities → Temporal Facts → Neo4j Graph → Cypher Retrieval
```

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://python.org)
[![License MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

---

## Table of Contents

- [Why mem-void?](#why-mem-void)
- [What It Does](#what-it-does)
- [Quick Start](#quick-start)
- [Core Concepts](#core-concepts)
- [Architecture](#architecture)
- [Usage](#usage)
- [Graph Data Model](#graph-data-model)
- [Predicate System](#predicate-system)
- [Entity Resolution](#entity-resolution)
- [Testing](#testing)
- [Current Limitations](#current-limitations)
- [Future Roadmap](#future-roadmap)
- [Repository Structure](#repository-structure)

---

## Why mem-void?

AI agents today are **stateless**. Every conversation starts from zero. Existing solutions have gaps:

| Approach | Problem |
|----------|---------|
| Message logs / context windows | No structured querying. Can't ask "where did Alice work before OpenAI?" |
| Vector databases (RAG) | No temporal awareness. Facts have no notion of "before" vs "now." |
| Key-value stores | No graph structure. Can't traverse (Alice → Project Phoenix → teammates) |
| GraphRAG | Overkill for V1. Community detection, global summaries — heavy and slow. |

mem-void fills the gap: a **minimal, graph-native memory system** that tracks *what* happened, *when* it happened, and how entities *relate* — without embeddings, without vector search, without a research-grade framework.

### Design Philosophy

1. **Ship in one week** — every feature adding >1 day is deferred.
2. **Neo4j as source of truth** — no second database, no cache invalidation.
3. **Explicit temporality** — every fact has `valid_from` / `valid_to`. Nothing is implicitly "now."
4. **Library-first** — `from mem_void import Memory`. No servers, no HTTP, no API.
5. **Predicate-aware** — the system *knows* which facts are exclusive vs additive.
6. **Deterministic where possible** — entity resolution uses exact match, not vector similarity.

---

## What It Does

Given three raw text events:

```python
memory.ingest("Alice joined Acme")
memory.ingest("Alice works on Project Phoenix")
memory.ingest("Alice joined OpenAI")
```

The system automatically:

1. Creates **Episode** nodes (the raw events)
2. Extracts **Entity** nodes via LLM (Alice, Acme, OpenAI, Project Phoenix)
3. Resolves entities deterministically (no duplicates)
4. Extracts **Fact** relationships via LLM
5. Applies predicate-aware resolution — closes old WORKS_AT, preserves WORKS_ON
6. Supports **graph-native queries** — no embeddings, no semantic search

**Resulting graph:**
```
(Alice)-[:WORKS_AT {vf:2024-01, vt:2024-06}]->(Acme)    ← closed
(Alice)-[:WORKS_AT {vf:2024-06, vt:null}]->(OpenAI)      ← active
(Alice)-[:WORKS_ON {vf:2024-02, vt:null}]->(Project Phoenix) ← active
```

**Queries you can run:**
```python
current_facts(client, "Alice")
# → WORKS_AT → OpenAI, WORKS_ON → Project Phoenix

fact_history(client, "Alice", predicate="WORKS_AT")
# → OpenAI (active), Acme (closed at 2024-06)

related_entities(client, "Alice")
# → OpenAI, Project Phoenix

facts_at_time(client, "Alice", datetime(2024, 3, 1))
# → WORKS_AT → Acme  (she was at Acme in March)

facts_in_range(client, "Alice", datetime(2024, 1, 1), datetime(2024, 12, 31))
# → both Acme and OpenAI  (both overlapped 2024)
```

---

## Quick Start

### Prerequisites

- Python 3.10+
- Neo4j 5.x (Community Edition — free)
- OpenAI API key **or** Ollama (local, free)

### Setup

```bash
# Clone
git clone https://github.com/chikku1234568/MemVoid.git
cd MemVoid/mem-void

# Virtual environment
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
.\.venv\Scripts\Activate.ps1    # Windows

# Install
pip install -e ".[dev]"
cp .env.example .env
```

### Configure

Edit `.env`:

```env
# Neo4j
MEMVOID_NEO4J_URI=bolt://localhost:7687
MEMVOID_NEO4J_USER=neo4j
MEMVOID_NEO4J_PASSWORD=your-password-here

# LLM (pick one)
MEMVOID_LLM_PROVIDER=openai          # or: ollama
MEMVOID_LLM_MODEL=gpt-4o-mini        # or: llama3.2
MEMVOID_LLM_API_KEY=sk-...           # not needed for ollama
MEMVOID_LLM_BASE_URL=                # http://localhost:11434/v1 for ollama
```

### Start Neo4j

```bash
docker run -d --name memvoid-neo4j \
  -p 7687:7687 -p 7474:7474 \
  -e NEO4J_AUTH=neo4j/your-password-here \
  neo4j:5-community
```

### Run the Demo

```bash
python examples/alice_demo.py
```

Open Neo4j Browser at `http://localhost:7474` to inspect the graph visually.

---

## Core Concepts

### Episode

An **Episode** is the raw event — the text that was ingested. It answers: *"What did we observe?"*

```
(:Episode {
    uuid: "a1b2c3...",
    content: "Alice joined Acme",
    timestamp: 2024-01-15T00:00:00Z,
    source: null
})
```

Episodes are the **provenance** — every entity and fact links back to the episode that created it.

### Entity

An **Entity** is a real-world thing — a person, organization, project, location. It answers: *"Who or what was involved?"*

```
(:Entity {
    uuid: "d4e5f6...",
    name: "Alice",           ← unique, indexed
    entity_type: "PERSON",
    aliases: ["A. Smith"]
})
```

Entities are created once and reused. "Alice" mentioned in three episodes is still one Entity node.

### Fact

A **Fact** is a time-bounded relationship between two entities. It answers: *"What was true, and when?"*

Facts are stored as **Neo4j relationships** (edges), not nodes. The predicate *is* the relationship type.

```
(Alice)-[:WORKS_AT {
    uuid: "g7h8i9...",
    valid_from: 2024-01-15,
    valid_to: 2024-06-01,    ← null = still true
    episode_uuid: "a1b2c3..."
}]->(Acme)
```

**Why edges, not nodes?**

| Approach | Query | Hops |
|----------|-------|------|
| Facts as edges | `MATCH (a)-[:WORKS_AT]->(e) WHERE r.valid_to IS NULL` | 1 |
| Facts as nodes | `MATCH (a)-[:SUBJECT]->(f)-[:OBJECT]->(e)` | 2 |

Edges are natural in a property graph. Every predicate maps 1:1 to a relationship type. The graph is self-describing in Neo4j Browser.

---

## Architecture

```
src/mem_void/
│
├── config/                         # Settings from .env / env vars
│   └── settings.py                 #   pydantic-settings, MEMVOID_ prefix
│
├── models/                         # Pydantic v2 data models
│   ├── episode.py                  #   Episode (uuid, content, timestamp)
│   ├── entity.py                   #   Entity, EntitySpan
│   └── fact.py                     #   Fact (subject, predicate, object, valid_from/to)
│
├── graph/                          # Neo4j interaction (internal layer)
│   ├── client.py                   #   Neo4jClient — driver wrapper, sessions
│   ├── schema.py                   #   ensure_schema() — constraints + indexes
│   └── repository.py               #   CRUD functions: create_fact, current_facts, etc.
│
├── resolution/                     # Business logic
│   ├── entity_resolver.py          #   EntityResolver — exact name → alias → create
│   ├── fact_resolver.py            #   FactResolver — predicate-aware close + create
│   └── predicate_registry.py       #   EXCLUSIVE vs ADDITIVE predicate classification
│
├── ingestion/                      # LLM-powered extraction
│   ├── entity_extractor.py         #   extract_entities(text) → list[EntitySpan]
│   └── fact_extractor.py           #   extract_facts(text, entity_names) → list[triples]
│
├── retrieval/                      # Query layer (pure Cypher)
│   ├── graph_traversal.py          #   current_facts, fact_history, related_entities
│   └── temporal.py                 #   facts_at_time, facts_in_range
│
├── utils/
│   └── llm.py                      #   OpenAI/Ollama client wrapper
│
└── memory.py                       # Memory class — public API entry point
```

### Ingestion Pipeline

```
Memory.ingest("Alice joined Acme")
    │
    ├─ 1. Create Episode node (Neo4j)
    │
    ├─ 2. Entity Extraction (LLM)
    │      prompt → structured JSON → Pydantic TypeAdapter validation
    │      "Alice joined Acme" → [{name: "Alice", type: PERSON}, {name: "Acme", type: ORG}]
    │
    ├─ 3. Entity Resolution (deterministic)
    │      For each extracted span:
    │        a) Exact name match? → return existing Entity
    │        b) Alias match?      → return canonical Entity
    │        c) Otherwise         → MERGE create new Entity
    │
    ├─ 4. Fact Extraction (LLM)
    │      prompt + entity names → structured JSON → Pydantic TypeAdapter
    │      → [{subject: "Alice", predicate: "WORKS_AT", object: "Acme"}]
    │
    └─ 5. Fact Resolution (predicate-aware)
           For each extracted triple:
             EXCLUSIVE predicate? → close_active_facts(subject, predicate, now)
             ADDITIVE predicate?  → skip close
             create_fact(subject, predicate, object)
```

### Retrieval

All retrieval is **pure Cypher**. No embeddings. No vector search. No semantic similarity.

```python
from mem_void.retrieval import (
    current_facts,      # Active facts (valid_to IS NULL)
    fact_history,       # All facts, active + closed
    related_entities,   # Connected entities via active relationships
    facts_at_time,      # Snapshot at a point in time
    facts_in_range,     # Facts overlapping a time range
)
```

---

## Graph Data Model

### Nodes

```
(:Episode)            (:Entity)
  uuid: String*         uuid: String*
  content: String       name: String*      ← unique constraint
  timestamp: DateTime   entity_type: String
  source: String?       aliases: [String]
  created_at: DateTime  created_at: DateTime
```

`*` = unique constraint (prevents duplicates).

### Relationships

**Schema relationships** (provenance tracking):
```
(Entity)-[:EXTRACTED_FROM]->(Episode)
```

**Domain relationships** (facts — predicate IS the type):
```
(Entity)-[PREDICATE {
    uuid: String
    valid_from: DateTime
    valid_to: DateTime?     ← null = currently true
    episode_uuid: String
    confidence: Float?      ← extraction confidence (0.0–1.0)
}]->(Entity)
```

### Constraints & Indexes

```cypher
-- Constraints (enforce uniqueness)
CONSTRAINT episode_uuid_unique ON (e:Episode) ASSERT e.uuid IS UNIQUE
CONSTRAINT entity_uuid_unique  ON (e:Entity)  ASSERT e.uuid IS UNIQUE
CONSTRAINT entity_name_unique  ON (e:Entity)  ASSERT e.name IS UNIQUE

-- B-tree indexes (accelerate lookups)
INDEX entity_type_idx       ON (e:Entity)  BY e.entity_type
INDEX episode_timestamp_idx ON (e:Episode) BY e.timestamp
INDEX fact_valid_from_idx   ON ()-[r]-()   BY r.valid_from
INDEX fact_valid_to_idx     ON ()-[r]-()   BY r.valid_to
```

**No vector index.** No embeddings stored anywhere.

---

## Predicate System

The Predicate Registry classifies every relationship type:

### Exclusive Predicates

Only **one active fact** per (subject, predicate) can exist at a time. A new fact **closes** the old one.

| Predicate | Example |
|-----------|---------|
| `WORKS_AT` | Alice works at Acme → OpenAI (Acme closed) |
| `LIVES_IN` | Alice lives in SF → NYC (SF closed) |
| `LOCATED_IN` | Office in NY → SF (NY closed) |
| `REPORTS_TO` | Alice reports to Bob → Carol (Bob closed) |
| `HAS_TITLE` | Alice is Engineer → Senior Engineer |
| `HEADQUARTERED_IN` | Acme HQ: SF → Austin |

```
Event 1: "Alice joined Acme"
  → CREATE (Alice)-[:WORKS_AT {vf: Jan, vt: null}]->(Acme)

Event 2: "Alice joined OpenAI"
  → SET   (Alice)-[:WORKS_AT]->(Acme).valid_to = Jun
  → CREATE (Alice)-[:WORKS_AT {vf: Jun, vt: null}]->(OpenAI)
```

### Additive Predicates

Multiple active facts **coexist**. New facts never close old ones.

| Predicate | Example |
|-----------|---------|
| `WORKS_ON` | Alice works on Phoenix + Titan (both active) |
| `KNOWS` | Alice knows Bob + Carol (both active) |
| `USES` | Alice uses Python + React (both active) |
| `LIKES` | Alice likes coffee + tea |
| `HAS_SKILL` | Alice has skill: Python + React |
| `ATTENDED` | Alice attended Q1 planning + Q2 review |

### Unknown Predicates

Predicates not in either set default to **ADDITIVE** — safe-by-default. Never destroy data. The registry is extensible:

```python
# src/mem_void/resolution/predicate_registry.py
EXCLUSIVE_PREDICATES.add("MARRIED_TO")
ADDITIVE_PREDICATES.add("SUBSCRIBED_TO")
```

---

## Entity Resolution

Deterministic, no embeddings. Three-step lookup:

```
resolve("Microsoft")
  │
  ├─ 1. Exact name match (indexed, O(1))
  │      MATCH (e:Entity {name: "Microsoft"})
  │      → found? return it
  │
  ├─ 2. Alias lookup (scans all alias lists)
  │      MATCH (e:Entity) WHERE "Microsoft" IN e.aliases
  │      → found? return canonical entity
  │
  └─ 3. Create new entity (MERGE, concurrency-safe)
         MERGE (e:Entity {name: "Microsoft"})
         ON CREATE SET ...
```

Step 3 uses Neo4j's `MERGE` with the `entity_name_unique` constraint — two concurrent threads both trying to create "Microsoft" will end up with the same node.

**Why not embeddings?** Embeddings add 80MB+ of model weights, cosine similarity thresholds to tune, and vector index maintenance — for marginal gain over V1's simple approach. Deterministic resolution is fast, predictable, and trivially debuggable.

---

## Testing

```bash
# Unit tests — no Docker, no LLM, <1 second (43 tests)
pytest tests/test_config/ tests/test_models/ \
       tests/test_resolution/test_predicate_registry.py \
       tests/test_resolution/test_fact_resolver.py \
       tests/test_ingestion/test_extractors.py -v

# All tests — requires Docker for Neo4j container (103 tests)
pytest -v
```

### Test Architecture

| Layer | Tests | Requires | Fixture |
|-------|-------|----------|---------|
| Config | 3 | Nothing | `Settings(_env_file=None)` |
| Models | 24 | Nothing | Direct instantiation |
| Resolution (unit) | 10 | Nothing | `unittest.mock.patch` |
| Graph (integration) | 35 | Docker | Session-scoped Neo4j 5.x container |
| Resolution (integration) | 14 | Docker | Session-scoped Neo4j container |
| Ingestion | 9 | Docker + mocked LLM | `patch("...generate", ...)` |
| Retrieval | 9 | Docker | Session-scoped Neo4j container |

---

## Current Limitations

These are **explicitly deferred**, not bugs.

| Limitation | Why | Mitigation |
|-----------|-----|------------|
| No semantic search | V1 is graph-native only | Caller can layer embeddings on top |
| No fuzzy entity matching | Deterministic resolution | Pre-seed aliases; V2 can add embedding fallback |
| No explicit fact negation | "Alice left Acme" needs a new employer to close old | Frame events as transitions |
| No REST API | Library-first design | V2 thin FastAPI wrapper |
| No async support | Synchronous is simpler | Add `AsyncMemory` in V2 |
| No batch ingestion | One event at a time | Loop in caller code |
| Retrieval not wired into `Memory` class | Use `memory._client` directly | V2 will add convenience methods |
| Multi-agent isolation | Single graph | V2: add `agent_id` partitioning |

---

## Future Roadmap

### V1.1 (Next)
- Wire retrieval into `Memory` class (`memory.current_facts("Alice")`)
- Add `memory.fact_history()`, `memory.related_entities()`
- Batch ingest: `memory.ingest_many([...])`

### V2 (Planned)
- **Embedding-based entity resolution** — optional fuzzy matching fallback
- **Semantic retrieval** — embed queries, search entities by concept
- **REST API** — thin FastAPI wrapper
- **Async support** — `AsyncMemory`, `AsyncNeo4jClient`
- **Multi-agent isolation** — partition entities/facts by `agent_id`
- **Explicit fact negation** — recognize "left", "quit", "no longer" patterns
- **Confidence-weighted ranking** — use extraction confidence in retrieval ordering

### V3+ (Ideas)
- **Reflection / introspection** — the system reasons about its own knowledge gaps
- **Causal graphs** — cause-effect chains and counterfactuals
- **Memory consolidation** — summarize old episodes, merge redundant facts
- **Community detection** — discover entity clusters (teams, departments)
- **Streaming ingestion** — real-time event processing via Kafka/webhooks

---

## Repository Structure

```
mem-void/
├── src/mem_void/       # Package source (14 modules)
├── tests/              # 103 tests across 6 test packages
├── examples/           # alice_demo.py — canonical V1 demo
├── planning/           # Milestone logs (local only, gitignored)
├── deepseek/           # Architecture documents (local only, gitignored)
├── pyproject.toml      # Build + dependencies
├── .env.example        # Configuration template
└── README.md
```

## License

MIT
