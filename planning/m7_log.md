# M7 Log

**Date:** 2026-06-28

**Objective:** Event Ingestion Pipeline — connect all components: text → entities → facts → Neo4j.

**Files created (7):**
- `src/mem_void/utils/__init__.py` — (implicit)
- `src/mem_void/utils/llm.py` — LLM client (OpenAI/Ollama), `generate(settings, prompt) -> str`
- `src/mem_void/ingestion/entity_extractor.py` — `extract_entities(settings, text) -> list[EntitySpan]`
- `src/mem_void/ingestion/fact_extractor.py` — `extract_facts(settings, text, entity_names) -> list[ExtractedTriple]`
- `src/mem_void/memory.py` — `Memory` class: `ingest(text)` pipeline + `IngestResult`
- `tests/test_ingestion/test_extractors.py` — 6 unit tests (mocked LLM)
- `tests/test_ingestion/test_pipeline.py` — 3 integration tests (mocked LLM + real Neo4j)

**Files modified (4):**
- `src/mem_void/__init__.py` — exports `Memory`, `Settings`
- `src/mem_void/config/settings.py` — added `llm_provider`, `llm_model`, `llm_api_key`, `llm_base_url`
- `pyproject.toml` — added `openai>=1.0` dependency
- `.env.example` — added LLM config vars

**Pipeline:** `memory.ingest(text)` → `Episode` → `extract_entities()` → `EntityResolver.resolve()` → `extract_facts()` → `FactResolver.resolve()` → Neo4j

**Design decisions:**
- **LLM via OpenAI-compatible API** — `openai` package works with both OpenAI and Ollama (via `base_url`)
- **JSON via Pydantic TypeAdapter** — structured prompts, validated output, never raw `json.loads` on untrusted data
- **Malformed JSON → empty list** — extraction failures are silent (loggable), pipeline continues
- **Memory.ingest() returns IngestResult** — counts of entities/facts created for observability
- **Lazy schema init** — `ensure_schema()` called once on first ingest
