"""Hard runtime boundary: technical analysis cannot authorize War Room capital."""
from __future__ import annotations
from collections.abc import Mapping, Sequence
from pathlib import Path
import json
import re

FORBIDDEN_DECISION_TOKENS = {
    "sma", "ema", "moving_average", "moving average", "rsi", "macd", "stochastic",
    "vwap", "price_momentum", "price momentum", "relative_strength", "relative strength",
    "breakout", "support_resistance", "support resistance", "candlestick", "chart_pattern",
    "chart pattern", "trend_following", "trend following", "price_breadth", "price breadth",
    "technical_target", "technical target", "technical_stop", "technical stop",
}
AUTHORIZED_CAPITAL_STATES = {"HUMAN_APPROVED_LIMITED_PRODUCTION", "LIMITED_PRODUCTION_ELIGIBLE"}


def _text(value: object) -> str:
    return str(value or "").strip().lower()


def contains_forbidden_decision_term(value: object) -> list[str]:
    """Match forbidden terms as semantic tokens, not arbitrary substrings.

    The earlier substring check incorrectly flagged words such as ``demand`` because they contain
    ``ema``. Normalizing separators and applying token boundaries closes that false-positive while
    still catching forms such as ``RSI_signal`` and ``moving-average``.
    """
    text = _text(value)
    normalized = re.sub(r"[^a-z0-9]+", " ", text).strip()
    hits: set[str] = set()
    for token in FORBIDDEN_DECISION_TOKENS:
        normalized_token = re.sub(r"[^a-z0-9]+", " ", token.lower()).strip()
        if not normalized_token:
            continue
        if re.search(r"(?<![a-z0-9])" + re.escape(normalized_token) + r"(?![a-z0-9])", normalized):
            hits.add(token)
    return sorted(hits)


def validate_feature_names(feature_names: Sequence[str]) -> list[str]:
    violations: list[str] = []
    for name in feature_names:
        hits = contains_forbidden_decision_term(name)
        if hits:
            violations.append(f"{name}: {','.join(hits)}")
    return violations


def assert_registry_has_no_active_technical_components(registry: Mapping[str, object]) -> None:
    components = registry.get("components") if isinstance(registry, Mapping) else None
    components = components if isinstance(components, Mapping) else {}
    problems: list[str] = []
    for component_id, raw in components.items():
        row = raw if isinstance(raw, Mapping) else {}
        active = bool(row.get("decision_active")) or _text(row.get("capital_permission")) in {
            x.lower() for x in AUTHORIZED_CAPITAL_STATES
        }
        if not active:
            continue
        haystack = " ".join([str(component_id), str(row.get("scope")), str(row.get("claim_limit")), str(row.get("state"))])
        hits = contains_forbidden_decision_term(haystack)
        if hits:
            problems.append(f"{component_id}: {','.join(hits)}")
    if problems:
        raise RuntimeError("Technical component reached decision-active registry: " + " | ".join(problems))


def enforce_payload(payload: object, path: str = "root") -> None:
    """Reject any capital-authorized payload containing technical decision semantics."""
    if isinstance(payload, Mapping):
        permission = _text(payload.get("capital_permission"))
        authorized = permission in {x.lower() for x in AUTHORIZED_CAPITAL_STATES}
        if authorized:
            violations: list[str] = []
            for key, value in payload.items():
                violations.extend(f"{path}.{key}:{hit}" for hit in contains_forbidden_decision_term(key))
                if isinstance(value, (str, int, float)):
                    violations.extend(f"{path}.{key}:{hit}" for hit in contains_forbidden_decision_term(value))
            if violations:
                raise RuntimeError("Technical semantics in capital-authorized payload: " + " | ".join(violations))
        for key, value in payload.items():
            enforce_payload(value, f"{path}.{key}")
    elif isinstance(payload, Sequence) and not isinstance(payload, (str, bytes, bytearray)):
        for i, value in enumerate(payload):
            enforce_payload(value, f"{path}[{i}]")


def load_policy(package_root: str | Path | None = None) -> dict:
    root = Path(package_root) if package_root else Path(__file__).resolve().parents[1]
    return json.loads((root / "NO_TECHNICAL_ANALYSIS_POLICY.json").read_text(encoding="utf-8"))
