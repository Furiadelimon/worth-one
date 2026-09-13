#!/usr/bin/env bash
# Autonomous brain run. Uses Claude Code non-interactively (existing subscription auth via CLAUDE_CODE_OAUTH_TOKEN).
# The brain reads the full project state, then returns a JSON plan which this script applies through worthctl.
# It never touches money, never posts anywhere by itself: it produces content, ideas, decisions and activity records.
set -uo pipefail
export PATH=$PATH:/root/.local/bin:/usr/local/bin
APP=/opt/worth-one
OUT=/var/lib/worth-one/brain
mkdir -p "$OUT"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
MODEL=${WORTH_BRAIN_MODEL:-sonnet}
NEXT=$(( $(date +%s) + 6*3600 ))

if [ "$(worthctl state | python3 -c 'import sys,json;print(json.load(sys.stdin)["settings"]["PROJECT_STATUS"])')" = "PAUSED" ]; then
  worthctl run brain skipped "PROJECT PAUSED by owner" "$NEXT"; exit 0
fi
if { [ -z "${CLAUDE_CODE_OAUTH_TOKEN:-}" ] && [ ! -f /root/.claude/.credentials.json ]; } || ! command -v claude >/dev/null 2>&1; then
  worthctl human "Authorize the autonomous brain" "On the LXC either run 'claude' and log in (/login), or run 'claude setup-token' and then 'worth-authorize <token>'. Until then, only deterministic jobs run (site, analytics, reports)."
  worthctl run brain skipped "brain not authorized (no CLAUDE_CODE_OAUTH_TOKEN)" "$NEXT"; exit 0
fi

