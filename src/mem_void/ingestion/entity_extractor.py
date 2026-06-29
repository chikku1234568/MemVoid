from __future__ import annotations

import json

from pydantic import TypeAdapter

from mem_void.config import Settings
from mem_void.models.entity import EntitySpan
from mem_void.utils.llm import generate

_ENTITY_PROMPT = """\
Extract entities from the text. Use EXACT names as written — do not expand or modify.
Return ONLY a JSON array. Each object must have:
  - "name" (string): the entity name as it appears in the text
  - "entity_type" (string): one of PERSON, ORG, PROJECT, LOCATION, PRODUCT, EVENT, UNKNOWN

Text: "{text}"

JSON output:"""

_entity_list_adapter = TypeAdapter(list[EntitySpan])


def extract_entities(settings: Settings, text: str) -> list[EntitySpan]:
    """Extract entity spans from raw text using the configured LLM."""
    prompt = _ENTITY_PROMPT.format(text=text)
    raw = generate(settings, prompt)
    return _parse_entity_response(raw)


def _parse_entity_response(raw: str) -> list[EntitySpan]:
    raw = _strip_markdown_fences(raw)
    try:
        data = json.loads(raw)
        return _entity_list_adapter.validate_python(data)
    except (json.JSONDecodeError, ValueError):
        return []


def _strip_markdown_fences(raw: str) -> str:
    """Strip ```json ... ``` markdown wrapping from LLM output."""
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()
