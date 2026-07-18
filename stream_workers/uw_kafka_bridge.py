"""Persistent Unusual Whales Kafka-to-HTTP snapshot bridge.

Official UW Kafka messages are protobuf encoded. This worker therefore requires a decoder
module supplied with the streaming entitlement/schema. It never silently treats protobuf as
JSON. For the provider's JSON WebSocket delivery, use ``uw_websocket_bridge.py`` instead.

Required:
  UW_KAFKA_BOOTSTRAP_SERVERS
  UW_KAFKA_DECODER_MODULE   Python module exposing decode(topic, value_bytes, key_bytes)->dict
Optional:
  UW_KAFKA_USERNAME / UW_KAFKA_PASSWORD and normal Kafka security variables.
"""
from __future__ import annotations

from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import import_module
from threading import Lock, Thread
from urllib.parse import parse_qs, urlparse
import json
import os
import signal
import time

from confluent_kafka import Consumer, KafkaError

TOPICS = [x.strip() for x in os.getenv(
    "UW_KAFKA_TOPICS",
    "greek-flow,live-gex,net-flow,option-states,interpolated-iv,iv-term-structure,"
    "risk-reversal-skew,interval-flow,chain-frag,multi-leg-spreads,flow-alerts,"
    "all-option-trades,all-trade-report,sec-filings,ticker-stock-states,trading-halts",
).split(",") if x.strip()]
HOST = os.getenv("UW_BRIDGE_HOST", "127.0.0.1")
PORT = int(os.getenv("UW_BRIDGE_PORT", "8765"))
TOKEN = os.getenv("UW_BRIDGE_TOKEN", "")
MAX_PER_TOPIC_TICKER = int(os.getenv("UW_BRIDGE_MAX_PER_TOPIC_TICKER", "150"))
DECODER_MODULE = os.getenv("UW_KAFKA_DECODER_MODULE", "").strip()
ALLOW_JSON = os.getenv("UW_KAFKA_ALLOW_JSON", "0") == "1"

STORE = defaultdict(lambda: defaultdict(lambda: deque(maxlen=MAX_PER_TOPIC_TICKER)))
LOCK = Lock()
RUNNING = True
HEALTH = {"state": "STARTING", "last_message_at": None, "last_error": None, "decoded": 0, "dropped": 0}


def _load_decoder():
    if not DECODER_MODULE:
        return None
    module = import_module(DECODER_MODULE)
    decoder = getattr(module, "decode", None)
    if not callable(decoder):
        raise RuntimeError(f"{DECODER_MODULE}.decode(topic, value_bytes, key_bytes) is required")
    return decoder


def ticker_of(payload, key_bytes=None):
    if isinstance(payload, dict):
        for key in ("ticker", "symbol", "underlying", "underlying_symbol", "underlyingSymbol"):
            value = payload.get(key)
            if value:
                return str(value).upper()
        data = payload.get("data") or payload.get("payload")
        if isinstance(data, dict):
            nested = ticker_of(data, key_bytes)
            if nested != "__GLOBAL__":
                return nested
    if key_bytes:
        try:
            value = key_bytes.decode("utf-8").strip()
            if value:
                return value.upper()
        except Exception:
            pass
    return "__GLOBAL__"


def _decode(decoder, topic, value, key):
    if decoder is not None:
        payload = decoder(topic, value, key)
        if not isinstance(payload, dict):
            raise TypeError("decoder must return dict")
        return payload
    if ALLOW_JSON:
        payload = json.loads(value.decode("utf-8"))
        if not isinstance(payload, dict):
            return {"data": payload}
        return payload
    raise RuntimeError("UW Kafka is protobuf: set UW_KAFKA_DECODER_MODULE or use uw_websocket_bridge.py")


