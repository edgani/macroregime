from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
src = (ROOT / "prospective_validation.py").read_text(encoding="utf-8")

assert "confidence.isin({'HIGH','MEDIUM'})" in src
assert "revision_state.isin" in src
assert "('Existing engine',idx" in src
assert "isin({'READY','PARTIAL'})" in src

print("TEST_BASELINE_EVIDENCE_GATES_V33_PASS")
