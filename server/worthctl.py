#!/usr/bin/env python3
"""worthctl - command line for humans and for the autonomous brain.

  worthctl status                          quick status
  worthctl cmd "PAUSE DROP" DROP-001       human override command (see commands.py)
  worthctl seed                            load engine/drops.json + engine/campaigns.json into the DB
  worthctl report [YYYY-MM-DD]             build the daily report (optionally with --insights file.json)
  worthctl activity <channel> "<message>" [DROP-ID]
  worthctl campaign <file.json>            upsert a campaign record
  worthctl drop <file.json>                upsert a drop record
  worthctl human "<title>" "<detail>"      register HUMAN ACTION REQUIRED
  worthctl aicost <run> <model> <in> <out> <usd>
  worthctl run <kind> <status> "<summary>" [next_epoch]
  worthctl state [--compact]               JSON dump used by the brain prompt (--compact = cheap, for routine runs)
  worthctl scorecard                       daily growth scorecard (deterministic)
  worthctl winners                         drop x channel x country x hook experiments + verdicts
  worthctl notify "<text>"                 ntfy push to the owner (if configured)
  worthctl asset <file.json>               upsert expansion asset(s): directory/newsletter/publisher/backlink/embed/press
  worthctl assets [type]                   list expansion assets
  worthctl outreach <asset_id> [--dry]     send the recorded pitch by email (needs project mailbox in env)
  worthctl outreach-batch [n]              send up to n prepared pitches with an email contact (daily job)
  worthctl executor                        run one Action Executor cycle (discover -> auto-execute -> verify -> batch Telegram)
  worthctl queue [status]                  list the action queue, optionally filtered by status
  worthctl ingest_targets <file.json>      load a verified distribution_targets.json into assets (idempotent)
  worthctl ingest_wbc <file.json>          load wbc_distribution_targets.json into assets, tagged drop_id=WBC
  worthctl queue_report                    AUTO QUEUED / WAITING HUMAN / WAITING SENDER / REJECTED-STALE counts

Words Before Coffee (active project since 2026-09-13):
  worthctl state --wbc                     compact growth state for the brain (metrics + what is known)
  worthctl wbc                             print the product metrics as seen by the engine
  worthctl freeze                          archive every Worth One action/asset (idempotent)
  worthctl evaluate <asset_id>             run the 8 outreach checks on a pitch without sending
  worthctl leads                           list WBC assets by status (lead / prepared / manual_only / do_not_contact ...)
"""
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import db  # noqa: E402
import stats  # noqa: E402
import commands  # noqa: E402
import report  # noqa: E402

ENGINE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "engine")


def seed():
    n = 0
    p = os.path.join(ENGINE, "drops.json")
    if os.path.exists(p):
        for d in json.load(open(p, encoding="utf-8")):
            existing = db.q1("SELECT status FROM drops WHERE drop_id=?", (d["drop_id"],))
            if existing and existing["status"] in ("KILLED", "PAUSED"):
                d["status"] = existing["status"]
            db.upsert_drop(d); n += 1
    p = os.path.join(ENGINE, "campaigns.json")
    if os.path.exists(p):
        for c in json.load(open(p, encoding="utf-8")):
            db.upsert_campaign(c); n += 1
    p = os.path.join(ENGINE, "assets.json")
    if os.path.exists(p):
        for a in json.load(open(p, encoding="utf-8")):
            existing = db.q1("SELECT status FROM assets WHERE asset_id=?", (a["asset_id"],))
            if existing and existing["status"] in ("submitted", "accepted", "published", "rejected", "live"):
                a["status"] = existing["status"]
            db.upsert_asset(a); n += 1
    print(f"seeded {n} records")


