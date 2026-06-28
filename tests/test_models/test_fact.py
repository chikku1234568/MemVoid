from __future__ import annotations

from datetime import datetime, timezone

import pytest

from mem_void.models import Fact


class TestFact:
    def test_defaults(self) -> None:
        f = Fact(subject="Alice", predicate="WORKS_AT", object="Acme")
        assert f.uuid is not None
        assert f.subject == "Alice"
        assert f.predicate == "WORKS_AT"
        assert f.object == "Acme"
        assert f.valid_from is not None
        assert f.valid_to is None
        assert f.is_active is True
        assert f.created_at is not None

    def test_with_valid_to(self) -> None:
        ts = datetime(2024, 6, 1, tzinfo=timezone.utc)
        f = Fact(
            subject="Alice",
            predicate="WORKS_AT",
            object="Acme",
            valid_to=ts,
        )
        assert f.valid_to == ts
        assert f.is_active is False

    def test_custom_timestamps(self) -> None:
        start = datetime(2024, 1, 15, tzinfo=timezone.utc)
        end = datetime(2024, 6, 1, tzinfo=timezone.utc)
        f = Fact(
            subject="Alice",
            predicate="WORKS_AT",
            object="OpenAI",
            valid_from=start,
            valid_to=end,
        )
        assert f.valid_from == start
        assert f.valid_to == end

    def test_with_confidence(self) -> None:
        f = Fact(
            subject="Alice",
            predicate="KNOWS",
            object="Bob",
            confidence=0.95,
        )
        assert f.confidence == 0.95

    def test_confidence_at_boundaries(self) -> None:
        f_min = Fact(subject="A", predicate="KNOWS", object="B", confidence=0.0)
        f_max = Fact(subject="A", predicate="KNOWS", object="C", confidence=1.0)
        assert f_min.confidence == 0.0
        assert f_max.confidence == 1.0

    def test_confidence_out_of_range_raises(self) -> None:
        with pytest.raises(ValueError):
            Fact(subject="A", predicate="KNOWS", object="B", confidence=-0.1)
        with pytest.raises(ValueError):
            Fact(subject="A", predicate="KNOWS", object="B", confidence=1.1)

    def test_uuid_is_unique(self) -> None:
        f1 = Fact(subject="Alice", predicate="WORKS_AT", object="Acme")
        f2 = Fact(subject="Alice", predicate="WORKS_ON", object="Phoenix")
        assert f1.uuid != f2.uuid

    def test_with_episode_uuid(self) -> None:
        from uuid import uuid4
        ep_uuid = uuid4()
        f = Fact(
            subject="Alice",
            predicate="WORKS_AT",
            object="Acme",
            episode_uuid=ep_uuid,
        )
        assert f.episode_uuid == ep_uuid


class TestFactValidatePredicate:
    def test_valid_predicates(self) -> None:
        Fact.validate_predicate("WORKS_AT")
        Fact.validate_predicate("KNOWS")
        Fact.validate_predicate("LIVES_IN")
        Fact.validate_predicate("HAS_SKILL")

    def test_invalid_lowercase_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid predicate"):
            Fact.validate_predicate("works_at")

    def test_invalid_with_spaces_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid predicate"):
            Fact.validate_predicate("WORKS AT")

    def test_invalid_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid predicate"):
            Fact.validate_predicate("")

    def test_invalid_special_chars_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid predicate"):
            Fact.validate_predicate("WORKS-AT")

    def test_valid_with_numbers(self) -> None:
        Fact.validate_predicate("VERSION_2")
