"""
mem-void V1 Demo — The Alice Scenario

Demonstrates: ingest → entities → facts → temporal invalidation → retrieval.

Run with: python examples/alice_demo.py

Requires: Neo4j running, OPENAI_API_KEY set (or MEMVOID_LLM_API_KEY).
"""

from datetime import datetime, timezone
from mem_void import Memory, Settings

settings = Settings()
memory = Memory(settings)

print("Ingesting three events...\n")

memory.ingest("Alice joined Acme.", timestamp=datetime(2024, 1, 15, tzinfo=timezone.utc))
print("  [1] Alice joined Acme")

memory.ingest("Alice works on Project Phoenix.", timestamp=datetime(2024, 2, 1, tzinfo=timezone.utc))
print("  [2] Alice works on Project Phoenix")

memory.ingest("Alice joined OpenAI.", timestamp=datetime(2024, 6, 1, tzinfo=timezone.utc))
print("  [3] Alice joined OpenAI")

print("\n--- current_facts('Alice') ---")
from mem_void.retrieval import current_facts
facts = current_facts(memory._client, "Alice")
for f in facts:
    print(f"  {f.predicate} -> {f.object} (since {f.valid_from.strftime('%Y-%m')})")

print("\n--- fact_history('Alice', predicate='WORKS_AT') ---")
from mem_void.retrieval import fact_history
history = fact_history(memory._client, "Alice", predicate="WORKS_AT")
for f in history:
    status = "active" if f.is_active else f"closed ({f.valid_to.strftime('%Y-%m')})"
    print(f"  {f.object}: {status}")

print("\n--- related_entities('Alice') ---")
from mem_void.retrieval import related_entities
entities = related_entities(memory._client, "Alice")
for e in entities:
    print(f"  {e['entity']} (via {e['predicate']})")

print("\nV1 demo complete.")
memory.close()
