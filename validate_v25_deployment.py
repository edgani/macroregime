from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS: list[dict] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    RESULTS.append({"name": name, "pass": bool(condition), "detail": detail})
    if not condition:
        raise AssertionError(f"{name}: {detail}")


def main() -> int:
    status = "PASS"
    error = None
    try:
        app = (HERE / "app.py").read_text(encoding="utf-8")
        html = (HERE / "dashboard.html").read_text(encoding="utf-8")
        cfg = (HERE / ".streamlit" / "config.toml").read_text(encoding="utf-8")
        req = (HERE / "requirements.txt").read_text(encoding="utf-8")

        check("local HTML Path is embedded", "st.iframe(DASH_SOURCE" in app)
        check("broken static HTML URL removed", 'st.iframe(url' not in app and 'url = "app/static/dashboard_live.html' not in app)
        check("explicit visible fallback", "components.html" in app and "could not be embedded" in app)
        check("static JSON serving enabled", "enableStaticServing = true" in cfg)
        check("deployment-safe bind", 'address = "0.0.0.0"' in cfg)
        check("supported Streamlit iframe API", "streamlit>=1.56,<2" in req)
        check("same-origin static JSON resolver", "staticAssetUrl('desk_snapshot.json')" in html and "window.parent.location.href" in html)
        check("no relative srcdoc JSON fetch", "const DATA_URL = 'desk_snapshot.json'" not in html)

        script = html[html.rfind("<script>") + len("<script>"): html.rfind("</script>")]
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False, encoding="utf-8") as fh:
            fh.write(script)
            js_path = fh.name
        try:
            proc = subprocess.run(["node", "--check", js_path], capture_output=True, text=True, timeout=30)
            check("dashboard JavaScript syntax", proc.returncode == 0, proc.stderr.strip())
        finally:
            Path(js_path).unlink(missing_ok=True)

        old = os.environ.get("WARROOM_DISABLE_AUTOSTART")
        os.environ["WARROOM_DISABLE_AUTOSTART"] = "1"
        sys.path.insert(0, str(HERE))
        try:
            from streamlit.testing.v1 import AppTest
            at = AppTest.from_file(str(HERE / "app.py"), default_timeout=30).run(timeout=30)
            check("Streamlit app has no exception", len(at.exception) == 0,
                  "; ".join(str(getattr(e, "value", e)) for e in at.exception))
            iframe_nodes = [x for x in at.main if getattr(x, "type", "") == "iframe"]
            check("exactly one iframe", len(iframe_nodes) == 1, str(len(iframe_nodes)))
            proto = iframe_nodes[0].proto
            srcdoc = str(getattr(proto, "srcdoc", ""))
            src = str(getattr(proto, "src", ""))
            check("iframe uses srcdoc not URL text", not src and srcdoc.lstrip().startswith("<!doctype html>"),
                  f"src={src!r}, srcdoc_len={len(srcdoc)}")
            check("embedded dashboard content present", "WAR ROOM OS" in srcdoc and "staticAssetUrl" in srcdoc)
            check("old URL not rendered as text", "app/static/dashboard_live.html?v=24" not in srcdoc)
        finally:
            if old is None:
                os.environ.pop("WARROOM_DISABLE_AUTOSTART", None)
            else:
                os.environ["WARROOM_DISABLE_AUTOSTART"] = old
    except Exception as exc:
        status = "FAIL"
        error = f"{type(exc).__name__}: {exc}"

    report = {
        "status": status,
        "version": "2.5",
        "checks": RESULTS,
        "error": error,
        "verified": [
            "Streamlit 1.59.2 AppTest embeds the full dashboard as iframe srcdoc",
            "static JSON endpoint pattern is used instead of static HTML serving",
            "dashboard JavaScript parses",
        ],
        "not_verified_without_user_environment": [
            "paid provider credentials and entitlements",
            "hosting platform subprocess lifetime policy for the background worker",
            "external provider reachability from the deployed container",
        ],
    }
    (HERE / "V25_DEPLOYMENT_TEST_REPORT.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
