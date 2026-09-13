# Handoff (2026-09-13, evening) — PIVOT: Words Before Coffee is the only active project

## What changed
- **Worth One is ARCHIVED / PAUSED** (owner directive). Nothing deleted. `STATUS.md` + README banner. All Worth One
  actions/assets archived in the DB (`executor.freeze_worth_one()`, idempotent, runs every cycle), human actions
  closed, no outreach batch, no IndexNow, no brain work. Old dashboard read-only at `/admin/worth-one`.
- **The growth engine on LXC 140 now works for Words Before Coffee** (wordsbeforecoffee.com, LXC 117):
  - `server/wbc.py` reads the product's own `/api/growth` (LAN, `WBC_GROWTH_TOKEN`), hourly snapshots, attribution
    of players to assets by `?src=` tag, game verdicts, winning pattern.
  - `server/outreach.py` = 8-check pipeline (policy fetch cached per domain, public-contact verification, no-AI /
    no-unsolicited prohibitions, no duplicate address/domain 30d, render check, no internal notes, no agent
    vocabulary). Any failure → `do_not_contact` / `pitch_rejected`. `email_log` keeps the exact text sent.
    Cap: `WBC_EMAIL_CAP`=2/day until `clean_sends` ≥ 20 (`CLEAN_SENDS_TARGET`). `COMPLAINT <asset_id>` command.
  - `server/executor.py` = MEASURE→ANALYSE→FIND→EXECUTE→MEASURE RESULT→LEARN, WBC only. Leads from the brain (status
    `lead`) are verified (research cache, never twice) → `prepared` / `needs_pitch` / `manual_only` / `do_not_contact`.
    Form recipes: theforest.link, shouldseethis.com (FUN), weirdwebtools.com (Turnstile → MANUAL_ONLY if it does not
    clear), alldle.net. Verification = real players arriving from the source (acquisition) or the listing page.
  - `server/admin.html` = WORDS BEFORE COFFEE · GROWTH CONTROL CENTER (8 blocks as specified; human actions collapsed).
  - `brain/prompt.md` + `brain/run.sh`: WBC-only, real players as the only metric, replicate winners, leads with
    authored pitches, daily AI budget gate (`AI_DAILY_BUDGET_USD`, default 1.00), 3 runs/day. Social ideas are
    prepared only (engine/wbc/social-ideas.md), never published.
  - `engine/wbc/assets.json`: first hand-verified opportunities (Alldle + The Dles already submitted 2026-09-13;
    todoELE (ES), LikeWordle (EN), Weird Web Tools (EN) pitches authored by hand; theforest + shouldseethis forms).
- **WBC repo** (`WordsBeforeCoffee`, commit ca4750f on branch feature/estetica, pushed to origin main):
  `app/growth.py` (visits by src/referrer/country + share events, `/api/t`, `/api/growth`), `?src=share` on shared
  links, `/sitemap.xml`, `/robots.txt`, `/indexnow.txt`, intent-matched titles/descriptions, OG + JSON-LD.
  Tests green (`.venv\Scripts\python -m pytest -q`). `deploy/remote_deploy.sh` provisions `WBC_GROWTH_TOKEN`
  and `WBC_INDEXNOW_KEY` in the LXC env automatically.

## Deployed (owner authorized the WBC deploy in a second message)
- WBC releases 20260913-181100 and the follow-up (visits by IP host ignored) deployed with `scripts/deploy.ps1
  -SkipTests` after 152 e2e + 20 smoke tests passed. `WBC_GROWTH_TOKEN` / `WBC_GROWTH_URL` copied into
  `/etc/worth-one/env` on LXC 140 (never printed). Live metrics flow: 524 users/30d, 210/7d, 31/24h; games 30d:
  words 342 users / 868 played, slide 118/190, search 51/63, memory 42/51; D1 retention 4%.
- Smoke tests hit http://192.168.1.117 directly and were counted as 22 "direct" visitors: rows deleted, and
  `growth.note_visit` now ignores requests whose Host is an IP. Note: smoke tests still create players/runs in the
  production DB (pre-existing; the 2026-09-11 spike of 78 "players" is the previous deploy's tests).
- Only optional human items remain: the MANUAL_ONLY list (Miniplay, CrazyGames, captcha contact forms).

## Verified working on the LXC (2026-09-13 15:38-15:50 UTC)
- `worthctl freeze` archived 65 Worth One actions + 14 assets; Control Center `/admin` 200, archived `/admin/worth-one` 200.
- Executor cycle: The Forest planted, SHOULDSEETHIS (FUN) submitted (both via Playwright recipes); Alldle + The Dles
  recorded as submitted (done by hand in the morning); 3 verified pitches QUEUED (todoELE ES, LikeWordle EN, Weird
  Web Tools EN) - all 8 checks PASS on the LXC - held by the daily cap (15 old-pipeline sends count for today);
  21 targets MANUAL_ONLY; playlin.io unreachable (lead).
- Brain run (Sonnet, $0.14): returned valid JSON, 4 leads (ProfeDeELE, Try Hard Guides, 65 Y Más, PuzzleNation Blog),
  2 SEO page ideas (`/juego-de-palabras-diario`, `/daily-spanish-word-game`) in engine/wbc/seo-ideas.md; executor
  verifies leads right after (research cache). Daily AI spend $0.45 of the $1.00 budget.
- Bug fixed on the way: `last_attempt` was never stored (agent counters read 0); AI-prohibition regex matched a
  directory's "AI Tools" category; `_reachable` treats 3xx as reachable.

## Facts to remember
- 15 WBC emails + 38 Worth One emails went out on 2026-09-13 09:50 through the OLD pipeline; the WBC ones carried
  research notes as body text. Those addresses are burned (NO_DUPLICATE) and count as 0 clean sends. Shared
  editors (Microsiervos, Xataka, Hipertextual, WWWhat's new, El Proxy, Trecebits...) received Worth One mail →
  cannot be emailed for WBC (one message per address, ever).
- Emails sent today count against the cap (`outreach.sent_today` uses assets.submitted_ts), so the first two
  clean sends go out on 2026-09-14 (todoELE ES, Weird Web Tools EN), then LikeWordle.
- playlin.io was unreachable from both networks on 2026-09-13; kept as `lead`, rechecked every 2 days.
- nosignuptools.com has no games category → not a target. weirdwebtools form has Cloudflare Turnstile.
- WBC product numbers (2026-09-13): 531 players lifetime, ~3–78 new/day (spiky, owner's own video posts), 863
  word runs, 184 slide, 58 search, 45 memory, 10 accounts. Retention purge 60 days.
