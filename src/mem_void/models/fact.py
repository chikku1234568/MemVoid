from __future__ import annotations

import re
from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

_PREDICATE_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")


class Fact(BaseModel):
    """A temporal relationship between two entities.

    In the Neo4j graph, facts are stored as relationships (edges),
    not as nodes. The predicate becomes the relationship type.
    Subject and object reference Entity nodes by name.
    """

    uuid: UUID = Field(default_factory=uuid4)
    subject: str
    predicate: str
    object: str
    valid_from: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    valid_to: datetime | None = None
    episode_uuid: UUID | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_active(self) -> bool:
        return self.valid_to is None

    @staticmethod
    def validate_predicate(predicate: str) -> str:
        if not _PREDICATE_RE.match(predicate):
            raise ValueError(
                f"Invalid predicate name: '{predicate}'. "
                f"Must match pattern: UPPER_SNAKE_CASE"
            )
        return predicate
