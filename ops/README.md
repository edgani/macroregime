# Streamlit Operations Runbook

## 1. Verify package integrity

```bash
sha256sum -c WarRoom_OS_v3_Streamlit_Trading_2026-07-13.sha256
python scripts/validate_all.py
```

## 2. Install on Oracle Ubuntu

```bash
sudo bash ops/install_oracle_ubuntu.sh
```

The installer:

1. creates a non-root `warroom` service user;
2. copies the release to `/opt/warroom`;
3. creates a virtual environment;
4. installs dependencies and the local package;
5. checks Binance public-market-data connectivity;
6. bootstraps BTCUSDT and ETHUSDT;
7. installs the Streamlit service and collector timer;
8. binds Streamlit to `127.0.0.1:8501`.

## 3. Secure access

```bash
ssh -L 8501:127.0.0.1:8501 ubuntu@SERVER_IP
```

Open `http://127.0.0.1:8501` locally.

Do not expose port 8501 directly to the public internet without an authenticated reverse proxy or private network.

## 4. Optional operator PIN

```bash
sudo systemctl edit warroom-streamlit.service
```

```ini
[Service]
Environment=WARROOM_OPERATOR_PIN=replace-with-a-long-secret
```

```bash
sudo systemctl daemon-reload
sudo systemctl restart warroom-streamlit.service
```

## 5. Service health

```bash
sudo systemctl status warroom-streamlit.service
sudo systemctl status warroom-collector.timer
sudo journalctl -u warroom-streamlit.service -n 100 --no-pager
sudo journalctl -u warroom-collector.service -n 100 --no-pager
curl http://127.0.0.1:8501/_stcore/health
```

A healthy Streamlit endpoint returns `ok`.

## 6. Data operations

```bash
warroom bootstrap-all
warroom collect-all
warroom status
warroom evaluate
```

The collector timer runs every five minutes but only stores finalized bars newer than the per-scope head.

## 7. Backups

Stop writes briefly, copy the runtime directory, then resume:

```bash
sudo systemctl stop warroom-collector.timer
sudo tar -C /opt/warroom -czf /var/backups/warroom-runtime-$(date -u +%Y%m%dT%H%M%SZ).tgz runtime
sudo systemctl start warroom-collector.timer
```

Never edit journal lines to repair a failure. Preserve the runtime copy and diagnose separately.

## 8. Upgrade

1. Back up `/opt/warroom/runtime`.
2. Validate the new package before installation.
3. Stop Streamlit and the collector timer.
4. Replace code but preserve runtime.
5. Re-run validation.
6. Confirm the release manifest and prospective seal were intentionally regenerated.
7. Start services and check health.

## 9. Docker

```bash
docker compose up --build -d
ssh -L 8501:127.0.0.1:8501 ubuntu@SERVER_IP
```

The compose file binds Streamlit to localhost and persists `./runtime`.
