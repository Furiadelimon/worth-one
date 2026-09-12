"""Daily report generator. Deterministic numbers; the WHAT WORKED / LEARNED sections are filled by the brain run
when available, otherwise by simple rules."""
import json
import time

import db
import stats


def _best_worst(rows, key, label):
    rows = [r for r in rows if r.get(key) is not None]
    if not rows:
        return "n/a", "n/a"
    best = max(rows, key=lambda r: r[key])
    worst = min(rows, key=lambda r: r[key])
    return best[label], worst[label]


def build(day=None, insights=None):
    day = day or db.day_of(time.time() - 86400)
    d1 = stats.counts(days=1)
    total = stats.counts()
    drops = stats.by_drop(days=1)
    channels = stats.by_channel(days=1)
    countries = stats.by_country(days=1)
    top_drop, worst_drop = _best_worst(drops, "users", "drop_id")
    top_ch, worst_ch = _best_worst(channels, "users", "channel")
    since = time.time() - 86400
    created = db.q1("SELECT COUNT(*) n FROM activity WHERE ts>=? AND message LIKE 'Created%'", (since,))["n"]
    published = db.q1("SELECT COUNT(*) n FROM activity WHERE ts>=? AND message LIKE 'Published%'", (since,))["n"]
    started = db.q1("SELECT COUNT(*) n FROM drops WHERE created_ts>=?", (since,))["n"]
    killed = db.q1("SELECT COUNT(*) n FROM activity WHERE ts>=? AND message LIKE '%KILLED%'", (since,))["n"]
    cost = stats.ai_cost(1)
    ins = insights or {}
    worked = ins.get("worked") or ("No qualified traffic yet. Nothing has proven itself." if d1["users"] < 20 else "See metrics: " + json.dumps({"share_rate": d1["share_rate"], "k": d1["k"]}))
    failed = ins.get("failed") or ("Distribution is the bottleneck." if d1["users"] < 20 else "-")
    learned = ins.get("learned") or "More traffic needed before any statistical conclusion."
    plan = ins.get("plan") or "Keep DROP-001 live, publish prepared content on authorized channels, add DROP-002 if the pipeline allows."
    fund = stats.car_fund()
    lines = [
        f"DAILY REPORT  {day}  (PROJECT WORTH ONE)",
        "=" * 48,
        f"TRAFFIC (views)      {d1['page_views']}",
        f"USERS                {d1['users']}",
        f"NEW USERS            {d1['new_users']}",
        f"SHARES               {d1['share_events']}  (share rate {d1['share_rate']:.1%}, K={d1['k']})",
        f"COUNTRIES            {len(countries)}  " + ", ".join(c['country'] for c in countries[:8]),
        "",
        f"TOP DROP             {top_drop}",
        f"WORST DROP           {worst_drop}",
        f"TOP CHANNEL          {top_ch}",
        f"WORST CHANNEL        {worst_ch}",
        "",
        f"CONTENT CREATED      {created}",
        f"CONTENT PUBLISHED    {published}",
        f"EXPERIMENTS STARTED  {started}",
        f"EXPERIMENTS KILLED   {killed}",
        "",
        f"SUPPORT INTENT (24h) worth1={d1['support_intent']['1']} worth3={d1['support_intent']['3']} worth5={d1['support_intent']['5']} other={d1['support_intent']['other']} no={d1['support_intent']['no']}",
        f"INTENDED VALUE (24h) EUR {d1['intended_value']:.2f}   READY TO SUPPORT (emails, total) {total['ready_to_support']}",
        f"CAR FUND             REAL EUR {fund['real']:.2f} / {fund['car_target']:.0f}   INTENDED EUR {fund['intended_value']:.2f}   PAYMENTS {'ON' if fund['payments_enabled'] else 'OFF'}",
        f"AI COST (24h)        USD {cost['usd']:.4f}  ({cost['runs']} runs)",
        "",
        "WHAT WORKED", "  " + worked, "",
        "WHAT FAILED", "  " + failed, "",
        "WHAT WAS LEARNED", "  " + learned, "",
        "NEXT 24H PLAN", "  " + plan,
    ]
    text = "\n".join(lines)
    with db.tx() as c:
        c.execute("INSERT INTO daily_reports(day,ts,report) VALUES(?,?,?) ON CONFLICT(day) DO UPDATE SET report=excluded.report, ts=excluded.ts", (day, time.time(), text))
    db.log_activity("report", f"Daily report generated for {day}")
    return text
