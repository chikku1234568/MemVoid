from __future__ import annotations

from mem_void.models import Entity, EntitySpan


class TestEntity:
    def test_defaults(self) -> None:
        e = Entity(name="Alice", entity_type="PERSON")
        assert e.uuid is not None
        assert e.name == "Alice"
        assert e.entity_type == "PERSON"
        assert e.aliases == []
        assert e.created_at is not None

    def test_unknown_type_default(self) -> None:
        e = Entity(name="Something")
        assert e.entity_type == "UNKNOWN"

    def test_with_aliases(self) -> None:
        e = Entity(name="Microsoft", aliases=["MSFT", "Microsoft Corp"])
        assert e.aliases == ["MSFT", "Microsoft Corp"]

    def test_uuid_is_unique(self) -> None:
        e1 = Entity(name="Alice")
        e2 = Entity(name="Bob")
        assert e1.uuid != e2.uuid


class TestEntitySpan:
    def test_defaults(self) -> None:
        span = EntitySpan(name="Alice")
        assert span.name == "Alice"
        assert span.entity_type == "UNKNOWN"
        assert span.start_char is None
        assert span.end_char is None

    def test_with_offsets(self) -> None:
        span = EntitySpan(name="Acme", entity_type="ORG", start_char=14, end_char=18)
        assert span.start_char == 14
        assert span.end_char == 18
