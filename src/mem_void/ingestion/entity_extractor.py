from __future__ import annotations

import json

from pydantic import TypeAdapter

from mem_void.config import Settings
from mem_void.models.entity import EntitySpan
from mem_void.utils.llm import generate

_ENTITY_PROMPT = """\
Extract entities from the text below.
Return ONLY a JSON array. Each object must have:
  - "name" (string): the entity name
  - "entity_type" (string): one of PERSON, ORG, PROJECT, LOCATION, PRODUCT, EVENT, UNKNOWN

Text: "{text}"

Output:"""

_entity_list_adapter = TypeAdapter(list[EntitySpan])


def extract_entities(settings: Settings, text: str) -> list[EntitySpan]:
    """Extract entity spans from raw text using the configured LLM."""
    prompt = _ENTITY_PROMPT.format(text=text)
    raw = generate(settings, prompt)
    return _parse_entity_response(raw)


def _parse_entity_response(raw: str) -> list[EntitySpan]:
    try:
        data = json.loads(raw)
        return _entity_list_adapter.validate_python(data)
    except (json.JSONDecodeError, ValueError):
        return []
