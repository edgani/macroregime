# Deploy from zero — GitHub preview first, then Vercel + Cloud Run

## Stage A — inspect v2.4 before migrating the frontend

1. Extract the ZIP locally.
2. Replace the files in your GitHub repository with the extracted contents.
3. Commit and push.
4. If the repository is already connected to Streamlit Community Cloud, it will redeploy from the new commit. Use this as the **visual approval build**.
5. Check these three screens first:
   - Opportunities → Leverage: US, Crypto, FX and Commodity must all be visible. Only qualified rows may say ACTION.
   - Opportunities → Options: US + BTC/ETH must be visible. Non-qualified BTC/ETH must say thesis gated rather than disappear.
   - Macro & Events: the first screen should be the projection heatmap + pressure chart rather than long prose.

GitHub itself renders source/README, not a live Streamlit application. The live visual check is the Streamlit deployment attached to the GitHub commit.

## Stage B — final production architecture after visual approval

Target:

```
Vercel / Next.js frontend
        |
        | HTTPS JSON
        v
Google Cloud Run / Python API
        |
        +-- macro engine
        +-- opportunity scanner
        +-- entry engine
        +-- expression engine
        +-- replay / backtest jobs
```

Do not deploy the current Streamlit `app.py` directly to Vercel as the final product. Streamlit remains the research/diagnostic app; the production UI should be a Next.js client backed by the Python API.

### Google Cloud Run account setup

- Create a Google Cloud project.
- Attach billing (Cloud Run free-tier usage is applied before charges; still configure billing budgets/alerts).
- Install Google Cloud CLI locally, then run:

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com
```

Use Jakarta unless you have a reason not to:

```bash
gcloud config set run/region asia-southeast2
```

### Cloud Run deploy command once the API folder exists

From the Python API directory:

```bash
gcloud run deploy oie-api \
  --source . \
  --region asia-southeast2 \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --min 0 \
  --max 2
```

Cloud Run prints an HTTPS service URL after a successful deployment. Keep that URL; it becomes the frontend API base URL.

### Vercel setup once the Next.js frontend folder exists

1. Sign in to Vercel with GitHub.
2. Add New → Project → Import the same GitHub repository.
3. If the frontend is in a monorepo folder such as `web`, set **Root Directory = web**.
4. Framework Preset should auto-detect Next.js.
5. Add an environment variable:

```
NEXT_PUBLIC_OIE_API_URL=https://YOUR-CLOUD-RUN-URL
```

6. Deploy.
7. After changing an environment variable, redeploy so the new value is applied.

## Why Stage B is intentionally after approval
The v2.4 change is primarily a decision/UX contract change. Approving the visual hierarchy in the existing research app first prevents doing the same frontend redesign twice.
