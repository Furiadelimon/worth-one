# WORTH ONE — Global Distribution Map (reconnaissance 2026-09-13)

Companion files: `distribution_targets.json` (138 rows, scored), `TOP_20_TARGETS.md`, `SCOUT_EXPANSION_HANDOFF.md`.
Words Before Coffee has its own, independent map: `WBC_DISTRIBUTION_MAP.md` (do not merge the brands).

Every target below was checked live on 2026-09-13 (page fetched, HTTP status, contact route inspected). Where a route
could not be verified the row says **NO VERIFIED CONTACT FOUND** and nothing was inferred.

## 0. Headline numbers

| | |
|---|---|
| Targets researched | 138 (120 live, 18 rejected) |
| Tier A / B / C | 17 / 57 / 46 |
| Verified public email contacts | 44 |
| Submission forms / submit URLs | 50 |
| Auto-executable by the Executor (email or plain form) | 69 |
| Human-required (login, captcha, GitHub identity, manual read) | 51 |
| No verified route (kept only as leads) | 33 |

## 1. What the web actually looks like for these two products

1. **English "screen time calculator" is saturated by app companies.** unplugged.rest, scrollguard.app, pagelock.app,
   habitbox.app, loggd.life, procalculator.co.uk, creativewidgets.io all rank with the same "days of your life" hook.
   Worth One will not win English SEO head-on; it wins on being *free, no signup, no app upsell* and on the receipt artefact.
