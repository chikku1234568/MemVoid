# M1 + M2 Implementation Plan

## 1. Repository Structure

Modern `src` layout. Package is `mem_void` (underscore for Python). Repository root is `mem-void` (hyphen for PyPI/GitHub).

```
mem-void/
├── src/
│   └── mem_void/
│       ├── __init__.py              # Empty; version string only
│       │
│       ├── config/
│       │   ├── __init__.py          # Empty
│       │   └── settings.py          # Settings (pydantic-settings)
│       │
│       ├── graph/
│       │   ├── __init__.py          # Empty
│       │   ├── client.py            # Neo4jClient
│       │   ├── schema.py            # ensure_schema()
│       │   └── repository.py        # CRUD (episode, entity)
│       │
│       └── models/
│           ├── __init__.py          # Re-exports Episode, Entity
│           ├── episode.py           # Episode model
│           └── entity.py            # Entity, EntitySpan models
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                  # Neo4j container fixture + client fixture
│   ├── test_graph/
│   │   ├── test_client.py
│   │   ├── test_schema.py
│   │   └── test_repository.py
│   └── test_models/
│       ├── test_episode.py
│       └── test_entity.py
│
├── .venv/                           # Virtual environment (gitignored)
├── .env.example                     # Template — committed to repo
├── .env                             # Actual secrets (gitignored)
├── .gitignore
├── pyproject.toml
└── README.md
```

**What is NOT created yet** (deferred to M3+):
- `ingestion/` — no extraction, no LLM calls
- `resolution/` — entity resolver skeleton only in M2; no fact resolver yet
- `retrieval/` — M5 territory
- `utils/llm.py` — M3 territory
- `examples/` — M6 territory

**For M1 + M2, only these directories exist:**
```
src/mem_void/
├── config/
├── graph/
├── models/
```

---

## 2. pyproject.toml

```toml
[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "mem-void"
version = "0.1.0"
description = "Temporal Knowledge Graph Memory System"
requires-python = ">=3.10"
readme = "README.md"
license = {text = "MIT"}
authors = [{name = "MemVoid Contributors"}]
dependencies = [
    "neo4j>=5.14,<6.0",
    "pydantic>=2.0,<3.0",
    "pydantic-settings>=2.0,<3.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0,<9.0",
    "testcontainers>=4.0,<5.0",
]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

[tool.setuptools.package-data]
"*" = ["py.typed"]
```

### Dependency Justification

| Package | Why | When needed |
|---------|-----|-------------|
| `neo4j` | Python driver for Neo4j | M1 (connection, schema, queries) |
| `pydantic` | Data validation, serialization | M1 (Episode, Entity models) |
| `pydantic-settings` | .env + env var config loading | M1 (Settings) |
| `pytest` | Test framework | M1 (test from day one) |
| `testcontainers` | Spin up Neo4j Docker for tests | M1 (integration tests) |

**Packages intentionally omitted from V1 pyproject.toml:**
- `openai` / `ollama` — added in M3 when LLM extraction begins
- `sentence-transformers` — never; no embeddings in V1
- `fastapi` / `uvicorn` — never; no API in V1
- `python-dotenv` — not needed; pydantic-settings reads .env natively

---

## 3. Configuration System

File: `src/mem_void/config/settings.py`

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="MEMVOID_",
        case_sensitive=False,
    )

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = ""
    neo4j_database: str = "neo4j"
```

**Key decisions:**
- `env_prefix="MEMVOID_"` — all env vars prefixed: `MEMVOID_NEO4J_URI`, `MEMVOID_NEO4J_PASSWORD`. Prevents collision with other projects.
- `neo4j_password` has no default (empty string) — forces the user to set it. In test environments, it defaults to "password" via the test fixture.
- No LLM settings yet — those appear in M3.
- No predicate registry settings yet — those appear in M4.

---

## 4. Environment Variable Strategy

### .env.example (committed)

```
# Neo4j Connection
MEMVOID_NEO4J_URI=bolt://localhost:7687
MEMVOID_NEO4J_USER=neo4j
MEMVOID_NEO4J_PASSWORD=change-me
MEMVOID_NEO4J_DATABASE=neo4j
```

### .env (gitignored, never committed)

User copies `.env.example` to `.env` and fills in their password.

### Test environment

In `conftest.py`, the Settings object is constructed programmatically (not from .env):

```python
import pytest
from mem_void.config import Settings

