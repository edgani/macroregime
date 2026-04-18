"""alert_engine.py

Sends real-time alerts when MacroRegime detects critical state changes.
Supports: Telegram bot (primary), console log (fallback)

Triggers:
- front_run_window changes to "now" → IMMEDIATE alert
- Regime flips (structural quad changes) → IMMEDIATE alert
- Narrative stage enters "early" → alert
- war_oil_hazard > 0.70 → alert
- VIX bucket changes (e.g., normal → elevated) → alert

Setup:
  TELEGRAM_BOT_TOKEN = your bot token from @BotFather
  TELEGRAM_CHAT_ID   = your personal chat ID from @userinfobot
  
  Set via environment variables or .streamlit/secrets.toml:
    TELEGRAM_BOT_TOKEN = "..."
    TELEGRAM_CHAT_ID   = "..."
"""
from __future__ import annotations
import hashlib
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict

import requests

try:
    from utils.streamlit_compat import st
    _HAS_ST = True
except Exception:
    _HAS_ST = False

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_ALERT_STATE_FILE = Path(".cache/alert_state.json")
_COOLDOWN_SECONDS = 300   # 5-minute cooldown per alert type


def _get_telegram_config() -> tuple[str, str]:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not (token and chat_id) and _HAS_ST:
        try:
            token = st.secrets.get("TELEGRAM_BOT_TOKEN", "").strip()
            chat_id = st.secrets.get("TELEGRAM_CHAT_ID", "").strip()
        except Exception:
            pass
    return token, chat_id


def _load_alert_state() -> Dict:
    try:
        if _ALERT_STATE_FILE.exists():
            return json.loads(_ALERT_STATE_FILE.read_text())
    except Exception:
        pass
    return {}


def _save_alert_state(state: Dict) -> None:
    try:
        _ALERT_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _ALERT_STATE_FILE.write_text(json.dumps(state))
    except Exception:
        pass


def _send_telegram(token: str, chat_id: str, message: str) -> bool:
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = requests.post(
            url,
            json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
            timeout=8,
        )
        return resp.status_code == 200
    except Exception:
        return False


def _should_send(state: Dict, alert_key: str) -> bool:
    """Cooldown check — don't spam same alert repeatedly."""
    last_sent = state.get(alert_key, 0)
    return (time.time() - last_sent) > _COOLDOWN_SECONDS


def _mark_sent(state: Dict, alert_key: str) -> None:
    state[alert_key] = time.time()


# ---------------------------------------------------------------------------
# Alert formatters
# ---------------------------------------------------------------------------

def _format_front_run_alert(core: Dict) -> str:
    rt = core.get("regime_transition", {})
    quad = rt.get("current_quad", "?")
    next_q = rt.get("most_likely_next", "?")
    rationale = rt.get("front_run_rationale", "")
    tickers = core.get("regime_tickers", {})
    longs = ", ".join(tickers.get("us_longs", [])[:4])
    ihsg = ", ".join(tickers.get("ihsg_buys", [])[:3])
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return (
        f"⚡ <b>FRONT-RUN WINDOW: NOW</b>\n"
        f"Regime: <b>{quad} → {next_q}</b>\n"
        f"{rationale}\n\n"
        f"🇺🇸 US Longs: <code>{longs}</code>\n"
        f"🇮🇩 IHSG: <code>{ihsg}</code>\n"
        f"<i>{ts}</i>"
    )


def _format_regime_flip_alert(old_quad: str, new_quad: str, confidence: float) -> str:
    quad_emoji = {"Q1": "🟢", "Q2": "🟡", "Q3": "🟠", "Q4": "🔴"}
    emoji = quad_emoji.get(new_quad, "⚪")
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return (
        f"{emoji} <b>REGIME FLIP ALERT</b>\n"
        f"<b>{old_quad} → {new_quad}</b>  (conf: {confidence:.0%})\n"
        f"Update your playbook. Regime ticker rotation required.\n"
        f"<i>{ts}</i>"
    )


def _format_war_oil_alert(hazard: float, news_summary: str) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return (
        f"🔥 <b>WAR/OIL HAZARD SPIKE</b>\n"
        f"Hazard score: <b>{hazard:.0%}</b>\n"
        f"{news_summary}\n"
        f"Action: Long XLE/GLD/ADRO.JK | Hedge IDR\n"
        f"<i>{ts}</i>"
    )


def _format_narrative_alert(narrative_name: str, stage: str, tickers: list) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    tkr_str = ", ".join(tickers[:4])
    return (
        f"⚡ <b>NARRATIVE ALERT: {narrative_name}</b>\n"
        f"Stage: <b>{stage.upper()}</b> — pre-institutional discovery\n"
        f"Tickers: <code>{tkr_str}</code>\n"
        f"Front-run before consensus discovers.\n"
        f"<i>{ts}</i>"
    )


def _format_vix_alert(old_bucket: str, new_bucket: str, vix: float) -> str:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    direction = "⬆️ escalating" if new_bucket in ("elevated", "stress", "crisis") else "⬇️ calming"
    return (
        f"📊 <b>VIX REGIME CHANGE</b> {direction}\n"
        f"{old_bucket.upper()} → <b>{new_bucket.upper()}</b>  (VIX: {vix:.1f})\n"
        f"Adjust position sizing accordingly.\n"
        f"<i>{ts}</i>"
    )


# ---------------------------------------------------------------------------
# Main alert checker
# ---------------------------------------------------------------------------

