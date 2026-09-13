"""ACTION EXECUTOR for Words Before Coffee (pivot 2026-09-13).

MEASURE -> ANALYSE -> FIND OPPORTUNITY -> EXECUTE -> MEASURE RESULT -> LEARN -> REPEAT.

Deterministic code, no model calls. The Brain (brain/run.sh) proposes leads and writes pitches; this module
verifies leads, executes what has a legitimate unattended path, verifies results, attributes real players
to the assets that produced them, and records what worked so the next Brain run can replicate it.

Statuses of an action
  PREPARED / QUEUED / EXECUTING   automatic path found
  SUBMITTED -> LIVE / NO_RESPONSE  sent or submitted, then verified (24h / 72h / 7d)
  MANUAL_ONLY                     login, CAPTCHA, account, payment or manual publication needed - parked in the
                                  collapsed "optional human actions" list; the system never waits for it
  DO_NOT_CONTACT                  an outreach check failed (see outreach.py)
  FAILED / STALE                  attempted and gave up
  ARCHIVED                        Worth One - frozen, never executed again, data kept

Runs on worth-executor.timer (every 2 h) and right after every Brain run.
"""
import json
import re
import time
import urllib.error
import urllib.request

import commands
import db
import outreach
import wbc

UA = "Mozilla/5.0 (compatible; WordsBeforeCoffee/1.0; +https://wordsbeforecoffee.com/)"
SITE = wbc.SITE
SENDER = "hello@wordsbeforecoffee.com"

VERIFY_SCHEDULE = [86400, 3 * 86400, 7 * 86400]
MAX_ATTEMPTS = 3
LEAD_RECHECK_DAYS = 30

# ---------------- form recipes (each inspected live before being added; never guess selectors) ----------------

WBC_DESCRIPTION_EN = ("Four daily Spanish puzzles: three words to guess, a sliding word puzzle, a themed word search and a "
                      "memory game. Same challenge for everyone, resets at midnight. No account, no ads.")


def _confirmed(page):
    body = page.inner_text("body").lower()
    return any(w in body for w in ("thank", "submitted", "review", "received", "reached us", "gracias", "recibido"))


def _recipe_theforest(page, a):
    url = a.get("url") or f"{SITE}/?src=theforest"
    page.goto("https://theforest.link/", timeout=25000, wait_until="domcontentloaded")
    page.wait_for_timeout(800)
    page.get_by_text("Plant", exact=True).click()
    page.wait_for_timeout(300)
    page.fill("input[name='website']", url)
    page.get_by_role("button", name="Plant it", exact=True).click()
    page.wait_for_timeout(3000)
    return ("SUBMITTED", "planted: " + url) if _confirmed(page) else ("FAILED", "no confirmation text after submit")


def _recipe_shouldseethis(page, a):
    page.goto("https://shouldseethis.com/submit/", timeout=25000, wait_until="networkidle")
    page.wait_for_timeout(1000)
    page.get_by_placeholder("https://example.com").fill(f"{SITE}/?src=shouldseethis")
    page.get_by_placeholder("What's the name of this awesome site?").fill("Words Before Coffee")
    page.get_by_role("button", name="FUN", exact=True).click()
    page.get_by_placeholder("What does this website do? Keep it short and sweet!").fill(
        "Four daily Spanish brain games: guess three words, slide letters into words, a themed word search and a memory. Same puzzle for everyone, new at midnight.")
    page.get_by_placeholder("Tell us what makes this website special! What made you stop and think 'I SHOULD SEE THIS'?").fill(
        "A five-minute morning ritual in Spanish: no account, no ads, one shared puzzle a day, and a Coffee Score that sums up how you did across all four games.")
    page.get_by_placeholder("Your name").fill("Words Before Coffee")
    page.get_by_placeholder("your@email.com").fill(SENDER)
    page.get_by_role("button", name="SUBMIT WEBSITE").click()
    page.wait_for_timeout(2500)
    return ("SUBMITTED", "form submitted: Words Before Coffee (FUN)") if _confirmed(page) else ("FAILED", "no confirmation text after submit")