@pytest.fixture(scope="session")
def settings(neo4j_container):
    return Settings(
        neo4j_uri=neo4j_container.get_connection_url(),
        neo4j_user="neo4j",
        neo4j_password="password",
        _env_file=None,  # Don't read .env in tests
    )
```

### Why this works

- **Development**: Copy `.env.example` → `.env`, fill in password, `Settings()` auto-loads it.
- **CI/Production**: Set `MEMVOID_NEO4J_URI` etc. as actual env vars. pydantic-settings reads env vars with higher priority than `.env`.
- **Testing**: Construct `Settings` directly with test values; no file I/O.

### Priority (pydantic-settings defaults)

1. Constructor arguments (highest)
2. Environment variables
3. `.env` file
4. Field defaults (lowest)

---

## 5. Neo4j Client Design

File: `src/mem_void/graph/client.py`

```python
from __future__ import annotations

from neo4j import GraphDatabase, Driver, Session, Result

from mem_void.config import Settings


class Neo4jClient:
    """Thin wrapper around neo4j.Driver with session management."""

    def __init__(self, settings: Settings) -> None:
        self._driver: Driver = GraphDatabase.driver(
            settings.neo4j_uri,
            auth=(settings.neo4j_user, settings.neo4j_password),
        )
        self._database: str = settings.neo4j_database

    @property
    def database(self) -> str:
        return self._database

    def health_check(self) -> bool:
        """Verify the driver can reach Neo4j."""
        try:
            self._driver.verify_connectivity()
            return True
        except Exception:
            return False

    def session(self, *, read_only: bool = False, **kwargs) -> Session:
        """Get a session. Use read_only=True for queries, False for writes."""
        default_db = {"database": self._database}
        return self._driver.session(**default_db, **kwargs)

    def write_session(self, **kwargs) -> Session:
        """Get a write session (convenience)."""
        return self._driver.session(
            database=self._database,
            default_access_mode="WRITE",
            **kwargs,
        )

    def read_session(self, **kwargs) -> Session:
        """Get a read session (convenience)."""
        return self._driver.session(
            database=self._database,
            default_access_mode="READ",
            **kwargs,
        )

    def close(self) -> None:
        self._driver.close()

    def __enter__(self) -> Neo4jClient:
        return self

    def __exit__(self, *args) -> None:
        self.close()
```

### Design Decisions

**Why not a connection pool manager?** The neo4j Python driver has built-in connection pooling. `driver.session()` returns a lightweight session that borrows a connection from the pool. No manual pool management needed.

**Why separate `session()`, `read_session()`, `write_session()`?** The neo4j driver supports routing to read replicas in a cluster via `default_access_mode`. For V1 (single-node Community Edition), this doesn't matter, but the API surface is correct for future scaling.

**Why no `execute_query()` convenience method?** The repository layer (M2) will have higher-level methods. The client stays thin — connection management only.

**Why `verify_connectivity()` for health check?** It's the canonical Neo4j driver method. It sends a lightweight message to confirm the server is reachable and authenticated.

**What about async?** Deferred. V1 is synchronous. Adding async support means `AsyncNeo4jClient` and `AsyncGraphDatabase.driver()`. This is straightforward to add later without breaking the sync API.

---

## 6. Core Pydantic Models

### Episode

File: `src/mem_void/models/episode.py`

```python
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Episode(BaseModel):
    """A discrete event ingested into the memory system."""

    uuid: UUID = Field(default_factory=uuid4)
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

### Entity

File: `src/mem_void/models/entity.py`

