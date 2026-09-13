"""INGEST — turns distribution_targets.json (Fable's verified research) into assets rows.

Deterministic transform, no model calls. Idempotent: matches existing assets by normalized name/url
before creating a new one, so re-running after a research refresh never duplicates rows.

Sender rule: Worth One has no configured mailbox of its own — outreach.py currently sends only as
hello@wordsbeforecoffee.com (Words Before Coffee's own domain). Every row that would otherwise auto-send
email gets tagged with a `notes` value starting "WAITING_WORTH_ONE_SENDER" instead of a live pitch;
executor.classify() reads that marker and blocks the send with an honest, specific reason until Pedro
configures a real Worth One address.

Run: `worthctl ingest_targets ../distribution_targets.json`
"""
import json
import os
import re
import time

import db

BASE = "https://furiadelimon.github.io/worth-one"
DROP_SLUG = {"DROP-001": "doomscroll-receipt", "DROP-002": "subscription-receipt"}

SENDER_NOTE = ("WAITING_WORTH_ONE_SENDER: outreach.py currently sends only as hello@wordsbeforecoffee.com "
               "(Words Before Coffee's own domain, not Worth One's). ")

# ---------------- pitch templates (short, honest, no hype; V3 voice: no "help us", no car) ----------------

_PRESS = {
    "en": "Hi,\n\n{why}\n\n{angle}\n\nIf it's a fit, here it is: {link}\n\nNo pressure either way — thanks for reading.\nWorth One?",
    "es": "Hola,\n\n{why}\n\n{angle}\n\nSi encaja, aquí está: {link}\n\nSin ninguna prisa, gracias por leer.\nWorth One?",
    "pt": "Olá,\n\n{why}\n\n{angle}\n\nSe fizer sentido, aqui está: {link}\n\nSem pressa nenhuma, obrigado pela leitura.\nWorth One?",
    "fr": "Bonjour,\n\n{why}\n\n{angle}\n\nSi ça convient, voici le lien : {link}\n\nAucune urgence, merci de votre lecture.\nWorth One?",
    "de": "Hallo,\n\n{why}\n\n{angle}\n\nFalls es passt, hier der Link: {link}\n\nKeine Eile, danke fürs Lesen.\nWorth One?",
}
_EDU = {
    "en": "Hi,\n\n{why}\n\n{angle} No signup, no ads, no medical claims — just a five-minute discussion starter.\n\n{link}\n\nHappy to answer anything.\nWorth One?",
    "es": "Hola,\n\n{why}\n\n{angle} Sin registro, sin anuncios, sin afirmaciones médicas: solo un punto de partida de cinco minutos.\n\n{link}\n\nEncantado de responder cualquier duda.\nWorth One?",
    "pt": "Olá,\n\n{why}\n\n{angle} Sem registo, sem anúncios, sem alegações médicas: só um ponto de partida de cinco minutos.\n\n{link}\n\nTerei todo o gosto em responder a qualquer dúvida.\nWorth One?",
    "fr": "Bonjour,\n\n{why}\n\n{angle} Sans inscription, sans publicité, sans allégation médicale : juste un point de départ de cinq minutes.\n\n{link}\n\nAvec plaisir pour toute question.\nWorth One?",
    "de": "Hallo,\n\n{why}\n\n{angle} Keine Anmeldung, keine Werbung, keine medizinischen Aussagen — nur ein Fünf-Minuten-Gesprächsanlass.\n\n{link}\n\nGerne stehe ich für Fragen zur Verfügung.\nWorth One?",
}
_EMBED = {
    "en": "Hi,\n\n{why}\n\n{angle}\n\nOne line of code (iframe), readers never leave the page: {link}\n\nHappy to send the exact snippet if useful.\nWorth One?",
    "es": "Hola,\n\n{why}\n\n{angle}\n\nUna línea de código (iframe), sin sacar al lector de la página: {link}\n\nEncantado de enviar el fragmento exacto si es útil.\nWorth One?",
    "pt": "Olá,\n\n{why}\n\n{angle}\n\nUma linha de código (iframe), sem tirar o leitor da página: {link}\n\nTerei todo o gosto em enviar o excerto exato, se for útil.\nWorth One?",
    "fr": "Bonjour,\n\n{why}\n\n{angle}\n\nUne ligne de code (iframe), sans faire quitter la page au lecteur : {link}\n\nAvec plaisir pour l'extrait exact si utile.\nWorth One?",
    "de": "Hallo,\n\n{why}\n\n{angle}\n\nEine Zeile Code (iframe), ohne die Leser die Seite verlassen zu lassen: {link}\n\nGerne schicke ich das genaue Snippet, falls hilfreich.\nWorth One?",
}
_SUBJECT = {
    "en": "A small free tool — {name}",
    "es": "Una pequeña herramienta gratuita — {name}",
    "pt": "Uma pequena ferramenta gratuita — {name}",
    "fr": "Un petit outil gratuit — {name}",
    "de": "Ein kleines kostenloses Tool — {name}",
}


