from __future__ import annotations

import json

from pydantic import BaseModel, TypeAdapter

from mem_void.config import Settings
from mem_void.utils.llm import generate


class ExtractedTriple(BaseModel):
    subject: str
    predicate: str
    object: str


_triple_list_adapter = TypeAdapter(list[ExtractedTriple])

_FACT_PROMPT = """\
Extract relationship triples from the text below.
Use ONLY the entity names listed. Return ONLY a JSON array.
Each object must have:
  - "subject" (string): entity name from the list
  - "predicate" (string): UPPER_SNAKE_CASE (e.g. WORKS_AT, WORKS_ON, LIVES_IN)
  - "object" (string): entity name from the list

Entities: {entities}
Text: "{text}"

Output:"""


def extract_facts(
    settings: Settings,
    text: str,
    entity_names: list[str],
) -> list[ExtractedTriple]:
    """Extract fact triples from raw text using the configured LLM."""
    prompt = _FACT_PROMPT.format(
        entities=json.dumps(entity_names),
        text=text,
    )
    raw = generate(settings, prompt)
    return _parse_fact_response(raw)


def _parse_fact_response(raw: str) -> list[ExtractedTriple]:
    try:
        data = json.loads(raw)
        return _triple_list_adapter.validate_python(data)
    except (json.JSONDecodeError, ValueError):
        return []
