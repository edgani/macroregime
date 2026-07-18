# Start Here

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Configure at minimum a real SEC user-agent; add paid provider keys as available. See `.env.example` and `DATA_CONNECTORS.md`.

3. Start:

```bash
streamlit run app.py
```

4. Open the Streamlit URL. The default view is `OBSERVED`. Use `ALL LAYERS` only when you intentionally want structural/inferred maps shown alongside observed data.

5. Run the integrity audit after changes:

```bash
python validate_redesign.py
```

The included `War_Room_OS_preview.html` outside the project folder is a UI preview fixture only. It is not the production data path.
