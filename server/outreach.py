"""Outreach for Words Before Coffee. One honest email per contact, ever, and only after every check passes.

Pipeline (owner directive 2026-09-13). If ANY check fails the target becomes DO_NOT_CONTACT / PITCH_REJECTED and
nothing is sent:

  CONTACT_POLICY_CHECK             the site's contact/about page was fetched and read (cached per domain)
  PUBLIC_CONTACT_VERIFICATION      the address we hold appears on a public page of that site
  NO_AI_OUTREACH_PROHIBITION       the site does not say it refuses AI-written / automated messages
  NO_UNSOLICITED_EMAIL_PROHIBITION the site does not say it refuses unsolicited pitches / press / submissions
  NO_DUPLICATE                     address never contacted before (either brand), domain not contacted in 30 days
  FINAL_MESSAGE_RENDER_CHECK       the message is rendered exactly as it will be sent and inspected as a whole
  NO_INTERNAL_NOTES                no research notes, scoring, "why them" fragments or template residue in the text
  NO_AGENT_INSTRUCTIONS_IN_EMAIL   no agent / model / pipeline vocabulary, no placeholders

Every attempt is written to email_log with the rendered message and the check results, so a complaint can be
traced to the exact text that went out. Worth One is archived: its assets are never sent from here.

Sender: hello@wordsbeforecoffee.com (WORTH_SMTP_* / WORTH_FROM in /etc/worth-one/env), display name
"Words Before Coffee", Reply-To the same address. Plain text only.
"""
import html
import json
import os
import re
import smtplib
import time
import urllib.error
import urllib.request
from email.message import EmailMessage
from email.utils import formatdate, make_msgid, formataddr, parseaddr

import db

SITE = "https://wordsbeforecoffee.com"
FROM_NAME = "Words Before Coffee"
SIGNATURE = "Words Before Coffee\nhttps://wordsbeforecoffee.com/\n"
UA = "Mozilla/5.0 (compatible; WordsBeforeCoffee/1.0; +https://wordsbeforecoffee.com/)"

CHECKS = [
    "CONTACT_POLICY_CHECK", "PUBLIC_CONTACT_VERIFICATION", "NO_AI_OUTREACH_PROHIBITION",
    "NO_UNSOLICITED_EMAIL_PROHIBITION", "NO_DUPLICATE", "FINAL_MESSAGE_RENDER_CHECK",
    "NO_INTERNAL_NOTES", "NO_AGENT_INSTRUCTIONS_IN_EMAIL",
]

POLICY_CACHE_DAYS = 30
DOMAIN_COOLDOWN_DAYS = 30

# A real prohibition names AI/automation AND the thing refused (pitch, submission, email, message, content, outreach)
# in one breath. "No login · AI Tools" on a directory page is a category label, not a policy.
_AI_TERMS = r"(?:ai|a\.i\.|artificial intelligence|ai-generated|ai generated|chatgpt|llm|automated|bot|machine)"
_MSG_TERMS = r"(?:submissions?|pitches|emails?|messages?|content|outreach|requests?|proposals?|inquiries|mail)"
AI_FORBID = re.compile(
    rf"\bno {_AI_TERMS}[- ]?(?:generated |written |assisted |driven )?{_MSG_TERMS}\b"
    rf"|\b(?:do not|don't|won't|will not|never) (?:accept|read|respond to|consider|reply to|publish)[^.\n]{{0,30}}\b{_AI_TERMS}[- ]?(?:generated |written |assisted )?{_MSG_TERMS}\b"
    rf"|\b{_AI_TERMS}[- ]?(?:generated |written |assisted )?{_MSG_TERMS}\b[^.\n]{{0,40}}\b(?:not accepted|will be (?:ignored|deleted|rejected)|prohibited|banned|are not welcome|get rejected|are rejected)\b"
    r"|\bno (?:aceptamos|se aceptan|admitimos|leemos)\b[^.\n]{0,40}\b(?:inteligencia artificial|generad[oa]s? (?:por|con) ia|escrit[oa]s? por ia|automatizad[oa]s?|bots?)\b",
    re.I,
)
UNSOLICITED_FORBID = re.compile(
    r"\bno unsolicited\b|\bunsolicited (pitches|emails?|submissions?|press releases?|messages?)\b[^.\n]{0,60}"
    r"\b(ignored|deleted|rejected|not (accepted|read|welcome))\b|\bdo not (contact|email|send|pitch)\b|\bno pitches\b|"
    r"\bno press releases\b|\bno prs\b|\bno cold (emails?|outreach|pitches)\b|\bno spam\b[^.\n]{0,30}\bpitch|"
    r"\bno (aceptamos|se aceptan|admitimos)\b[^.\n]{0,40}\b(colaboraciones|notas de prensa|publicidad|propuestas|"
    r"sugerencias|env[ií]os|promociones)\b|\bno (enviar|env[ií]es|nos env[ií]es)\b[^.\n]{0,40}\b(notas|propuestas|"
    r"publicidad|promociones)\b|\bnot accepting (submissions|pitches|new (sites|tools|games))\b|\bsubmissions? (are )?closed\b",
    re.I,
)

