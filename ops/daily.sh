#!/usr/bin/env bash
# Daily (00:05 UTC): Words Before Coffee growth report + IndexNow for the WBC sitemap. Worth One is archived:
# no outreach batch, no Worth One IndexNow, nothing external for it.
set -uo pipefail
INS=/var/lib/worth-one/insights.json
if [ -s "$INS" ]; then R=$(worthctl report --insights "$INS"); else R=$(worthctl report); fi
worthctl notify "$(echo "$R" | head -30)" >/dev/null 2>&1 || true
git -C /opt/worth-one pull --ff-only -q || true
/usr/local/bin/worth-indexnow-wbc || true
