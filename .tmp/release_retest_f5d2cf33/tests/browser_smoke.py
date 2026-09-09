from __future__ import annotations

import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts" / "ui_after"
URL = os.environ.get("OIE_BROWSER_URL", "http://127.0.0.1:8501")
EXECUTABLE = os.environ.get("OIE_BROWSER_EXECUTABLE")
ROUTES = ["CONTROL ROOM", "OPPORTUNITIES", "VERTICALS", "MACRO & EVENTS", "LEARNING / REPLAY"]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    console_errors: list[str] = []
    page_errors: list[str] = []
    evidence: list[dict[str, object]] = []
    with sync_playwright() as pw:
        launch_options: dict[str, object] = {
            "headless": True,
            "args": ["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
        }
        if EXECUTABLE:
            launch_options["executable_path"] = EXECUTABLE
        browser = pw.chromium.launch(**launch_options)
        for width, height, label in [(1440, 1000, "desktop"), (390, 844, "mobile")]:
            context = browser.new_context(viewport={"width": width, "height": height})
            page = context.new_page()
            page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
            page.on("pageerror", lambda error: page_errors.append(str(error)))
            page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
            page.get_by_role("button", name="CONTROL ROOM", exact=True).wait_for(timeout=60_000)
            for route in ROUTES:
                page.get_by_role("button", name=route, exact=True).click()
                page.locator("[data-testid='stAppViewBlockContainer']").wait_for(timeout=60_000)
                page.wait_for_function(
                    "() => !document.querySelector('[data-testid=stSpinner]')",
                    timeout=60_000,
                )
                assert page.get_by_role("button", name=route, exact=True).count() == 1
                assert page.locator("[data-testid='stException']").count() == 0
                assert page.locator("[data-testid='stStatusWidget']").count() == 0
                assert page.locator("[data-testid='stAppViewBlockContainer']").inner_text().strip()
                slug = route.lower().replace(" & ", "_").replace(" / ", "_").replace(" ", "_")
                shot = OUT / f"{label}_{slug}.png"
                page.screenshot(path=str(shot), full_page=True)
                assert shot.stat().st_size > 0
                evidence.append({"route": route, "viewport": [width, height], "screenshot": shot.relative_to(ROOT).as_posix()})
            context.close()
        browser.close()
    result = {"url": URL, "routes": evidence, "console_errors": console_errors, "page_errors": page_errors}
    (OUT / "browser_smoke.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    assert not console_errors, console_errors
    assert not page_errors, page_errors
    print(f"BROWSER_SMOKE_PASS {len(evidence)} route/viewport checks")


if __name__ == "__main__":
    main()