# Anything that reveals machinery, research notes or template residue. Case-insensitive, on the rendered text.
INTERNAL_PATTERNS = [
    r"\bwhy (you|them|this|their audience)\b", r"\bpitch[_ ]angle\b", r"\bwhy[_ ]fit\b", r"\bexact use case\b",
    r"\bprecedent\b", r"\bWrote the\b", r"\bcovered (the|a) .{0,30}\bcategory\b", r"^\s*(same|same\.|idem)\s*$",
    r"\bnotes?:", r"\bangle:", r"\bfit:", r"\btier [abc]\b", r"\bscore(d)? \d", r"\bsub-?scores?\b",
    r"\bhuman[_ ]required\b", r"\bmanual[_ ]only\b", r"\bdo[_ ]not[_ ]contact\b", r"\bwaiting[_ ]\w+[_ ]sender\b",
    r"\bAST-[A-Z0-9-]+", r"\bACT-[A-Z0-9-]+", r"\bdrop[_ ]id\b", r"\basset[_ ]id\b", r"\bDROP-0\d\d\b",
    r"\bWorth One\b", r"\bworth-one\b", r"\bfuriadelimon\b",
    r"(?-i:\b(TODO|FIXME|TBD)\b)", r"\blorem ipsum\b", r"\bxxx+\b", r"_{3,}", r"\[[^\]]{1,40}\]", r"\{[^}]{1,40}\}", r"<[^>]{1,40}>",
    r"\bSubject:\s", r"\bAsunto:\s",
]
AGENT_PATTERNS = [
    r"\b(as an|i am an|i'm an|soy una?) (ai|a\.i\.|assistant|language model|inteligencia artificial|asistente virtual)\b",
    r"\b(claude|chatgpt|gpt-?\d|openai|anthropic|llm|large language model)\b", r"\bprompt\b", r"\binstructions?\b[^.\n]{0,20}\b(agent|model|assistant)\b",
    r"\b(executor|pipeline|payload|json|api key|control center|brain run|autonomous)\b", r"\bthe agent\b", r"\bel agente\b",
    r"\bgenerated (by|with) (ai|a model|an assistant)\b", r"\bautomated (message|email|outreach)\b", r"\bmensaje automático\b",
]
ES_WORDS = {"el", "la", "los", "las", "que", "de", "y", "para", "con", "sin", "una", "un", "en", "es", "por"}
EN_WORDS = {"the", "and", "for", "with", "without", "that", "this", "is", "are", "you", "your", "of", "to", "in", "on"}


# ---------------- policy: fetch + read the site's public contact page ----------------

def _host(url):
    m = re.match(r"https?://(?:www\.)?([^/:?#]+)", url or "")
    return m.group(1).lower() if m else ""


