"""Fast integrity audit for the Capital Intelligence Map redesign."""
from __future__ import annotations

from pathlib import Path
import os
import py_compile
import re
import subprocess
import sys
import tempfile

HERE = Path(__file__).resolve().parent


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    for name in ("app.py", "run.py", "data_layer.py", "institutional_data.py", "build_feeds.py", "engines/live_data_engine.py"):
        py_compile.compile(str(HERE / name), doraise=True)

    data_layer = (HERE / "data_layer.py").read_text(encoding="utf-8")
    require("allow_synthetic=False" in data_layer, "Production synthetic default is not disabled")
    require('return {}, "NO_DATA' in data_layer, "Missing prices do not preserve NO_DATA")

    live_engine = (HERE / "engines/live_data_engine.py").read_text(encoding="utf-8")
    require("AGGREGATE_SHORT_VOLUME_NOT_DARK_POOL_PRINT_OR_SHORT_INTEREST" in live_engine,
            "FINRA semantics guard missing")
    require("OI_IMPLIED_GAMMA_PROXY_NOT_DEALER_POSITION" in live_engine,
            "Option-chain gamma semantics guard missing")
    require("MM hedging dark-pool buys" not in live_engine, "Unsupported dark-pool intent claim remains")

    html = (HERE / "dashboard.html").read_text(encoding="utf-8")
    require("/*__INJECT_DATA__*/" in html, "Dashboard injection marker missing")
    require("Missing feed = NO DATA" in html, "NO_DATA production rule missing")
    require("if(state.mode==='all')" in html, "Observed/structural candidate gate missing")

    scripts = re.findall(r"<script(?:\\s[^>]*)?>(.*?)</script>", html, flags=re.S | re.I)
    require(bool(scripts), "Dashboard JavaScript missing")
    with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as handle:
        handle.write(scripts[-1])
        check_js = handle.name
    try:
        if subprocess.run(["node", "--check", check_js], capture_output=True).returncode != 0:
            raise AssertionError("Dashboard JavaScript syntax check failed")
    finally:
        Path(check_js).unlink(missing_ok=True)

    for key in ("UNUSUAL_WHALES_API_KEY", "MASSIVE_API_KEY", "NANSEN_API_KEY", "ARKHAM_API_KEY", "WARROOM_SEC_USER_AGENT"):
        os.environ.pop(key, None)
    from institutional_data import collect_institutional_data
    result = collect_institutional_data({"alpha": [{"tk": "NVDA"}], "markets": {}})
    require(result["overall_state"] == "NOT_CONFIGURED", "Missing credentials did not remain NOT_CONFIGURED")
    require(not result["events"], "Missing credentials emitted placeholder events")

    print("PASS — Python, JavaScript, data semantics and no-credential behavior are intact.")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"FAIL — {type(exc).__name__}: {exc}", file=sys.stderr)
        raise