def check_and_send_alerts(core: Dict, previous_state: Dict | None = None) -> Dict:
    """
    Check current core state against previous state.
    Send Telegram alerts for any significant changes.
    Returns updated state dict for next call.

    Call this from a background job or at the end of build_snapshot.
    
    Usage in app:
        from utils.alert_engine import check_and_send_alerts
        alert_state = check_and_send_alerts(shared_core)
    """
    token, chat_id = _get_telegram_config()
    has_telegram = bool(token and chat_id)
    alert_log = _load_alert_state()
    new_state = dict(previous_state or {})
    alerts_sent = []

    rt = core.get("regime_transition", {})
    news = core.get("news_state", {})
    regime = core.get("regime", {})
    tickers = core.get("regime_tickers", {})
    narr = core.get("narrative_discovery", {})
    opt_sig = core.get("options_regime", {})

    # ------------------------------------------------------------------
    # 1. Front-run window = "now"
    # ------------------------------------------------------------------
    fw = str(rt.get("front_run_window", "not yet"))
    prev_fw = str(new_state.get("front_run_window", "not yet"))
    if fw == "now" and prev_fw != "now":
        alert_key = "front_run_now"
        if _should_send(alert_log, alert_key):
            msg = _format_front_run_alert(core)
            if has_telegram:
                _send_telegram(token, chat_id, msg)
            _mark_sent(alert_log, alert_key)
            alerts_sent.append(("front_run", fw))
    new_state["front_run_window"] = fw

    # ------------------------------------------------------------------
    # 2. Regime flip
    # ------------------------------------------------------------------
    current_quad = str(regime.get("current_quad", "Q?"))
    prev_quad = str(new_state.get("current_quad", "Q?"))
    if current_quad != prev_quad and prev_quad != "Q?" and current_quad != "Q?":
        alert_key = f"regime_flip_{prev_quad}_{current_quad}"
        if _should_send(alert_log, alert_key):
            conf = float(regime.get("structural_confidence", regime.get("confidence", 0.5)))
            msg = _format_regime_flip_alert(prev_quad, current_quad, conf)
            if has_telegram:
                _send_telegram(token, chat_id, msg)
            _mark_sent(alert_log, alert_key)
            alerts_sent.append(("regime_flip", f"{prev_quad}→{current_quad}"))
    new_state["current_quad"] = current_quad

    # ------------------------------------------------------------------
    # 3. War/oil hazard spike (>0.70)
    # ------------------------------------------------------------------
    war_h = float(news.get("war_oil_hazard", 0.0))
    prev_war = float(new_state.get("war_oil_hazard", 0.0))
    if war_h >= 0.70 and prev_war < 0.70:
        alert_key = "war_oil_spike"
        if _should_send(alert_log, alert_key):
            summary = str(news.get("summary", "Geopolitical risk elevated"))
            msg = _format_war_oil_alert(war_h, summary)
            if has_telegram:
                _send_telegram(token, chat_id, msg)
            _mark_sent(alert_log, alert_key)
            alerts_sent.append(("war_oil", f"{war_h:.0%}"))
    new_state["war_oil_hazard"] = war_h

    # ------------------------------------------------------------------
    # 4. Early narrative alert (new early-stage narrative detected)
    # ------------------------------------------------------------------
    early_alerts = narr.get("early_stage_alerts", [])
    prev_early = set(new_state.get("early_alerts", []))
    for narr_name in early_alerts:
        if narr_name not in prev_early:
            alert_key = f"narrative_early_{hashlib.md5(narr_name.encode()).hexdigest()[:8]}"
            if _should_send(alert_log, alert_key):
                # Find tickers
                active = {n["name"]: n for n in narr.get("active_narratives", [])}
                tkrs = active.get(narr_name, {}).get("primary_beneficiaries", [])
                msg = _format_narrative_alert(narr_name, "early", tkrs)
                if has_telegram:
                    _send_telegram(token, chat_id, msg)
                _mark_sent(alert_log, alert_key)
                alerts_sent.append(("narrative", narr_name))
    new_state["early_alerts"] = list(set(early_alerts))

    # ------------------------------------------------------------------
    # 5. VIX bucket change
    # ------------------------------------------------------------------
    vix_bucket = str(opt_sig.get("vix_bucket", ""))
    prev_bucket = str(new_state.get("vix_bucket", ""))
    bucket_order = ["goldilocks", "normal", "elevated", "stress", "crisis"]
    if vix_bucket and prev_bucket and vix_bucket != prev_bucket:
        prev_idx = bucket_order.index(prev_bucket) if prev_bucket in bucket_order else 1
        curr_idx = bucket_order.index(vix_bucket) if vix_bucket in bucket_order else 1
        if abs(curr_idx - prev_idx) >= 1:  # any bucket change = alert
            alert_key = f"vix_bucket_{prev_bucket}_{vix_bucket}"
            if _should_send(alert_log, alert_key):
                vix = float(opt_sig.get("vix_spot", 20.0))
                msg = _format_vix_alert(prev_bucket, vix_bucket, vix)
                if has_telegram:
                    _send_telegram(token, chat_id, msg)
                _mark_sent(alert_log, alert_key)
                alerts_sent.append(("vix", f"{prev_bucket}→{vix_bucket}"))
    new_state["vix_bucket"] = vix_bucket

    _save_alert_state(alert_log)
    new_state["last_check"] = datetime.now(timezone.utc).isoformat()
    new_state["alerts_sent_this_run"] = alerts_sent
    new_state["telegram_configured"] = has_telegram

    return new_state