```python
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Entity(BaseModel):
    """A person, organization, project, location, or other real-world thing."""

    uuid: UUID = Field(default_factory=uuid4)
    name: str
    entity_type: str = "UNKNOWN"
    aliases: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EntitySpan(BaseModel):
    """An entity extracted from episode text (before resolution)."""

    name: str
    entity_type: str = "UNKNOWN"
    start_char: int | None = None
    end_char: int | None = None
```

### Model Design Notes

**UUID as Python `UUID`, not `str`.** Pydantic handles serialization. For Neo4j, UUIDs are stored as strings (Neo4j has no native UUID type). The repository layer converts: `str(entity.uuid)` on write, `UUID(record["uuid"])` on read.

**`datetime.now(timezone.utc)` instead of `datetime.utcnow()`.** The latter is deprecated in Python 3.12. The `timezone.utc` approach works from 3.10+.

**`entity_type` defaults to `"UNKNOWN"`.** The LLM extractor (M3) will populate this. Default is safe.

**`EntitySpan` has character offsets.** These are populated by the LLM extractor when available. Useful for debugging which part of the text produced an entity. Nullable for when the extractor doesn't provide them.

**No `EntityResolutionResult` yet.** That model appears when entity resolution logic is implemented (M2 full).

### models/__init__.py

```python
from mem_void.models.episode import Episode
from mem_void.models.entity import Entity, EntitySpan

__all__ = ["Episode", "Entity", "EntitySpan"]
```

---

## 7. Development Workflow

### Initial Setup (once)

```powershell
# 1. Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install in editable mode with dev deps
pip install -e ".[dev]"

# 3. Start Neo4j via Docker
docker run -d --name memvoid-neo4j `
  -p 7687:7687 -p 7474:7474 `
  -e NEO4J_AUTH=neo4j/password `
  neo4j:5-community

# 4. Copy and configure environment
copy .env.example .env
# Edit .env if password is not "password"
```

### Daily Workflow

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Run tests (requires Docker running)
pytest

# Run tests without integration tests
pytest tests/test_models/ tests/test_graph/test_client.py

# Run only unit tests (no Docker needed)
pytest tests/test_models/

# Format / lint (to be added after initial scaffold)
# ruff check src/ tests/
# ruff format src/ tests/
```

### Schema Initialization

Schema is initialized programmatically, not via a migration tool. `ensure_schema()` is called:
- Once at application startup (lazy; first use)
- In tests, via a fixture (before each integration test)

No external migration framework. The schema is idempotent — running it twice is safe.

---

## 8. Testing Strategy

### Test Layers

| Layer | What it tests | Requires Neo4j | Requires Docker |
|-------|--------------|----------------|-----------------|
| **Unit (models)** | Pydantic validation, serialization, defaults | No | No |
| **Unit (schema)** | Constraint/index creation, idempotency | Yes | Yes |
| **Integration (graph)** | Neo4j client, schema, repository CRUD | Yes | Yes |

### conftest.py

File: `tests/conftest.py`

```python
from __future__ import annotations

import pytest
from testcontainers.neo4j import Neo4jContainer

from mem_void.config import Settings
from mem_void.graph import Neo4jClient


@pytest.fixture(scope="session")
def neo4j_container():
    """Session-scoped Neo4j container. Shared across all integration tests."""
    container = Neo4jContainer(
        image="neo4j:5-community",
        username="neo4j",
        password="password",
    )
    container.start()
    yield container
    container.stop()


@pytest.fixture(scope="session")
def settings(neo4j_container: Neo4jContainer):
    """Settings pointing at the test container."""
    return Settings(
        neo4j_uri=neo4j_container.get_connection_url(),
        neo4j_user="neo4j",
        neo4j_password="password",
    )


@pytest.fixture(scope="session")
def neo4j_client(settings: Settings):
    """Session-scoped Neo4j client connected to test container."""
    client = Neo4jClient(settings)
    yield client
    client.close()
```

### Test File: tests/test_graph/test_client.py

