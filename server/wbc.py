"""Words Before Coffee - the product this growth engine works for.

Reads the first-party growth metrics that the WBC app exposes on the LAN (`/api/growth`, token-protected,
see app/growth.py in the WordsBeforeCoffee repo), keeps hourly snapshots so history and "users generated"
deltas survive restarts, and attributes users to the expansion assets that carry a `?src=` tag.

No model calls here. Everything is SQL and one HTTP request.
"""
import json
import os
import re
import time
import urllib.error
import urllib.request

import db

GROWTH_URL = os.environ.get("WBC_GROWTH_URL", "http://192.168.1.117/api/growth")
GROWTH_TOKEN = os.environ.get("WBC_GROWTH_TOKEN", "")
SITE = "https://wordsbeforecoffee.com"
GAME_NAMES = {"words": "Words Before Coffee", "slide": "Word Slide", "search": "Word Search", "memory": "Memory"}
GAME_PATHS = {"words": "/words-before-coffee", "slide": "/word-slide", "search": "/word-search", "memory": "/word-memory"}

_cache = {"ts": 0, "data": None}


def configured():
    return bool(GROWTH_TOKEN)


def fetch(timeout=25):
    if not GROWTH_TOKEN:
        raise RuntimeError("WBC_GROWTH_TOKEN not set")
    req = urllib.request.Request(GROWTH_URL, headers={"X-Growth-Token": GROWTH_TOKEN, "Host": "wordsbeforecoffee.com", "User-Agent": "wbc-growth-engine/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def snapshot():
    """Fetch and persist (at most one row per hour). Returns the metrics or raises."""
    data = fetch()
    now = time.time()
    last = db.q1("SELECT ts FROM wbc_snapshots ORDER BY ts DESC LIMIT 1")
    if not last or now - last["ts"] >= 3500:
        with db.tx() as c:
            c.execute("INSERT INTO wbc_snapshots(ts, day, data) VALUES(?,?,?)", (now, db.day_of(now), json.dumps(data)))
    _cache.update(ts=now, data=data)
    return data


def latest(max_age=600):
    """Fresh metrics if possible, else the last stored snapshot marked stale. Never raises."""
    if _cache["data"] and time.time() - _cache["ts"] < max_age:
        return _cache["data"]
    try:
        return snapshot()
    except Exception as e:  # noqa: BLE001
        row = db.q1("SELECT ts, data FROM wbc_snapshots ORDER BY ts DESC LIMIT 1")
        if row:
            d = json.loads(row["data"])
            d["stale"] = True
            d["stale_since"] = row["ts"]
            d["error"] = str(e)[:200]
            return d
        return {"stale": True, "error": str(e)[:200], "windows": {}, "dau": [], "games": {"7d": [], "30d": []},
                "acquisition": {"7d": [], "30d": []}, "countries": {"7d": [], "30d": []}, "retention": {}, "shares": {}, "referral_users": {}}


def snapshot_at(age_seconds):
    """The stored snapshot closest to `age_seconds` ago (for users-generated deltas)."""
    target = time.time() - age_seconds
    row = db.q1("SELECT ts, data FROM wbc_snapshots WHERE ts <= ? ORDER BY ts DESC LIMIT 1", (target,))
    return (json.loads(row["data"]), row["ts"]) if row else (None, None)


def users_generated(days):
    """New WBC users in the window, from the live metrics (falls back to snapshot deltas)."""
    m = latest()
    w = (m.get("windows") or {})
    key = {1: "24h", 7: "7d", 30: "30d"}.get(days)
    if key and w.get(key):
        return w[key].get("new_users", 0)
    return 0


def game_verdicts(m=None):
    """BEST GAME / FASTEST GROWING / BEST RETENTION / BEST ACQUISITION / BEST SHARE RATE, from the metrics."""
    m = m or latest()
    g7 = {g["game"]: g for g in (m.get("games") or {}).get("7d", [])}
    g30 = {g["game"]: g for g in (m.get("games") or {}).get("30d", [])}
    if not g30:
        return {}
    def pick(rows, key):
        best = max(rows.values(), key=lambda r: r.get(key) or 0)
        return best["game"] if (best.get(key) or 0) > 0 else None
    growth = {}
    for g, r in g7.items():
        prev = (g30.get(g, {}).get("games_played", 0) - r.get("games_played", 0)) / 23.0 * 7  # avg of the previous 23 days, scaled to 7
        growth[g] = r.get("games_played", 0) - prev
    fastest = max(growth, key=growth.get) if growth else None
    return {
        "best_game": pick(g30, "games_played"),
        "fastest_growing_game": fastest if fastest and growth[fastest] > 0 else None,
        "best_retention_game": pick(g30, "repeat_rate"),
        "best_acquisition_game": pick(g30, "users"),
        "best_share_rate_game": pick(g30, "share_rate"),
    }


# ---------------- attribution: which assets actually produced players ----------------

def src_tag_of(asset):
    """The ?src= tag an asset's outbound link carries (set at ingest/pitch time)."""
    if asset.get("src_tag"):
        return asset["src_tag"]
    for field in ("pitch", "notes", "url"):
        m = re.search(r"[?&]src=([A-Za-z0-9_.:-]+)", asset.get(field) or "")
        if m:
            return m.group(1)
    return None


def attribute(m=None):
    """Write 'N users (7d) / M users (30d)' into assets.result for every WBC asset whose src tag shows up
    in acquisition, and return the winners (>= 5 users in 30d)."""
    m = m or latest()
    by_src_7 = {r["source"]: r for r in (m.get("acquisition") or {}).get("7d", [])}
    by_src_30 = {r["source"]: r for r in (m.get("acquisition") or {}).get("30d", [])}
    winners = []
    for a in db.q("SELECT * FROM assets WHERE drop_id='WBC'"):
        tag = src_tag_of(a)
        if not tag:
            continue
        r7, r30 = by_src_7.get(tag), by_src_30.get(tag)
        u7, u30 = (r7 or {}).get("users", 0), (r30 or {}).get("users", 0)
        if not (u7 or u30):
            continue
        conv = (r30 or {}).get("conversion", 0)
        result = f"{u7} users 7d / {u30} users 30d, conversion {conv:.0%}"
        if (a.get("result") or "") != result:
            with db.tx() as c:
                c.execute("UPDATE assets SET result=?, updated_ts=? WHERE asset_id=?", (result, time.time(), a["asset_id"]))
        if u30 >= 5:
            winners.append({"asset_id": a["asset_id"], "name": a["name"], "type": a["type"], "users_30d": u30, "users_7d": u7, "conversion": conv, "src": tag})
    winners.sort(key=lambda w: -w["users_30d"])
    return winners
