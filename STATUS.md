# Project status

## Worth One — ARCHIVED / PAUSED (since 2026-09-13)

Frozen by owner decision. Nothing is deleted: code, data, analytics, the public site, the API and the event
ingest stay exactly as they were. What stopped:

- new drops, outreach, SEO pages, newsletters, directories, embeds, publishers, contact research, campaigns
- the daily outreach batch and the Worth One IndexNow ping
- every queued action (archived in the `actions` table with status `ARCHIVED`), every prepared asset (`archived`)
- the open human actions (Search Console, tinytools, cross-promo card) — closed as `archived`

The old dashboard is still readable at `/admin/worth-one` (read-only).

## Words Before Coffee — ACTIVE (the only growth project)

The autonomous growth engine in this repository now works exclusively for https://wordsbeforecoffee.com.

- Control Center: `/admin` → **WORDS BEFORE COFFEE · GROWTH CONTROL CENTER** (users, DAU, per-game performance,
  acquisition, countries, expansion, agent performance, recent activity; optional human actions collapsed).
- Metrics come from the product itself (`/api/growth` on the WBC LXC, token-protected, LAN only): `server/wbc.py`.
- Cycle (every 2 h, `server/executor.py`): MEASURE → ANALYSE → FIND OPPORTUNITY → EXECUTE → MEASURE RESULT → LEARN.
- Brain (3×/day, Sonnet, budget-gated, `brain/`): proposes verified-able leads and writes pitches; never publishes.
- Outreach (`server/outreach.py`): max 2 emails/day until 20 clean sends; 8 mandatory checks, any failure = DO_NOT_CONTACT.
- Anything needing login / CAPTCHA / account / payment / manual publish is `MANUAL_ONLY` and never blocks the loop.
- Social: ideas and assets are prepared only; the owner decides what gets published.
- Cost: `AI_DAILY_BUDGET_USD` setting (default 1.00); research cache (`research_cache`) so no domain is investigated twice.