```python
from mem_void.graph import Neo4jClient


class TestNeo4jClient:
    def test_health_check_passes(self, neo4j_client: Neo4jClient):
        assert neo4j_client.health_check() is True

    def test_session_executes_cypher(self, neo4j_client: Neo4jClient):
        with neo4j_client.session() as session:
            result = session.run("RETURN 1 AS n")
            record = result.single()
            assert record["n"] == 1

    def test_context_manager(self, settings):
        with Neo4jClient(settings) as client:
            assert client.health_check() is True
```

### Test File: tests/test_graph/test_schema.py

```python
from mem_void.graph import Neo4jClient, ensure_schema


class TestEnsureSchema:
    def test_creates_constraints(self, neo4j_client: Neo4jClient):
        ensure_schema(neo4j_client)

        with neo4j_client.session() as session:
            constraints = session.run("SHOW CONSTRAINTS").data()
            constraint_names = [c["name"] for c in constraints]

        assert "episode_uuid_unique" in constraint_names
        assert "entity_uuid_unique" in constraint_names
        assert "entity_name_unique" in constraint_names

    def test_idempotent(self, neo4j_client: Neo4jClient):
        ensure_schema(neo4j_client)
        ensure_schema(neo4j_client)  # Must not raise
        ensure_schema(neo4j_client)  # Three times is fine

    def test_creates_indexes(self, neo4j_client: Neo4jClient):
        ensure_schema(neo4j_client)

        with neo4j_client.session() as session:
            indexes = session.run("SHOW INDEXES").data()
            index_names = [i["name"] for i in indexes]

        assert "entity_type_idx" in index_names
```

### Test File: tests/test_models/test_episode.py

```python
from mem_void.models import Episode


class TestEpisode:
    def test_defaults(self):
        ep = Episode(content="Alice joined Acme")
        assert ep.uuid is not None
        assert ep.content == "Alice joined Acme"
        assert ep.timestamp is not None
        assert ep.source is None
        assert ep.created_at is not None

    def test_custom_timestamp(self,):
        from datetime import datetime, timezone
        ts = datetime(2024, 1, 15, tzinfo=timezone.utc)
        ep = Episode(content="Test", timestamp=ts)
        assert ep.timestamp == ts
```

### Test File: tests/test_models/test_entity.py

```python
from mem_void.models import Entity


class TestEntity:
    def test_defaults(self):
        e = Entity(name="Alice", entity_type="PERSON")
        assert e.uuid is not None
        assert e.name == "Alice"
        assert e.entity_type == "PERSON"
        assert e.aliases == []
        assert e.created_at is not None

    def test_unknown_type_default(self):
        e = Entity(name="Something")
        assert e.entity_type == "UNKNOWN"
```

### Running Tests

```powershell
# All tests (needs Docker running)
pytest -v

# Unit tests only (no Docker needed)
pytest tests/test_models/ -v

# Integration tests only
pytest tests/test_graph/ -v
```

---

## 9. Architecture Refinements Before Implementation

These are changes to the architecture documents that should be made, or decisions that differ from the current architecture docs.

### 9a. Package Name: tcmg → mem_void

The architecture docs use `tcmg` as the package name. The project is now called `mem-void`. The Python package is `mem_void`. All imports change:

```python
# Old
from tcmg.graph import Neo4jClient

# New
from mem_void.graph import Neo4jClient
```

This is a simple rename. No structural changes needed.

### 9b. Neo4j Version: 5.x Minimum

The revised architecture says "Neo4j 4.x+ works fine since no vector indexes." While true, targeting 4.x means:
- Constraint `IF NOT EXISTS` syntax differs (not available in 4.x)
- `SHOW CONSTRAINTS` / `SHOW INDEXES` syntax may differ
- testcontainers must pin a 4.x image

**Recommendation:** Target Neo4j 5.x (Community Edition). It's been stable since 2022, the Docker image is the same size, and the Cypher syntax is cleaner. The `IF NOT EXISTS` constraint syntax works from 5.7+. This costs nothing and avoids conditional code paths.

