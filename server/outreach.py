"""Outreach sender for newsletters / publishers / directories that accept email.

Inactive until a project mailbox exists: set WORTH_SMTP_HOST, WORTH_SMTP_PORT, WORTH_SMTP_USER, WORTH_SMTP_PASS,
WORTH_FROM ("Worth One? <hello@...>") in /etc/worth-one/env. Never uses a personal address.

Rules enforced here: one message per contact, ever (tracked in assets.submitted_ts); no bulk; plain text; honest subject.
"""
import os
import smtplib
import time
from email.message import EmailMessage

import db


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
    if not a["pitch"]:
        return "no pitch on record"
    if not configured():
        db.add_human_action("Create the project mailbox (hello@) so outreach can send itself",
                            "A dedicated address for WORTH ONE? (never a personal one). Put SMTP host/user/pass and WORTH_FROM in /etc/worth-one/env. "
                            f"{db.q1('SELECT COUNT(*) n FROM assets WHERE contact LIKE ? AND submitted_ts IS NULL', ('%@%',))['n']} pitches are ready to go.")
        return "smtp not configured; marked ACCESS REQUIRED"
    subject, _, body = a["pitch"].partition("\n")
    msg = EmailMessage()
    msg["From"] = os.environ["WORTH_FROM"]
    msg["To"] = a["contact"]
    msg["Subject"] = subject.replace("Subject:", "").strip()[:120]
    msg.set_content(body.strip() + "\n\n-- \nWORTH ONE?  https://furiadelimon.github.io/worth-one/\nAn independent internet experiment run by one person with autonomous software.\n")
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
