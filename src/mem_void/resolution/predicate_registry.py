from __future__ import annotations

EXCLUSIVE_PREDICATES: set[str] = {
    "WORKS_AT",
    "LIVES_IN",
    "LOCATED_IN",
    "REPORTS_TO",
    "HAS_TITLE",
    "HEADQUARTERED_IN",
}

ADDITIVE_PREDICATES: set[str] = {
    "WORKS_ON",
    "KNOWS",
    "USES",
    "LIKES",
    "HAS_SKILL",
    "ATTENDED",
}

_DEFAULT_BEHAVIOR: str = "additive"


def is_exclusive(predicate: str) -> bool:
    """Return True if this predicate requires closing old active facts."""
    if predicate in EXCLUSIVE_PREDICATES:
        return True
    if predicate in ADDITIVE_PREDICATES:
        return False
    return _DEFAULT_BEHAVIOR == "exclusive"


def is_additive(predicate: str) -> bool:
    """Return True if this predicate allows multiple active facts to coexist."""
    return not is_exclusive(predicate)