**Change:** Update `pyproject.toml` to `"neo4j>=5.14,<6.0"`. Update architecture docs to say "Neo4j 5.x+".

### 9c. src Layout

The architecture shows `tcmg/` as the package directory directly in the repo root (flat layout). This is fine but `src` layout is now the modern Python standard:

| Aspect | Flat layout | src layout |
|--------|-------------|------------|
| Import during dev | `import tcmg` (may import local dir, not installed pkg) | `import mem_void` (must install with `pip install -e .`) |
| Accidental shadowing | Risk of importing wrong dir | No — `src/` is not on path |
| PyPI publishing | Works | Works |
| Tooling support | Good | Better (mypy, ruff, pytest support src layout natively) |

**Recommendation:** Use `src` layout. Add `"pip install -e ."` to the dev setup step. The `pyproject.toml` includes `[tool.setuptools.packages.find] where = ["src"]`.

### 9d. env_prefix

The architecture shows env vars without a prefix (`NEO4J_URI`, `NEO4J_USER`, etc.). In practice, these are generic names that might collide with other tools.

**Recommendation:** Prefix all env vars with `MEMVOID_`: `MEMVOID_NEO4J_URI`, `MEMVOID_NEO4J_USER`, etc. This is trivial with pydantic-settings' `env_prefix` config.

### 9e. Schema Module: Idempotency Strategy

The architecture says `ensure_schema()` is idempotent. Implementation approach:

```python
def ensure_schema(client: Neo4jClient) -> None:
    statements = [
        "CREATE CONSTRAINT episode_uuid_unique IF NOT EXISTS FOR (e:Episode) REQUIRE e.uuid IS UNIQUE",
        "CREATE CONSTRAINT entity_uuid_unique  IF NOT EXISTS FOR (e:Entity)  REQUIRE e.uuid IS UNIQUE",
        "CREATE CONSTRAINT entity_name_unique  IF NOT EXISTS FOR (e:Entity)  REQUIRE e.name IS UNIQUE",
        "CREATE INDEX entity_type_idx       IF NOT EXISTS FOR (e:Entity)  ON (e.entity_type)",
        "CREATE INDEX episode_timestamp_idx IF NOT EXISTS FOR (e:Episode) ON (e.timestamp)",
    ]
    with client.session() as session:
        for stmt in statements:
            session.run(stmt)
```

For Neo4j < 5.7, `IF NOT EXISTS` is not available. The fallback is `SHOW CONSTRAINTS` to check existence, or catch the error. Since we're targeting Neo4j 5.x, `IF NOT EXISTS` works for 5.7+. For 5.0-5.6, we need try/except. The simplest approach that covers all 5.x:

```python
from neo4j.exceptions import ClientError

def ensure_schema(client: Neo4jClient) -> None:
    with client.session() as session:
        for stmt in statements:
            try:
                session.run(stmt)
            except ClientError as e:
                if "already exists" in str(e).lower():
                    continue  # Idempotent — constraint/index already there
                raise
```

**Recommendation:** Use try/except for Neo4j 5.x compatibility. Drop the fallback once 5.7+ is the minimum (when 5.6 goes EOL). The performance hit is negligible (only called once at startup).

### 9f. Repository Layer Scope for M1-M2

The architecture lists `graph/repository.py` with methods: `create_episode`, `upsert_entity`, `entity_by_name`, `entity_by_alias`, `create_fact`, `close_fact`, `get_active_facts`, `get_fact_history`.

**For M1-M2, implement only:**
- `create_episode(client, episode: Episode) -> None`
- `upsert_entity(client, entity: Entity) -> None`
- `entity_by_name(client, name: str) -> Entity | None`

**Deferred to M3+** : fact-related methods.

Each repository method is a standalone function (not a class) that takes `client` as the first argument. This is simpler than a Repository class with DI and allows the resolution/ingestion layers to call individual functions.

### 9g. Timezone Handling

