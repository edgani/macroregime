"""Configurable Unusual Whales JSON-WebSocket-to-HTTP bridge.

UW documents JSON WebSocket as the simpler dashboard delivery, but connection URL,
authorization and subscription payloads are entitlement-specific. This worker accepts those
values through environment variables instead of hard-coding an unverified handshake.

Required:
  UW_WEBSOCKET_URL
Optional:
  UW_WEBSOCKET_HEADERS_JSON          JSON object passed as HTTP headers
  UW_WEBSOCKET_AUTH_MESSAGE_JSON     JSON sent immediately after connection
  UW_WEBSOCKET_SUBSCRIBE_MESSAGE_JSON JSON sent after auth
  UW_WEBSOCKET_TOPICS                informational topic list
"""
from __future__ import annotations
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock, Thread
from urllib.parse import parse_qs, urlparse
import json, os, signal, time
import websocket

URL = os.getenv("UW_WEBSOCKET_URL", "").strip()
HOST = os.getenv("UW_WS_BRIDGE_HOST", "127.0.0.1")
PORT = int(os.getenv("UW_WS_BRIDGE_PORT", "8767"))
TOKEN = os.getenv("UW_WS_BRIDGE_TOKEN", "")
TOPICS = [x.strip() for x in os.getenv("UW_WEBSOCKET_TOPICS", "").split(",") if x.strip()]
MAX_PER_TOPIC_TICKER = int(os.getenv("UW_WS_BRIDGE_MAX_PER_TOPIC_TICKER", "150"))
STORE = defaultdict(lambda: defaultdict(lambda: deque(maxlen=MAX_PER_TOPIC_TICKER)))
LOCK = Lock(); RUNNING = True
HEALTH = {"state": "NOT_CONFIGURED" if not URL else "STARTING", "last_message_at": None, "last_error": None, "messages": 0}


def parse_env_json(name, default):
    raw = os.getenv(name, "").strip()
    if not raw: return default
    value = json.loads(raw)
    return value


def ticker_of(payload):
    if not isinstance(payload, dict): return "__GLOBAL__"
    for key in ("ticker", "symbol", "underlying", "underlying_symbol", "underlyingSymbol"):
        if payload.get(key): return str(payload[key]).upper()
    for key in ("data", "payload", "message"):
        if isinstance(payload.get(key), dict):
            t = ticker_of(payload[key])
            if t != "__GLOBAL__": return t
    return "__GLOBAL__"


def topic_of(payload):
    if not isinstance(payload, dict): return "unknown"
    return str(payload.get("topic") or payload.get("type") or payload.get("channel") or payload.get("event") or "unknown")


def run_socket():
    if not URL: return
    headers_obj = parse_env_json("UW_WEBSOCKET_HEADERS_JSON", {})
    header_list = [f"{k}: {v}" for k, v in headers_obj.items()]
    auth = parse_env_json("UW_WEBSOCKET_AUTH_MESSAGE_JSON", None)
    subscribe = parse_env_json("UW_WEBSOCKET_SUBSCRIBE_MESSAGE_JSON", None)
    while RUNNING:
        try:
            def on_open(ws):
                HEALTH.update(state="LIVE", last_error=None)
                if auth is not None: ws.send(json.dumps(auth))
                if subscribe is not None: ws.send(json.dumps(subscribe))
            def on_message(_ws, message):
                try: payload = json.loads(message)
                except Exception: return
                items = payload if isinstance(payload, list) else [payload]
                for item in items:
                    if not isinstance(item, dict): item = {"data": item}
                    topic = topic_of(item); ticker = ticker_of(item)
                    record = {"topic": topic, "ticker": ticker, "received_at": time.time(), "payload": item}
                    with LOCK: STORE[topic][ticker].appendleft(record)
                    HEALTH.update(state="LIVE", last_message_at=record["received_at"], last_error=None,
                                  messages=int(HEALTH["messages"]) + 1)
            def on_error(_ws, error): HEALTH.update(state="ERROR", last_error=str(error))
            ws = websocket.WebSocketApp(URL, header=header_list, on_open=on_open, on_message=on_message, on_error=on_error)
            ws.run_forever(ping_interval=20, ping_timeout=10)
        except Exception as exc:
            HEALTH.update(state="ERROR", last_error=f"{type(exc).__name__}: {exc}")
        if RUNNING: time.sleep(2)


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*_): return
    def write(self, body, status=200):
        raw=json.dumps(body,separators=(",",":"),default=str).encode();self.send_response(status)
        self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(raw)));self.end_headers();self.wfile.write(raw)
    def do_GET(self):
        if TOKEN and self.headers.get("Authorization","") != f"Bearer {TOKEN}": self.write({"state":"UNAUTHORIZED"},401);return
        p=urlparse(self.path)
        if p.path=="/health": self.write({**HEALTH,"topics":TOPICS,"generated":time.time()});return
        if p.path!="/snapshot": self.write({"state":"NOT_FOUND"},404);return
        q=parse_qs(p.query); tickers={x.upper() for x in ",".join(q.get("tickers",[])).split(",") if x};limit=min(2500,int((q.get("limit")or["800"])[0]))
        rows=[]
        with LOCK:
            for topic,by_ticker in STORE.items():
                for ticker,records in by_ticker.items():
                    if tickers and ticker not in tickers and ticker!="__GLOBAL__": continue
                    rows.extend(list(records))
        rows.sort(key=lambda x:x.get("received_at",0),reverse=True)
        self.write({"state":HEALTH["state"],"generated":time.time(),"health":HEALTH,"data":rows[:limit]})


def stop(*_):
    global RUNNING; RUNNING=False

def main():
    for sig in (signal.SIGINT,signal.SIGTERM): signal.signal(sig,stop)
    Thread(target=run_socket,daemon=True).start();server=ThreadingHTTPServer((HOST,PORT),Handler);server.timeout=1
    print(f"UW WebSocket bridge listening on http://{HOST}:{PORT}/snapshot",flush=True)
    try:
        while RUNNING: server.handle_request()
    finally: server.server_close()

if __name__=="__main__": main()
