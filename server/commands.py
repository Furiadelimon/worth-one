"""Human override commands (the owner keeps absolute control) + notifications.

PAUSE ALL / RESUME ALL
PAUSE DROP <id> / RESUME DROP <id> / KILL DROP <id> / SCALE DROP <id>
PAUSE CHANNEL <name> / RESUME CHANNEL <name> / BLOCK CHANNEL <name> / UNBLOCK CHANNEL <name>
BLOCK COUNTRY <CC> / UNBLOCK COUNTRY <CC>
CHANGE CAR TARGET <eur>
CHANGE PRIORITY <text>
ENABLE PAYMENTS / DISABLE PAYMENTS
SET REAL CONTRIBUTIONS <eur>   (only for money actually received; never intent)
"""
import json
import os
import urllib.request

import db

DROP_STATES = {"IDEA", "BUILDING", "TESTING", "LIVE", "GROWING", "VIRAL", "PAUSED", "KILLED"}


def _list(key):
    try:
        return json.loads(db.get_setting(key, "[]"))
    except Exception:
        return []


def _set_list(key, items):
    db.set_setting(key, json.dumps(sorted(set(items))))


def set_drop_status(drop_id, status):
    if status not in DROP_STATES:
        raise ValueError("bad status")
    r = db.q1("SELECT drop_id FROM drops WHERE drop_id=?", (drop_id,))
    if not r:
        raise ValueError(f"unknown drop {drop_id}")
    with db.tx() as c:
        c.execute("UPDATE drops SET status=?, updated_ts=strftime('%s','now') WHERE drop_id=?", (status, drop_id))


def run(cmd, arg="", actor="system"):
    cmd = cmd.upper().replace("_", " ").strip()
    arg = arg.strip()
    msg = None
    if cmd == "PAUSE ALL":
        db.set_setting("PROJECT_STATUS", "PAUSED"); msg = "Everything paused. Only the site stays online."
    elif cmd == "RESUME ALL":
        db.set_setting("PROJECT_STATUS", "ACTIVE"); msg = "Project resumed."
    elif cmd in ("PAUSE DROP", "RESUME DROP", "KILL DROP", "SCALE DROP"):
        st = {"PAUSE DROP": "PAUSED", "RESUME DROP": "LIVE", "KILL DROP": "KILLED", "SCALE DROP": "GROWING"}[cmd]
        set_drop_status(arg.upper(), st); msg = f"{arg.upper()} -> {st}"
        if cmd == "SCALE DROP":
            db.set_setting("PRIORITY", arg.upper())
    elif cmd in ("PAUSE CHANNEL", "RESUME CHANNEL"):
        l = _list("PAUSED_CHANNELS"); a = arg.lower()
        if cmd == "PAUSE CHANNEL":
            l.append(a)
        elif a in l:
            l.remove(a)
        _set_list("PAUSED_CHANNELS", l); msg = f"paused channels: {l}"
    elif cmd in ("BLOCK CHANNEL", "UNBLOCK CHANNEL"):
        l = _list("BLOCKED_CHANNELS"); a = arg.lower()
        if cmd == "BLOCK CHANNEL":
            l.append(a)
        elif a in l:
            l.remove(a)
        _set_list("BLOCKED_CHANNELS", l); msg = f"blocked channels: {l}"
    elif cmd in ("BLOCK COUNTRY", "UNBLOCK COUNTRY"):
        l = _list("BLOCKED_COUNTRIES"); a = arg.upper()[:2]
        if cmd == "BLOCK COUNTRY":
            l.append(a)
        elif a in l:
            l.remove(a)
        _set_list("BLOCKED_COUNTRIES", l); msg = f"blocked countries: {l}"
    elif cmd == "CHANGE CAR TARGET":
        v = float(arg); db.set_setting("CAR_TARGET", v); msg = f"CAR_TARGET = {v:.0f} EUR"
    elif cmd == "CHANGE PRIORITY":
        db.set_setting("PRIORITY", arg); msg = f"priority: {arg}"
    elif cmd == "ENABLE PAYMENTS":
        db.set_setting("PAYMENTS_ENABLED", "true"); msg = "PAYMENTS_ENABLED=true (real payment provider must be configured on the site)"
    elif cmd == "DISABLE PAYMENTS":
        db.set_setting("PAYMENTS_ENABLED", "false"); msg = "PAYMENTS_ENABLED=false"
    elif cmd == "SET REAL CONTRIBUTIONS":
        v = float(arg); db.set_setting("REAL_CONTRIBUTIONS", v); msg = f"REAL_CONTRIBUTIONS = {v:.2f} EUR (money actually received)"
    elif cmd == "SET CURRENT ACTION":
        db.set_setting("CURRENT_ACTION", arg); msg = arg
    elif cmd == "SET NEXT ACTION":
        db.set_setting("NEXT_ACTION", arg); msg = arg
    elif cmd == "RESOLVE ACTION":
        db.resolve_human_action(int(arg)); msg = f"human action {arg} resolved"
    elif cmd == "SET":
        k, _, v = arg.partition("=")
        db.set_setting(k.strip().upper(), v.strip()); msg = f"{k.strip().upper()}={v.strip()}"
    else:
        raise ValueError(f"unknown command: {cmd}")
    db.log_activity("control", f"{cmd} {arg}".strip() + (f" -> {msg}" if msg else ""), actor=actor)
    return msg


def notify(text):
    """Push a message to the owner: Telegram bot (WORTH_TG_TOKEN + WORTH_TG_CHAT) and/or ntfy.sh (WORTH_NTFY_TOPIC)."""
    sent = False
    tok, chat = os.environ.get("WORTH_TG_TOKEN"), os.environ.get("WORTH_TG_CHAT")
    if tok and chat:
        try:
            data = json.dumps({"chat_id": chat, "text": "WORTH ONE?\n" + text[:3800], "disable_web_page_preview": True}).encode("utf-8")
            req = urllib.request.Request(f"https://api.telegram.org/bot{tok}/sendMessage", data=data, headers={"Content-Type": "application/json"})
            urllib.request.urlopen(req, timeout=10)
            sent = True
        except Exception:
            pass
    topic = os.environ.get("WORTH_NTFY_TOPIC")
    if topic:
        try:
            req = urllib.request.Request(f"https://ntfy.sh/{topic}", data=text.encode("utf-8"), headers={"Title": "Worth One"})
            urllib.request.urlopen(req, timeout=8)
            sent = True
        except Exception:
            pass
    return sent
