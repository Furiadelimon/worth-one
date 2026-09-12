"""Metric computations. Conventional software, no AI. Everything derived from the events table."""
import json
import time

from db import q, q1, all_settings


def _since(days):
    return time.time() - days * 86400


def counts(days=None, drop_id=None):
    where, p = ["1=1"], []
    if days:
        where.append("ts>=?"); p.append(_since(days))
    if drop_id:
        where.append("drop_id=?"); p.append(drop_id)
    w = " AND ".join(where)
    rows = q(f"SELECT type, COUNT(*) n, COUNT(DISTINCT sid) u, COALESCE(SUM(amount),0) amt FROM events WHERE {w} GROUP BY type", p)
    out = {r["type"]: {"n": r["n"], "users": r["u"], "amount": r["amt"]} for r in rows}
    def g(t, k="n"):
        return out.get(t, {}).get(k, 0)
    users = q1(f"SELECT COUNT(DISTINCT sid) u FROM events WHERE {w} AND type='page_view'", p)["u"]
    new_users = q1(f"SELECT COUNT(*) u FROM sessions WHERE first_ts>=? {'AND 1=1' if not drop_id else ''}", [_since(days) if days else 0])["u"]
    results = g("drop_result", "users")
    shares = g("share", "users")
    referral_new = q1(f"SELECT COUNT(*) u FROM sessions WHERE ref IS NOT NULL AND ref!='' AND first_ts>=?", [_since(days) if days else 0])["u"]
    share_rate = round(shares / results, 4) if results else 0.0
    referral_rate = round(referral_new / users, 4) if users else 0.0
    # K = new users generated per user (via referral links). Simple, honest estimate.
    k = round(referral_new / users, 3) if users else 0.0
    intents = q(f"SELECT amount, COUNT(*) n FROM events WHERE {w} AND type='support_intent' GROUP BY amount", p)
    intent = {"1": 0, "3": 0, "5": 0, "other": 0, "no": 0, "value": 0.0}
    for r in intents:
        a = r["amount"] or 0
        if a <= 0:
            intent["no"] += r["n"]
        else:
            key = str(int(a)) if a in (1, 3, 5) else "other"
            intent[key] += r["n"]
            intent["value"] += a * r["n"]
    ready = q1(f"SELECT COUNT(*) n FROM supporters WHERE ts>=? AND email IS NOT NULL AND email!=''", [_since(days) if days else 0])["n"]
    return {
        "page_views": g("page_view"), "users": users, "new_users": new_users,
        "drop_starts": g("drop_start", "users"), "drop_results": results, "shares": shares, "share_events": g("share"),
        "share_rate": share_rate, "referral_new_users": referral_new, "referral_rate": referral_rate, "k": k,
        "support_intent": intent, "would_support_1plus": intent["1"] + intent["3"] + intent["5"] + intent["other"],
        "intended_value": round(intent["value"], 2), "ready_to_support": ready,
        "repeat_users": q1("SELECT COUNT(*) n FROM sessions WHERE visits>1")["n"],
    }


def by_country(days=None, limit=30):
    p = [_since(days) if days else 0]
    return q("""SELECT COALESCE(NULLIF(country,''),'XX') country, COUNT(DISTINCT sid) users, COUNT(*) views,
                SUM(type='share') shares, SUM(type='support_intent' AND amount>0) intents
                FROM events WHERE ts>=? AND type IN ('page_view','share','support_intent') GROUP BY 1 ORDER BY users DESC LIMIT ?""", p + [limit])


def by_channel(days=None):
    p = [_since(days) if days else 0]
    return q("""SELECT COALESCE(NULLIF(src,''),'direct') channel, COUNT(DISTINCT sid) users, COUNT(*) views,
                SUM(type='share') shares, SUM(type='support_intent' AND amount>0) intents
                FROM events WHERE ts>=? AND type IN ('page_view','share','support_intent') GROUP BY 1 ORDER BY users DESC""", p)


