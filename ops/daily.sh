#!/usr/bin/env bash
# Daily: build report (with brain insights if the last brain run left any), keep the repo in sync.
set -uo pipefail
INS=/var/lib/worth-one/insights.json
if [ -s "$INS" ]; then worthctl report --insights "$INS"; else worthctl report; fi
git -C /opt/worth-one pull --ff-only -q || true
/usr/local/bin/worth-indexnow || true
