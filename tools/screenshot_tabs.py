"""R2 screenshot tool: boot the 17-tab app with the real cache and capture every tab.

Usage:
    .venv/Scripts/python.exe tools/screenshot_tabs.py

Requires: streamlit run app.py reachable on localhost:8501 (this script starts it),
playwright + chromium installed. Output: docs/audit/screenshots/tab_XX_name.png
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "audit" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

TAB_NAMES = [
    "mission_control", "morning_brief", "briefing", "command_center", "alpha_center",
    "cross_asset_rotation", "causal_chains", "us_stocks", "crypto", "commodities",
    "fx", "ihsg", "flow", "bottleneck", "market_state", "track_record", "risk_health",
]


def main() -> int:
    env = dict(os.environ, WARROOM_OFFLINE="1", WARROOM_AUTO_SHADOW="0")
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py",
         "--server.port", "8531", "--server.headless", "true"],
        cwd=str(ROOT), env=env,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1680, "height": 1050})
            # wait for server
            for _ in range(120):
                try:
                    page.goto("http://localhost:8531", timeout=5000)
                    break
                except Exception:
                    time.sleep(2)
            else:
                print("ERROR: streamlit server did not come up")
                return 1
            page.wait_for_selector("[role='tab']", timeout=180000)
            page.wait_for_timeout(15000)  # engines + render settle
            tabs = page.locator("[role='tab']")
            n = tabs.count()
            print(f"tabs found: {n}")
            for i in range(min(n, len(TAB_NAMES))):
                tabs.nth(i).click()
                page.wait_for_timeout(4000)
                name = f"tab_{i + 1:02d}_{TAB_NAMES[i]}.png"
                page.screenshot(path=str(OUT / name), full_page=False)
                print(f"  saved {name}")
            browser.close()
        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    sys.exit(main())
