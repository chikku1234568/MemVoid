# M6 Log

**Date:** 2026-06-28

**Objective:** Retrieval Engine — graph-native queries, no embeddings, no vector search.

**Files created (4):**
- `src/mem_void/retrieval/__init__.py` — exports current_facts, fact_history, related_entities, facts_at_time, facts_in_range
- `src/mem_void/retrieval/graph_traversal.py` — `related_entities()` — connected entities via active relationships
- `src/mem_void/retrieval/temporal.py` — `facts_at_time()` (point-in-time), `facts_in_range()` (range overlap)
- `tests/test_retrieval/test_retrieval.py` — 9 integration tests

**Verification:** 37/37 unit tests pass. 94 total tests collected.

**Design decisions:**
- `current_facts` and `fact_history` re-exported from repository (already implemented in M4)
- `related_entities` returns list of {entity, predicate} dicts — simple, no model overhead
- Temporal queries use interval overlap logic: `valid_from <= to AND (valid_to >= from OR valid_to IS NULL)`
- All retrieval is pure Cypher — no embeddings, no LLM, no vector search
