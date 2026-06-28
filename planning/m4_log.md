# M4 Log

**Date:** 2026-06-28

**What was done:** Fact model and storage layer — facts stored as Neo4j relationships with temporal bounds.

**Files created (3):**
- `src/mem_void/models/fact.py` — `Fact` model (uuid, subject, predicate, object, valid_from/to, episode_uuid, confidence, created_at)
- `tests/test_models/test_fact.py` — 14 unit tests
- `tests/test_graph/test_fact_repository.py` — 13 integration tests

**Files updated (2):**
- `src/mem_void/graph/repository.py` — added `create_fact()`, `current_facts()`, `fact_history()`
- `src/mem_void/graph/__init__.py` — exports new functions
- `src/mem_void/models/__init__.py` — exports Fact

**Design decision — Facts as edges:**
- Predicate becomes Neo4j relationship type: `(Alice)-[:WORKS_AT]->(Acme)`
- Temporal bounds (`valid_from`, `valid_to`) stored as relationship properties
- Queries are natural: `MATCH (a)-[r:WORKS_AT]->(e) WHERE r.valid_to IS NULL`
- Dynamic relationship types use validated string interpolation (regex: `^[A-Z][A-Z0-9_]*$`)
- Episode provenance tracked via `episode_uuid` property on relationship

**Trade-off accepted:** Relationships can't link to Episode nodes for provenance (Neo4j limitation). Tracked via property. Reification (facts-as-nodes) can be added in V2 if needed.

**Verification:** 33/33 unit tests pass. 35 integration tests require Docker (infrastructure ready). 68 total tests collected.

**What was NOT implemented:** Predicate-aware invalidation (M5). `create_fact()` creates relationships without closing old ones.
