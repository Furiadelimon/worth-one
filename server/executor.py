"""ACTION EXECUTOR — turns PREPARED assets into a worked queue instead of a PREPARED graveyard.

DISCOVER -> QUALIFY -> PREPARE -> QUEUE -> AUTO EXECUTE -> VERIFY -> SUBMITTED/LIVE/FAILED.
Only HUMAN_REQUIRED when no legitimate automatic path exists (login, CAPTCHA, 2FA, payment,
a public GitHub identity, manual publish on TikTok). Everything here is deterministic code —
no model calls. The Brain decides what deserves doing; this module does the doing.

Run one cycle: `worthctl executor` (also wired to worth-executor.timer).
"""
import json
import re
import subprocess
import time
import urllib.error
import urllib.request

import commands
import db
import outreach

UA = "Mozilla/5.0 (compatible; WorthOneVerifier/1.0; +https://furiadelimon.github.io/worth-one/)"

# Sites with a hand-verified, selector-level recipe for unattended form submission.
# Each entry was inspected live with Playwright (real DOM, real field names/placeholders) before
# being added — see section 5/25 of the executor directive: code drives known flows, never guesswork.
# A recipe never fabricates a submitter identity: if the form carries an email field and the action's
# payload has no submitter_email, it aborts with HUMAN_REQUIRED (WAITING_*_SENDER) instead of guessing
# or leaving a half-filled submission behind.

def _has_unfillable_email(page, payload):
    """True if the form exposes an email field we have no legitimate address to put in."""
    if payload.get("submitter_email"):
        return False
    try:
        return bool(page.evaluate("() => !!document.querySelector('input[type=email]')"))
    except Exception:
        return False


def _confirmed(page):
    body = page.inner_text("body").lower()
    return any(w in body for w in ("thank", "submitted", "review", "received", "reached us"))


def _recipe_theforest(page, a):
    payload = json.loads(a.get("payload") or "{}")
    url = payload.get("target_url")
    if not url:
        return "FAILED", "payload missing target_url"
    page.goto("https://theforest.link/", timeout=25000, wait_until="domcontentloaded")
    page.wait_for_timeout(800)
    # the "Plant it" form lives behind a "Plant" tab (default view is the "Walk" random-discovery
    # button); the input is present but hidden until that tab is selected.
    page.get_by_text("Plant", exact=True).click()
    page.wait_for_timeout(300)
    page.fill("input[name='website']", url)
    # the page carries several type=submit buttons (a stray "Info", the "Plant" tab itself); only
    # "Plant it" is the real submit for the form we just filled.
    page.get_by_role("button", name="Plant it", exact=True).click()
    page.wait_for_timeout(3000)
    if _confirmed(page):
        return "SUBMITTED", "planted: " + url
    return "FAILED", "no confirmation text after submit"


def _recipe_nosignuptools(page, a):
    payload = json.loads(a.get("payload") or "{}")
    for k in ("target_url", "site_name", "short_desc", "long_desc", "category"):
        if not payload.get(k):
            return "FAILED", f"payload missing {k}"
    page.goto("https://nosignuptools.com/submit", timeout=25000, wait_until="networkidle")
    page.wait_for_timeout(1000)
    if _has_unfillable_email(page, payload):
        return "HUMAN_REQUIRED", "WAITING_WORTH_ONE_SENDER: this form carries a contact-email field and no Worth One sender is configured yet"
    page.fill("#name", payload["site_name"])
    page.fill("#url", payload["target_url"])
    page.fill("#shortDescription", payload["short_desc"])
    page.fill("#longDescription", payload["long_desc"])
    if page.query_selector("select"):
        page.select_option("select", payload["category"])
    for tag in payload.get("tags", []):
        btn = page.get_by_role("button", name=tag, exact=True)
        if btn.count():
            btn.first.click()
    if payload.get("submitter_name"):
        page.fill("#submitterName", payload["submitter_name"])
    if payload.get("submitter_email"):
        page.fill("#submitterEmail", payload["submitter_email"])
    page.click("button[type='submit']")
    page.wait_for_timeout(2000)
    if _confirmed(page):
        return "SUBMITTED", "form submitted: " + payload["site_name"]
    return "FAILED", "no confirmation text after submit"


