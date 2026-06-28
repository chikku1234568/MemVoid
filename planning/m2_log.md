# M2 Log

**Date:** 2026-06-28

**What was done:** Entity storage layer — Pydantic models for Episode and Entity, Neo4j CRUD repository, model + integration tests.

**Files created (6):**
- `src/mem_void/models/episode.py` — `Episode` (uuid, content, timestamp, source, created_at)
- `src/mem_void/models/entity.py` — `Entity` (uuid, name, entity_type, aliases, created_at) + `EntitySpan` (name, type, char offsets)
- `src/mem_void/graph/repository.py` — `create_episode()`, `upsert_entity()`, `entity_by_name()`
- `tests/test_models/test_episode.py` — 4 unit tests
- `tests/test_models/test_entity.py` — 6 unit tests (Entity + EntitySpan)
- `tests/test_graph/test_repository.py` — 8 integration tests (need Docker)

**Files updated (2):**
- `src/mem_void/models/__init__.py` — exports Episode, Entity, EntitySpan
- `src/mem_void/graph/__init__.py` — exports create_episode, upsert_entity, entity_by_name

**Verification:** 13/13 unit tests pass (10 new model tests + 3 existing config tests). All imports verified clean.

**Design decisions:**
- `datetime.now(timezone.utc)` instead of deprecated `utcnow()`
- UUID stored as string in Neo4j (no native UUID type), converted in repository layer
- `MERGE ... ON CREATE` pattern for idempotent upsert
- `entity_by_name` uses exact name match on unique constraint — the foundation for deterministic resolution in M3
- Repository functions are standalone (no class), take Neo4jClient as first argument
