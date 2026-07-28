"""Blind signal-ID custodian.

The model-facing research process receives opaque signal IDs only. The name mapping is
stored encrypted using a Fernet key controlled by a separate data custodian. The key is
never written into the release package.
"""
from __future__ import annotations

import json
import secrets
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

SCHEMA = "warroom.v85.blind_signal_map.v1"


def new_signal_id() -> str:
    return "SIG_" + secrets.token_hex(12).upper()


def create_mapping(signal_names: list[str]) -> dict[str, Any]:
    clean = []
    seen = set()
    for name in signal_names:
        text = str(name).strip()
        if not text or text in seen:
            raise ValueError("Signal names must be non-empty and unique")
        seen.add(text)
        clean.append(text)
    return {"schema": SCHEMA, "signals": {new_signal_id(): name for name in clean}}


def encrypt_mapping(mapping: dict[str, Any], key: bytes) -> bytes:
    if mapping.get("schema") != SCHEMA or not isinstance(mapping.get("signals"), dict):
        raise ValueError("Invalid signal mapping")
    raw = json.dumps(mapping, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return Fernet(key).encrypt(raw)


def decrypt_mapping(token: bytes, key: bytes) -> dict[str, Any]:
    try:
        raw = Fernet(key).decrypt(token)
    except InvalidToken as exc:
        raise ValueError("Blind mapping key or ciphertext invalid") from exc
    mapping = json.loads(raw)
    if mapping.get("schema") != SCHEMA:
        raise ValueError("Signal mapping schema mismatch")
    return mapping


def write_encrypted_mapping(path: str | Path, mapping: dict[str, Any], key: bytes) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(encrypt_mapping(mapping, key))


def public_registry(mapping: dict[str, Any]) -> dict[str, Any]:
    if mapping.get("schema") != SCHEMA:
        raise ValueError("Signal mapping schema mismatch")
    return {"schema": "warroom.v85.public_signal_registry.v1", "signal_ids": sorted(mapping["signals"])}
