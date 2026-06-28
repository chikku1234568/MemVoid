# M8 Log

**Date:** 2026-06-28

**Objective:** V1 Final Demo — working Alice scenario, comprehensive README.

**Files created (1):**
- `examples/alice_demo.py` — canonical Alice scenario (3 ingests → current_facts → fact_history → related_entities)

**Files modified (1):**
- `README.md` — complete rewrite: architecture, usage, capabilities, limitations, testing

**Verification:** 43/43 unit tests pass. 103 total tests collected. Demo runs end-to-end (requires Neo4j + LLM).

**V1 is complete.** The system:
1. Ingests free-text events via LLM extraction
2. Resolves entities deterministically (exact name → alias → create)
3. Extracts facts as temporal relationships
4. Applies predicate-aware invalidation (exclusive vs additive)
5. Stores everything in Neo4j
6. Supports graph-native retrieval (current, history, related, time-travel)