def _link(drop_id, lang):
    slug = DROP_SLUG.get(drop_id, "")
    prefix = f"{BASE}/es" if lang == "es" and slug else BASE
    if not slug:
        return BASE
    return f"{prefix}/drops/{slug}/"


def build_pitch(row):
    lang = row.get("language") if row.get("language") in _PRESS else "en"
    cluster = row.get("campaign_cluster") or ""
    table = _EDU if cluster.startswith("EDU") else _EMBED if row.get("type") == "embed" or "embed" in (row.get("pitch_angle") or "").lower() else _PRESS
    why = (row.get("why_fit") or "").strip()
    angle = (row.get("pitch_angle") or "").strip()
    link = _link(row.get("drop_id"), lang) + f"?src={_slug(row['name'])}"
    body = table[lang].format(why=why, angle=angle, link=link)
    subject = _SUBJECT[lang].format(name=row["name"])
    return subject + "\n" + body


def _slug(name):
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s[:40]


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _host(url):
    m = re.match(r"https?://(?:www\.)?([^/]+)", url or "")
    return m.group(1).lower() if m else ""


def _urlkey(url):
    """Normalized scheme+host+path, no query/fragment/trailing-slash — precise enough that two
    different pages on a multi-tenant host (e.g. github.com/a/... vs github.com/b/...) never collide,
    unlike a bare-host key would."""
    if not url:
        return ""
    u = re.sub(r"^https?://(?:www\.)?", "", url).split("?")[0].split("#")[0].rstrip("/")
    return u.lower()


def _existing_index():
    """name/url -> asset_id, for already-tracked assets (avoid duplicating pre-existing rows)."""
    idx = {}
    for a in db.q("SELECT asset_id, name, url FROM assets"):
        idx[_norm(a["name"])] = a["asset_id"]
        uk = _urlkey(a["url"])
        if uk:
            idx.setdefault("url:" + uk, a["asset_id"])
    return idx


def _seed_counters():
    """Start each cluster's counter above the highest suffix already in the DB, so a re-run can
    never generate an id that collides with (and silently overwrites, via upsert_asset) an
    unrelated existing row — counters must never restart from zero once anything has been created."""
    counters = {}
    for a in db.q("SELECT asset_id FROM assets WHERE asset_id LIKE 'AST-%'"):
        m = re.match(r"AST-([A-Z0-9]+)-(\d+)$", a["asset_id"])
        if m:
            tag, n = m.group(1), int(m.group(2))
            counters[tag] = max(counters.get(tag, 0), n)
    return counters


def _next_id(cluster, counters):
    tag = re.sub(r"[^A-Za-z0-9]", "", cluster or "MISC").upper()[:8]
    counters[tag] = counters.get(tag, 0) + 1
    return f"AST-{tag}-{counters[tag]:03d}"


def transform(row, counters, idx):
    """Return (asset_dict, human_note) or None to skip. Never overwrites an already-tracked target."""
    name, url = row["name"], row.get("relevant_page") or row.get("submission_url") or row.get("url")
    key = _norm(name)
    ukey = "url:" + _urlkey(row.get("submission_url") or row.get("url") or "")
    if key in idx or (ukey != "url:" and ukey in idx):
        return None, f"already tracked as {idx.get(key) or idx.get(ukey)}"

    if row.get("tier") == "REJECT":
        return None, "rejected in research, not ingested"

    method = row.get("method") or "none"
    tier = row.get("tier")
    if tier == "C" and not row.get("contact") and not row.get("submission_url"):
        return None, "tier C, no verified route — kept as a lead only"

    asset_id = _next_id(row.get("campaign_cluster"), counters)
    d = {"asset_id": asset_id, "type": row.get("type") or "directory", "name": name,
         "url": row.get("submission_url") or url, "drop_id": row.get("drop_id") or "DROP-001",
         "why": (row.get("why_fit") or "")[:500], "pitch": None, "contact": None,
         "submitted_ts": None, "result": None, "notes": None}

    if method == "email" and row.get("contact"):
        d["status"] = "prepared"
        d["contact"] = row["contact"]
        d["pitch"] = build_pitch(row)
        d["url"] = url  # the article/page, so a later verify can look for our link on it
        d["notes"] = SENDER_NOTE + (row.get("pitch_angle") or "")[:300]
    elif method in ("form_submit", "contact_form"):
        d["status"] = "prepared"
        host = _host(d["url"])
        has_recipe = host in ("theforest.link", "nosignuptools.com", "shouldseethis.com")
        if row.get("login_required") or row.get("captcha"):
            d["notes"] = (f"login required, " if row.get("login_required") else "") + \
                         (f"captcha present, " if row.get("captcha") else "") + \
                         f"open {d['url']} and submit by hand: {(row.get('pitch_angle') or '')[:200]}"
        elif not has_recipe:
            d["notes"] = f"no tested form recipe yet — open {d['url']} and submit by hand: {(row.get('pitch_angle') or '')[:200]}"
        # else: leave notes empty; classify() will route it to form_submit once an action exists
        # and ingest_actions() attaches the drop-specific payload for the known recipe hosts.
    elif method in ("login_form", "github_pr"):
        d["status"] = "access_required"
        d["notes"] = ("GitHub PR requires a public GitHub identity — HUMAN_GITHUB_ACTION_REQUIRED. "
                       if method == "github_pr" else f"requires creating an account at {d['url']}. ") + \
                      (row.get("pitch_angle") or "")[:200]
    else:
        return None, f"no automatable or human route recorded (method={method})"

    return d, None


