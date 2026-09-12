#!/usr/bin/env bash
# Reads the current quick-tunnel URL from cloudflared's log and publishes it as the API base in docs/config.js
# (committed + pushed so GitHub Pages picks it up). Also records PUBLIC_URL/API_URL settings.
set -uo pipefail
APP=/opt/worth-one
LOG=/var/log/worth-tunnel.log
URL=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$LOG" 2>/dev/null | tail -1)
[ -z "$URL" ] && { echo "no tunnel url yet"; exit 0; }
# verify the tunnel actually answers
curl -fsS -m 10 "$URL/healthz" >/dev/null 2>&1 || { echo "tunnel $URL not healthy"; exit 0; }
CUR=$(grep -oE 'WO_API = "[^"]*"' "$APP/docs/config.js" | sed -E 's/WO_API = "([^"]*)"/\1/')
worthctl cmd SET "API_URL=$URL" >/dev/null
worthctl cmd SET "PUBLIC_URL=https://furiadelimon.github.io/worth-one" >/dev/null
[ "$CUR" = "$URL" ] && exit 0
cd "$APP" && git pull --ff-only -q || true
sed -i -E "s#WO_API = \"[^\"]*\"#WO_API = \"$URL\"#" docs/config.js
git config user.email "worth-one-bot@users.noreply.github.com"; git config user.name "worth-one bot"
git add docs/config.js && git commit -q -m "ops: tunnel url -> $URL" && git push -q origin HEAD:main && echo "published $URL" \
  && worthctl activity ops "Published new API tunnel URL $URL to GitHub Pages"