2. **Spanish, Portuguese, French and German are open.** Every 2026 subscription-audit article found in those languages
   (WWWhat's new ES, Doutor Finanças PT ×2, cinema-series-tv.fr, GeldNavi DE, MundoOfertas ES, Cuentas Claras ES) has
   **no calculator at all**. That is the embed gap. The site already has `/es/` and ES widgets; PT/FR/DE copy is the only blocker.
3. **Spanish curiosity press has a documented habit of covering tiny tools** (Microsiervos FAQ literally asks for honest
   tips from makers; Genbeta and WWWhat's new run "webs útiles" roundups weekly). This is the highest-probability editorial door.
4. **Directories of single-purpose tools are real and free** (Weird Web Tools, NoSignupTools, ShouldSeeThis, yourhack.ai,
   The Forest, Cloudhiker, Indieseek). Low traffic each, but they compound and give clean dofollow links.
5. **Broken-link replacement yields nothing honest.** TrackMySubs is alive (200), Trim redirects to OneMain, Mint pages redirect
   to Credit Karma, Moment app (inthemoment.io) is dead but was a tracker, not a calculator. No page was found where Worth One
   is a *legitimate* replacement. Strategy dropped; see §10.
6. **Operational conflict:** Worth One outreach currently sends from `hello@wordsbeforecoffee.com`. Now that WBC has its own
   acquisition plan, the same editors (Microsiervos, Genbeta, WWWhat's new, Web Curios, Xataka) appear on both maps. Two
   "independent" brands pitching from one address burns both. Worth One needs its own sender before FIN/WEB campaigns run,
   and the same editor must never get both pitches within 30 days.

## 2. Channel families → clusters → replicability

| Family | Cluster id | What it is | Audience intent | Try-rate | SEO | Embed | Replicable? |
|---|---|---|---|---|---|---|---|
| Curated internet | WEB-01 | single-purpose-tool & indie-web directories, launch boards | browsing for neat tools | high | medium (dofollow) | no | yes: 30+ similar directories exist (theindex.fyi lists 38) |
| Newsletters / link blogs | WEB-02 | curious-internet newsletters, Spanish/German/French/Portuguese tech blogs | curiosity | high | medium | no | yes: Hark's list, InboxReads, Substack "similar" pages |
| Digital wellbeing / edu | EDU-01 | parent-safety orgs, teacher resource sites, LibGuides, detox challenges | practical / classroom | medium | high (edu/org links) | yes (resource pages) | yes: every country has a klicksafe/Internet Matters/Empantallados equivalent |
| Personal finance | FIN-01 | subscription-audit articles, frugal blogs, financial-education portals | saving money | high | high | **yes** | yes: "subscription audit" 2026 posts exist in every language |
| Weird | WEIRD-01 | datasets newsletter, LibGuides, monthly challenge orgs | niche | low-medium | medium | sometimes | partially |

100 relevant visitors beat 10,000 impressions: EDU-01 and FIN-01 links sit on evergreen pages and keep sending
people who actually run the calculator. WEB-02 gives spikes; WEB-01 gives the link graph.

## 3. Campaigns

### CAMPAIGN WEB-01 — Single-purpose-tool directories
- Target count: 25 (4 A, 14 B, 7 C). Auto-executable: 9 (plain forms/email); 16 need a human (login/captcha).
- Core message: "Two free, no-signup receipts: scrolling time → days of life; subscriptions → 10-year cost."
- Primary drop: DROP-001 for curiosity directories, DROP-002 for utility/finance categories.
- Expected value: 20–100 visits per listing, compounding dofollow links, permanent.
- Execution: Executor `form_submit` after a one-time human inspection to write `FORM_RECIPES` for Weird Web Tools,
  NoSignupTools, ShouldSeeThis, The Forest. Human batch (30 min): Indieseek, Random Daily URLs, Mr. Free Tools,
  Website Hunt, Uneed, Smol Launch, tinytools DROP-002, Show HN, Product Hunt.

### CAMPAIGN WEB-02 — Curious-internet newsletters and link blogs (EN/ES/DE/FR/PT)
- Target count: 31 (6 A, 13 B, 12 C). Auto-executable: 21.
- Core message: "A receipt for your scrolling time. 2 hours a day = 304 days over ten years. Free, no signup, made by one person."
- Primary drop: DROP-001 (the receipt is the shareable artefact). Wonder Tools / Advisorator get DROP-002 (utility angle).
- Expected value: one placement in Microsiervos / Genbeta / WWWhat's new ≈ 200–2,000 ES visits; Web Curios / Wonder Tools ≈ 50–500.
- Execution: Executor `email_outreach` (one message per contact, ever). Spanish pitches in Spanish, linking `/es/`.

### CAMPAIGN EDU-01 — Digital wellbeing for schools and parents
- Target count: 32 (5 A, 15 B, 12 C). Auto-executable: 22.
- Core message: "A free calculator that turns screen time into a receipt — a five-minute discussion starter. No signup, no medical claims."
- Primary drop: DROP-001.
- Expected value: resource-page links (Healthy Screen Habits, UK Safer Internet Centre, klicksafe, Internet Sans Crainte)
  are evergreen; each sends a trickle of parents/teachers who actually try it. Larry Ferlazzo / TeachersFirst listings persist for years.
- Execution: email + contact forms. Fairplay network needs a human to join first.

### CAMPAIGN FIN-01 — Subscription-audit publishers (embed first)
- Target count: 30 (2 A, 15 B, 13 C). Auto-executable: 17.
- Core message: "€14.99/month doesn't look like much → €1,799 over ten years. Embed the receipt; readers stay on your page."
- Primary drop: DROP-002. Offer `/embed/subscriptions.html` (ES exists; EN exists; PT/FR/DE copy to build on demand).
- Expected value: an embed on Doutor Finanças or WWWhat's new is worth more than ten directory listings (readers already
  in audit mode). UK/US frugal blogs: link or mention.
- Execution: email/contact forms. Embed offers must name the exact paragraph (see §7).

### CAMPAIGN WEIRD-01 — Unconventional but legitimate (see §12)
- Target count: 10 ideas, 2 with verified routes. Execution mostly human/one-off.

## 4. Doomscroll Receipt (DROP-001) target map

Hook 1: "Two hours a day becomes 304 days over ten years." Hook 2: "A free calculator that turns screen time into a receipt." No medical claims.

| Segment | Targets (tier) |
|---|---|
| Screen-time / wellbeing resource pages | Healthy Screen Habits (A), UK Safer Internet Centre screen-time page (B), Childnet (B), Smartphone Free Childhood tools hub (B), Wait Until 8th (B), Children and Screens (B), Catherine Price Family Tech Recs (B), Internet Matters (B, no route), Fairplay Resource Library (B, join first) |
| Parents, non-English | Empantallados ES (A fit, no route yet), PantallasAmigas ES (B), klicksafe DE (B), Internet-ABC DE (B), Elternguide DE (B), Internet Sans Crainte FR (B), Offzeit DE embed (B) |
| Teachers | TeachersFirst (A), Larry Ferlazzo (A), EDUCACIÓN 3.0 (A), Cult of Pedagogy (C), Free Tech for Teachers (B, no route) |
| Students / universities | LibGuides digital-wellbeing cluster: Towson, Exeter (C, replicable ×20), Penn State, OSU |
| Curious-internet / productivity writers | Web Curios (A), Kottke (B), Wonder Tools (A), Advisorator (B), Laughing Squid (B), The Whippet (B), Kraftfuttermischwerk DE (B), Microsiervos ES (A), Xataka ES (B) |
| Internet-culture publications | Garbage Day, Tedium, Today in Tabs (C: weak fit, keep for a news hook only) |
| Detox challenges | TheChallenge.org (C), No Scroll September / zalipoff (C) |

## 5. Subscription Lifetime Receipt (DROP-002) target map

Hook: "€14.99/month becomes €1,799 over ten years." Prefer embeds.

| Segment | Targets (tier) |
|---|---|
| Embed candidates (2026 articles without any calculator) | WWWhat's new ES (A), Doutor Finanças PT ×2 (A), MundoOfertas ES guide (B), cinema-series-tv.fr (B), GeldNavi DE (B), DebtMirror US (B), Monedalia ES (B), Service Today Life (C) |
| Frugal / money blogs, UK | Be Clever With Your Cash (B), Money to the Masses (B), Skint Dad (B), MoneyMagpie (B) |
| Frugal / money blogs, US | The Frugal Girl (B), Frugalwoods (B), Money Saving Mom (C), Get Rich Slowly (C) |
| Financial-education portals | Jump$tart Clearinghouse (B, free provider account), La finance pour tous FR calculators page (B), Todos Contam PT (C, no route), NGPF (C, no route) |
| Tools newsletters | Wonder Tools (A), Advisorator (B), Cool Tools (C: reader-written only) |
| Directories (utility/finance category) | NoSignupTools (A), Weird Web Tools (A), Mr. Free Tools (B), yourhack.ai (A), tinytools DROP-002 (B) |
| Rejected | NerdWallet-type lead-gen sites; competitor app blogs (Canopy, Subtrakr, Richify, Gravity); verbraucherzentrale-finanzen.org lookalike |

## 6. The editorial story ("tiny useful things made by one person — can they pay for something real?")

Genuinely relevant only where the *maker story* is the format: Microsiervos (covers one-person projects and says so),
Manual do Usuário (independent tech, non-commercial focus), Kottke ("if you have a project you're proud of, send it"),
Web Curios, El Proxy, Hacker News Show HN (the format is the story). Do **not** use it for EDU-01, FIN-01 or directories:
there the product is the story and the car is a footnote at most. Keep V3 rule: no "help us", no counter.

## 7. Embed strategy (interactive beats a backlink)

| Article | Why an embed helps them | Tool | Contact | Proposed placement |
|---|---|---|---|---|
| WWWhat's new — "Suscripciones digitales: cómo descubrir cuánto gastas" (2026-04-16) | article makes readers list subscriptions but gives no total; widget turns their list into a 10-year receipt | DROP-002 ES widget | diego@wwwhatsnew.com | right after the "revisa extractos / App Store / PayPal" step |
| Doutor Finanças — "Como poupar nas subscrições de serviços" and "Como poupar nos serviços de streaming" | both list prices per service; no calculator | DROP-002 (PT copy needed) | info@doutorfinancas.pt | after the price table |
| cinema-series-tv.fr — "Comment bien gérer son budget face aux abonnements" (2026-08-08) | recommends computing cost per hour; no tool | DROP-002 (FR copy) | contact page | after "coût par heure" paragraph |
| GeldNavi — "Abonnements kündigen & sparen: 80–250 € pro Monat" | claims a four-digit yearly figure; no calculator | DROP-002 (DE copy) | kontakt@geldnavi.de | under the savings claim |
| DebtMirror — "The 2026 Subscription Audit" (2026-02-04) | links only its own dashboard; "$747/year" stat | DROP-002 EN widget | contact@debtmirror.co | next to the $747 stat |
| MundoOfertas — "Cancelar suscripciones digitales: auditoría en 30 días" | 30-day guide, no totals | DROP-002 ES | info@mundoofertas.com | day-1 step |
| Offzeit.de — "Bildschirmzeit" Ratgeber (2025-01-03) | explains averages (3.4 h/day) without showing lifetime impact | DROP-001 (DE copy) | contact form | after the "3,4 Stunden" figure |
| EDUCACIÓN 3.0 — "bienestar digital" (2026-04) | routines article; no interactive element | DROP-001 ES | contact form | after the routines list |

Widgets: `docs/embed/doomscroll.html`, `docs/embed/subscriptions.html`, loader `docs/embed.js`. Offer the iframe snippet, one line, plus a `?src=` tag per host.

## 8. Broken / outdated tool replacement — result: none honest

Checked: trackmysubs.com (alive), asktrim.com (→ OneMain), Truebill (→ Rocket Money), Mint (→ Credit Karma), inthemoment.io
(Moment app; connection dead), timewellspent.io (alive, different owner), RSPH Scroll Free September (discontinued campaign).
None of these was a calculator that Worth One replaces one-for-one. Recorded so nobody re-runs this; no manipulative link building.

## 9. Newsletter strategy (small → medium → large)

| Size | Name | Audience | Route | Drop | Angle |
|---|---|---|---|---|---|
| small | El Proxy (ES) | Spanish tech filter readers | info@jesusysustics.com | 001 | "juego de números: 2 h/día = 304 días" |
| small | The Whippet (AU) | curious readers | contact form | 001 | the receipt as an artefact |
| small | Kraftfuttermischwerk (DE) | German net culture | contact form | 001 | Kassenzettel für Scrollzeit |
| small | Random Daily URLs | one link a day | form (captcha) | 001 | plain link |
| medium | Web Curios (UK) | internet-strange, weekly | matt@webcurios.co.uk | 001 | two lines, no ask |
| medium | Advisorator | practical tech tips | hello@jarednewman.com | 002 | free, no account, useful |
| medium | Website Hunt (5.9k) | hand-picked sites | login submit | 001 | plain |
| large | Wonder Tools | useful sites/apps | jeremy.caplan@journalism.cuny.edu | 002 | reader tool pick |
| large | Microsiervos / Genbeta / WWWhat's new (ES) | Spanish tech | email/form | 001+002 | honest maker note in Spanish |
| large | Recomendo / Dense Discovery / Now I Know | — | NO VERIFIED CONTACT | — | skip until a route appears |
| done | Internet Is Beautiful | — | already pitched; no follow-up (rule) | 001 | — |

## 10. Outreach template structures (one per campaign; short, no hype)

**WEB-01 (directory form)** — Name; URL; one sentence: "Type your daily scrolling time, get a receipt: per year, per decade, days of life. Free, no signup, no ads."; category; tags.

**WEB-02 (editor email)** — WHY YOU: one line naming a recent piece of theirs. WHY THIS: "a small free tool: a receipt for scrolling time (2 h/day = 304 days over 10 years)". WHERE IT FITS: their links section / roundup. WHAT YOUR AUDIENCE GETS: a number for a vague feeling, no signup. ONE LINK. Sign-off: "Made by one person; happy to answer anything." Spanish version for ES targets.

**EDU-01 (org / teacher)** — WHY YOU: "your screen-time page lists tools for families". WHY THIS: free calculator, no account, no data collected, no medical claims. WHERE IT FITS: Tools/Resources list or classroom warm-up. WHAT THEY GET: a five-minute discussion starter that students can screenshot. ONE LINK (+ embed snippet on request).

**FIN-01 (embed offer)** — WHY YOU: name the article and the exact sentence where readers add up costs. WHY THIS: the receipt shows 1/5/10-year totals instantly. WHERE IT FITS: after that paragraph, as an iframe (snippet included, 1 line). WHAT THEY GET: readers stay on the page and share a receipt. ONE LINK. Offer PT/FR/DE copy if needed.

**WEIRD-01** — case by case; never templated.

## 11. Scoring

Score 0–100 = audience fit 25 % + acceptance probability 20 % + traffic 15 % + SEO 10 % + embed 10 % + repeatability 10 % + (low) effort 10 %.
Sub-scores are in each JSON row. Rejected rows score 0. Tier is a judgement on top of the score (A = strong fit + active + legitimate + realistic route).

## 12. Weird distribution (10 legitimate, unconventional channels)

1. **LibGuides digital-wellbeing cluster** — university librarians publish guide-owner emails (Towson, Exeter verified; ~20 more via `libguides "digital wellbeing"`). Ask for a link in the "tools" box.
2. **Alldle-style daily rituals do not apply to Worth One, but "monthly challenge" orgs do** — TheChallenge.org (non-profit since 2026) runs a 31-day digital detox; propose "print your receipt on day 1 and day 31".
3. **Screen-Free Week (May) and No Scroll September** — seasonal hooks; pitch in April / August, not now.
4. **Data Is Plural** — publish an aggregated, anonymised "receipts" dataset (hours/day distribution by country), then suggest it (route: jsvine.com contact; not yet verified).
5. **Financial-education clearinghouses** — Jump$tart Clearinghouse accepts free educational resources from registered providers; La finance pour tous has a calculators page with no subscription calculator.
6. **Family-agreement templates** — Childnet Family Agreement / klicksafe Mediengutscheine pages: offer the receipt as the "before" step.
7. **Teacher "Best of" lists** — Larry Ferlazzo's lists are permanent and re-linked by thousands of school pages.
8. **Cool Tools user review** — cannot be pitched by the maker; if a real user emerges (support-intent list), ask them to write it (they pay $25 to the reviewer).
9. **Search engines of the small web** — Marginalia (email), Wiby, Search My Site: not directories, but they are how the indie-web audience browses.
10. **Peer calculators as neighbours, not enemies** — English screen-time calculators run by app companies will not link us; but Spanish/PT/FR/DE finance blogs have no calculator to defend. Concentrate there.

## 13. Recursive expansion rule (for Scout/Sonnet)

When a target produces ≥ 5 real users (by `?src=`): find 10–30 look-alikes with the query that found it (queries listed in
`SCOUT_EXPANSION_HANDOFF.md`). ≥ 20 users: raise the cluster to top priority and prepare localised copy for it. ≥ 100 users:
80 % of outreach effort on that cluster until it saturates.

## 14. Rejected (never retry)

Web Tools Weekly, Tech Productivity (social-DM only); Kagi Small Web, ooh.directory (blogs only); Awwwards/CSSDA (paid);
Online Tools Forge (not a directory); Launch Llama (AI only); Console.dev/DevHunt (dev tools); BetaList (startups);
mass-submission services; WebCurate (paid); RSPH Scroll Free September (dead); Common Sense Education reviews (paused);
Ditch That Textbook (explicit no-pitch policy); NerdWallet-type lead-gen; competitor app blogs; verbraucherzentrale-finanzen.org (lookalike).