def status():
    s = db.all_settings()
    c = stats.counts()
    f = stats.car_fund()
    print(f"PROJECT {s['PROJECT_STATUS']}  payments={s['PAYMENTS_ENABLED']}  priority={s['PRIORITY']}")
    print(f"users={c['users']} views={c['page_views']} shares={c['share_events']} share_rate={c['share_rate']:.1%} K={c['k']}")
    print(f"fund real={f['real']} / {f['car_target']}  worth1+={f['people_worth_1plus']} intended={f['intended_value']} ready={f['ready_to_support']}")
    for a in db.q("SELECT id,title FROM human_actions WHERE status='open'"):
        print(f"HUMAN ACTION REQUIRED #{a['id']}: {a['title']}")


def _hosts_known():
    import re
    hosts = set()
    for a in db.q("SELECT url, contact_source FROM assets WHERE drop_id='WBC'"):
        for u in (a.get("url"), a.get("contact_source")):
            m = re.match(r"https?://(?:www\.)?([^/:?#]+)", u or "")
            if m:
                hosts.add(m.group(1).lower())
    for r in db.q("SELECT key FROM research_cache"):
        m = re.match(r"(?:url:https?://(?:www\.)?|policy:)([^/:?#]+)", r["key"])
        if m:
            hosts.add(m.group(1).lower())
    return sorted(hosts)


def state_wbc():
    import wbc
    m = wbc.latest()
    now = time.time()
    s = db.all_settings()
    acq = m.get("acquisition") or {}
    out = {
        "settings": {k: s.get(k) for k in ("PROJECT_STATUS", "AI_DAILY_BUDGET_USD", "WBC_EMAIL_CAP", "WINNING_PATTERN", "NEXT_ACTION")},
        "ai_spent_today": round(db.q1("SELECT COALESCE(SUM(usd),0) usd FROM ai_cost WHERE ts>=?", (now - (now % 86400),))["usd"], 4),
        "metrics_stale": bool(m.get("stale")),
        "users": m.get("windows"),
        "dau_last_14": (m.get("dau") or [])[-14:],
        "games_30d": (m.get("games") or {}).get("30d"),
        "game_verdicts": wbc.game_verdicts(m) if m.get("games") else {},
        "acquisition_7d": (acq.get("7d") or [])[:15],
        "acquisition_30d": (acq.get("30d") or [])[:15],
        "top_source": acq.get("top_source"), "fastest_growing_source": acq.get("fastest_growing_source"), "best_converting_source": acq.get("best_converting_source"),
        "countries_30d": ((m.get("countries") or {}).get("30d") or [])[:10],
        "retention": m.get("retention"),
        "shares": m.get("shares"), "referral_users": m.get("referral_users"),
        "winning_pattern": s.get("WINNING_PATTERN", ""),
        "assets_by_status": db.q("SELECT status, COUNT(*) n FROM assets WHERE drop_id='WBC' GROUP BY status"),
        "live": db.q("SELECT name, type, result FROM assets WHERE drop_id='WBC' AND status='live' ORDER BY updated_ts DESC LIMIT 15"),
        "submitted_awaiting": db.q("SELECT name, type FROM assets WHERE drop_id='WBC' AND status='submitted' ORDER BY updated_ts DESC LIMIT 25"),
        "manual_only": db.q("SELECT name, result FROM assets WHERE drop_id='WBC' AND status='manual_only' ORDER BY updated_ts DESC LIMIT 15"),
        "do_not_contact": db.q("SELECT name, result FROM assets WHERE drop_id='WBC' AND status IN ('do_not_contact','pitch_rejected') ORDER BY updated_ts DESC LIMIT 15"),
        "needs_pitch": db.q("SELECT asset_id, name, url, contact, pitch_lang FROM assets WHERE drop_id='WBC' AND status='needs_pitch' LIMIT 10"),
        "already_known_hosts": _hosts_known(),
        "emails_today": db.q1("SELECT COUNT(*) n FROM email_log WHERE status='sent' AND ts>=?", (now - (now % 86400),))["n"],
        "clean_sends": db.clean_sends(), "complaints": db.complaints(),
        "recent": db.q("SELECT channel, substr(message,1,110) message FROM activity WHERE drop_id='WBC' ORDER BY ts DESC LIMIT 12"),
        "last_insights": _last_insights(),
    }
    print(json.dumps(out, indent=1, default=str))


