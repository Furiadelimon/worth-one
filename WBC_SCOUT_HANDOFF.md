# SCOUT / SONNET / EXECUTOR HANDOFF — Words Before Coffee (2026-09-13)

Independent brand, independent stack (LXC 117, wordsbeforecoffee.com). Do not run these through the Worth One assets
table or control center; if the WBC repo has no outreach machinery yet, keep a simple `marketing/targets_status.json`
next to `wbc_distribution_targets.json` with `status`, `sent_ts`, `verified_ts`, `users_7d`.

## 1. Order of execution
1. Directories with plain forms (Alldle, Playlin, The Dles, Weird Web Tools, SHOULDSEETHIS, The Forest): one sitting, 4 entries each where the site lists games individually.
2. Product: implement Alldle SDK (≈10 lines) after listing; add peer footer block.
3. Spanish press emails (Microsiervos → El Proxy → Trecebits → Genbeta form → Xataka → WWWhat's new → Hipertextual), one per day, Spanish, own-project declared.
4. Teachers: todoELE publish; US bell-ringer bloggers (English), ELE sites, Orientación Andújar, Aula PT.
5. Human batch: Miniplay dev account; captcha forms.
6. Conditional (needs a static build): CrazyGames, Newgrounds, itch.io, Coolmath (stripped, no leaderboard).

## 2. Rules
- One message per contact, ever. Plain text. Honest subject ("Cuatro juegos diarios en español, proyecto propio").
- Sender is a WBC address. Never mention Worth One. Never send both brands to one editor within 30 days.
- No social media. No paid listings (DLE Games rejected). No invented emails: only `contact` with `contact_source`.
- Per-target link: `https://wordsbeforecoffee.com/?src=<slug>`; for teacher targets deep-link the game most suited (Word Search for primary, Words Before Coffee for ELE/US classes).

## 3. Metrics that decide priority (per `src`)
first visit → game completion (any of the 4) → return next day → 7-day retention. A channel with 30 first visits and 8 returning
beats one with 300 visits and 5 returning. Report weekly per cluster.

## 4. Recursive expansion queries (run when a `src` reaches ≥ 5 returning users)
| Cluster | Query |
|---|---|
| DIR | `"daily games" list site all daily puzzles one place wordle-likes directory submit game`; `best Wordle alternatives 2026 daily word games list article` (each list = a submission/inclusion request) |
| PRESS-ES | `"juegos de palabras" diarios "en español" wordle Xataka OR Genbeta OR Hipertextual OR Microsiervos`; `Loxik juegos diarios español` (who else covered Loxik) |
| EDU-US | `Spanish teacher blog "Wordle" español bell ringer warm-up`; `Spanish teacher blog "free online games" Spanish class "sopa de letras"` |
| EDU-ELE | `ProfeDeELE OR Todoele OR Marcoele juegos de vocabulario online gratis clase ELE`; `Todoele "publica"` |
| EDU-ES | `"Orientación Andújar" OR Actiludis OR "Mundo Primaria" OR "Aula PT" juegos de palabras online gratis` |
| SENIORS | `estimulación cognitiva mayores juegos online gratis sopa de letras memoria recursos web` |
| LEARNERS | `Spanish learning blog for learners "word games" practice Spanish vocabulary daily resources` |
| PORTALS | github.com/ayomide321/game-portals (56 portals with developer links) — verify each before use |

## 5. Escalate to Fable only if
an English mode is being considered (unlocks EN directories/press/Coolmath: a product fork), a portal offers a revenue deal,
or a cluster passes 100 returning users (then concentrate and localise landing pages for it).

## 6. No-verified-route leads (do not pitch; re-check monthly)
Apalabras, Loxik, JugaLetras, La palabra del día (peers) · ProfeDeELE · Fundación Pasqual Maragall blog · FluentU / Preply
lists · Warp Door, Indie Games Plus · GameSnacks · Vandal · Spanish daily newsletters (no "juego del día" sections found).
