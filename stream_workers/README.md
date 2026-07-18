# Persistent live-stream workers

Streamlit reruns are not a safe owner for permanent WebSocket or Kafka sessions. Run these workers as separate processes. They expose bounded local `/snapshot` endpoints and `/health`; War Room isolates failures and shows `STALE`, `OFFLINE`, `NOT_CONFIGURED`, or `ERROR` rather than fabricating data.

## 1. Unusual Whales Kafka bridge

`uw_kafka_bridge.py` consumes entitled topics such as Greek flow, live GEX, option states, IV term structure, risk-reversal skew, net flow, flow alerts and option trades.

The official stream is protobuf. Set `UW_KAFKA_DECODER_MODULE` to a local Python module exposing:

```python
def decode(topic: str, value: bytes, key: bytes | None) -> dict:
    ...
```

Then point the app to:

```env
UNUSUAL_WHALES_STREAM_BRIDGE_URL="http://127.0.0.1:8765/snapshot"
UNUSUAL_WHALES_STREAM_BRIDGE_TOKEN="...optional..."
```

`uw_websocket_bridge.py` is an alternative only when the provider gives your account a JSON WebSocket gateway and subscription messages.

## 2. Massive stock/options bridge

`massive_ws_bridge.py` maintains entitled stock and option WebSockets. Configure exact stock and option subscriptions allowed by the account:

```env
MASSIVE_STREAM_BRIDGE_URL="http://127.0.0.1:8766/snapshot"
MASSIVE_STREAM_BRIDGE_TOKEN="...optional..."
```

The stock stream preserves exchange/TRF identifiers. A print remains `intent unconfirmed`; size alone is not accumulation.

## 3. Databento futures/options bridge

`databento_bridge.py` uses the official Databento Live client. Configure one dataset per worker and explicit schemas/symbol types in `DATABENTO_SUBSCRIPTIONS_JSON`. The default example subscribes to CME `statistics` and `trades` for ES/NQ/CL/GC parent symbols.

```env
DATABENTO_STREAM_BRIDGE_URL="http://127.0.0.1:8767/snapshot"
DATABENTO_STREAM_BRIDGE_TOKEN="...optional..."
```

Statistics records can include open interest and settlement values. They do not reveal which side initiated a position.

## Run

```bash
pip install -r requirements.txt -r requirements-streaming.txt
python stream_workers/uw_kafka_bridge.py
python stream_workers/massive_ws_bridge.py
python stream_workers/databento_bridge.py
```

Use separate terminals or a process supervisor. Verify `/health` before starting Streamlit.
