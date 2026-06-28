from __future__ import annotations

from unittest.mock import patch

from mem_void.config import Settings
from mem_void.ingestion.entity_extractor import extract_entities
from mem_void.ingestion.fact_extractor import extract_facts


class TestEntityExtractor:
    def test_extracts_person_and_org(self) -> None:
        settings = Settings(_env_file=None)
        llm_response = '[{"name": "Alice", "entity_type": "PERSON"}, {"name": "Acme", "entity_type": "ORG"}]'

        with patch("mem_void.ingestion.entity_extractor.generate", return_value=llm_response):
            spans = extract_entities(settings, "Alice joined Acme")

        assert len(spans) == 2
        assert spans[0].name == "Alice"
        assert spans[0].entity_type == "PERSON"
        assert spans[1].name == "Acme"
        assert spans[1].entity_type == "ORG"

    def test_handles_malformed_json(self) -> None:
        settings = Settings(_env_file=None)

        with patch("mem_void.ingestion.entity_extractor.generate", return_value="not json"):
            spans = extract_entities(settings, "some text")

        assert spans == []

    def test_handles_empty_response(self) -> None:
        settings = Settings(_env_file=None)

        with patch("mem_void.ingestion.entity_extractor.generate", return_value="[]"):
            spans = extract_entities(settings, "some text")

        assert spans == []


class TestFactExtractor:
    def test_extracts_works_at_triple(self) -> None:
        settings = Settings(_env_file=None)
        llm_response = '[{"subject": "Alice", "predicate": "WORKS_AT", "object": "Acme"}]'

        with patch("mem_void.ingestion.fact_extractor.generate", return_value=llm_response):
            triples = extract_facts(settings, "Alice joined Acme", ["Alice", "Acme"])

        assert len(triples) == 1
        assert triples[0].subject == "Alice"
        assert triples[0].predicate == "WORKS_AT"
        assert triples[0].object == "Acme"

    def test_handles_malformed_json(self) -> None:
        settings = Settings(_env_file=None)

        with patch("mem_void.ingestion.fact_extractor.generate", return_value="bad"):
            triples = extract_facts(settings, "text", ["Alice"])

        assert triples == []

    def test_handles_empty_response(self) -> None:
        settings = Settings(_env_file=None)

        with patch("mem_void.ingestion.fact_extractor.generate", return_value="[]"):
            triples = extract_facts(settings, "text", ["Alice"])

        assert triples == []
