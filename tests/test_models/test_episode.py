from __future__ import annotations

from datetime import datetime, timezone

from mem_void.models import Episode


class TestEpisode:
    def test_defaults(self) -> None:
        ep = Episode(content="Alice joined Acme")
        assert ep.uuid is not None
        assert ep.content == "Alice joined Acme"
        assert ep.timestamp is not None
        assert ep.source is None
        assert ep.created_at is not None

    def test_custom_timestamp(self) -> None:
        ts = datetime(2024, 1, 15, tzinfo=timezone.utc)
        ep = Episode(content="Test", timestamp=ts)
        assert ep.timestamp == ts

    def test_custom_source(self) -> None:
        ep = Episode(content="Event", source="slack")
        assert ep.source == "slack"

    def test_uuid_is_unique(self) -> None:
        ep1 = Episode(content="A")
        ep2 = Episode(content="B")
        assert ep1.uuid != ep2.uuid
