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
  worthctl state                           JSON dump used by the brain prompt
  worthctl notify "<text>"                 ntfy push to Pedro (if configured)
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


def state():
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
    }
    print(json.dumps(out, indent=1, default=str))


def main(argv):
    if not argv:
        print(__doc__); return 1
    cmd, args = argv[0], argv[1:]
    if cmd == "status":
        status()
    elif cmd == "state":
        state()
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
    elif cmd == "notify":
        print("sent" if commands.notify(args[0]) else "not configured / failed")
    else:
        print(__doc__); return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
