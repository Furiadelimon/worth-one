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

## Blocked in this session (classifier) — the ONLY human steps
1. **Deploy WBC** (Production Deploy was denied): in the WBC repo run `.\scripts\deploy.ps1 -SkipTests`
   (tests already pass; or without the flag). Then copy the token into the engine:
   `ssh root@192.168.1.117 grep WBC_GROWTH_TOKEN /etc/wordsbeforecoffee/wordsbeforecoffee.env` →
   add `WBC_GROWTH_TOKEN=<value>` (and `WBC_GROWTH_URL=http://192.168.1.117/api/growth`) to `/etc/worth-one/env` on
   LXC 140 and `systemctl restart worth-one`. Until then the Control Center shows "metrics not configured" and the
   engine runs without product metrics (still executes/verifies/learns what it can).
2. Optional (never blocking): MANUAL_ONLY list in the Control Center (Miniplay, CrazyGames, captcha contact forms).

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