def _recipe_shouldseethis(page, a):
    payload = json.loads(a.get("payload") or "{}")
    for k in ("target_url", "site_name", "category", "what_it_does", "why_awesome"):
        if not payload.get(k):
            return "FAILED", f"payload missing {k}"
    page.goto("https://shouldseethis.com/submit/", timeout=25000, wait_until="networkidle")
    page.wait_for_timeout(1000)
    if _has_unfillable_email(page, payload):
        return "HUMAN_REQUIRED", "WAITING_WORTH_ONE_SENDER: this form requires a contact email and no Worth One sender is configured yet"
    page.get_by_placeholder("https://example.com").fill(payload["target_url"])
    page.get_by_placeholder("What's the name of this awesome site?").fill(payload["site_name"])
    page.get_by_role("button", name=payload["category"], exact=True).click()
    page.get_by_placeholder("What does this website do? Keep it short and sweet!").fill(payload["what_it_does"])
    page.get_by_placeholder("Tell us what makes this website special! What made you stop and think 'I SHOULD SEE THIS'?").fill(payload["why_awesome"])
    page.get_by_placeholder("Your name").fill(payload.get("submitter_name") or "Worth One?")
    if payload.get("submitter_email"):
        page.get_by_placeholder("your@email.com").fill(payload["submitter_email"])
    page.get_by_role("button", name="SUBMIT WEBSITE").click()
    page.wait_for_timeout(2000)
    if _confirmed(page):
        return "SUBMITTED", "form submitted: " + payload["site_name"]
    return "FAILED", "no confirmation text after submit"


FORM_RECIPES = {
    "theforest.link": _recipe_theforest,
    "nosignuptools.com": _recipe_nosignuptools,
    "shouldseethis.com": _recipe_shouldseethis,
}

# Assets/targets investigated this session that need a human for a specific, named reason.
# Populated as the executor (or a human) discovers a hard blocker, so it is asked only once.
KNOWN_HUMAN_ONLY = {
    "AST-DIR-007": ("GitHub PR requires a public GitHub identity", "HUMAN_GITHUB_ACTION_REQUIRED", 3),
    "AST-CP-001": ("target file lives in the Words Before Coffee repo, the LXC has no write access there", "paste the snippet from engine/cross-promo/wordsbeforecoffee-snippet.md into app/templates/_games_sheet.html", 2),
    "AST-DIR-010": ("tinytools requires sign-in (email magic link / GitHub / Google) before submitting a tool", "sign in at https://tinytools.tools/submit and paste the Subscription Lifetime Receipt URL", 2),
    "AST-SEO-002": ("Search Console access grant requires the owner's Google account", "add the service-account user in Search Console once verified", 3),
}

VERIFY_SCHEDULE = [86400, 3 * 86400, 7 * 86400]  # 24h, 72h, 7d after SUBMITTED
MAX_ATTEMPTS = 3


def _host(url):
    m = re.match(r"https?://([^/]+)", url or "")
    return m.group(1).lower() if m else ""


def score(a):
    eff = max(a.get("effort") or 1, 0.1)
    return round((a.get("expected_users") or 0) * (a.get("confidence") or 0.5) * (a.get("strategic_value") or 0.5) / eff, 4)


# ---------------- DISCOVER / QUALIFY / PREPARE: turn assets into actions ----------------

DEFAULTS_BY_TYPE = {
    # (expected_users, confidence, strategic_value, effort)
    "newsletter": (15, 0.4, 0.6, 0.2),
    "publisher": (12, 0.4, 0.6, 0.2),
    "resource_page": (10, 0.4, 0.5, 0.2),
    "directory": (10, 0.5, 0.5, 0.3),
    "backlink": (5, 0.6, 0.7, 0.1),
    "embed": (5, 0.4, 0.4, 0.1),
    "press": (20, 0.3, 0.7, 0.3),
    "localization": (5, 0.5, 0.4, 0.5),
}


def sync_from_assets():
    """DISCOVER+PREPARE: one open action per asset still needing work. Idempotent."""
    created = 0
    assets = db.q("SELECT * FROM assets WHERE status IN ('prepared','access_required')")
    for a in assets:
        action_id = "ACT-" + a["asset_id"]
        eu, conf, sv, eff = DEFAULTS_BY_TYPE.get(a["type"], (8, 0.4, 0.5, 0.3))
        made = db.add_action(
            action_id, "pending_classification",
            asset_id=a["asset_id"], target=a["name"], url=a["url"], drop_id=a["drop_id"],
            expected_users=eu, confidence=conf, strategic_value=sv, effort=eff,
            status="PREPARED",
        )
        if made:
            created += 1
    return created