def _recipe_weirdwebtools(page, a):
    page.goto("https://www.weirdwebtools.com/submit", timeout=25000, wait_until="networkidle")
    page.wait_for_timeout(1500)
    page.fill("input[name='name']", "Words Before Coffee")
    page.fill("input[name='url']", f"{SITE}/?src=weirdwebtools")
    page.fill("textarea[name='description']", WBC_DESCRIPTION_EN[:280])
    page.check("input[name='type'][value='NO_LOGIN']")
    page.select_option("select[name='category']", "GAME")
    page.fill("input[name='tags']", "daily, spanish, word game, puzzle")
    page.fill("input[name='email']", SENDER)
    # honeypot field 'website' stays empty on purpose
    page.wait_for_timeout(4000)
    token = page.evaluate("() => (document.querySelector('input[name=cf-turnstile-response]')||{}).value || ''")
    if not token:
        return "MANUAL_ONLY", "Cloudflare Turnstile challenge did not clear unattended; submit by hand or email hello@weirdwebtools.com"
    page.get_by_role("button", name="Submit for review").click()
    page.wait_for_timeout(3000)
    return ("SUBMITTED", "form submitted: Words Before Coffee (GAME, no login)") if _confirmed(page) else ("FAILED", "no confirmation text after submit")


def _recipe_alldle(page, a):
    payload = json.loads(a.get("payload") or "{}")
    name, url = payload.get("name") or "Words Before Coffee", payload.get("target_url") or f"{SITE}/?src=alldle"
    page.goto("https://www.alldle.net/submit", timeout=25000, wait_until="networkidle")
    page.wait_for_timeout(1000)
    page.fill("#name", name)
    page.fill("#url", url)
    page.click("form button[type='submit']")
    page.wait_for_timeout(3000)
    return ("SUBMITTED", f"submitted {name}") if _confirmed(page) else ("FAILED", "no confirmation text after submit")


FORM_RECIPES = {
    "theforest.link": _recipe_theforest,
    "shouldseethis.com": _recipe_shouldseethis,
    "weirdwebtools.com": _recipe_weirdwebtools,
    "alldle.net": _recipe_alldle,
}

# Targets that need a person for a specific, verified reason (login / captcha / account / payment).
KNOWN_MANUAL = {
    "AST-WBCWBCPO-001": "Miniplay/Minijuegos: developer account + support ticket (login)",
    "AST-WBCWBCPO-002": "CrazyGames: developer account and an uploaded build (login + product work)",
    "AST-WBCWBCPO-004": "Newgrounds: account required",
    "AST-WBCWBCPO-005": "itch.io: account required",
    "AST-WBCWBCED-003": "Mis Clases Locas contact form has a CAPTCHA",
    "AST-WBCWBCPR-002": "Magisnet contact form has a CAPTCHA",
    "AST-WBCWBCED-006": "Spanish Playground contact form has a CAPTCHA",
    "AST-WBCWBCED-007": "Srta Spanish contact form has a CAPTCHA",
    "AST-WBCWBCPO-003": "Coolmath Games: Google Form may require a Google sign-in; not inspected",
}


def _host(url):
    m = re.match(r"https?://(?:www\.)?([^/:?#]+)", url or "")
    return m.group(1).lower() if m else ""


def _slug(name):
    return re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")[:40]


def score(a):
    eff = max(a.get("effort") or 1, 0.1)
    return round((a.get("expected_users") or 0) * (a.get("confidence") or 0.5) * (a.get("strategic_value") or 0.5) / eff, 4)


DEFAULTS_BY_TYPE = {
    # (expected_users, confidence, strategic_value, effort) - expected REAL PLAYERS, not visits
    "directory": (12, 0.5, 0.7, 0.2),
    "publisher": (15, 0.35, 0.6, 0.2),
    "press": (40, 0.25, 0.7, 0.3),
    "newsletter": (15, 0.35, 0.5, 0.2),
    "resource_page": (10, 0.45, 0.7, 0.2),
    "peer_site": (6, 0.4, 0.6, 0.2),
    "portal": (30, 0.3, 0.5, 0.6),
    "backlink": (4, 0.6, 0.6, 0.1),
    "embed": (5, 0.4, 0.4, 0.3),
}


# ---------------- FREEZE: Worth One is archived ----------------

