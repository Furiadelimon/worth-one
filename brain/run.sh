#!/usr/bin/env bash
# Autonomous brain run for WORDS BEFORE COFFEE. Uses Claude Code non-interactively (subscription auth via
# CLAUDE_CODE_OAUTH_TOKEN). Reads the growth state, returns a JSON plan, and this script applies it through worthctl:
# leads become assets (status "lead") that the Action Executor verifies and executes. It never publishes anywhere
# and never sends anything itself.
set -uo pipefail
export PATH=$PATH:/root/.local/bin:/usr/local/bin
APP=/opt/worth-one
OUT=/var/lib/worth-one/brain
mkdir -p "$OUT"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
MODEL=${WORTH_BRAIN_MODEL:-sonnet}
NEXT=$(( $(date +%s) + 8*3600 ))

STATUS=$(worthctl state --wbc 2>/dev/null | python3 -c 'import sys,json;d=json.load(sys.stdin);s=d["settings"];print(s.get("PROJECT_STATUS","ACTIVE"), s.get("AI_DAILY_BUDGET_USD","1.0"), d.get("ai_spent_today",0))')
read -r PSTATUS BUDGET SPENT <<<"$STATUS"
if [ "$PSTATUS" = "PAUSED" ]; then
  worthctl run brain skipped "PROJECT PAUSED by owner" "$NEXT"; exit 0
fi
# daily AI budget: when reached, only analytics and essential jobs keep running (this run is research -> skip)
if python3 -c "import sys; sys.exit(0 if float('$SPENT') >= float('$BUDGET') else 1)"; then
  worthctl run brain skipped "daily AI budget reached (\$$SPENT of \$$BUDGET); research paused until tomorrow" "$NEXT"
  worthctl activity brain "Daily AI budget reached (\$$SPENT of \$$BUDGET): low-priority research paused until tomorrow" "WBC" >/dev/null
  exit 0
fi
if { [ -z "${CLAUDE_CODE_OAUTH_TOKEN:-}" ] && [ ! -f /root/.claude/.credentials.json ]; } || ! command -v claude >/dev/null 2>&1; then
  worthctl run brain skipped "brain not authorized (no CLAUDE_CODE_OAUTH_TOKEN)" "$NEXT"; exit 0
fi

STATE=$(worthctl state --wbc)
PROMPT=$(cat "$APP/brain/prompt.md"; echo; echo '## CURRENT STATE (JSON)'; echo "$STATE")
cd "$APP"
worthctl cmd "SET CURRENT ACTION" "Brain run $STAMP: measuring and looking for the next source of players" >/dev/null
RAW=$(printf '%s' "$PROMPT" | claude -p --model "$MODEL" --output-format json --max-turns 3 --tools "" 2>"$OUT/$STAMP.err") || true
echo "$RAW" > "$OUT/$STAMP.raw.json"
if ! printf '%s' "$RAW" | python3 -c 'import sys,json,re;d=json.load(sys.stdin);t=d.get("result") or "";m=re.search(r"\{.*\}",t,re.S);json.loads(m.group(0)) if m else sys.exit(1)' 2>/dev/null; then
  RAW=$(printf '%s\n\nREMINDER: you have NO tools and NO memory files. Do not narrate. Your entire response must be the single JSON object, starting with { and ending with }.' "$PROMPT" | claude -p --model "$MODEL" --output-format json --max-turns 3 --tools "" 2>>"$OUT/$STAMP.err") || true
  echo "$RAW" > "$OUT/$STAMP.raw.json"
fi
python3 - "$RAW" "$STAMP" <<'PY'
import json, sys, subprocess, re, os, time
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
# leads -> assets with status "lead"; the executor verifies them (reachability, public contact, policy) before use
leads = plan.get("leads", [])[:20]
for l in leads:
    a = {"asset_id": l.get("asset_id"), "type": l.get("type") or "directory", "name": l.get("name"), "url": l.get("url"),
         "drop_id": "WBC", "status": "lead", "why": (l.get("why") or "")[:500], "pitch": l.get("pitch") or None,
         "contact": (l.get("contact") or "").strip() or None, "contact_source": l.get("contact_source") or None,
         "pitch_lang": l.get("lang") or None, "src_tag": l.get("src_tag") or None, "pitch_source": "brain" if l.get("pitch") else None,
         "notes": f"country={l.get('country','')} expected_players={l.get('expected_players','')} confidence={l.get('confidence','')}"}
    if not a["asset_id"] or not a["name"] or not a["url"]:
        continue
    p = f"{out}/{stamp}-{re.sub(r'[^A-Za-z0-9_-]', '_', a['asset_id'])}.json"; json.dump(a, open(p, "w")); ctl("asset", p)
if leads:
    ctl("activity", "lead", f"Brain proposed {len(leads)} leads for verification: " + ", ".join(l.get("name", "")[:30] for l in leads[:6]), "WBC")
for mo in plan.get("manual_only", [])[:10]:
    ctl("activity", "lead", f"MANUAL_ONLY (not pursued): {mo.get('name','')} - {mo.get('reason','')}", "WBC")
for sp in plan.get("seo_pages", [])[:2]:
    ctl("activity", "seo", f"SEO page idea {sp.get('path','')} for '{sp.get('intent','')}' ({sp.get('language','')}): {sp.get('why','')[:100]}", "WBC")
    open("/opt/worth-one/engine/wbc/seo-ideas.md", "a", encoding="utf-8").write(f"\n## {stamp} {sp.get('path','')} - {sp.get('intent','')} ({sp.get('language','')})\n{sp.get('why','')}\n\nMust contain: {sp.get('must_contain','')}\n")
so = plan.get("social_ideas", [])[:2]
if so:
    with open("/opt/worth-one/engine/wbc/social-ideas.md", "a", encoding="utf-8") as f:
        f.write(f"\n# {stamp} (prepared, NOT published - owner decides)\n")
        for c in so:
            f.write(f"- game: {c.get('game','')}\n  hook: {c.get('hook','')}\n  beats: {c.get('beats','')}\n  caption: {c.get('caption','')}\n")
    ctl("activity", "social", f"Prepared {len(so)} social ideas (not published; owner decides)", "WBC")
json.dump(plan.get("insights") or {}, open("/var/lib/worth-one/insights.json", "w"))
if plan.get("current_action"): ctl("cmd", "SET CURRENT ACTION", plan["current_action"][:200])
if plan.get("next_action"): ctl("cmd", "SET NEXT ACTION", plan["next_action"][:200])
ctl("run", "brain", "done", (plan.get("summary") or "")[:300], str(int(time.time()) + 8*3600))
PY
# hand new leads straight to the Action Executor (verify -> execute)
worthctl executor >/dev/null 2>&1 || true
git add -A engine/wbc >/dev/null 2>&1 && git -c user.email=worth-one-bot@users.noreply.github.com -c user.name="worth-one bot" commit -q -m "brain: wbc ideas $STAMP" >/dev/null 2>&1 && git push -q origin HEAD:main >/dev/null 2>&1 || true