def classify(a):
    """Return (auto_type_or_None, reason, human_action_text, estimated_minutes)."""
    asset_id = a.get("asset_id")
    if asset_id in KNOWN_HUMAN_ONLY:
        reason, text, mins = KNOWN_HUMAN_ONLY[asset_id]
        return None, reason, text, mins

    asset = db.q1("SELECT * FROM assets WHERE asset_id=?", (asset_id,)) if asset_id else None
    if asset and asset.get("contact") and "@" in asset["contact"] and asset.get("pitch"):
        notes = asset.get("notes") or ""
        if notes.startswith("WAITING_WORTH_ONE_SENDER") or notes.startswith("WAITING_WBC_SENDER"):
            reason = notes.splitlines()[0]
            return None, reason, "configure the sender described in the reason; this pitch then sends on the next cycle", 1
        return "email_outreach", None, None, None

    if asset and asset["type"] == "backlink" and "indexnow" in (asset["name"] or "").lower():
        return "indexnow", None, None, None

    url = a.get("url") or (asset or {}).get("url")
    if url and _host(url) in FORM_RECIPES:
        return "form_submit", None, None, None

    # No verified automatic path: human, but keep the reason honest and specific.
    notes = (asset or {}).get("notes") or ""
    return None, "no automated path yet (no email contact, no login-free public form recipe)", \
        notes or f"open {url}, follow the submit/contact flow described in the asset notes", 3


# ---------------- EXECUTE handlers (deterministic; no model calls) ----------------

def h_email_outreach(a):
    res = outreach.send(a["asset_id"])
    if res == "sent":
        return "SUBMITTED", "sent"
    if res.startswith("already contacted"):
        return "SUBMITTED", res
    if "smtp not configured" in res:
        return "HUMAN_REQUIRED", res
    return "FAILED", res


def h_indexnow(a):
    try:
        r = subprocess.run(["/usr/local/bin/worth-indexnow"], capture_output=True, text=True, timeout=30)
        ok = r.returncode == 0
        return ("SUBMITTED", "indexnow ping run") if ok else ("FAILED", (r.stderr or "")[:300])
    except Exception as e:
        return "FAILED", str(e)[:300]


def h_verify_http(a):
    url = a.get("url")
    if not url:
        return "FAILED", "no url to verify"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=15) as resp:
            code = resp.status
            body = resp.read(30000).decode("utf-8", "ignore")
        payload = json.loads(a.get("payload") or "{}")
        check = (payload.get("check_text") or "").lower()
        ok = code < 400 and (not check or check in body.lower())
        detail = f"HTTP {code}" + (f", check_text {'found' if check in body.lower() else 'MISSING'}" if check else "")
        return ("LIVE", detail) if ok else ("FAILED", detail)
    except urllib.error.HTTPError as e:
        return "FAILED", f"HTTP {e.code}"
    except Exception as e:
        return "FAILED", str(e)[:200]


def h_form_submit(a):
    host = _host(a.get("url"))
    recipe = FORM_RECIPES.get(host)
    if not recipe:
        return "HUMAN_REQUIRED", "no tested recipe for this host"
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(user_agent=UA)
        try:
            result = recipe(page, a)
        finally:
            browser.close()
    return result


HANDLERS = {
    "email_outreach": h_email_outreach,
    "indexnow": h_indexnow,
    "verify_http": h_verify_http,
    "form_submit": h_form_submit,
}


# ---------------- VERIFY loop ----------------

def _next_check(attempts):
    return VERIFY_SCHEDULE[min(attempts, len(VERIFY_SCHEDULE) - 1)]


def run_verify():
    due = db.q("SELECT * FROM actions WHERE status='SUBMITTED' AND next_verify_at IS NOT NULL AND next_verify_at<=?", (time.time(),))
    out = {"LIVE": 0, "NO_RESPONSE": 0}
    for a in due:
        check_url = a.get("url")
        status, result = h_verify_http({**a, "url": check_url}) if check_url else ("FAILED", "no url")
        attempts = (a["attempts"] or 0) + 1
        if status == "LIVE":
            db.update_action(a["action_id"], status="LIVE", result=result, attempts=attempts, next_verify_at=None)
            out["LIVE"] += 1
            if a.get("asset_id"):
                with db.tx() as c:
                    c.execute("UPDATE assets SET status='live', result=?, updated_ts=? WHERE asset_id=?", (result, time.time(), a["asset_id"]))
        elif attempts >= MAX_ATTEMPTS:
            db.update_action(a["action_id"], status="NO_RESPONSE", result=result, attempts=attempts, next_verify_at=None)
            out["NO_RESPONSE"] += 1
        else:
            db.update_action(a["action_id"], attempts=attempts, next_verify_at=time.time() + _next_check(attempts))
    return out


# ---------------- Telegram batching ----------------

def _should_notify(a):
    if not a.get("telegram_notified_ts"):
        return True
    age_days = (time.time() - a["telegram_notified_ts"]) / 86400
    return age_days >= 3  # section 23: only re-notify if it's been sitting a while


