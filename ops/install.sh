#!/usr/bin/env bash
# Installs / updates PROJECT WORTH ONE inside the LXC (Debian 13). Idempotent.
# Layout: /opt/worth-one (git clone), /var/lib/worth-one (db), /etc/worth-one/env (secrets, never in git)
set -euo pipefail
APP=/opt/worth-one
DATA=/var/lib/worth-one
ENVF=/etc/worth-one/env
REPO=${REPO:-https://github.com/Furiadelimon/worth-one.git}

mkdir -p "$DATA" /etc/worth-one
if [ ! -d "$APP/.git" ]; then git clone "$REPO" "$APP"; else git -C "$APP" pull --ff-only; fi

if [ ! -f "$ENVF" ]; then
  cat > "$ENVF" <<EOF
WORTH_ADMIN_TOKEN=$(head -c 24 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | head -c 32)
WORTH_DB=$DATA/worth.db
WORTH_SITE=$APP/docs
# WORTH_NTFY_TOPIC=worthone-xxxx        # optional: ntfy.sh topic for phone pushes
# CLAUDE_CODE_OAUTH_TOKEN=               # from: claude setup-token   (enables the autonomous brain)
# WORTH_BRAIN_MODEL=sonnet
EOF
  chmod 600 "$ENVF"
fi

if [ ! -d "$APP/.venv" ]; then python3 -m venv "$APP/.venv"; fi
"$APP/.venv/bin/pip" install -q -r "$APP/server/requirements.txt"

install -m 755 "$APP/ops/worthctl" /usr/local/bin/worthctl
install -m 755 "$APP/ops/tunnel-sync.sh" /usr/local/bin/worth-tunnel-sync
install -m 755 "$APP/ops/daily.sh" /usr/local/bin/worth-daily
install -m 755 "$APP/brain/run.sh" /usr/local/bin/worth-brain
for u in worth-one.service worth-tunnel.service worth-tunnel-sync.service worth-tunnel-sync.timer worth-daily.service worth-daily.timer worth-brain.service worth-brain.timer; do
  install -m 644 "$APP/ops/systemd/$u" /etc/systemd/system/$u
done
systemctl daemon-reload
systemctl enable --now worth-one.service worth-daily.timer worth-brain.timer
# Public ingress (Cloudflare quick tunnel) is only enabled when the owner explicitly asks for it: ENABLE_TUNNEL=1 bash ops/install.sh
if [ "${ENABLE_TUNNEL:-0}" = "1" ]; then systemctl enable --now worth-tunnel.service worth-tunnel-sync.timer; fi
systemctl restart worth-one.service
sleep 2
set -a; . "$ENVF"; set +a
"$APP/.venv/bin/python" "$APP/server/worthctl.py" seed
curl -fsS http://127.0.0.1:8080/healthz && echo
echo "OK. Control center: http://192.168.1.140:8080/admin?token=$WORTH_ADMIN_TOKEN"
