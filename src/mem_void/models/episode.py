from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Episode(BaseModel):
    """A discrete event ingested into the memory system."""

    uuid: UUID = Field(default_factory=uuid4)
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
