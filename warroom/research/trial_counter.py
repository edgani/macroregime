"""warroom/research/trial_counter.py — global trial counter and registry (R9.2).

Why this exists: the V84 anti-overfit audit revoked the V82/V83 confirmatory
claim because the global research-trial ledger was incomplete — local PBO/DSR
cannot correct an uncounted search history. The false discovery rate cannot be
identified retroactively, so trials must be counted prospectively, from
registration, with an append-only chain the application cannot edit.

This module unifies the two historical hash-chain formats without rewriting
any historical entry:

- research/trial_ledger/trials.jsonl  (flat format, ``previous_hash`` chain,
  entry_hash = sha256 of canonical sorted-compact JSON without entry_hash)
- data/research/trial_ledger.jsonl    (wrapped format from R7/R8,
  ``prev_hash`` chain written by warroom/research/ledger.py)

New registrations append to the canonical registry
(research/trial_ledger/trials.jsonl) in its native flat format, so the chain
stays continuous and fully verifiable.

Enforcement: producers of evaluation records (e.g. shadow_runner_v101) must
call require_registered(trial_id) BEFORE recording. Unregistered trials fail
closed: no registration, no records.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Iterable, Mapping

HERE = Path(__file__).resolve().parents[2]
CANONICAL_REGISTRY = HERE / "research" / "trial_ledger" / "trials.jsonl"
WRAPPED_REGISTRY = HERE / "data" / "research" / "trial_ledger.jsonl"
DEFAULT_REGISTRIES: tuple[Path, ...] = (CANONICAL_REGISTRY, WRAPPED_REGISTRY)

UTC = dt.timezone.utc


class TrialNotRegistered(RuntimeError):
    """Raised when a producer tries to record against an unregistered trial."""


class DuplicateTrialRegistration(RuntimeError):
    """Raised when a trial_id is registered twice."""


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _canonical(entry: Mapping[str, Any]) -> bytes:
    return json.dumps(entry, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def verify_flat(path: Path = CANONICAL_REGISTRY) -> dict[str, Any]:
    """Verify the flat (previous_hash) chain, recomputing every entry_hash."""
    entries = _read_jsonl(path)
    errors: list[str] = []
    prev = "GENESIS"
    for index, entry in enumerate(entries):
        if entry.get("previous_hash") != prev:
            errors.append(f"entry {index}: chain break (previous_hash mismatch)")
        base = {k: v for k, v in entry.items() if k != "entry_hash"}
        if hashlib.sha256(_canonical(base)).hexdigest() != entry.get("entry_hash"):
            errors.append(f"entry {index}: entry_hash mismatch (tamper evidence)")
        prev = entry.get("entry_hash") or prev
    return {"path": str(path), "format": "flat", "entries": len(entries), "valid": not errors, "errors": errors}


def verify_wrapped(path: Path = WRAPPED_REGISTRY) -> dict[str, Any]:
    """Verify the wrapped (prev_hash) chain written by warroom/research/ledger.py."""
    entries = _read_jsonl(path)
    errors: list[str] = []
    prev = "GENESIS"
    for index, entry in enumerate(entries):
        if entry.get("prev_hash") != prev:
            errors.append(f"entry {index}: chain break (prev_hash mismatch)")
        base = {k: v for k, v in entry.items() if k != "entry_hash"}
        raw = json.dumps(base, sort_keys=True, default=str).encode("utf-8")
        if hashlib.sha256(raw).hexdigest() != entry.get("entry_hash"):
            errors.append(f"entry {index}: entry_hash mismatch (tamper evidence)")
        prev = entry.get("entry_hash") or prev
    return {"path": str(path), "format": "wrapped", "entries": len(entries), "valid": not errors, "errors": errors}


def verify_all(registries: Iterable[Path] = DEFAULT_REGISTRIES) -> dict[str, Any]:
    reports = []
    for path in registries:
        if not path.exists():
            reports.append({"path": str(path), "format": "missing", "entries": 0, "valid": True, "errors": []})
            continue
        first = _read_jsonl(path)[0] if _read_jsonl(path) else {}
        reports.append(verify_wrapped(path) if "prev_hash" in first else verify_flat(path))
    return {
        "schema": "warroom.trial_counter.verification.v1",
        "registries": reports,
        "total_entries": sum(r["entries"] for r in reports),
        "valid": all(r["valid"] for r in reports),
    }


def structural_hash(spec: Mapping[str, Any]) -> str:
    """Hash the strategy's logical structure, not code text.

    Two implementations of the same operators/fields/lookbacks produce the
    same hash; this is what makes the trial count honest about how many
    independent hypotheses were actually tried.
    """
    return hashlib.sha256(_canonical(dict(spec))).hexdigest()


def content_hash(registries: Iterable[Path] = DEFAULT_REGISTRIES) -> str:
    """Deterministic binding of the full global registry state.

    sha256 over the per-file sha256s (path-stable order as given). Any append,
    edit, or deletion anywhere in any registry changes this value.
    """
    parts = []
    for path in registries:
        digest = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "MISSING"
        parts.append(f"{path.name}:{digest}")
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def registered_trial_ids(registries: Iterable[Path] = DEFAULT_REGISTRIES) -> set[str]:
    ids: set[str] = set()
    for path in registries:
        for entry in _read_jsonl(path):
            if "trial_id" in entry:
                ids.add(str(entry["trial_id"]))
            trial = entry.get("trial")
            if isinstance(trial, Mapping):
                for key in ("trial_id", "id"):
                    if trial.get(key):
                        ids.add(str(trial[key]))
    return ids


def is_registered(trial_id: str, registries: Iterable[Path] = DEFAULT_REGISTRIES) -> bool:
    return str(trial_id) in registered_trial_ids(registries)


def require_registered(trial_id: str, registries: Iterable[Path] = DEFAULT_REGISTRIES) -> None:
    """Fail-closed gate: no prospective registration, no evaluation records."""
    if not is_registered(trial_id, registries):
        raise TrialNotRegistered(
            f"trial_id {trial_id!r} is not registered in the global trial registry; "
            "register it prospectively (trial_counter.py register) before recording any evaluation"
        )


def register(
    trial_id: str,
    spec: Mapping[str, Any],
    *,
    claims: Iterable[str] = (),
    outcome: str = "REGISTERED_PROSPECTIVE",
    registry: Path = CANONICAL_REGISTRY,
    note: str | None = None,
) -> dict[str, Any]:
    """Append one prospective trial registration to the canonical registry.

    Fail-closed on duplicates: a trial_id may only be registered once.
    """
    registry = Path(registry)
    registry.parent.mkdir(parents=True, exist_ok=True)
    if is_registered(trial_id, (registry,)):
        raise DuplicateTrialRegistration(f"trial_id {trial_id!r} already registered in {registry}")
    entries = _read_jsonl(registry)
    previous_hash = entries[-1]["entry_hash"] if entries else "GENESIS"
    entry: dict[str, Any] = {
        "trial_id": str(trial_id),
        "timestamp": dt.datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "outcome": outcome,
        "claims": sorted(str(c) for c in claims),
        "structural_hash": structural_hash(spec),
        "spec": dict(spec),
        "previous_hash": previous_hash,
    }
    if note:
        entry["note"] = note
    entry["entry_hash"] = hashlib.sha256(_canonical(entry)).hexdigest()
    with registry.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, default=str) + "\n")
    return entry


def main() -> None:
    parser = argparse.ArgumentParser(description="Global trial counter / registry")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("verify")
    reg = sub.add_parser("register")
    reg.add_argument("--trial-id", required=True)
    reg.add_argument("--spec-file", help="JSON file whose parsed content becomes the trial spec")
    reg.add_argument("--claim", action="append", default=[])
    reg.add_argument("--note")
    args = parser.parse_args()

    if args.command == "verify":
        print(json.dumps(verify_all(), indent=2, ensure_ascii=False))
        return
    spec: dict[str, Any] = {}
    if args.spec_file:
        spec_path = Path(args.spec_file)
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        spec = {"spec_file": spec_path.name, "spec_file_sha256": hashlib.sha256(spec_path.read_bytes()).hexdigest(), "parsed": spec}
    entry = register(args.trial_id, spec, claims=args.claim, note=args.note)
    print(json.dumps(entry, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
