# M1 Log

**Date:** 2026-06-28

**What was done:** Project foundation — repository scaffold, dependency setup, Neo4j client, schema initialization.

**Files created (18):**
- `pyproject.toml` — build config, 3 runtime deps (`neo4j`, `pydantic`, `pydantic-settings`), 2 dev deps (`pytest`, `testcontainers`)
- `.env.example`, `.gitignore`, `README.md`
- `src/mem_void/__init__.py` — version string
- `src/mem_void/config/settings.py` — pydantic-settings, `MEMVOID_` prefix, `.env` auto-load
- `src/mem_void/graph/client.py` — `Neo4jClient` wrapper (driver, sessions, health_check, context manager)
- `src/mem_void/graph/schema.py` — `ensure_schema()` idempotent constraints + b-tree indexes
- `src/mem_void/models/__init__.py` — empty placeholder
- `tests/conftest.py` — session-scoped Neo4j 5.x testcontainer, client fixture
- `tests/test_config/test_settings.py` — 3 unit tests (pass, no Docker needed)
- `tests/test_graph/test_client.py` — 4 integration tests (need Docker)
- `tests/test_graph/test_schema.py` — 3 integration tests (need Docker)

**Verification:** 3/3 config tests pass. Integration tests require Docker. Package imports cleanly.

**Design decisions:** src layout, MEMVOID_ env prefix, Neo4j 5.x minimum, try/except fallback for older 5.x IF NOT EXISTS syntax.
