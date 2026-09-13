"""Daily report for Words Before Coffee. Deterministic numbers; WHAT WORKED / LEARNED come from the last brain run
when available. Sent to the owner once a day (Telegram) by ops/daily.sh."""
import json
import time

import db
import stats
import wbc


def build(day=None, insights=None):
    day = day or db.day_of(time.time() - 86400)
    m = wbc.latest()
    w = m.get("windows") or {}
    d1, d7, d30 = w.get("24h") or {}, w.get("7d") or {}, w.get("30d") or {}
    acq = (m.get("acquisition") or {})
    top = (acq.get("7d") or [])[:5]
    games = (m.get("games") or {}).get("7d") or []
    verdicts = wbc.game_verdicts(m) if games else {}
    ret = m.get("retention") or {}
    countries = (m.get("countries") or {}).get("7d") or []
    cost = stats.ai_cost(1)
    ok24, bad24 = stats._agent_perf(1)
    ins = insights or {}
    s = db.all_settings()
    lines = [
        f"WORDS BEFORE COFFEE  daily growth report  {day}",
        "=" * 48,
        "REAL PLAYERS",
        f"  users 24h {d1.get('users', '?')}  (new {d1.get('new_users', '?')}, returning {d1.get('returning_users', '?')})",
        f"  users 7d {d7.get('users', '?')}   users 30d {d30.get('users', '?')}   all time {(w.get('all') or {}).get('users', '?')}",
        f"  games played 24h {d1.get('games_played', '?')}   7d {d7.get('games_played', '?')}",
        f"  retention D1 {ret.get('d1', {}).get('rate', 0):.0%}  D7 {ret.get('d7', {}).get('rate', 0):.0%}   shares 7d {(m.get('shares') or {}).get('7d', 0)}   referral users 30d {(m.get('referral_users') or {}).get('30d', 0)}",
        "GAMES (7d)",
    ] + [f"  {g['game']:<7} users {g['users']:<4} played {g['games_played']:<4} completion {g['completion']:.0%}  repeat {g['repeat_rate']:.0%}  share {g['share_rate']:.0%}" for g in games] + [
        f"  best {verdicts.get('best_game', '-')} | fastest {verdicts.get('fastest_growing_game', '-')} | retention {verdicts.get('best_retention_game', '-')} | share {verdicts.get('best_share_rate_game', '-')}",
        "SOURCES (7d, first touch)",
    ] + ([f"  {r['source'][:28]:<28} users {r['users']:<4} new {r['new_users']:<4} games {r['games_played']:<4} conv {r['conversion']:.0%} ({'+' if r.get('growth', 0) >= 0 else ''}{r.get('growth', 0)})" for r in top] or ["  no visits recorded yet"]) + [
        f"  top {acq.get('top_source') or '-'} | fastest {acq.get('fastest_growing_source') or '-'} | best converting {acq.get('best_converting_source') or '-'}",
        "COUNTRIES (7d) " + ", ".join(f"{c['country']} {c['users']}" for c in countries[:8]),
        "AGENT",
        f"  successful actions 24h {ok24}   failed {bad24}   emails today {db.q1('SELECT COUNT(*) n FROM email_log WHERE status=? AND ts>=?', ('sent', time.time() - (time.time() % 86400)))['n']} / cap {s.get('WBC_EMAIL_CAP', '2')}",
        f"  clean sends {db.clean_sends()} / {s.get('CLEAN_SENDS_TARGET', '20')}   complaints {db.complaints()}",
        f"  AI cost 24h ${cost['usd'] or 0:.3f} (budget ${s.get('AI_DAILY_BUDGET_USD', '1')}/day)",
        f"  winning pattern: {s.get('WINNING_PATTERN') or 'none yet (no source has produced 5+ players)'}",
        "WHAT WORKED   " + (ins.get("worked") or "-"),
        "WHAT FAILED   " + (ins.get("failed") or "-"),
        "LEARNED       " + (ins.get("learned") or "-"),
        "NEXT          " + (s.get("NEXT_ACTION") or ins.get("plan") or "-"),
    ]
    if m.get("stale"):
        lines.insert(2, f"  (metrics stale: {m.get('error', '')[:80]})")
    text = "\n".join(lines)
    with db.tx() as c:
        c.execute("INSERT INTO daily_reports(day,ts,report) VALUES(?,?,?) ON CONFLICT(day) DO UPDATE SET ts=excluded.ts, report=excluded.report", (day, time.time(), text))
    return text