# payload for the three hosts with a real FORM_RECIPES entry, keyed by (host, drop_id)
_RECIPE_PAYLOADS = {
    ("theforest.link", "DROP-001"): lambda link: {"target_url": link},
    ("theforest.link", "DROP-002"): lambda link: {"target_url": link},
    ("nosignuptools.com", "DROP-001"): lambda link: {
        "target_url": link, "site_name": "Doomscroll Receipt",
        "short_desc": "Type your daily scrolling time, get a receipt: per year, per decade, days of your life.",
        "long_desc": "A free calculator that turns how long you scroll each day into a printed-receipt style breakdown — per year, over a decade, in days of your life. No signup, no ads, no account. Made by one person.",
        "category": "productivity", "tags": ["No Ads", "Mobile Friendly"], "submitter_name": "Worth One?",
    },
    ("nosignuptools.com", "DROP-002"): lambda link: {
        "target_url": link, "site_name": "Subscription Lifetime Receipt",
        "short_desc": "Type a monthly subscription price, see what it really costs over 1/5/10 years.",
        "long_desc": "A free calculator that turns a monthly subscription price into its true cost over one, five and ten years. No signup, no ads, no account. Made by one person.",
        "category": "math-stem", "tags": ["No Ads", "Mobile Friendly"], "submitter_name": "Worth One?",
    },
    ("shouldseethis.com", "DROP-001"): lambda link: {
        "target_url": link, "site_name": "Doomscroll Receipt", "category": "USEFUL",
        "what_it_does": "Type your daily scrolling time and get a receipt: days, months and years of your life, over a decade.",
        "why_awesome": "It turns a vague feeling about screen time into one concrete, shareable number. Free, no signup, no ads, made by one person.",
        "submitter_name": "Worth One?",
    },
    ("shouldseethis.com", "DROP-002"): lambda link: {
        "target_url": link, "site_name": "Subscription Lifetime Receipt", "category": "USEFUL",
        "what_it_does": "Type a monthly subscription price and see the real cost over one, five and ten years.",
        "why_awesome": "€14.99/month doesn't look like much until it's €1,799 over ten years. Free, no signup, no ads, made by one person.",
        "submitter_name": "Worth One?",
    },
}


def attach_recipe_payloads():
    """After sync_from_assets() has created ACT-<asset_id> rows, give the three recipe hosts their content."""
    attached = 0
    for a in db.q("SELECT * FROM assets WHERE status='prepared'"):
        host = _host(a["url"])
        key = (host, a["drop_id"])
        if key in _RECIPE_PAYLOADS:
            action_id = "ACT-" + a["asset_id"]
            row = db.q1("SELECT action_id FROM actions WHERE action_id=?", (action_id,))
            if row:
                link = a["url"]
                payload = _RECIPE_PAYLOADS[key](link)
                db.update_action(action_id, payload=json.dumps(payload))
                attached += 1
    return attached


def run(path):
    rows = json.load(open(path, encoding="utf-8"))["targets"]
    idx = _existing_index()
    counters = _seed_counters()
    created, skipped = 0, {}
    for row in rows:
        d, skip_reason = transform(row, counters, idx)
        if d is None:
            skipped[skip_reason] = skipped.get(skip_reason, 0) + 1
            continue
        db.upsert_asset(d)
        idx[_norm(d["name"])] = d["asset_id"]
        uk = _urlkey(d["url"])
        if uk:
            idx["url:" + uk] = d["asset_id"]
        created += 1
    return {"created": created, "skipped": skipped, "total_rows": len(rows)}