def freeze_worth_one():
    """Idempotent. Parks every Worth One action/asset; data stays; nothing external ever runs for it again."""
    with db.tx() as c:
        n1 = c.execute("UPDATE actions SET status='ARCHIVED', updated_ts=? WHERE (drop_id IS NULL OR drop_id!='WBC') AND status IN ('PREPARED','QUEUED','EXECUTING','HUMAN_REQUIRED','FAILED')", (time.time(),)).rowcount
        n2 = c.execute("UPDATE assets SET status='archived', updated_ts=? WHERE (drop_id IS NULL OR drop_id!='WBC') AND status IN ('prepared','access_required')", (time.time(),)).rowcount
        n3 = c.execute("UPDATE actions SET next_verify_at=NULL WHERE (drop_id IS NULL OR drop_id!='WBC') AND next_verify_at IS NOT NULL").rowcount
        n4 = c.execute("UPDATE human_actions SET status='archived', resolved_ts=? WHERE status='open' AND (title LIKE '%Search Console%' OR title LIKE '%tinytools%' OR title LIKE '%Worth One%' OR title LIKE '%cross-promotion%' OR title LIKE '%GitHub%' OR title LIKE '%Subscription Lifetime%' OR title LIKE '%mailbox%' OR title LIKE '%Doomscroll%')", (time.time(),)).rowcount
    db.set_setting("WORTH_ONE_STATUS", "ARCHIVED")
    db.set_setting("ACTIVE_PROJECT", "WBC")
    if n1 or n2 or n4:
        db.log_activity("control", f"Worth One frozen: {n1} actions and {n2} assets archived, {n4} human actions closed; no further external actions", None, actor="executor")
    return {"actions_archived": n1, "assets_archived": n2, "verifies_cancelled": n3, "human_actions_closed": n4}


# ---------------- FIND OPPORTUNITY: leads -> verified assets ----------------

def _reachable(url):
    key = "url:" + url
    c = db.cache_get(key, LEAD_RECHECK_DAYS * 86400)
    if c and (c["status"] == "ok" or time.time() - c["ts"] < 2 * 86400):  # unreachable sites are retried after 2 days
        return c["status"] == "ok", c["data"]
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15) as resp:
            code = resp.status
            body = resp.read(200000).decode("utf-8", "ignore")
        ok = code < 400
        title = re.search(r"<title[^>]*>(.*?)</title>", body, re.S | re.I)
        data = {"http": code, "title": (title.group(1).strip()[:120] if title else "")}
    except urllib.error.HTTPError as e:
        ok, data = False, {"http": e.code}
    except Exception as e:  # noqa: BLE001
        ok, data = False, {"error": str(e)[:120]}
    db.cache_set(key, "ok" if ok else "unreachable", data)
    return ok, data


def verify_leads():
    """Brain-proposed leads (assets with status 'lead') become prepared (verified route), manual_only or
    do_not_contact. Each domain/url is checked once (research cache); never re-investigated."""
    out = {"prepared": 0, "manual_only": 0, "do_not_contact": 0, "unreachable": 0}
    for a in db.q("SELECT * FROM assets WHERE drop_id='WBC' AND status='lead'"):
        url = a.get("url") or ""
        ok, data = _reachable(url) if url else (False, {"error": "no url"})
        if not ok:
            _set_asset(a["asset_id"], "unreachable", f"lead url not reachable: {json.dumps(data)[:120]}")
            out["unreachable"] += 1
            continue
        if not a.get("src_tag"):
            with db.tx() as c:
                c.execute("UPDATE assets SET src_tag=? WHERE asset_id=?", (_slug(a["name"]), a["asset_id"]))
        contact = (a.get("contact") or "").strip()
        if contact and "@" in contact:
            pol = outreach.policy_check(a)
            if pol["status"] != "checked" or not pol["public_contact"] or pol["forbids_ai"] or pol["forbids_unsolicited"]:
                why = ("address not found on a public page" if not pol["public_contact"] else
                       "site refuses AI/automated messages" if pol["forbids_ai"] else
                       "site refuses unsolicited pitches" if pol["forbids_unsolicited"] else f"site not readable ({pol['status']})")
                _set_asset(a["asset_id"], "do_not_contact", "DO_NOT_CONTACT: " + why + (" | " + pol["evidence"][:200] if pol["evidence"] else ""))
                out["do_not_contact"] += 1
                continue
            if a.get("pitch") and (a.get("pitch_source") in ("brain", "human")):
                _set_asset(a["asset_id"], "prepared", "verified: public contact, no prohibitions; pitch ready")
            else:
                _set_asset(a["asset_id"], "needs_pitch", "verified: public contact, no prohibitions; waiting for an authored pitch")
            out["prepared"] += 1
            continue
        if _host(url) in FORM_RECIPES:
            _set_asset(a["asset_id"], "prepared", "verified: tested form recipe available")
            out["prepared"] += 1
            continue
        _set_asset(a["asset_id"], "manual_only", "MANUAL_ONLY: no public email and no tested login-free form; " + (a.get("notes") or "")[:120])
        out["manual_only"] += 1
    return out


