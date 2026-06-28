# M3 Log

**Date:** 2026-06-28

**What was done:** Deterministic Entity Resolution — `EntityResolver` class with three-step resolution strategy.

**Files created (4):**
- `src/mem_void/resolution/__init__.py` — exports EntityResolver
- `src/mem_void/resolution/entity_resolver.py` — EntityResolver class
- `tests/test_resolution/test_entity_resolver.py` — 6 unit tests + 6 integration tests

**Files updated (2):**
- `src/mem_void/graph/repository.py` — added `entity_by_alias()` function
- `src/mem_void/graph/__init__.py` — exports entity_by_alias

**Resolution strategy (deterministic, ordered):**
1. Exact canonical name match → returns existing Entity
2. Alias lookup (full scan of `Entity.aliases` lists) → returns canonical Entity
3. Create new Entity via `upsert_entity()` (MERGE-safe)

**Verification:** 19/19 unit tests pass. 6 integration tests require Docker (infrastructure ready).

**Design decisions:**
- Class-based (`EntityResolver(client)`) for testability — mock repository functions in unit tests
- `entity_by_alias` uses `WHERE $name IN e.aliases` — full scan, acceptable for V1 entity counts
- Exact name takes priority over alias match (edge case: "Microsoft" could be both a canonical name AND an alias)
- `entity_type` parameter only used on creation; ignored when entity already exists (avoids accidental type mutation)
