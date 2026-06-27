from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class Entity(BaseModel):
    """A person, organization, project, location, or other real-world thing."""

    uuid: UUID = Field(default_factory=uuid4)
    name: str
    entity_type: str = "UNKNOWN"
    aliases: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EntitySpan(BaseModel):
    """An entity extracted from episode text, before resolution."""

    name: str
    entity_type: str = "UNKNOWN"
    start_char: int | None = None
    end_char: int | None = None
