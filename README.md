# Worth One?

**Free little things for strangers. Goal: one car.**

One person is trying to buy a car by publishing free, useful, surprising or entertaining web experiences ("drops").
Everything is free. After using a drop you get one question: *was this worth €1 to you?*
Payments are closed until enough people say yes; until then the site only measures intention, shown separately
from real money, which is €0. Target: €30,000. The person behind it is not named; the public identity is the project itself.

Site: https://furiadelimon.github.io/worth-one/

## Drops

| id | name | status |
|---|---|---|
| DROP-001 | [Doomscroll Receipt](https://furiadelimon.github.io/worth-one/drops/doomscroll-receipt/) | live |
| DROP-002 | [Subscription Lifetime Receipt](https://furiadelimon.github.io/worth-one/drops/subscription-receipt/) | live |
| DROP-003 | Weekends Left | next |

Suggest one: open an issue.

## How it is built (honest version)

- `docs/` public site, plain HTML/CSS/JS, served by GitHub Pages and by the API host. No frameworks, no trackers.
- `server/` FastAPI + SQLite: event ingest, support-intent, public stats, private control center, daily reports, human override commands.
- `engine/` experiment registry (drops with scores) and generated content per channel.
- `brain/` the autonomous reasoning run (Claude Code non-interactive) that proposes drops, writes channel-native content,
  records campaigns and decides scale/iterate/pause/kill from metrics. It cannot move money or post by itself.
- `ops/` install script, systemd units, tunnel URL sync.

Rules the system runs under: no spam, no fake accounts, no fake engagement, no bought followers, no fake testimonials,
no simulated donations, no dark patterns, respect platform rules, always say the money is for a car.

## Run locally

```
python -m venv .venv && .venv/bin/pip install -r server/requirements.txt
WORTH_ADMIN_TOKEN=dev .venv/bin/uvicorn --app-dir server app:app --port 8080
```

Control center: `http://127.0.0.1:8080/admin?token=dev`

## License

Code: MIT. Content and drop concepts: CC BY 4.0.