def _last_insights():
    try:
        return json.load(open("/var/lib/worth-one/insights.json", encoding="utf-8"))
    except Exception:
        return {}


def state(compact=False):
    if compact:
        w = stats.winners(14)
        out = {
            "settings": {k: v for k, v in db.all_settings().items() if k in ("PROJECT_STATUS", "PAYMENTS_ENABLED", "CAR_TARGET", "PRIORITY", "PAUSED_CHANNELS", "BLOCKED_CHANNELS", "BLOCKED_COUNTRIES", "NEXT_EXPANSION_ACTION")},
            "scorecard_24h": stats.scorecard(1),
            "metrics_7d": {k: stats.counts(days=7)[k] for k in ("users", "page_views", "drop_results", "shares", "share_rate", "referral_new_users", "k", "would_support_1plus")},
            "experiments_14d": w["experiments"][:12],
            "drops": db.q("SELECT drop_id,name,status,score FROM drops ORDER BY score DESC"),
            "assets": db.q("SELECT asset_id,type,name,status,contact FROM assets ORDER BY updated_ts DESC LIMIT 25"),
            "channels_7d": stats.by_channel(days=7),
            "countries_7d": stats.by_country(days=7)[:10],
            "open_human_actions": db.q("SELECT id,title FROM human_actions WHERE status='open'"),
            "recent_actions": db.q("SELECT channel,substr(message,1,90) message FROM activity WHERE actor='agent' ORDER BY ts DESC LIMIT 15"),
            "tiktok_campaigns": db.q("SELECT campaign_id,drop_id,status,impressions,visitors FROM campaigns WHERE platform='tiktok'"),
            "action_queue": db.q("SELECT status, COUNT(*) n FROM actions GROUP BY status"),
        }
        print(json.dumps(out, indent=1, default=str)); return
    out = {
        "settings": db.all_settings(),
        "fund": stats.car_fund(),
        "metrics_all": stats.counts(),
        "metrics_24h": stats.counts(days=1),
        "metrics_7d": stats.counts(days=7),
        "drops": db.q("SELECT drop_id,name,status,score,concept,viral_mechanism FROM drops ORDER BY score DESC"),
        "drop_metrics": stats.by_drop(days=7),
        "channels_7d": stats.by_channel(days=7),
        "countries_7d": stats.by_country(days=7),
        "campaigns": db.q("SELECT campaign_id,drop_id,platform,country,status,url,visitors,shares,support_intent,result FROM campaigns ORDER BY updated_ts DESC LIMIT 60"),
        "open_human_actions": db.q("SELECT id,title,detail FROM human_actions WHERE status='open'"),
        "recent_activity": db.q("SELECT ts,channel,drop_id,message FROM activity ORDER BY ts DESC LIMIT 40"),
        "last_runs": db.q("SELECT ts,kind,status,summary FROM runs ORDER BY ts DESC LIMIT 5"),
        "ai_cost_30d": stats.ai_cost(30),
        "expansion": stats.expansion(),
        "assets": db.q("SELECT asset_id,type,name,url,drop_id,status,result FROM assets ORDER BY updated_ts DESC LIMIT 80"),
        "action_queue": db.q("SELECT status, COUNT(*) n FROM actions GROUP BY status"),
        "actions": db.q("SELECT action_id,type,target,status,attempts,priority,result FROM actions ORDER BY updated_ts DESC LIMIT 80"),
        "last_executor_run": db.q1("SELECT ts,status,summary FROM runs WHERE kind='executor' ORDER BY ts DESC LIMIT 1"),
        "last_telegram_batch": db.q1("SELECT ts,human_actions_count,estimated_minutes FROM telegram_log ORDER BY ts DESC LIMIT 1"),
    }
    print(json.dumps(out, indent=1, default=str))


