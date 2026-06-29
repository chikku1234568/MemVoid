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
Extract relationship triples from the text. Return ONLY a JSON array.

RULES:
1. Use entity names EXACTLY as provided — do not modify or expand them.
2. Choose a SPECIFIC predicate from this list (match the meaning):
   - "WORKS_AT" — employment, joining a company, working for an org
   - "WORKS_ON" — project assignment, working on an initiative
   - "LIVES_IN" — residing in a location
   - "KNOWS" — knowing a person
   - "LOCATED_IN" — physical location of an office/entity
3. NEVER use generic predicates like "RELATES_TO" or "IS".
4. Predicate must be UPPER_SNAKE_CASE.

Entities: {entities}
Text: "{text}"

JSON output:"""


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
    raw = _strip_markdown_fences(raw)
    try:
        data = json.loads(raw)
        return _triple_list_adapter.validate_python(data)
    except (json.JSONDecodeError, ValueError):
        return []


def _strip_markdown_fences(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()
