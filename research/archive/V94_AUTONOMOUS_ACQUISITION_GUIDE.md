# Autonomous acquisition guide

1. Set `WARROOM_SEC_USER_AGENT` to an application name plus a real contact email.
2. Set a free `FRED_API_KEY`; `CFTC_APP_TOKEN` is optional but recommended.
3. Run `python autonomous_public_data_plane_v94.py`.
4. For IDX, use the generated official-browser handoff. Export the Network JSON response without editing and import it with `V94_BROWSER_EXPORT_IMPORT.py`.
5. Licensed history and account fills remain separate imports. Their absence cannot be solved by web search because they are access-controlled or private.

The collector never generates forecasts or orders.