def consume():
    global RUNNING
    try:
        decoder = _load_decoder()
        config = {
            "bootstrap.servers": os.environ["UW_KAFKA_BOOTSTRAP_SERVERS"],
            "group.id": os.getenv("UW_KAFKA_GROUP_ID", "warroom-live"),
            "auto.offset.reset": os.getenv("UW_KAFKA_OFFSET_RESET", "latest"),
            "enable.auto.commit": True,
        }
        username = os.getenv("UW_KAFKA_USERNAME", "")
        password = os.getenv("UW_KAFKA_PASSWORD", "")
        if username or password:
            config.update({
                "security.protocol": os.getenv("UW_KAFKA_SECURITY_PROTOCOL", "SASL_SSL"),
                "sasl.mechanisms": os.getenv("UW_KAFKA_SASL_MECHANISM", "PLAIN"),
                "sasl.username": username,
                "sasl.password": password,
            })
        consumer = Consumer(config)
        consumer.subscribe(TOPICS)
        HEALTH["state"] = "LIVE"
        try:
            while RUNNING:
                message = consumer.poll(1.0)
                if message is None:
                    continue
                if message.error():
                    if message.error().code() != KafkaError._PARTITION_EOF:
                        HEALTH.update(state="ERROR", last_error=str(message.error()))
                    continue
                try:
                    payload = _decode(decoder, message.topic(), message.value(), message.key())
                    record = {
                        "topic": message.topic(), "partition": message.partition(), "offset": message.offset(),
                        "received_at": time.time(), "ticker": ticker_of(payload, message.key()), "payload": payload,
                    }
                    with LOCK:
                        STORE[record["topic"]][record["ticker"]].appendleft(record)
                    HEALTH.update(state="LIVE", last_message_at=record["received_at"], last_error=None,
                                  decoded=int(HEALTH["decoded"]) + 1)
                except Exception as exc:
                    HEALTH.update(state="ERROR", last_error=f"{type(exc).__name__}: {exc}",
                                  dropped=int(HEALTH["dropped"]) + 1)
        finally:
            consumer.close()
    except Exception as exc:
        HEALTH.update(state="ERROR", last_error=f"{type(exc).__name__}: {exc}")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_):
        return

    def _authorized(self):
        return not TOKEN or self.headers.get("Authorization", "") == f"Bearer {TOKEN}"

    def _write(self, body, status=200):
        raw = json.dumps(body, separators=(",", ":"), default=str).encode("utf-8")
        self.send_response(status); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw))); self.end_headers(); self.wfile.write(raw)

    def do_GET(self):
        if not self._authorized():
            self._write({"state": "UNAUTHORIZED"}, 401); return
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._write({**HEALTH, "topics": TOPICS, "generated": time.time(), "decoder_module": DECODER_MODULE or None}); return
        if parsed.path != "/snapshot":
            self._write({"state": "NOT_FOUND"}, 404); return
        query = parse_qs(parsed.query)
        tickers = {x.upper() for x in ",".join(query.get("tickers", [])).split(",") if x}
        topics = set(query.get("topic", [])) or set(TOPICS)
        limit = min(2500, int((query.get("limit") or ["800"])[0]))
        rows = []
        with LOCK:
            for topic, by_ticker in STORE.items():
                if topic not in topics:
                    continue
                for ticker, records in by_ticker.items():
                    if tickers and ticker not in tickers and ticker != "__GLOBAL__":
                        continue
                    rows.extend(list(records))
        rows.sort(key=lambda x: x.get("received_at", 0), reverse=True)
        self._write({"state": HEALTH["state"], "generated": time.time(), "topics": TOPICS,
                     "health": HEALTH, "data": rows[:limit]})


def stop(*_):
    global RUNNING
    RUNNING = False


def main():
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, stop)
    Thread(target=consume, daemon=True).start()
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    server.timeout = 1.0
    print(f"UW Kafka bridge listening on http://{HOST}:{PORT}/snapshot", flush=True)
    try:
        while RUNNING:
            server.handle_request()
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