def _set_asset(asset_id, status, result=None):
    with db.tx() as c:
        if result is None:
            c.execute("UPDATE assets SET status=?, updated_ts=? WHERE asset_id=?", (status, time.time(), asset_id))
        else:
            c.execute("UPDATE assets SET status=?, result=?, updated_ts=? WHERE asset_id=?", (status, result[:300], time.time(), asset_id))


# ---------------- DISCOVER / QUALIFY ----------------

def sync_from_assets():
    created = 0
    # actions parked under the old HUMAN_REQUIRED status get one fresh classification: several of them now have an
    # autonomous route (a public email with an authored pitch, a tested form recipe), the rest become MANUAL_ONLY.
    with db.tx() as c:
        c.execute("UPDATE actions SET status='PREPARED', updated_ts=? WHERE drop_id='WBC' AND status='HUMAN_REQUIRED'", (time.time(),))
        # keep actions aligned with what already happened to their asset (e.g. a directory submitted by hand):
        # never re-submit something that is already submitted or live, never re-queue a do-not-contact target.
        c.execute("""UPDATE actions SET status='SUBMITTED', next_verify_at=COALESCE(next_verify_at, ?), updated_ts=?
                     WHERE drop_id='WBC' AND status IN ('PREPARED','QUEUED','FAILED','STALE')
                       AND asset_id IN (SELECT asset_id FROM assets WHERE status='submitted')""", (time.time() + VERIFY_SCHEDULE[0], time.time()))
        c.execute("""UPDATE actions SET status='LIVE', next_verify_at=NULL, updated_ts=? WHERE drop_id='WBC' AND status!='LIVE'
                       AND asset_id IN (SELECT asset_id FROM assets WHERE status='live')""", (time.time(),))
        c.execute("""UPDATE actions SET status='DO_NOT_CONTACT', updated_ts=? WHERE drop_id='WBC' AND status IN ('PREPARED','QUEUED')
                       AND asset_id IN (SELECT asset_id FROM assets WHERE status IN ('do_not_contact','pitch_rejected','archived'))""", (time.time(),))
    for a in db.q("SELECT * FROM assets WHERE drop_id='WBC' AND status='prepared'"):
        eu, conf, sv, eff = DEFAULTS_BY_TYPE.get(a["type"], (8, 0.4, 0.5, 0.3))
        if db.add_action("ACT-" + a["asset_id"], "pending_classification", asset_id=a["asset_id"], target=a["name"], url=a["url"],
                         drop_id="WBC", expected_users=eu, confidence=conf, strategic_value=sv, effort=eff, status="PREPARED"):
            created += 1
    return created


def classify(a):
    """(auto_type or None, manual_reason)."""
    asset_id = a.get("asset_id")
    if asset_id in KNOWN_MANUAL:
        return None, KNOWN_MANUAL[asset_id]
    asset = db.q1("SELECT * FROM assets WHERE asset_id=?", (asset_id,)) if asset_id else None
    if asset and asset.get("contact") and "@" in asset["contact"] and asset.get("pitch"):
        return "email_outreach", None
    url = a.get("url") or (asset or {}).get("url") or ""
    if _host(url) in FORM_RECIPES:
        return "form_submit", None
    notes = ((asset or {}).get("notes") or "").lower()
    if "login" in notes or "captcha" in notes or "account" in notes or "cuenta" in notes:
        return None, "needs login, account or CAPTCHA: " + notes[:140]
    if asset and asset.get("contact") and "@" in asset["contact"]:
        return None, "public email found but no authored pitch yet (the Brain writes it next run)"
    return None, "no autonomous route: contact form without a tested recipe, no public email"


# ---------------- EXECUTE ----------------

def h_email_outreach(a):
    res = outreach.send(a["asset_id"])
    if res == "sent":
        return "SUBMITTED", "sent after 8/8 checks"
    if res.startswith("already contacted"):
        return "SUBMITTED", res
    if res.startswith("blocked:"):
        return "DO_NOT_CONTACT", res
    if "smtp not configured" in res:
        return "MANUAL_ONLY", res
    return "FAILED", res


def h_form_submit(a):
    recipe = FORM_RECIPES.get(_host(a.get("url")))
    if not recipe:
        return "MANUAL_ONLY", "no tested recipe for this host"
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=UA)
        try:
            result = recipe(page, a)
        finally:
            browser.close()
    return result