def _fetch(url, limit=400_000, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*;q=0.5", "Accept-Language": "es,en;q=0.8"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, resp.read(limit).decode("utf-8", "ignore")


def _text(html_src):
    t = re.sub(r"<(script|style|noscript)[^>]*>.*?</\1>", " ", html_src, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)
    return re.sub(r"[ \t\r\f\v]+", " ", t)


def _email_variants(addr):
    """The address as it may appear on a page, including common obfuscations."""
    addr = addr.lower()
    user, _, dom = addr.partition("@")
    return [addr, f"{user} at {dom}", f"{user}[at]{dom}", f"{user} [at] {dom}", f"{user}(at){dom}", f"{user} (at) {dom}",
            f"{user}&#64;{dom}", f"{user}%40{dom}", f"{user} @ {dom}"]


def policy_check(asset, force=False):
    """Fetch the target's public pages once per domain (cached), verify the address is public, and read the policy.
    Returns dict(status, public_contact, forbids_ai, forbids_unsolicited, evidence, pages)."""
    contact = (asset.get("contact") or "").strip().lower()
    host = _host(asset.get("contact_source") or asset.get("url") or "")
    if not contact or "@" not in contact or not host:
        return {"status": "no_contact", "public_contact": False, "forbids_ai": False, "forbids_unsolicited": False, "evidence": "no email or host", "pages": []}
    key = f"policy:{host}:{contact}"
    cached = None if force else db.cache_get(key, POLICY_CACHE_DAYS * 86400)
    if cached and cached["data"]:
        return cached["data"]
    candidates = []
    for u in (asset.get("contact_source"), asset.get("url")):
        if u and u not in candidates:
            candidates.append(u)
    base = f"https://{host}"
    for path in ("/contact", "/contacto", "/contact-us", "/contactar", "/about", "/sobre-nosotros", "/quienes-somos", "/acerca-de", "/about-us", "/submit", "/faq", "/"):
        if base + path not in candidates:
            candidates.append(base + path)
    result = {"status": "checked", "public_contact": False, "forbids_ai": False, "forbids_unsolicited": False, "evidence": "", "pages": []}
    variants = _email_variants(contact)
    fetched = 0
    for url in candidates[:9]:
        try:
            code, src = _fetch(url)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            result["pages"].append({"url": url, "error": f"HTTP {e.code}"})
            continue
        except Exception as e:  # noqa: BLE001
            result["pages"].append({"url": url, "error": str(e)[:80]})
            continue
        fetched += 1
        low = src.lower()
        txt = _text(src)
        found = any(v in low for v in variants) or any(v in txt.lower() for v in variants)
        page = {"url": url, "http": code, "has_contact": found}
        if found:
            result["public_contact"] = True
        m = AI_FORBID.search(txt)
        if m:
            result["forbids_ai"] = True
            result["evidence"] += f"[{url}] {txt[max(0, m.start() - 80):m.end() + 80].strip()} | "
            page["forbids_ai"] = True
        m = UNSOLICITED_FORBID.search(txt)
        if m:
            result["forbids_unsolicited"] = True
            result["evidence"] += f"[{url}] {txt[max(0, m.start() - 80):m.end() + 80].strip()} | "
            page["forbids_unsolicited"] = True
        result["pages"].append(page)
        if result["public_contact"] and len(result["pages"]) >= 3:
            break
    if fetched == 0:
        result["status"] = "unreachable"
    result["evidence"] = result["evidence"][:600]
    db.cache_set(key, result["status"], result)
    return result


# ---------------- message checks ----------------

def _sentences(text):
    return [s.strip().lower() for s in re.split(r"(?<=[.!?])\s+|\n+", text) if len(s.strip()) > 25]


def render(asset):
    """(subject, body_as_sent). The pitch is stored as 'Subject line\\n\\nbody'."""
    pitch = (asset.get("pitch") or "").replace("\r\n", "\n").strip()
    subject, _, body = pitch.partition("\n")
    subject = re.sub(r"^(subject|asunto)\s*:\s*", "", subject.strip(), flags=re.I)[:120]
    body = body.strip() + "\n\n-- \n" + SIGNATURE
    return subject, body


def message_checks(asset, subject, body):
    """FINAL_MESSAGE_RENDER_CHECK + NO_INTERNAL_NOTES + NO_AGENT_INSTRUCTIONS_IN_EMAIL on the rendered text."""
    problems = {"FINAL_MESSAGE_RENDER_CHECK": [], "NO_INTERNAL_NOTES": [], "NO_AGENT_INSTRUCTIONS_IN_EMAIL": []}
    full = subject + "\n" + body
    core = body.split("\n-- \n")[0]

    # render
    if not (10 <= len(subject) <= 90):
        problems["FINAL_MESSAGE_RENDER_CHECK"].append(f"subject length {len(subject)}")
    if "\n" in subject:
        problems["FINAL_MESSAGE_RENDER_CHECK"].append("subject has a newline")
    if not (250 <= len(core) <= 1800):
        problems["FINAL_MESSAGE_RENDER_CHECK"].append(f"body length {len(core)}")
    if "wordsbeforecoffee.com" not in core:
        problems["FINAL_MESSAGE_RENDER_CHECK"].append("no link to wordsbeforecoffee.com")
    if core.count("http") > 2:
        problems["FINAL_MESSAGE_RENDER_CHECK"].append("more than two links")
    if not re.search(r"[?&]src=[A-Za-z0-9_.:-]+", core):
        problems["FINAL_MESSAGE_RENDER_CHECK"].append("link carries no ?src= tag")
    paragraphs = [p for p in core.split("\n\n") if p.strip()]
    if len(paragraphs) < 3:
        problems["FINAL_MESSAGE_RENDER_CHECK"].append("fewer than 3 paragraphs (greeting, message, sign-off)")
    sents = _sentences(core)
    if len(sents) != len(set(sents)):
        problems["FINAL_MESSAGE_RENDER_CHECK"].append("a sentence is repeated")
    lang = (asset.get("pitch_lang") or "").lower()
    words = set(re.findall(r"[a-záéíóúñü]+", core.lower()))
    es, en = len(words & ES_WORDS), len(words & EN_WORDS)
    if lang == "es" and (es < 4 or en > es):
        problems["FINAL_MESSAGE_RENDER_CHECK"].append(f"language mismatch: expected Spanish (es={es}, en={en})")
    if lang == "en" and (en < 4 or es > en):
        problems["FINAL_MESSAGE_RENDER_CHECK"].append(f"language mismatch: expected English (es={es}, en={en})")
    if not lang:
        problems["FINAL_MESSAGE_RENDER_CHECK"].append("pitch_lang not set")
    if (asset.get("pitch_source") or "") not in ("brain", "human"):
        problems["FINAL_MESSAGE_RENDER_CHECK"].append("pitch was not authored (pitch_source must be brain or human, not a research template)")

    # internal notes: patterns + verbatim research fragments
    for pat in INTERNAL_PATTERNS:
        m = re.search(pat, full, flags=re.I | re.M)
        if m:
            problems["NO_INTERNAL_NOTES"].append(f"'{m.group(0)[:40]}' matches {pat}")
    research = " ".join((asset.get(k) or "") for k in ("why", "notes"))
    for frag in _sentences(research):
        if len(frag) > 30 and frag in core.lower():
            problems["NO_INTERNAL_NOTES"].append(f"research fragment reused verbatim: '{frag[:50]}'")

    # agent vocabulary / placeholders
    for pat in AGENT_PATTERNS:
        m = re.search(pat, full, flags=re.I)
        if m:
            problems["NO_AGENT_INSTRUCTIONS_IN_EMAIL"].append(f"'{m.group(0)[:40]}' matches {pat}")
    return {k: v for k, v in problems.items()}


def duplicate_check(asset):
    contact = (asset.get("contact") or "").strip().lower()
    dom = contact.partition("@")[2]
    problems = []
    dup = db.q1("SELECT asset_id, name FROM assets WHERE lower(contact)=? AND submitted_ts IS NOT NULL AND asset_id!=?", (contact, asset["asset_id"]))
    if dup:
        problems.append(f"address already contacted via {dup['asset_id']} ({dup['name']})")
    if db.q1("SELECT id FROM email_log WHERE lower(to_addr)=? AND status='sent'", (contact,)):
        problems.append("address already in email_log as sent")
    since = time.time() - DOMAIN_COOLDOWN_DAYS * 86400
    dom_hit = db.q1("SELECT asset_id, name FROM assets WHERE lower(contact) LIKE ? AND submitted_ts>=? AND asset_id!=?", (f"%@{dom}", since, asset["asset_id"]))
    if dom_hit and dom not in ("gmail.com", "hotmail.com", "outlook.com", "yahoo.com", "icloud.com", "protonmail.com", "proton.me"):
        problems.append(f"domain {dom} contacted in the last {DOMAIN_COOLDOWN_DAYS} days via {dom_hit['asset_id']}")
    return problems


def evaluate(asset, force_policy=False):
    """Run the whole pipeline without sending. Returns (ok, checks, subject, body)."""
    checks = {c: {"ok": True, "detail": ""} for c in CHECKS}
    if (asset.get("drop_id") or "") != "WBC":
        for c in checks.values():
            c["ok"] = False; c["detail"] = "not a Words Before Coffee target (Worth One is archived)"
        return False, checks, "", ""
    contact = (asset.get("contact") or "").strip().lower()
    if not contact or "@" not in contact:
        checks["PUBLIC_CONTACT_VERIFICATION"] = {"ok": False, "detail": "no email address on record"}
        return False, checks, "", ""
    pol = policy_check(asset, force=force_policy)
    if pol["status"] != "checked":
        checks["CONTACT_POLICY_CHECK"] = {"ok": False, "detail": f"site not readable ({pol['status']})"}
    if not pol["public_contact"]:
        checks["PUBLIC_CONTACT_VERIFICATION"] = {"ok": False, "detail": "address not found on any public page of the site"}
    if pol["forbids_ai"]:
        checks["NO_AI_OUTREACH_PROHIBITION"] = {"ok": False, "detail": pol["evidence"][:300]}
    if pol["forbids_unsolicited"]:
        checks["NO_UNSOLICITED_EMAIL_PROHIBITION"] = {"ok": False, "detail": pol["evidence"][:300]}
    dups = duplicate_check(asset)
    if dups:
        checks["NO_DUPLICATE"] = {"ok": False, "detail": "; ".join(dups)[:300]}
    subject, body = render(asset)
    for name, probs in message_checks(asset, subject, body).items():
        if probs:
            checks[name] = {"ok": False, "detail": "; ".join(probs)[:400]}
    return all(c["ok"] for c in checks.values()), checks, subject, body


def configured():
    return all(os.environ.get(k) for k in ("WORTH_SMTP_HOST", "WORTH_SMTP_USER", "WORTH_SMTP_PASS", "WORTH_FROM"))


def _mark(asset_id, status, note):
    with db.tx() as c:
        c.execute("UPDATE assets SET status=?, result=?, updated_ts=? WHERE asset_id=?", (status, note[:300], time.time(), asset_id))


def send(asset_id, dry_run=False):
    """Evaluate, then send. Returns a short status string. Every outcome is logged."""
    a = db.q1("SELECT * FROM assets WHERE asset_id=?", (asset_id,))
    if not a:
        raise ValueError("unknown asset")
    if a["submitted_ts"]:
        return "already contacted; one message per contact, ever"
    ok, checks, subject, body = evaluate(a)
    failed = [c for c, r in checks.items() if not r["ok"]]
    if not ok:
        status = "blocked:" + ",".join(failed)
        db.log_email(asset_id, a.get("contact"), subject, body, checks, status)
        if any(f in ("CONTACT_POLICY_CHECK", "PUBLIC_CONTACT_VERIFICATION", "NO_AI_OUTREACH_PROHIBITION", "NO_UNSOLICITED_EMAIL_PROHIBITION", "NO_DUPLICATE") for f in failed):
            _mark(asset_id, "do_not_contact", "DO_NOT_CONTACT: " + "; ".join(f"{f}: {checks[f]['detail'][:80]}" for f in failed))
        else:
            _mark(asset_id, "pitch_rejected", "PITCH_REJECTED: " + "; ".join(f"{f}: {checks[f]['detail'][:80]}" for f in failed))
        return status
    if not configured():
        return "smtp not configured"
    _, addr = parseaddr(os.environ["WORTH_FROM"])
    addr = addr or os.environ["WORTH_FROM"]
    msg = EmailMessage()
    msg["From"] = formataddr((FROM_NAME, addr))
    msg["To"] = a["contact"]
    msg["Subject"] = subject
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="wordsbeforecoffee.com")
    msg["Reply-To"] = addr
    msg.set_content(body)
    if dry_run:
        return msg.as_string()
    with smtplib.SMTP(os.environ["WORTH_SMTP_HOST"], int(os.environ.get("WORTH_SMTP_PORT", "587")), timeout=20) as s:
        s.starttls()
        s.login(os.environ["WORTH_SMTP_USER"], os.environ["WORTH_SMTP_PASS"])
        s.send_message(msg)
    with db.tx() as c:
        c.execute("UPDATE assets SET status='submitted', submitted_ts=?, updated_ts=? WHERE asset_id=?", (time.time(), time.time(), asset_id))
    db.log_email(asset_id, a["contact"], subject, body, checks, "sent")
    db.log_activity("outreach", f"Emailed {a['type']} {a['name']} ({a['contact']}) after all 8 checks passed", "WBC", actor="executor")
    return "sent"