def _format_telegram(human, executed, verified):
    total_min = sum((a.get("estimated_human_time") or 3) for a in human)
    ranked = sorted(human, key=lambda x: -(x.get("priority") or 0))
    n = len(ranked)
    # relative thirds, not fixed score thresholds: the label should stay meaningful as the
    # scoring defaults evolve, instead of every item landing in the same bucket.
    labels = {}
    for i, a in enumerate(ranked):
        labels[a["action_id"]] = "HIGH" if i < max(1, n // 3) else "LOW" if i >= n - max(1, n // 3) else "MEDIUM"
    lines = ["WORTH ONE - HUMAN ACTIONS", "", "Automatic work completed:"]
    lines.append(f"- {executed.get('SUBMITTED', 0) + executed.get('LIVE', 0)} actions executed")
    lines.append(f"- {executed.get('SUBMITTED', 0)} submissions sent")
    lines.append(f"- {verified.get('LIVE', 0)} listings verified live")
    if executed.get("FAILED"):
        lines.append(f"- {executed['FAILED']} failed (will retry)")
    lines.append("")
    lines.append(f"Human actions pending: {len(human)}")
    lines.append("")
    for i, a in enumerate(ranked, 1):
        pr = labels[a["action_id"]]
        lines.append(f"{i}. [{pr}] {a.get('target') or a['action_id']}")
        lines.append(f"   Action: {a.get('human_action_text') or a.get('human_required_reason') or 'see control center'}")
        if a.get("url"):
            lines.append(f"   URL: {a['url']}")
        lines.append(f"   Estimated time: {a.get('estimated_human_time') or 3} min")
    lines.append("")
    lines.append(f"TOTAL ESTIMATED HUMAN TIME: {total_min} minutes")
    return "\n".join(lines)


# ---------------- Main cycle ----------------

def run_cycle():
    discovered = sync_from_assets()

    queue = db.q("SELECT * FROM actions WHERE status IN ('PREPARED','QUEUED')")
    auto, newly_human = [], 0
    for a in queue:
        auto_type, reason, human_text, mins = classify(a)
        if auto_type:
            p = score(a)
            db.update_action(a["action_id"], type=auto_type, status="QUEUED", priority=p)
            a["type"], a["priority"] = auto_type, p
            auto.append(a)
        else:
            db.update_action(a["action_id"], status="HUMAN_REQUIRED", priority=score(a),
                              human_required_reason=reason, human_action_text=human_text,
                              estimated_human_time=mins)
            newly_human += 1

    auto.sort(key=lambda a: -(a.get("priority") or 0))
    executed = {}
    for a in auto:
        db.update_action(a["action_id"], status="EXECUTING", attempts=(a["attempts"] or 0) + 1, last_attempt=time.time())
        try:
            status, result = HANDLERS[a["type"]](a)
        except Exception as e:
            status, result = "FAILED", str(e)[:300]
        extra = {}
        if status == "SUBMITTED":
            extra["next_verify_at"] = time.time() + VERIFY_SCHEDULE[0]
        elif status == "HUMAN_REQUIRED":
            # a handler (not classify()) decided this at execution time — carry its specific
            # reason into the columns the Telegram batch actually reads, instead of the generic
            # "see control center" fallback.
            extra["human_required_reason"] = (result or "")[:200]
            extra["human_action_text"] = (result or "")[:200]
            extra["estimated_human_time"] = a.get("estimated_human_time") or 3
        elif status == "FAILED" and (a["attempts"] or 0) + 1 >= MAX_ATTEMPTS:
            status = "STALE"
        db.update_action(a["action_id"], status=status, result=(result or "")[:500], **extra)
        executed[status] = executed.get(status, 0) + 1
        if status in ("SUBMITTED", "LIVE") and a.get("asset_id"):
            with db.tx() as c:
                c.execute("UPDATE assets SET status=?, result=?, updated_ts=? WHERE asset_id=?",
                          ("live" if status == "LIVE" else "submitted", result, time.time(), a["asset_id"]))
        db.log_activity(a["type"], f"{a['action_id']} {status}: {(result or '')[:90]}", a.get("drop_id"), actor="executor")

    verified = run_verify()

    pending_human = db.q("SELECT * FROM actions WHERE status='HUMAN_REQUIRED' ORDER BY priority DESC")
    to_notify = [a for a in pending_human if _should_notify(a)]
    telegram_sent = False
    if to_notify:
        msg = _format_telegram(to_notify, executed, verified)
        if commands.notify(msg):
            telegram_sent = True
            now = time.time()
            for a in to_notify:
                db.update_action(a["action_id"], telegram_notified_ts=now)
            db.log_telegram_batch(len(to_notify), sum((a.get("estimated_human_time") or 3) for a in to_notify), [a["action_id"] for a in to_notify])

    summary = f"discovered={discovered} executed={executed} verified={verified} human_pending={len(pending_human)} telegram_sent={telegram_sent}"
    db.record_run("executor", "ok", summary)
    return {
        "discovered": discovered, "executed": executed, "verified": verified,
        "newly_human": newly_human, "human_pending": len(pending_human), "telegram_sent": telegram_sent,
        "summary": summary,
    }
