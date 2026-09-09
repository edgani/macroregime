from pathlib import Path
import math
import tempfile

from opportunity_kernel import FeatureSpec, aggregate_change, robust_change_reading, sequence_signature, vertical_readiness
from market_memory import MarketMemory


def run():
    r = robust_change_reading([10,10,11,11,12,18], FeatureSpec("x",1,"flow"))
    assert math.isfinite(r.robust_z) and r.robust_z > 0
    a = aggregate_change([r])
    assert a["feature_count"] == 1
    assert sequence_signature(["QUIET","QUIET","UNUSUAL","ACCELERATING"]) == "QUIET → UNUSUAL → ACCELERATING"
    ready = vertical_readiness("FX", ["relative_rates","macro_surprise","central_bank","positioning","valuation","memory"])
    assert ready["status"] == "READY"
    with tempfile.TemporaryDirectory() as td:
        m = MarketMemory(Path(td)/"m.sqlite")
        assert m.record_snapshot("ABC","US",{"x":1},state="QUIET",observed_at_utc="2026-01-01T00:00:00Z")
        assert m.record_snapshot("ABC","US",{"x":2},state="UNUSUAL",observed_at_utc="2026-01-02T00:00:00Z")
        h = m.history("ABC","US")
        assert len(h)==2 and list(h["x"])==[1,2]
        assert m.states("ABC","US") == ["QUIET","UNUSUAL"]
    print("PASS test_opportunity_kernel")

if __name__ == "__main__":
    run()
