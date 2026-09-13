#!/usr/bin/env bash
# Daily: build report (with brain insights if the last brain run left any), keep the repo in sync.
set -uo pipefail
INS=/var/lib/worth-one/insights.json
if [ -s "$INS" ]; then R=$(worthctl report --insights "$INS"); else R=$(worthctl report); fi
worthctl notify "$(echo "$R" | head -24)" >/dev/null 2>&1 || true
git -C /opt/worth-one pull --ff-only -q || true
/usr/local/bin/worth-indexnow || true
worthctl outreach-batch 5 || true
