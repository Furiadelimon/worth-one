#!/usr/bin/env bash
# Pings IndexNow (Bing, Yandex, Naver, Seznam) with every site URL whenever site/urls.json changes. Runs from worth-daily.
set -uo pipefail
APP=/opt/worth-one
KEY=$(cat "$APP/ops/indexnow.key" 2>/dev/null) || exit 0
URLS="$APP/site/urls.json"
[ -f "$URLS" ] || exit 0
HASH=$(sha256sum "$URLS" | cut -c1-16)
LAST=/var/lib/worth-one/indexnow.last
[ -f "$LAST" ] && [ "$(cat "$LAST")" = "$HASH" ] && exit 0
BODY=$(python3 -c "import json;u=json.load(open('$URLS'));k='$KEY';print(json.dumps({'host':'furiadelimon.github.io','key':k,'keyLocation':'https://furiadelimon.github.io/worth-one/'+k+'.txt','urlList':u}))")
CODE=$(curl -s -o /dev/null -w '%{http_code}' -X POST https://api.indexnow.org/indexnow -H 'content-type: application/json; charset=utf-8' --data-binary "$BODY")
if [ "$CODE" = "200" ] || [ "$CODE" = "202" ]; then
  echo "$HASH" > "$LAST"
  worthctl activity seo "Submitted $(python3 -c "import json;print(len(json.load(open('$URLS'))))") URLs to IndexNow (HTTP $CODE)" ""
else
  worthctl activity seo "IndexNow submission failed (HTTP $CODE)" ""
fi