def sent_today(brand="wbc"):
    start = time.time() - (time.time() % 86400)
    cond = "drop_id='WBC'" if brand == "wbc" else "(drop_id IS NULL OR drop_id!='WBC')"
    n = db.q1(f"SELECT COUNT(*) n FROM assets WHERE submitted_ts>=? AND {cond} AND contact LIKE '%@%'", (start,))["n"]
    return n


def daily_cap():
    try:
        return int(db.get_setting("WBC_EMAIL_CAP", "2"))
    except ValueError:
        return 2


def batch(limit=None, dry_run=False):
    """Send up to the daily cap of WBC pitches that pass every check. Called by the executor."""
    cap = daily_cap()
    room = cap - sent_today("wbc")
    if limit is not None:
        room = min(room, limit)
    if room <= 0:
        return ["daily cap reached"]
    rows = db.q("SELECT asset_id, name FROM assets WHERE drop_id='WBC' AND status='prepared' AND contact LIKE '%@%' AND pitch IS NOT NULL AND pitch!='' AND submitted_ts IS NULL ORDER BY created_ts LIMIT ?", (room * 4,))
    out, sent = [], 0
    for r in rows:
        if sent >= room:
            break
        res = send(r["asset_id"], dry_run=dry_run)
        out.append(f"{r['asset_id']} {r['name'][:40]}: {res[:80]}")
        if res == "sent" or (dry_run and res.startswith("From:")):
            sent += 1
    return out or ["nothing to send"]
