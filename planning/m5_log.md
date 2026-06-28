# M5 Log

**Date:** 2026-06-28

**Objective:** Predicate-aware Fact Resolution — temporal consistency via Predicate Registry.

**Files created (5):**
- `src/mem_void/resolution/predicate_registry.py` — EXCLUSIVE/ADDITIVE predicate sets + `is_exclusive()`/`is_additive()`
- `src/mem_void/resolution/fact_resolver.py` — `FactResolver` class — orchestrates close + create
- `tests/test_resolution/test_predicate_registry.py` — 4 unit tests
- `tests/test_resolution/test_fact_resolver.py` — 6 unit tests (mocked)
- `tests/test_resolution/test_fact_resolver_integration.py` — 8 integration tests

**Files modified (3):**
- `src/mem_void/graph/repository.py` — added `close_active_facts(subject, predicate, closed_at)`
- `src/mem_void/resolution/__init__.py` — exports FactResolver, predicate registry functions
- `src/mem_void/graph/__init__.py` — exports close_active_facts

**Verification:** 37/37 unit tests pass. 85 total tests collected (48 integration need Docker).

**Design decisions:**
- **Default: ADDITIVE** — Unknown predicates never destroy data. Safe-by-default.
- **Separate `close_active_facts` in repository** — keeps Cypher in the data layer; resolver is pure orchestration
- **Closes ALL active facts for (subject, predicate)** — handles pre-M5 state where multiple active facts may exist
- **Exclusive close is predicate-scoped only** — changing `WORKS_AT` doesn't affect `LIVES_IN`, `WORKS_ON`, etc.
- **Exclusive close is subject-scoped** — Alice changing jobs doesn't affect Bob's employment facts

**Tests added:**
- Unit: 4 predicate registry + 6 fact resolver (mocked) = 10
- Integration: 8 fact resolver (real Neo4j) — exclusive close, additive preserve, mixed, multi-close, different subjects, different predicates

**Known limitations:**
- Predicate registry is code-based (not DB-backed); adding a predicate requires a code change
- No explicit fact negation ("Alice left Acme" without new employer)
- No predicate configuration via env vars yet (planned M6)