STATE=$(worthctl state --compact)
PROMPT=$(cat "$APP/brain/prompt.md"; echo; echo '## CURRENT STATE (compact JSON)'; echo "$STATE"; echo; echo '## CONTENT ALREADY WRITTEN (do not repeat)'; ls -1 "$APP/engine/content" "$APP/engine/tiktok" 2>/dev/null | tr '
' ' ')
cd "$APP"
worthctl cmd "SET CURRENT ACTION" "Brain run $STAMP in progress" >/dev/null
RAW=$(printf '%s' "$PROMPT" | claude -p --model "$MODEL" --output-format json --max-turns 3 --tools "" 2>"$OUT/$STAMP.err") || true
echo "$RAW" > "$OUT/$STAMP.raw.json"
# retry once if the answer is not a JSON plan (the model sometimes narrates instead of answering)
if ! printf '%s' "$RAW" | python3 -c 'import sys,json,re;d=json.load(sys.stdin);t=d.get("result") or "";m=re.search(r"\{.*\}",t,re.S);json.loads(m.group(0)) if m else sys.exit(1)' 2>/dev/null; then
  worthctl activity brain "First attempt returned no JSON plan; retrying once" "" >/dev/null
  RAW=$(printf '%s\n\nREMINDER: you have NO tools and NO memory files. Do not narrate, do not call tools. Your entire response must be the single JSON object, starting with { and ending with }.' "$PROMPT" | claude -p --model "$MODEL" --output-format json --max-turns 3 --tools "" 2>>"$OUT/$STAMP.err") || true
  echo "$RAW" > "$OUT/$STAMP.raw.json"
fi
python3 - "$RAW" "$STAMP" <<'PY'
import json, sys, subprocess, re, os
raw, stamp = sys.argv[1], sys.argv[2]
def ctl(*a): return subprocess.run(["worthctl", *a], capture_output=True, text=True).stdout.strip()
try:
    env = json.loads(raw)
except Exception:
    ctl("run", "brain", "failed", "claude returned non-json"); sys.exit(0)
usage = env.get("usage") or {}
cost = env.get("total_cost_usd") or 0
ctl("aicost", "brain", os.environ.get("WORTH_BRAIN_MODEL", "sonnet"), str(usage.get("input_tokens", 0)), str(usage.get("output_tokens", 0)), str(cost), stamp)
text = env.get("result") or ""
m = re.search(r"\{.*\}", text, re.S)
if not m:
    ctl("run", "brain", "failed", "no JSON plan in result"); sys.exit(0)
try:
    plan = json.loads(m.group(0))
except Exception as e:
    ctl("run", "brain", "failed", f"bad plan json: {e}"); sys.exit(0)
out = "/var/lib/worth-one/brain"
for a in plan.get("activity", [])[:30]:
    ctl("activity", a.get("channel", "brain"), a.get("message", "")[:300], a.get("drop_id") or "")
for d in plan.get("new_drops", [])[:5]:
    p = f"{out}/{stamp}-{d['drop_id']}.json"; json.dump(d, open(p, "w")); ctl("drop", p)
for a in plan.get("assets", [])[:20]:
    p = f"{out}/{stamp}-{a['asset_id']}.json"; json.dump(a, open(p, "w")); ctl("asset", p)
for sp in plan.get("seo_pages", [])[:10]:
    ctl("activity", "seo", f"Proposed page {sp.get('path','')} for query '{sp.get('query','')}': {sp.get('why','')[:120]}", "")
if plan.get("next_expansion_action"): ctl("cmd", "SET", "NEXT_EXPANSION_ACTION=" + plan["next_expansion_action"][:200])
for c in plan.get("campaigns", [])[:20]:
    p = f"{out}/{stamp}-{c['campaign_id']}.json"; json.dump(c, open(p, "w")); ctl("campaign", p)
for h in plan.get("human_actions", [])[:5]:
    ctl("human", h.get("title", "")[:120], h.get("detail", "")[:800])
# TikTok creatives: finished content the owner must publish manually (no API access)
tt = plan.get("tiktok_creatives", [])[:4]
if tt:
    lines = ["# TikTok creatives generated " + stamp, "Status: MANUAL_PUBLISH_REQUIRED. Words Before Coffee account, cross-promotion only.", ""]
    for c in tt:
        url = f"https://furiadelimon.github.io/worth-one/{'es/' if c.get('language') == 'es' else ''}drops/{'doomscroll-receipt' if c.get('drop_id') == 'DROP-001' else 'subscription-receipt'}/?src=wbc-tiktok&c={c.get('campaign_id', '')}"
        lines += [f"## {c.get('campaign_id', '')} ({c.get('language', 'en')})", f"**Hook:** {c.get('hook', '')}", f"**Beats:** {c.get('beats', '')}", f"**Caption:** {c.get('caption', '')}", f"**Link:** {url}", ""]
        p = f"{out}/{stamp}-{c.get('campaign_id', 'TT')}.json"
        json.dump({"campaign_id": c.get("campaign_id"), "drop_id": c.get("drop_id"), "platform": "tiktok",
                   "account": "Words Before Coffee (authorized, cross-promotion only)", "language": c.get("language", "en"),
                   "country": "ES" if c.get("language") == "es" else "GLOBAL", "audience": "FYP + existing followers",
                   "hypothesis": c.get("hook", "")[:200], "content": "engine/tiktok/generated.md", "cta": "free calculator - link in bio",
                   "url": url, "status": "manual_publish_required",
                   "community_rules": "TikTok guidelines; no health claims; no owner identity; 1-2 Worth One pieces/day max."}, open(p, "w"))
        ctl("campaign", p)
    open("/opt/worth-one/engine/tiktok/generated.md", "a", encoding="utf-8").write("
".join(lines) + "
")
    ctl("activity", "tiktok", f"Generated {len(tt)} TikTok creatives (MANUAL_PUBLISH_REQUIRED): " + ", ".join(c.get("campaign_id", "") for c in tt), "")
# strategic escalations go to the owner, not to guesswork
for e in plan.get("escalate", [])[:3]:
    t = f"STRATEGIC DECISION: {e.get('decision', '')[:100]}"
    ctl("human", t, f"Evidence: {e.get('evidence', '')[:400]} | Options: {e.get('options', '')[:400]}")
    ctl("notify", t)
for k, v in (plan.get("content") or {}).items():
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", k)[:80]
    open(f"/opt/worth-one/engine/content/{safe}", "w", encoding="utf-8").write(v)
json.dump(plan.get("insights") or {}, open("/var/lib/worth-one/insights.json", "w"))
if plan.get("current_action"): ctl("cmd", "SET CURRENT ACTION", plan["current_action"][:200])
if plan.get("next_action"): ctl("cmd", "SET NEXT ACTION", plan["next_action"][:200])
for cmd in plan.get("commands", [])[:10]:
    if cmd.get("cmd", "").upper() in ("PAUSE DROP", "KILL DROP", "SCALE DROP", "RESUME DROP", "CHANGE PRIORITY"):
        ctl("cmd", cmd["cmd"], cmd.get("arg", ""))
ctl("run", "brain", "done", (plan.get("summary") or "")[:300], str(int(__import__('time').time()) + 6*3600))
PY
# hand freshly prepared assets straight to the Action Executor instead of waiting for its own timer
worthctl executor >/dev/null 2>&1 || true
# commit generated content so it is versioned and visible on GitHub
git add -A engine/content >/dev/null 2>&1 && git -c user.email=worth-one-bot@users.noreply.github.com -c user.name="worth-one bot" commit -q -m "brain: content $STAMP" >/dev/null 2>&1 && git push -q origin HEAD:main >/dev/null 2>&1 || true