def h_verify_http(a):
    url = a.get("url")
    if not url:
        return "FAILED", "no url to verify"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15) as resp:
            code = resp.status
            body = resp.read(400000).decode("utf-8", "ignore").lower()
        payload = json.loads(a.get("payload") or "{}")
        check = (payload.get("check_text") or "wordsbeforecoffee").lower()
        ok = code < 400 and check in body
        return ("LIVE", f"HTTP {code}, '{check}' found on page") if ok else ("PENDING", f"HTTP {code}, '{check}' not on page yet")
    except urllib.error.HTTPError as e:
        return "PENDING", f"HTTP {e.code}"
    except Exception as e:  # noqa: BLE001
        return "PENDING", str(e)[:200]


HANDLERS = {"email_outreach": h_email_outreach, "form_submit": h_form_submit}


# ---------------- MEASURE RESULT: verify listings + players attributed ----------------

def _players_from(asset):
    """Evidence from the product itself: players whose first visit carried this asset's src tag or referrer host."""
    m = wbc.latest()
    tag = wbc.src_tag_of(asset)
    host = _host(asset.get("url") or "")
    total = 0
    for r in (m.get("acquisition") or {}).get("30d", []):
        if (tag and r["source"] == tag) or (host and r["source"] == "ref:" + host):
            total += r.get("users", 0)
    return total


def run_verify():
    due = db.q("SELECT * FROM actions WHERE drop_id='WBC' AND status='SUBMITTED' AND next_verify_at IS NOT NULL AND next_verify_at<=?", (time.time(),))
    out = {"LIVE": 0, "NO_RESPONSE": 0, "pending": 0}
    for a in due:
        asset = db.q1("SELECT * FROM assets WHERE asset_id=?", (a.get("asset_id"),)) or {}
        players = _players_from(asset)
        if players:
            status, result = "LIVE", f"{players} players arrived from this source (30d)"
        elif a.get("type") == "form_submit" or asset.get("type") in ("directory", "resource_page", "peer_site", "portal"):
            status, result = h_verify_http({**a, "url": asset.get("url") or a.get("url")})
        else:
            status, result = "PENDING", "no players from this source yet"
        attempts = (a["attempts"] or 0) + 1
        if status == "LIVE":
            db.update_action(a["action_id"], status="LIVE", result=result, attempts=attempts, next_verify_at=None)
            _set_asset(a["asset_id"], "live", result)
            db.log_activity("verify", f"LIVE: {a.get('target')} - {result}", "WBC", actor="executor")
            out["LIVE"] += 1
        elif attempts >= MAX_ATTEMPTS:
            db.update_action(a["action_id"], status="NO_RESPONSE", result=result, attempts=attempts, next_verify_at=None)
            out["NO_RESPONSE"] += 1
        else:
            db.update_action(a["action_id"], attempts=attempts, result=result, next_verify_at=time.time() + VERIFY_SCHEDULE[min(attempts, len(VERIFY_SCHEDULE) - 1)])
            out["pending"] += 1
    return out


# ---------------- LEARN ----------------

def learn():
    """Attribute players to assets; when something works, record the pattern to replicate (the Brain reads it)."""
    try:
        winners = wbc.attribute()
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)[:120], "winners": []}
    if winners:
        w = winners[0]
        pattern = (f"{w['type']} '{w['name']}' produced {w['users_30d']} players in 30d (conversion {w['conversion']:.0%}). "
                   f"Find 20 more sites of the same kind ({w['type']}, same audience/country/language) and prepare them first.")
        if db.get_setting("WINNING_PATTERN") != pattern:
            db.set_setting("WINNING_PATTERN", pattern)
            db.log_activity("learn", "WINNER: " + pattern, "WBC", actor="executor")
            commands.notify("WBC growth: " + pattern)
    return {"winners": winners}


# ---------------- main cycle ----------------

def _budget_ok():
    try:
        budget = float(db.get_setting("AI_DAILY_BUDGET_USD", "1.0"))
    except ValueError:
        budget = 1.0
    spent = db.q1("SELECT COALESCE(SUM(usd),0) usd FROM ai_cost WHERE ts>=?", (time.time() - (time.time() % 86400),))["usd"]
    return spent < budget, spent, budget


