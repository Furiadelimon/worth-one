"""Metric computations. Conventional software, no AI.

Worth One metrics (events table) are kept for the archived project. `wbc_control()` builds the payload for the
WORDS BEFORE COFFEE - GROWTH CONTROL CENTER from the product's own growth API (server/wbc.py)."""
import json
import time

import db
import wbc
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
    ready = q1(f"SELECT COUNT(*) n FROM supporters WHERE ts>=? AND email IS NOT NULL AND email!='' AND status='intent'", [_since(days) if days else 0])["n"]
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


def executor_summary():
    """ACTION EXECUTOR panel: queue state, what ran today, and the standing human batch."""
    since_today = _since(1)
    counts_by_status = {r["status"]: r["n"] for r in q("SELECT status, COUNT(*) n FROM actions GROUP BY status")}
    submitted_today = q1("SELECT COUNT(*) n FROM actions WHERE status IN ('SUBMITTED','LIVE') AND last_attempt>=?", (since_today,))["n"]
    executed_today = q1("SELECT COUNT(*) n FROM actions WHERE last_attempt>=?", (since_today,))["n"]
    verified_today = q1("SELECT COUNT(*) n FROM actions WHERE status='LIVE' AND updated_ts>=?", (since_today,))["n"]
    failed_today = q1("SELECT COUNT(*) n FROM actions WHERE status IN ('FAILED','STALE') AND last_attempt>=?", (since_today,))["n"]
    outreach_today = q1("SELECT COUNT(*) n FROM actions WHERE type='email_outreach' AND status IN ('SUBMITTED','LIVE') AND last_attempt>=?", (since_today,))["n"]
    human_pending = q("""SELECT action_id, type, target, url, priority, estimated_human_time, human_action_text, human_required_reason
                          FROM actions WHERE status='HUMAN_REQUIRED' ORDER BY priority DESC LIMIT 20""")
    last_run = q1("SELECT ts, status, summary FROM runs WHERE kind='executor' ORDER BY ts DESC LIMIT 1")
    last_telegram = q1("SELECT ts, human_actions_count, estimated_minutes FROM telegram_log ORDER BY ts DESC LIMIT 1")
    recent = q("""SELECT action_id, type, target, status, attempts, result, drop_id, updated_ts
                  FROM actions ORDER BY updated_ts DESC LIMIT 40""")
    for r in recent:
        r["traffic"] = 0
        if r.get("drop_id"):
            src_like = "%" + r["action_id"].lower() + "%"
            r["traffic"] = q1("SELECT COUNT(DISTINCT sid) n FROM events WHERE type='page_view' AND drop_id=? AND lower(src) LIKE ?", (r["drop_id"], src_like))["n"]
    return {
        "queue_counts": counts_by_status,
        "today": {"executed": executed_today, "submitted": submitted_today, "verified_live": verified_today,
                   "failed": failed_today, "outreach_sent": outreach_today},
        "human_pending": human_pending,
        "human_pending_minutes": sum((h["estimated_human_time"] or 3) for h in human_pending),
        "last_run": last_run,
        "last_telegram": last_telegram,
        "recent": recent,
    }


