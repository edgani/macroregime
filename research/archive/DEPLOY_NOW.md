# Deploy V7.9 Now

1. Extract to a fresh folder.
2. Install dependencies with `python -m pip install -r requirements.txt` when needed.
3. Run `CHECK_FINAL_V79.bat`.
4. Run `SETUP_FINAL_CORE.bat`.
5. Run `RUN_FINAL_CORE.bat` after a calendar month has completed.
6. Launch the dashboard with `RUN_WARROOM.bat` only for visualization; the authoritative order receipt is `runtime/v79_last_instruction.json`.

No broker order is sent automatically. Any fail-closed or blocked state means no trade.
