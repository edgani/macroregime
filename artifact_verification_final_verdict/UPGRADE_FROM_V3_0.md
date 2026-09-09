# Upgrade from v3.0 to v3.1

1. Replace the v3.0 project files with this ZIP.
2. Keep `.streamlit/secrets.toml` from your existing install if you already configured optional IHSG data providers.
3. Double-click `START_MARKET_OPPORTUNITY_OS.bat` on Windows, or use `run_linux.sh` on Linux.
4. The existing Market Memory database can remain in the `state/` folder. New story/expectation fields will begin accumulating from the first v3.1 refresh.
5. Historical analyst revisions before v3.1 are not reconstructed automatically; they remain unavailable unless separately backfilled from a point-in-time source.
