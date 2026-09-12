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
    target = float(s.get("CAR_TARGET", 15000))
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