def main(argv):
    if not argv:
        print(__doc__); return 1
    cmd, args = argv[0], argv[1:]
    if cmd == "status":
        status()
    elif cmd == "state":
        if "--wbc" in args:
            state_wbc()
        else:
            state("--compact" in args)
    elif cmd == "wbc":
        import wbc
        print(json.dumps(wbc.latest(), indent=1, default=str)[:20000])
    elif cmd == "freeze":
        import executor
        print(json.dumps(executor.freeze_worth_one()))
    elif cmd == "evaluate":
        import outreach
        a = db.q1("SELECT * FROM assets WHERE asset_id=?", (args[0],))
        ok, checks, subject, body = outreach.evaluate(a, force_policy="--force" in args)
        print("RESULT:", "PASS - would send" if ok else "BLOCKED")
        for k, v in checks.items():
            print(f"  {'ok ' if v['ok'] else 'FAIL'} {k}: {v['detail'][:160]}")
        print("\n--- rendered ---\nSubject:", subject, "\n\n" + body)
    elif cmd == "leads":
        rows = db.q("SELECT asset_id, status, type, name, contact, substr(result,1,70) result FROM assets WHERE drop_id='WBC' ORDER BY status, updated_ts DESC")
        for r in rows:
            print(f"{r['asset_id']:<20} {r['status']:<15} {r['type']:<13} {(r['name'] or '')[:34]:<34} {(r['contact'] or '')[:30]:<30} {r['result'] or ''}")
    elif cmd == "scorecard":
        print(json.dumps(stats.scorecard(1), indent=1, default=str))
    elif cmd == "winners":
        w = stats.winners(14)
        for x in w["experiments"]:
            print(f"{x['drop_id']:<9} {x['channel']:<22} {x['country']:<3} {x['hook']:<16} users={x['users']:<4} share={x['share_rate']:.0%} intent={x['intent_rate']:.0%}  {x['verdict']}")
        print("viral:", json.dumps(stats.viral_mode()))
    elif cmd == "seed":
        seed()
    elif cmd == "cmd":
        print(commands.run(args[0], args[1] if len(args) > 1 else "", actor="cli"))
    elif cmd == "report":
        day = None; insights = None
        if args and not args[0].startswith("--"):
            day = args[0]
        if "--insights" in args:
            insights = json.load(open(args[args.index("--insights") + 1], encoding="utf-8"))
        print(report.build(day, insights))
    elif cmd == "activity":
        db.log_activity(args[0], args[1], args[2] if len(args) > 2 else None, actor="agent"); print("ok")
    elif cmd == "campaign":
        d = json.load(open(args[0], encoding="utf-8"))
        for c in (d if isinstance(d, list) else [d]):
            db.upsert_campaign(c); db.log_activity(c.get("platform", "growth"), f"Campaign {c['campaign_id']} {c.get('status', '')}: {c.get('hypothesis', '')[:80]}", c.get("drop_id"), actor="agent")
        print("ok")
    elif cmd == "drop":
        d = json.load(open(args[0], encoding="utf-8"))
        for x in (d if isinstance(d, list) else [d]):
            db.upsert_drop(x); db.log_activity("experiments", f"{x['drop_id']} {x.get('status', '')}: {x.get('name', '')}", x["drop_id"], actor="agent")
        print("ok")
    elif cmd == "human":
        db.add_human_action(args[0], args[1] if len(args) > 1 else ""); print("ok")
    elif cmd == "aicost":
        db.record_ai_cost(args[0], args[1], int(args[2]), int(args[3]), float(args[4]), args[5] if len(args) > 5 else ""); print("ok")
    elif cmd == "run":
        db.record_run(args[0], args[1], args[2], float(args[3]) if len(args) > 3 else None)
        if len(args) > 3:
            db.set_setting("NEXT_AUTONOMOUS_RUN", args[3])
        print("ok")
    elif cmd == "asset":
        d = json.load(open(args[0], encoding="utf-8"))
        for a in (d if isinstance(d, list) else [d]):
            db.upsert_asset(a); db.log_activity(a.get("type", "expansion"), f"{a.get('status', '')}: {a.get('name', '')} ({a.get('url', '')[:60]})", a.get("drop_id"), actor="agent")
        print("ok")
    elif cmd == "assets":
        rows = db.q("SELECT asset_id,type,name,status,url FROM assets" + (" WHERE type=?" if args else "") + " ORDER BY type,status", tuple(args[:1]))
        for r in rows:
            print(f"{r['asset_id']:<14} {r['type']:<12} {r['status']:<16} {r['name'][:40]:<40} {r['url']}")
    elif cmd == "outreach":
        import outreach
        print(outreach.send(args[0], dry_run="--dry" in args))
    elif cmd == "outreach-batch":
        import outreach
        print("\n".join(outreach.batch(int(args[0]) if args else 3, dry_run="--dry" in args)))
    elif cmd == "notify":
        print("sent" if commands.notify(args[0]) else "not configured / failed")
    elif cmd == "executor":
        import executor
        print(json.dumps(executor.run_cycle(), indent=1, default=str))
    elif cmd == "queue":
        where = " WHERE status=?" if args else ""
        rows = db.q("SELECT action_id,type,target,status,attempts,priority,result FROM actions" + where + " ORDER BY priority DESC", tuple(args[:1]))
        for r in rows:
            print(f"{r['action_id']:<16} {r['type']:<16} {r['status']:<15} attempts={r['attempts']} prio={r['priority']:<6} {(r['target'] or '')[:30]:<30} {(r['result'] or '')[:50]}")
    elif cmd == "ingest_targets":
        import ingest
        print(json.dumps(ingest.run(args[0]), indent=1, default=str))
    elif cmd == "ingest_wbc":
        import ingest
        print(json.dumps(ingest.run_wbc(args[0]), indent=1, default=str))
    elif cmd == "queue_report":
        rows = db.q("""SELECT a.action_id, a.status, a.type, a.target, a.human_required_reason, ast.status as asset_status
                       FROM actions a LEFT JOIN assets ast ON ast.asset_id = a.asset_id""")
        buckets = {"AUTO QUEUED": [], "WAITING SENDER": [], "WAITING HUMAN": [], "REJECTED / STALE": [], "LIVE / SUBMITTED": [], "OTHER": []}
        for r in rows:
            reason = r["human_required_reason"] or ""
            if r["status"] in ("QUEUED", "PREPARED", "EXECUTING"):
                buckets["AUTO QUEUED"].append(r)
            elif r["status"] == "HUMAN_REQUIRED" and reason.startswith("WAITING_"):
                buckets["WAITING SENDER"].append(r)
            elif r["status"] == "HUMAN_REQUIRED":
                buckets["WAITING HUMAN"].append(r)
            elif r["status"] in ("STALE", "NO_RESPONSE", "FAILED"):
                buckets["REJECTED / STALE"].append(r)
            elif r["status"] in ("LIVE", "SUBMITTED"):
                buckets["LIVE / SUBMITTED"].append(r)
            else:
                buckets["OTHER"].append(r)
        rej_assets = db.q1("SELECT COUNT(*) n FROM assets WHERE status='rejected'")["n"]
        for name, items in buckets.items():
            print(f"\n{name} ({len(items)})")
            for it in items[:60]:
                print(f"  {it['action_id']:<16} {(it['target'] or '')[:44]:<44} {it['human_required_reason'] or ''}")
        print(f"\nREJECTED assets (never queued): {rej_assets}")
    else:
        print(__doc__); return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
