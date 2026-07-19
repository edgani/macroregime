# Start War Room OS v2.3

1. Double-click `RUN_FAST_WARROOM.bat`.
2. On the first run, missing Python packages are installed from `requirements.txt`.
3. The browser opens immediately while `warroom_data_worker.py` collects data in the background.
4. Copy `.env.example` to `.env` and fill the providers you are entitled to use.
5. For public SEC EDGAR data, replace the placeholder in `WARROOM_SEC_USER_AGENT` with a descriptive app name and real contact email.

The application distinguishes `NO_SIGNAL`, `ACTION_REQUIRED`, `NOT_ENTITLED`, `STALE`, and true `NO_DATA`. It never fills missing production data with synthetic values.