def run_cycle():
    frozen = freeze_worth_one()
    metrics_ok = True
    try:
        wbc.snapshot()
    except Exception:  # noqa: BLE001
        metrics_ok = False
    leads = verify_leads()
    discovered = sync_from_assets()

    queue = db.q("SELECT * FROM actions WHERE drop_id='WBC' AND status IN ('PREPARED','QUEUED')")
    auto, manual = [], 0
    for a in queue:
        auto_type, reason = classify(a)
        if auto_type:
            p = score(a)
            db.update_action(a["action_id"], type=auto_type, status="QUEUED", priority=p)
            a["type"], a["priority"] = auto_type, p
            auto.append(a)
        else:
            db.update_action(a["action_id"], status="MANUAL_ONLY", priority=score(a), human_required_reason=reason, human_action_text=reason)
            _set_asset(a["asset_id"], "manual_only", "MANUAL_ONLY: " + reason)
            manual += 1

    auto.sort(key=lambda a: -(a.get("priority") or 0))
    executed, capped = {}, 0
    emails_left = outreach.daily_cap() - outreach.sent_today("wbc")
    db.set_setting("CURRENT_ACTION", f"Executor cycle: {len(auto)} queued, {max(0, emails_left)} email slots left today")
    for a in auto:
        if a["type"] == "email_outreach":
            if emails_left <= 0:
                capped += 1
                continue
        db.update_action(a["action_id"], status="EXECUTING", attempts=(a["attempts"] or 0) + 1, last_attempt=time.time())
        try:
            status, result = HANDLERS[a["type"]](a)
        except Exception as e:  # noqa: BLE001
            status, result = "FAILED", str(e)[:300]
        if a["type"] == "email_outreach" and status == "SUBMITTED" and "sent" in result:
            emails_left -= 1
        extra = {}
        if status == "SUBMITTED":
            extra["next_verify_at"] = time.time() + VERIFY_SCHEDULE[0]
            _set_asset(a["asset_id"], "submitted", result)
            db.set_setting("LAST_GROWTH_ACTION", f"{a['type']}: {a.get('target')} ({result[:60]}) at {db.day_of()}")
        elif status == "MANUAL_ONLY":
            extra["human_required_reason"] = (result or "")[:200]
            extra["human_action_text"] = (result or "")[:200]
            _set_asset(a["asset_id"], "manual_only", "MANUAL_ONLY: " + (result or "")[:200])
        elif status == "DO_NOT_CONTACT":
            pass  # outreach.send already marked the asset
        elif status == "FAILED" and (a["attempts"] or 0) + 1 >= MAX_ATTEMPTS:
            status = "STALE"
        db.update_action(a["action_id"], status=status, result=(result or "")[:500], **extra)
        executed[status] = executed.get(status, 0) + 1
        db.log_activity(a["type"], f"{a.get('target')}: {status} - {(result or '')[:100]}", "WBC", actor="executor")

    verified = run_verify()
    learned = learn()
    budget_ok, spent, budget = _budget_ok()

    manual_total = db.q1("SELECT COUNT(*) n FROM actions WHERE drop_id='WBC' AND status='MANUAL_ONLY'")["n"]
    queued_total = db.q1("SELECT COUNT(*) n FROM actions WHERE drop_id='WBC' AND status IN ('QUEUED','PREPARED')")["n"]
    nxt = ("send the next verified pitch when a daily email slot opens" if queued_total else
           "wait for the Brain to propose new verified leads" if not learned.get("winners") else
           "replicate the winning pattern: " + db.get_setting("WINNING_PATTERN", "")[:80])
    db.set_setting("NEXT_ACTION", nxt)
    summary = (f"leads={leads} discovered={discovered} executed={executed} capped={capped} verified={verified} "
               f"winners={len(learned.get('winners') or [])} manual_only={manual_total} metrics={'ok' if metrics_ok else 'unavailable'} "
               f"ai_spent_today=${spent:.2f}/{budget:.2f}")
    db.record_run("executor", "ok", summary)

    notable = []
    if executed.get("SUBMITTED"):
        notable.append(f"{executed['SUBMITTED']} growth actions executed (emails after 8 checks / form submissions)")
    if verified.get("LIVE"):
        notable.append(f"{verified['LIVE']} listings confirmed LIVE")
    if learned.get("winners"):
        notable.append("winning source: " + learned["winners"][0]["name"])
    if notable:
        commands.notify("Words Before Coffee - " + "; ".join(notable))
    return {"frozen": frozen, "leads": leads, "discovered": discovered, "executed": executed, "capped": capped,
            "verified": verified, "learned": learned, "manual_only": manual_total, "summary": summary}