Neo4j's `DateTime` type stores timezone-aware timestamps. Python's `datetime` with `timezone.utc` maps cleanly. All timestamps in the system should be UTC:
- `Episode.timestamp` — UTC
- `Episode.created_at` — UTC
- `Entity.created_at` — UTC
- Later: `FactRelation.valid_from`, `FactRelation.valid_to` — UTC

The `lambda: datetime.now(timezone.utc)` pattern in Pydantic defaults enforces this. The `pytz` library is not needed — Python 3.10's `zoneinfo` is sufficient, and `datetime.timezone.utc` is zero-dependency.

### 9h. Gitignore Strategy

```
# Python
__pycache__/
*.pyc
*.pyo
*.egg-info/
dist/
build/
*.egg

# Virtual environment
.venv/
venv/

# Environment
.env

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Testing
.pytest_cache/
.coverage
htmlcov/
```

---

## Acceptance Test for This Phase

When M1 + M2 structural scaffolding is complete, this must pass:

```python
from mem_void.config import Settings
from mem_void.graph import Neo4jClient, ensure_schema
from mem_void.models import Episode, Entity

# --- M1 Verification ---

client = Neo4jClient(Settings())
assert client.health_check()

ensure_schema(client)

with client.session() as session:
    result = session.run("SHOW CONSTRAINTS")
    names = [r["name"] for r in result]
assert "entity_name_unique" in names
assert "episode_uuid_unique" in names

# --- M2 Structural Verification (models exist and validate) ---

ep = Episode(content="Alice joined Acme")
assert ep.uuid is not None
assert ep.content == "Alice joined Acme"
assert ep.timestamp is not None

ent = Entity(name="Alice", entity_type="PERSON")
assert ent.name == "Alice"
assert ent.entity_type == "PERSON"
assert ent.aliases == []

# --- M2 Repository Verification (basic CRUD works) ---

from mem_void.graph.repository import create_episode, upsert_entity, entity_by_name

ep = Episode(content="Test event")
create_episode(client, ep)

ent = Entity(name="TestOrg", entity_type="ORG")
upsert_entity(client, ent)

found = entity_by_name(client, "TestOrg")
assert found is not None
assert found.name == "TestOrg"
assert found.entity_type == "ORG"

# --- Cleanup ---
client.close()
print("M1 + M2 scaffold verified.")
```

---

## Summary: Files to Create

| File | Purpose | Phase |
|------|---------|-------|
| `pyproject.toml` | Build config, deps | Create now |
| `.env.example` | Template for env vars | Create now |
| `.gitignore` | Ignore rules | Create now |
| `README.md` | Minimal project readme | Create now |
| `src/mem_void/__init__.py` | Package init | Create now |
| `src/mem_void/config/__init__.py` | Empty init | Create now |
| `src/mem_void/config/settings.py` | Settings class | Create now |
| `src/mem_void/graph/__init__.py` | Empty init | Create now |
| `src/mem_void/graph/client.py` | Neo4jClient | Create now |
| `src/mem_void/graph/schema.py` | ensure_schema() | Create now |
| `src/mem_void/graph/repository.py` | Episode + Entity CRUD | Create now |
| `src/mem_void/models/__init__.py` | Re-exports | Create now |
| `src/mem_void/models/episode.py` | Episode model | Create now |
| `src/mem_void/models/entity.py` | Entity, EntitySpan | Create now |
| `tests/__init__.py` | Empty | Create now |
| `tests/conftest.py` | Neo4j container fixture | Create now |
| `tests/test_graph/test_client.py` | Client tests | Create now |
| `tests/test_graph/test_schema.py` | Schema tests | Create now |
| `tests/test_graph/test_repository.py` | Repository tests | Create now |
| `tests/test_models/test_episode.py` | Episode model tests | Create now |
| `tests/test_models/test_entity.py` | Entity model tests | Create now |

**Total: 21 files.** 14 source files, 7 test files. All are small (<50 lines each except repository.py and conftest.py).
