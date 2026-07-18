"""Massive stock/options WebSocket-to-HTTP snapshot bridge.

Run separately from Streamlit. It stores trade/quote events in memory and exposes
/snapshot. Exact subscriptions depend on the user's market-data entitlement.
"""
from __future__ import annotations

from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock, Thread
from urllib.parse import parse_qs, urlparse
import json
import os
import signal
import time

import websocket

API_KEY = os.environ.get("MASSIVE_API_KEY", "")
HOST = os.getenv("MASSIVE_BRIDGE_HOST", "127.0.0.1")
PORT = int(os.getenv("MASSIVE_BRIDGE_PORT", "8766"))
TOKEN = os.getenv("MASSIVE_BRIDGE_TOKEN", "")
STOCKS = [x.strip().upper() for x in os.getenv("MASSIVE_STREAM_STOCKS", "SPY,QQQ,NVDA,AMD,TSLA").split(",") if x.strip()]
OPTION_SUBS = [x.strip() for x in os.getenv("MASSIVE_OPTIONS_SUBSCRIPTIONS", "").split(",") if x.strip()]
MAX_EVENTS = int(os.getenv("MASSIVE_BRIDGE_MAX_EVENTS", "5000"))
EVENTS = deque(maxlen=MAX_EVENTS)
LOCK = Lock()
RUNNING = True


def add_event(market, row):
    if not isinstance(row, dict):
        return
    ev = row.get("ev") or row.get("event_type")
    symbol = row.get("sym") or row.get("symbol") or row.get("ticker")
    normalized = {
        "market": market, "event": ev, "ticker": symbol,
        "timestamp": row.get("t") or row.get("sip_timestamp") or time.time() * 1000,
        "price": row.get("p") or row.get("price"), "size": row.get("s") or row.get("size"),
        "exchange": row.get("x") or row.get("exchange"),
        "trf_id": row.get("trfi") or row.get("trf_id"),
        "bid": row.get("bp") or row.get("bid_price"), "ask": row.get("ap") or row.get("ask_price"),
        "bid_size": row.get("bs") or row.get("bid_size"), "ask_size": row.get("as") or row.get("ask_size"),
        "conditions": row.get("c") or row.get("conditions") or [], "raw": row,
        "received_at": time.time(),
    }
    with LOCK:
        EVENTS.appendleft(normalized)


def run_socket(market, url, subscriptions):
    while RUNNING:
        try:
            def on_open(ws):
                ws.send(json.dumps({"action":"auth","params":API_KEY}))
                if subscriptions:
                    ws.send(json.dumps({"action":"subscribe","params":",".join(subscriptions)}))
            def on_message(_ws, message):
                try:
                    payload = json.loads(message)
                except Exception:
                    return
                for row in payload if isinstance(payload, list) else [payload]:
                    add_event(market, row)
            ws = websocket.WebSocketApp(url, on_open=on_open, on_message=on_message)
            ws.run_forever(ping_interval=20, ping_timeout=10)
        except Exception as exc:
            print(f"{market} socket error: {exc}", flush=True)
        if RUNNING:
            time.sleep(2)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_): return
    def do_GET(self):
        if TOKEN and self.headers.get("Authorization", "") != f"Bearer {TOKEN}":
            self.send_response(401); self.end_headers(); return
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            body = {"state":"LIVE" if RUNNING else "STOPPING","events":len(EVENTS),"generated":time.time()}
        elif parsed.path == "/snapshot":
            q = parse_qs(parsed.query)
            tickers = {x.upper() for x in ",".join(q.get("tickers", [])).split(",") if x}
            kind = (q.get("kind") or ["all"])[0]
            limit = min(2000, int((q.get("limit") or ["500"])[0]))
            with LOCK:
                rows = list(EVENTS)
            if kind != "all": rows = [x for x in rows if x.get("market") == kind]
            if tickers: rows = [x for x in rows if str(x.get("ticker") or "").upper() in tickers or x.get("market") == "options"]
            body = {"state":"LIVE","generated":time.time(),"data":rows[:limit]}
        else:
            self.send_response(404); self.end_headers(); return
        raw = json.dumps(body,separators=(",", ":")).encode()
        self.send_response(200);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(raw)));self.end_headers();self.wfile.write(raw)


def stop(*_):
    global RUNNING
    RUNNING = False


def main():
    if not API_KEY:
        raise SystemExit("MASSIVE_API_KEY is required")
    signal.signal(signal.SIGINT, stop); signal.signal(signal.SIGTERM, stop)
    stock_subs = [f"T.{t}" for t in STOCKS]
    Thread(target=run_socket,args=("stocks",os.getenv("MASSIVE_STOCKS_WS_URL","wss://socket.massive.com/stocks"),stock_subs),daemon=True).start()
    if OPTION_SUBS:
        Thread(target=run_socket,args=("options",os.getenv("MASSIVE_OPTIONS_WS_URL","wss://socket.massive.com/options"),OPTION_SUBS),daemon=True).start()
    server=ThreadingHTTPServer((HOST,PORT),Handler)
    print(f"Massive bridge listening on http://{HOST}:{PORT}/snapshot",flush=True)
    try:
        while RUNNING: server.handle_request()
    finally: server.server_close()


if __name__ == "__main__": main()
