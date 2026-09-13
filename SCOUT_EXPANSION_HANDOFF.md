# SCOUT / SONNET / EXECUTOR HANDOFF — Worth One distribution (2026-09-13)

You are executing a verified map, not researching from scratch. Files: `distribution_targets.json` (138 rows),
`DISTRIBUTION_MAP.md`, `TOP_20_TARGETS.md`. Words Before Coffee is a separate brand with its own files
(`wbc_*`, `WBC_*`); never merge pitches, senders or tracking.

## 1. Import into the assets table
For each row with `tier` in A/B and `contact` or `submission_url` not null, create/merge an asset:
- `name`, `type`, `url` (= `relevant_page`), `contact` (email only; forms go in `notes`), `drop_id`, `status=prepared`,
  `pitch` = generated from the campaign template in DISTRIBUTION_MAP §10 using `why_fit` + `pitch_angle` (Spanish for
  `language=es`, Portuguese for `pt`, French/German only if copy exists; otherwise English + offer to localise),
  `human_required` → tag `HUMAN_REQUIRED` when true, `HUMAN_GITHUB_ACTION_REQUIRED` for `method=github_pr`.
- Dedupe by contact: `diego@wwwhatsnew.com` appears twice (WEB-02 + FIN-01 embed) → one asset, one email.
- Rows with `tier=C` and no route: store as `lead` (not `prepared`); do not pitch.
- Rows with `tier=REJECT`: store `rejected` so they are never re-proposed (this includes Ditch That Textbook and the Gravity blog that were previously `prepared`).
- Link tag per target: `?src=<slug>` where slug = lowercase name, e.g. `?src=weirdwebtools`. Use `/es/` URLs for `language=es`.

## 2. Executor mapping
| `method` | handler | notes |
|---|---|---|
| `email` | `h_email_outreach` | one message per contact, ever; max 5/day; Worth One sender (see §5) |
| `form_submit` / `contact_form` with `captcha=false`, `login=false` | `h_form_submit` | **only after** a human opens the form once and a tested selector recipe exists in `FORM_RECIPES`. Recipes to write first (highest value): weirdwebtools.com/submit, nosignuptools.com/submit, shouldseethis.com/submit, theforest.link, yourhack.ai/submit, teachersfirst.org/contact.cfm, genbeta.com/contacto, educaciontrespuntocero.com/contacto. Never guess selectors. |
| anything with `captcha=true` or `login=true` | HUMAN_REQUIRED | batch into one Telegram message; see TOP_20 human batch |
| `github_pr` | HUMAN_GITHUB_ACTION_REQUIRED | prepare PR text only |
| `none` | lead | no action |

Verify loop: `h_verify_http` at 72 h / 7 d / 30 d on the `relevant_page` (directory listings) or on the pitched article
(embeds): look for our hostname in the HTML. Mark `live` when found; log `?src=` users from events.

## 3. Rules that override everything
- Never invent or scrape emails; only what is in `contact` with a `contact_source`.
- No social media (directive). Web Tools Weekly / Tech Productivity are rejected for that reason; do not revisit.
- Do not pitch competitors' product blogs (Canopy, Subtrakr, Richify, Gravity, screen-time app blogs).
- Respect "no unsolicited pitches" (Ditch That Textbook). Respect Cool Tools' rule (reader-written only).
- Spanish targets get Spanish text and `/es/` links. Portuguese: Portuguese text, EN tool link + offer to localise.
- No medical claims for Doomscroll. No "help us / car" language anywhere in pitches.

## 4. Recursive expansion (run only when a channel produces users)
Trigger: a `src` reaches ≥ 5 users. Then run the query that found the cluster and verify 10–30 look-alikes the same way
(fetch page → find submit/contact → record status, captcha, login, cost → score).

| Cluster | Queries that worked (reuse verbatim) |
|---|---|
| WEB-01 directories | `directory of free single-purpose web tools submit your tool no signup`; `indie web small web directory "submit"`; theindex.fyi (38 indie indexes); `cloudhiker OR "theforest.link" submit website random discovery` |
| WEB-02 newsletters | hark.news/best-internet-culture-newsletters; `newsletter of interesting websites "submit a site" OR "suggest a website"`; per language: `Microsiervos contacto enviar noticia`, `Linkblog deutsch Fundstücke Kontakt`, `Korben proposer un outil`, `Pplware sobre nós contacto` |
| EDU-01 resource pages | `digital wellbeing resources page "tools" screen time links for parents teens`; `libguides "digital wellbeing" screen time tools`; per country: `klicksafe Bildschirmzeit`, `Internet Sans Crainte temps d'écran`, `Empantallados tiempo de pantalla`, `SaferNet tempo de tela` |
| EDU-01 teachers | `Larry Ferlazzo "websites of the day" digital citizenship`; `teacher resources "suggest a resource" digital citizenship screen time` |
| FIN-01 embeds | `"subscription audit" blog post personal finance 2026 -app "how to"`; `"auditoría de suscripciones" cuánto gastas al año blog`; `subscrições cancelar poupar artigo`; `abonnements coût annuel faire le tri calculateur`; `Abos kündigen Kosten im Jahr Artikel 2026` |
| FIN-01 blogs | `personal finance blog subscription audit cancel unused subscriptions article 2026` + country names |

Escalate to Fable only for a real fork: a cluster hits ≥ 100 users (localisation decision), or an editor asks for
something not covered here (exclusive embed, data, interview).

## 5. Blockers to surface to the owner (Telegram, once)
1. **Own sender address for Worth One** (currently `hello@wordsbeforecoffee.com`). Needed before WEB-02/FIN-01 run, because WBC pitches the same editors.
2. Human batch (30 min): see TOP_20_TARGETS.md.
3. Copy decisions: build PT/FR/DE embed copy only after a "yes" from Doutor Finanças / cinema-series-tv / GeldNavi.
4. Fairplay Screen Time Action Network membership (check cost).

## 6. What not to do
Do not re-run the broken-link search (result documented: none honest). Do not pitch English screen-time-calculator
competitors. Do not submit to paid directories. Do not open GitHub PRs from the owner's account. Do not resend to
Internet Is Beautiful.