def by_drop(days=None):
    p = [_since(days) if days else 0]
    rows = q("""SELECT drop_id, COUNT(DISTINCT CASE WHEN type='page_view' THEN sid END) users,
                COUNT(DISTINCT CASE WHEN type='drop_result' THEN sid END) results,
                COUNT(DISTINCT CASE WHEN type='share' THEN sid END) shares,
                SUM(type='support_intent' AND amount>0) intents, SUM(type='support_intent' AND amount<=0) no_intents,
                COALESCE(SUM(CASE WHEN type='support_intent' THEN amount END),0) intended_value
                FROM events WHERE ts>=? AND drop_id IS NOT NULL AND drop_id!='' GROUP BY drop_id ORDER BY users DESC""", p)
    for r in rows:
        r["share_rate"] = round(r["shares"] / r["results"], 3) if r["results"] else 0
        r["intent_rate"] = round(r["intents"] / r["results"], 3) if r["results"] else 0
    return rows


def daily_series(days=14):
    p = [_since(days)]
    return q("""SELECT day, COUNT(DISTINCT CASE WHEN type='page_view' THEN sid END) users, SUM(type='page_view') views,
                SUM(type='share') shares, SUM(type='support_intent' AND amount>0) intents
                FROM events WHERE ts>=? GROUP BY day ORDER BY day""", p)


def car_fund():
    s = all_settings()
    target = float(s.get("CAR_TARGET", 30000))
    real = float(s.get("REAL_CONTRIBUTIONS", 0))
    c = counts()
    return {
        "car_target": target, "real": real, "real_pct": round(100 * real / target, 2) if target else 0,
        "payments_enabled": s.get("PAYMENTS_ENABLED", "false") == "true",
        "people_worth_1plus": c["would_support_1plus"], "intended_value": c["intended_value"],
        "ready_to_support": c["ready_to_support"], "not_worth": c["support_intent"]["no"],
    }


def ai_cost(days=None):
    p = [_since(days) if days else 0]
    r = q1("SELECT COALESCE(SUM(usd),0) usd, COALESCE(SUM(input_tokens),0) i, COALESCE(SUM(output_tokens),0) o, COUNT(*) runs FROM ai_cost WHERE ts>=?", p)
    return r


def public_stats():
    c = counts()
    drops = by_drop()
    return {
        "fund": car_fund(),
        "users": c["users"], "shares": c["share_events"], "countries": len(by_country()),
        "drops": [{"drop_id": d["drop_id"], "users": d["users"], "results": d["results"], "shares": d["shares"], "intents": d["intents"]} for d in drops],
        "generated": time.time(),
    }


SEARCH_SRC = ("google", "bing", "duckduckgo", "yahoo", "yandex", "ecosia", "baidu", "naver", "search", "brave")


def _src_users(where_src, since):
    return q1("SELECT COUNT(DISTINCT sid) u FROM events WHERE type='page_view' AND ts>=? AND (" + where_src + ")", [since])["u"]


