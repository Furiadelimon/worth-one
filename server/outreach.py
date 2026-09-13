"""Outreach sender for newsletters / publishers / directories that accept email.

Inactive until a project mailbox exists: set WORTH_SMTP_HOST, WORTH_SMTP_PORT, WORTH_SMTP_USER, WORTH_SMTP_PASS,
WORTH_FROM in /etc/worth-one/env. Never uses a personal address.

Sender decision (2026-09-13, explicit owner override): hello@wordsbeforecoffee.com is the single authorized
sender for BOTH Worth One and Words Before Coffee. Brand is read from the asset's drop_id ("WBC" -> Words
Before Coffee; anything else -> Worth One). Worth One mail is never sent as if Worth One were its own company:
the From display name and the signature both say it is "another small project from the maker of Words Before
Coffee" — no invented staff, no separate identity. Reply-To is always the same real address.

Rules enforced here: one message per contact address, ever — across BOTH brands, not just per asset (tracked in
assets.submitted_ts, checked here against every asset regardless of which one is being sent); no bulk; plain
text; honest subject. Daily volume is capped per-brand in executor.classify(), not here.
"""
import os
import smtplib
import time
from email.message import EmailMessage
from email.utils import formatdate, make_msgid, formataddr, parseaddr

import db

BRAND_SIGNATURES = {
    "worth_one": (
        "Worth One (via Words Before Coffee)",
        "Worth One -- another small project from the maker of Words Before Coffee.\nhttps://furiadelimon.github.io/worth-one/\n",
    ),
    "wbc": (
        "Words Before Coffee",
        "Words Before Coffee\nhttps://wordsbeforecoffee.com/\n",
    ),
}


def brand_of(asset):
    return "wbc" if (asset or {}).get("drop_id") == "WBC" else "worth_one"


def configured():
    return all(os.environ.get(k) for k in ("WORTH_SMTP_HOST", "WORTH_SMTP_USER", "WORTH_SMTP_PASS", "WORTH_FROM"))


def send(asset_id, dry_run=False):
    a = db.q1("SELECT * FROM assets WHERE asset_id=?", (asset_id,))
    if not a:
        raise ValueError("unknown asset")
    if a["submitted_ts"]:
        return "already contacted; one message per contact, ever"
    if not a["contact"] or "@" not in a["contact"]:
        return "no email contact on record"
    # never email the same address twice, even across the other brand or a different target
    dup = db.q1("SELECT asset_id, name FROM assets WHERE contact=? AND submitted_ts IS NOT NULL AND asset_id!=?",
                (a["contact"], asset_id))
    if dup:
        return f"already contacted this address via {dup['asset_id']} ({dup['name']}); one message per contact, ever"
    if not a["pitch"]:
        return "no pitch on record"
    if not configured():
        db.add_human_action("Create the project mailbox (hello@) so outreach can send itself",
                            "A dedicated address for WORTH ONE? (never a personal one). Put SMTP host/user/pass and WORTH_FROM in /etc/worth-one/env. "
                            f"{db.q1('SELECT COUNT(*) n FROM assets WHERE contact LIKE ? AND submitted_ts IS NULL', ('%@%',))['n']} pitches are ready to go.")
        return "smtp not configured; marked ACCESS REQUIRED"
    display_name, footer = BRAND_SIGNATURES[brand_of(a)]
    _, addr = parseaddr(os.environ["WORTH_FROM"])
    addr = addr or os.environ["WORTH_FROM"]
    subject, _, body = a["pitch"].partition("\n")
    msg = EmailMessage()
    msg["From"] = formataddr((display_name, addr))
    msg["To"] = a["contact"]
    msg["Subject"] = subject.replace("Subject:", "").strip()[:120]
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="wordsbeforecoffee.com")
    msg["Reply-To"] = addr
    msg.set_content(body.strip() + "\n\n-- \n" + footer)
    if dry_run:
        return msg.as_string()
    with smtplib.SMTP(os.environ["WORTH_SMTP_HOST"], int(os.environ.get("WORTH_SMTP_PORT", "587")), timeout=20) as s:
        s.starttls()
        s.login(os.environ["WORTH_SMTP_USER"], os.environ["WORTH_SMTP_PASS"])
        s.send_message(msg)
    with db.tx() as c:
        c.execute("UPDATE assets SET status='submitted', submitted_ts=?, updated_ts=? WHERE asset_id=?", (time.time(), time.time(), asset_id))
    db.log_activity("outreach", f"Contacted {a['type']} {a['name']} ({a['contact']})", a["drop_id"], actor="agent")
    return "sent"


def batch(limit=3, dry_run=False, brand=None):
    """Send up to `limit` prepared pitches that have an email contact. Called daily. One message per contact, ever.
    `brand`, if given ("worth_one" or "wbc"), restricts the batch to that project."""
    where = "status='prepared' AND contact LIKE '%@%' AND pitch IS NOT NULL AND pitch!='' AND submitted_ts IS NULL"
    if brand == "wbc":
        where += " AND drop_id='WBC'"
    elif brand == "worth_one":
        where += " AND (drop_id IS NULL OR drop_id!='WBC')"
    rows = db.q(f"SELECT asset_id, name FROM assets WHERE {where} ORDER BY created_ts LIMIT ?", (limit,))
    out = []
    for r in rows:
        out.append(f"{r['asset_id']} {r['name'][:40]}: {send(r['asset_id'], dry_run=dry_run)[:60]}")
    return out or ["nothing to send"]
