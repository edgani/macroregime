# START HERE — Full Live War Room

1. Copy `.env.example` to `.env`.
2. Add a real `WARROOM_SEC_USER_AGENT` and only the provider keys you own.
3. Install dependencies:

```bash
pip install -r requirements.txt
pip install -r requirements-streaming.txt
```

4. Validate code and semantics:

```bash
python validate_live_stack.py
python validate_redesign.py
```

5. Start entitled stream workers. See `stream_workers/README.md`.
6. Verify live connections on the deployment machine:

```bash
python verify_live_connections.py --strict --write-report
```

7. Start the dashboard:

```bash
streamlit run app.py
```

Windows users can run `RUN_LIVE_WARROOM.bat` after creating `.env`.

Read `LIVE_DATA_ACTIVATION.md` before interpreting direction, squeeze pressure, Greek context, targets or duration.
