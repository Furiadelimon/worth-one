#!/usr/bin/env bash
# Pings IndexNow (Bing, Yandex, Naver, Seznam) with the Words Before Coffee sitemap URLs, at most once a day and only
# when the key file is live on the domain (the WBC app serves it at /indexnow.txt once WBC_INDEXNOW_KEY is set).
set -uo pipefail
HOST=wordsbeforecoffee.com
KEY=$(curl -fsS -m 10 "https://$HOST/indexnow.txt" 2>/dev/null | tr -d '[:space:]')
[ -z "$KEY" ] && { echo "no indexnow key published on $HOST yet"; exit 0; }
LAST=/var/lib/worth-one/indexnow-wbc.last
[ -f "$LAST" ] && [ "$(cat "$LAST")" = "$(date -u +%F)" ] && exit 0
URLS=$(curl -fsS -m 10 "https://$HOST/sitemap.xml" | grep -oE '<loc>[^<]+</loc>' | sed -E 's#</?loc>##g')
[ -z "$URLS" ] && { echo "no sitemap"; exit 0; }
BODY=$(printf '%s\n' "$URLS" | python3 -c "import json,sys;u=[l.strip() for l in sys.stdin if l.strip()];print(json.dumps({'host':'$HOST','key':'$KEY','keyLocation':'https://$HOST/indexnow.txt','urlList':u}))")
CODE=$(curl -s -o /dev/null -w '%{http_code}' -X POST https://api.indexnow.org/indexnow -H 'content-type: application/json; charset=utf-8' --data-binary "$BODY")
if [ "$CODE" = "200" ] || [ "$CODE" = "202" ]; then
  date -u +%F > "$LAST"
  worthctl activity seo "IndexNow: submitted $(printf '%s\n' "$URLS" | grep -c .) Words Before Coffee URLs (HTTP $CODE)" "WBC"
else
  worthctl activity seo "IndexNow submission for Words Before Coffee failed (HTTP $CODE)" "WBC"
fi