def compare(drop_id, json_key, value, min_n=50):
    rows = q("SELECT CAST(json_extract(meta,?) AS REAL) v FROM events WHERE type='drop_result' AND drop_id=? AND json_extract(meta,?) IS NOT NULL", [json_key, drop_id, json_key])
    vals = sorted(r["v"] for r in rows if r["v"] is not None)
    n = len(vals)
    if n < min_n:
        return {"n": n, "ready": False}
    below = sum(1 for v in vals if v < value)
    return {"n": n, "ready": True, "avg": round(sum(vals) / n, 2), "median": vals[n // 2], "pct_below": round(100 * below / n)}


def winners(days=14, min_users=5):
    """DROP x CHANNEL x COUNTRY x HOOK(campaign) as separate experiments. Cheap SQL, no AI."""
    p = [_since(days)]
    rows = q("""SELECT drop_id, COALESCE(NULLIF(src,''),'direct') channel, COALESCE(NULLIF(country,''),'XX') country,
                COALESCE(NULLIF(campaign,''),'-') hook,
                COUNT(DISTINCT CASE WHEN type='page_view' THEN sid END) users,
                COUNT(DISTINCT CASE WHEN type='drop_result' THEN sid END) results,
                COUNT(DISTINCT CASE WHEN type='share' THEN sid END) sharers,
                SUM(type='support_intent' AND amount>0) intents
                FROM events WHERE ts>=? AND drop_id IS NOT NULL AND drop_id!=''
                GROUP BY 1,2,3,4 HAVING users>0 ORDER BY users DESC LIMIT 40""", p)
    ref = {r["ref"]: r["n"] for r in q("SELECT ref, COUNT(*) n FROM sessions WHERE ref IS NOT NULL AND ref!='' AND first_ts>=? GROUP BY 1", p)}
    total_ref = sum(ref.values())
    for r in rows:
        r["share_rate"] = round(r["sharers"] / r["results"], 3) if r["results"] else 0
        r["intent_rate"] = round(r["intents"] / r["results"], 3) if r["results"] else 0
        r["qualified"] = r["users"] >= min_users
        r["verdict"] = ("needs traffic" if not r["qualified"] else
                        "SCALE" if r["share_rate"] >= 0.10 or r["intent_rate"] >= 0.10 else
                        "iterate" if r["share_rate"] > 0 else "kill candidate")
    return {"experiments": rows, "referral_new_users": total_ref}


def viral_mode():
    """Thresholds from the directive: K>=1 viral scale, K>0.5 high priority, K>0.3 more resources."""
    c = counts(days=14)
    k = c["k"]; sr = c["share_rate"]
    mode = ("VIRAL SCALE" if k >= 1 else "HIGH PRIORITY" if k > 0.5 else "INCREASE RESOURCES" if k > 0.3 else "BASELINE")
    return {"k_14d": k, "share_rate_14d": sr, "mode": mode, "share_rate_alert": sr > 0.10}


def scorecard(days=1):
    """Daily growth scorecard. All deterministic; the only cost is SQL."""
    c = counts(days=days)
    e = expansion()
    cost = ai_cost(days)
    since = time.time() - days * 86400
    sent = q1("SELECT COUNT(*) n FROM assets WHERE submitted_ts>=?", (since,))["n"]
    listed = q1("SELECT COUNT(*) n FROM assets WHERE status IN ('accepted','live','published') AND updated_ts>=?", (since,))["n"]
    tiktok = q1("""SELECT COUNT(DISTINCT sid) users FROM events WHERE ts>=? AND type='page_view' AND src LIKE '%tiktok%'""", (since,))["users"]
    tt_views = q1("SELECT COALESCE(SUM(impressions),0) n FROM campaigns WHERE platform='tiktok'")["n"]
    usd = cost["usd"] or 0
    return {
        "real_users_total": counts()["users"], "new_users": c["new_users"], "users": c["users"], "views": c["page_views"],
        "results": c["drop_results"], "shares": c["share_events"], "share_rate": c["share_rate"],
        "referral_users": c["referral_new_users"], "k": c["k"], "worth1_intents": c["would_support_1plus"],
        "countries": len(by_country(days)), "seo_impressions": e["search_impressions"], "seo_clicks": e["organic_clicks"],
        "seo_users": e["seo_users_7d"], "outreach_sent": sent, "directory_listings": listed,
        "backlinks": e["backlinks"], "embed_views": e["embeds_views"],
        "tiktok_views": tt_views, "tiktok_users": tiktok,
        "ai_cost_usd": round(usd, 4), "users_per_eur_ai": round(c["users"] / (usd * 0.92), 1) if usd > 0.001 else None,
        "viral": viral_mode(),
    }


# =====================================================================================
# WORDS BEFORE COFFEE - GROWTH CONTROL CENTER
# =====================================================================================

RELEVANT_CHANNELS = ("outreach", "email_outreach", "form_submit", "verify", "learn", "seo", "brain", "lead", "directory",
                     "publisher", "press", "resource_page", "newsletter", "peer_site", "portal", "backlink", "embed",
                     "experiments", "content", "social", "product", "indexnow", "localization")
TECH_NOISE = ("SET API_URL", "SET PUBLIC_URL", "Published new API tunnel", "health", "Brain run", "in progress")


def _agent_perf(days):
    since = _since(days)
    ok = q1("SELECT COUNT(*) n FROM actions WHERE drop_id='WBC' AND status IN ('SUBMITTED','LIVE') AND last_attempt>=?", (since,))["n"]
    bad = q1("SELECT COUNT(*) n FROM actions WHERE drop_id='WBC' AND status IN ('FAILED','STALE','NO_RESPONSE','DO_NOT_CONTACT') AND last_attempt>=?", (since,))["n"]
    return ok, bad


def recent_activity(limit=40):
    """Only actions that matter to growth; technical noise grouped into one line per day."""
    rows = q("SELECT ts, channel, message, actor, drop_id FROM activity ORDER BY ts DESC LIMIT 400")
    out, tech = [], {}
    for r in rows:
        msg = r["message"] or ""
        noisy = r["channel"] in ("ops", "control") or any(t in msg for t in TECH_NOISE) or r["channel"] == "run"
        if noisy and "frozen" not in msg and "budget" not in msg.lower():
            d = db.day_of(r["ts"])
            tech[d] = tech.get(d, 0) + 1
            continue
        if r["channel"] not in RELEVANT_CHANNELS and r["actor"] not in ("executor", "owner"):
            continue
        out.append(r)
        if len(out) >= limit:
            break
    grouped = [{"ts": time.mktime(time.strptime(d, "%Y-%m-%d")), "channel": "technical", "message": f"{n} technical events (config, health, cron)", "actor": "system", "grouped": True}
               for d, n in list(tech.items())[:7]]
    return sorted(out + grouped, key=lambda r: -r["ts"])[:limit]


def wbc_control():
    m = wbc.latest()
    s = all_settings()
    now = time.time()
    verdicts = wbc.game_verdicts(m) if m.get("games") else {}
    ok24, bad24 = _agent_perf(1)
    ok7, bad7 = _agent_perf(7)
    cost = {"d1": ai_cost(1), "d30": ai_cost(30), "all": ai_cost()}
    new30 = ((m.get("windows") or {}).get("30d") or {}).get("new_users") or 0
    new1 = ((m.get("windows") or {}).get("24h") or {}).get("new_users") or 0
    new7 = ((m.get("windows") or {}).get("7d") or {}).get("new_users") or 0
    spent_today = q1("SELECT COALESCE(SUM(usd),0) usd FROM ai_cost WHERE ts>=?", (now - (now % 86400),))["usd"]
    live = q("SELECT asset_id, type, name, url, result, updated_ts FROM assets WHERE drop_id='WBC' AND status IN ('live','accepted','published') ORDER BY updated_ts DESC LIMIT 20")
    submitted = q("SELECT asset_id, type, name, url, result, updated_ts, submitted_ts FROM assets WHERE drop_id='WBC' AND status='submitted' ORDER BY COALESCE(submitted_ts, updated_ts) DESC LIMIT 20")
    new_opps = q1("SELECT COUNT(*) n FROM assets WHERE drop_id='WBC' AND status IN ('lead','prepared','needs_pitch') AND created_ts>=?", (_since(7),))["n"]
    manual = q("""SELECT a.action_id, a.target, a.url, a.human_action_text reason, a.priority, a.updated_ts, ast.type
                  FROM actions a LEFT JOIN assets ast ON ast.asset_id=a.asset_id
                  WHERE a.drop_id='WBC' AND a.status='MANUAL_ONLY' ORDER BY a.priority DESC LIMIT 40""")
    last_exec = q1("SELECT ts, status, summary FROM runs WHERE kind='executor' ORDER BY ts DESC LIMIT 1")
    last_brain = q1("SELECT ts, status, summary FROM runs WHERE kind='brain' ORDER BY ts DESC LIMIT 1")
    queue = {r["status"]: r["n"] for r in q("SELECT status, COUNT(*) n FROM actions WHERE drop_id='WBC' GROUP BY status")}
    emails = q("SELECT ts, asset_id, to_addr, subject, status, complaint FROM email_log ORDER BY ts DESC LIMIT 20")
    return {
        "now": now,
        "project": {"name": "Words Before Coffee", "site": wbc.SITE, "status": s.get("PROJECT_STATUS"), "worth_one": s.get("WORTH_ONE_STATUS", "ARCHIVED"),
                    "metrics_configured": wbc.configured(), "metrics_stale": bool(m.get("stale")), "metrics_error": m.get("error")},
        "metrics": m,
        "verdicts": verdicts,
        "expansion": {
            "current_action": s.get("CURRENT_ACTION", ""),
            "last_growth_action": s.get("LAST_GROWTH_ACTION", ""),
            "next_action": s.get("NEXT_ACTION", ""),
            "next_run": s.get("NEXT_AUTONOMOUS_RUN", ""),
            "winning_pattern": s.get("WINNING_PATTERN", ""),
            "new_opportunities": new_opps,
            "live_listings": live,
            "submitted": submitted,
            "backlinks": len(live),
            "referral_users": (m.get("referral_users") or {}),
            "queue": queue,
        },
        "agent": {
            "users_24h": new1, "users_7d": new7, "users_30d": new30,
            "ai_cost_24h": round(cost["d1"]["usd"] or 0, 4), "ai_cost_30d": round(cost["d30"]["usd"] or 0, 4), "ai_runs_30d": cost["d30"]["runs"],
            "ai_cost_per_user": round((cost["d30"]["usd"] or 0) / new30, 4) if new30 else None,
            "success_24h": ok24, "failed_24h": bad24, "success_7d": ok7, "failed_7d": bad7,
            "budget_usd": float(s.get("AI_DAILY_BUDGET_USD", "1") or 1), "spent_today": round(spent_today, 4),
            "email_cap": int(s.get("WBC_EMAIL_CAP", "2") or 2), "emails_today": q1("SELECT COUNT(*) n FROM email_log WHERE status='sent' AND ts>=?", (now - (now % 86400),))["n"],
            "clean_sends": db.clean_sends(), "clean_target": int(s.get("CLEAN_SENDS_TARGET", "20") or 20), "complaints": db.complaints(),
            "last_executor": last_exec, "last_brain": last_brain,
        },
        "activity": recent_activity(40),
        "manual": manual,
        "emails": emails,
    }