def expansion():
    """NON-SOCIAL GLOBAL EXPANSION metrics: search, referrals, embeds, assets (backlinks/directories/newsletters/publishers/press)."""
    now = time.time()
    since7, since14, since30 = now - 7 * 86400, now - 14 * 86400, now - 30 * 86400
    search_where = " OR ".join("lower(src) LIKE '%" + s + "%'" for s in SEARCH_SRC)
    seo_users = _src_users(search_where, 0)
    seo_users_7 = _src_users(search_where, since7)
    referral_users = q1("SELECT COUNT(*) u FROM sessions WHERE ref IS NOT NULL AND ref!=''")["u"]
    embed_views = q1("SELECT COUNT(*) n, COUNT(DISTINCT sid) u FROM events WHERE type='embed_view'")
    embed_hosts = q("SELECT json_extract(meta,'$.host') host, COUNT(*) n FROM events WHERE type='embed_view' GROUP BY 1 ORDER BY n DESC LIMIT 20")
    nav = q1("SELECT COUNT(*) n FROM events WHERE type='drop_nav'")["n"]
    assets = q("SELECT type, status, COUNT(*) n FROM assets GROUP BY type, status")
    by_type = {}
    for a in assets:
        by_type.setdefault(a["type"], {})[a["status"]] = a["n"]

    def cnt(t, *statuses):
        d = by_type.get(t, {})
        return sum(v for k, v in d.items() if not statuses or k in statuses)

    cur = {r["channel"]: r["users"] for r in q("SELECT COALESCE(NULLIF(src,''),'direct') channel, COUNT(DISTINCT sid) users FROM events WHERE type='page_view' AND ts>=? GROUP BY 1", [since7])}
    prev = {r["channel"]: r["users"] for r in q("SELECT COALESCE(NULLIF(src,''),'direct') channel, COUNT(DISTINCT sid) users FROM events WHERE type='page_view' AND ts>=? AND ts<? GROUP BY 1", [since14, since7])}
    top_source = max(cur.items(), key=lambda x: x[1])[0] if cur else "-"
    growth = sorted(((c, cur[c] - prev.get(c, 0)) for c in cur), key=lambda x: -x[1])
    fastest = growth[0][0] if growth and growth[0][1] > 0 else "-"
    pages = q("SELECT json_extract(meta,'$.path') path, COUNT(DISTINCT sid) users, COUNT(DISTINCT day) active_days FROM events WHERE type='page_view' AND ts>=? GROUP BY 1 ORDER BY users DESC LIMIT 15", [since30])
    best = next((p for p in pages if p["path"]), None)
    s = all_settings()
    c = counts()
    return {
        "search_impressions": None, "organic_clicks": None,
        "seo_users": seo_users, "seo_users_7d": seo_users_7,
        "referral_users": referral_users, "shares": c["share_events"], "k": c["k"],
        "backlinks": cnt("backlink", "live", "published", "accepted"), "backlinks_pending": cnt("backlink", "prepared", "submitted"),
        "directories_submitted": cnt("directory", "submitted", "accepted", "live"), "directories_listed": cnt("directory", "accepted", "live"), "directories_prepared": cnt("directory", "prepared", "access_required"),
        "embeds_views": embed_views["n"], "embeds_users": embed_views["u"], "embed_hosts": embed_hosts,
        "publishers_contacted": cnt("publisher", "submitted", "replied", "published"), "publishers_prepared": cnt("publisher", "prepared", "access_required"),
        "newsletters_contacted": cnt("newsletter", "submitted", "replied", "published"), "newsletters_prepared": cnt("newsletter", "prepared", "access_required"),
        "press_mentions": cnt("press", "published"),
        "countries": len(by_country()), "localized_pages": int(s.get("LOCALIZED_PAGES", "0") or 0),
        "drop_to_drop_clicks": nav,
        "top_source": top_source, "fastest_growing_source": fastest, "sources_7d": cur, "sources_prev7d": prev,
        "best_compounding_asset": best, "top_pages_30d": pages,
        "next_expansion_action": s.get("NEXT_EXPANSION_ACTION", ""),
    }


def compare(drop_id, json_key, value, min_n=50):
    rows = q("SELECT CAST(json_extract(meta,?) AS REAL) v FROM events WHERE type='drop_result' AND drop_id=? AND json_extract(meta,?) IS NOT NULL", [json_key, drop_id, json_key])
    vals = sorted(r["v"] for r in rows if r["v"] is not None)
    n = len(vals)
    if n < min_n:
        return {"n": n, "ready": False}
    below = sum(1 for v in vals if v < value)
    return {"n": n, "ready": True, "avg": round(sum(vals) / n, 2), "median": vals[n // 2], "pct_below": round(100 * below / n)}
