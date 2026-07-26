#!/usr/bin/env bash
set -euo pipefail
if [[ $EUID -ne 0 ]]; then echo "Run as root" >&2; exit 1; fi
APP=/opt/warroom
id warroom >/dev/null 2>&1 || useradd --system --create-home --home-dir /var/lib/warroom warroom
mkdir -p "$APP"
cp -a . "$APP/"
python3 -m venv "$APP/.venv"
"$APP/.venv/bin/pip" install --upgrade pip
"$APP/.venv/bin/pip" install -r "$APP/requirements.txt"
"$APP/.venv/bin/pip" install "$APP"
mkdir -p "$APP/runtime" /var/lib/warroom/.streamlit
chown -R warroom:warroom "$APP" /var/lib/warroom
runuser -u warroom -- env PYTHONPATH="$APP/src" WARROOM_ROOT="$APP" "$APP/.venv/bin/python" "$APP/scripts/build_release_manifest.py" --check
runuser -u warroom -- env PYTHONPATH="$APP/src" WARROOM_ROOT="$APP" "$APP/.venv/bin/python" "$APP/scripts/build_prospective_seal.py" --check
runuser -u warroom -- env PYTHONPATH="$APP/src" WARROOM_ROOT="$APP" "$APP/.venv/bin/python" "$APP/scripts/check_provider_registry.py"
runuser -u warroom -- env PYTHONPATH="$APP/src" WARROOM_ROOT="$APP" "$APP/.venv/bin/python" "$APP/scripts/check_runtime_store.py"
runuser -u warroom -- env PYTHONPATH="$APP/src" WARROOM_ROOT="$APP" "$APP/.venv/bin/python" "$APP/scripts/check_streamlit_app.py"
cp "$APP/ops/systemd/warroom-streamlit.service" /etc/systemd/system/
cp "$APP/ops/systemd/warroom-collector.service" /etc/systemd/system/
cp "$APP/ops/systemd/warroom-collector.timer" /etc/systemd/system/
systemctl daemon-reload
runuser -u warroom -- "$APP/.venv/bin/python" "$APP/ops/connectivity_probe.py"
runuser -u warroom -- env PYTHONPATH="$APP/src" WARROOM_ROOT="$APP" "$APP/.venv/bin/python" "$APP/scripts/warroom.py" bootstrap-all
systemctl disable --now warroom-api.service 2>/dev/null || true
systemctl enable --now warroom-streamlit.service warroom-collector.timer
echo "Streamlit is bound to localhost. Use: ssh -L 8501:127.0.0.1:8501 ubuntu@SERVER_IP"
echo "Then open: http://127.0.0.1:8501"
