"""Validation helpers for identifiers used as storage path components."""

import re

_STORAGE_IDENTIFIER = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")


def validate_storage_identifier(value: str, field_name: str) -> str:
    """Return a safe single path component or reject traversal and ambiguous names."""

    if (
        type(value) is not str
        or value in {".", ".."}
        or _STORAGE_IDENTIFIER.fullmatch(value) is None
    ):
        raise ValueError(f"{field_name} must be a safe storage identifier")
    return value
