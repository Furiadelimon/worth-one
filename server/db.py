"""SQLite persistence for PROJECT WORTH ONE. Single file, WAL mode, stdlib only."""
import json
import os
import sqlite3
import threading
import time
from contextlib import contextmanager

DB_PATH = os.environ.get("WORTH_DB", os.path.join(os.path.dirname(__file__), "..", "data", "worth.db"))
_lock = threading.RLock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
  id INTEGER PRIMARY KEY,
  ts REAL NOT NULL,
  day TEXT NOT NULL,
  type TEXT NOT NULL,
  drop_id TEXT,
  sid TEXT,
  country TEXT,
  ref TEXT,
  src TEXT,
  campaign TEXT,
  amount REAL,
  meta TEXT
);
CREATE INDEX IF NOT EXISTS ix_events_day ON events(day);
CREATE INDEX IF NOT EXISTS ix_events_type ON events(type);
CREATE INDEX IF NOT EXISTS ix_events_sid ON events(sid);

CREATE TABLE IF NOT EXISTS sessions (
  sid TEXT PRIMARY KEY,
  first_ts REAL, last_ts REAL, country TEXT, ref TEXT, src TEXT, campaign TEXT, visits INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS drops (
  drop_id TEXT PRIMARY KEY,
  name TEXT, slug TEXT, status TEXT, concept TEXT, target_audience TEXT, emotion TEXT, utility TEXT,
  share_trigger TEXT, viral_mechanism TEXT, expected_market TEXT, difficulty INTEGER, build_time TEXT,
  estimated_cost TEXT, expected_value TEXT, monetization_relation TEXT, score REAL,
  created_ts REAL, updated_ts REAL, notes TEXT
);

CREATE TABLE IF NOT EXISTS campaigns (
  campaign_id TEXT PRIMARY KEY,
  drop_id TEXT, platform TEXT, account TEXT, country TEXT, language TEXT, audience TEXT,
  hypothesis TEXT, content TEXT, cta TEXT, url TEXT, date TEXT, status TEXT,
  impressions INTEGER DEFAULT 0, clicks INTEGER DEFAULT 0, visitors INTEGER DEFAULT 0,
  shares INTEGER DEFAULT 0, registrations INTEGER DEFAULT 0, support_intent INTEGER DEFAULT 0,
  result TEXT, community_rules TEXT, created_ts REAL, updated_ts REAL
);

CREATE TABLE IF NOT EXISTS activity (
  id INTEGER PRIMARY KEY, ts REAL NOT NULL, channel TEXT, drop_id TEXT, message TEXT, actor TEXT
);

CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT);

CREATE TABLE IF NOT EXISTS human_actions (
  id INTEGER PRIMARY KEY, ts REAL, title TEXT, detail TEXT, status TEXT DEFAULT 'open', resolved_ts REAL
);

CREATE TABLE IF NOT EXISTS daily_reports (day TEXT PRIMARY KEY, ts REAL, report TEXT);

CREATE TABLE IF NOT EXISTS ai_cost (
  id INTEGER PRIMARY KEY, ts REAL, day TEXT, run TEXT, model TEXT,
  input_tokens INTEGER, output_tokens INTEGER, usd REAL, note TEXT
);

CREATE TABLE IF NOT EXISTS supporters (
  id INTEGER PRIMARY KEY, ts REAL, sid TEXT, email TEXT, amount REAL, drop_id TEXT, country TEXT, status TEXT DEFAULT 'intent'
);

CREATE TABLE IF NOT EXISTS runs (id INTEGER PRIMARY KEY, ts REAL, kind TEXT, status TEXT, summary TEXT, next_ts REAL);

CREATE TABLE IF NOT EXISTS assets (
  asset_id TEXT PRIMARY KEY,
  type TEXT, name TEXT, url TEXT, drop_id TEXT, status TEXT, why TEXT, pitch TEXT, contact TEXT,
  submitted_ts REAL, result TEXT, notes TEXT, created_ts REAL, updated_ts REAL
);

CREATE TABLE IF NOT EXISTS actions (
  action_id TEXT PRIMARY KEY,
  asset_id TEXT, type TEXT NOT NULL, target TEXT, url TEXT, drop_id TEXT, campaign_id TEXT,
  expected_users REAL DEFAULT 0, confidence REAL DEFAULT 0.5, strategic_value REAL DEFAULT 0.5, effort REAL DEFAULT 1,
  priority REAL DEFAULT 0,
  status TEXT DEFAULT 'PREPARED',
  attempts INTEGER DEFAULT 0,
  created_at REAL, last_attempt REAL, updated_ts REAL,
  result TEXT, human_required_reason TEXT, human_action_text TEXT, estimated_human_time INTEGER,
  payload TEXT, next_verify_at REAL, telegram_notified_ts REAL
);
CREATE INDEX IF NOT EXISTS ix_actions_status ON actions(status);
CREATE INDEX IF NOT EXISTS ix_actions_asset ON actions(asset_id);

CREATE TABLE IF NOT EXISTS telegram_log (
  id INTEGER PRIMARY KEY, ts REAL, human_actions_count INTEGER, estimated_minutes REAL, actions TEXT, resolved_at REAL
);

-- Words Before Coffee growth engine (pivot 2026-09-13) ------------------------------------------
CREATE TABLE IF NOT EXISTS wbc_snapshots (id INTEGER PRIMARY KEY, ts REAL, day TEXT, data TEXT);
CREATE INDEX IF NOT EXISTS ix_wbc_snap_ts ON wbc_snapshots(ts);

-- one row per domain/url investigated: never re-research the same thing (cost control)
CREATE TABLE IF NOT EXISTS research_cache (
  key TEXT PRIMARY KEY, ts REAL, status TEXT, data TEXT
);

-- every outbound email, rendered exactly as sent, with the checks that let it through
CREATE TABLE IF NOT EXISTS email_log (
  id INTEGER PRIMARY KEY, ts REAL, asset_id TEXT, to_addr TEXT, subject TEXT, body TEXT,
  checks TEXT, status TEXT, complaint INTEGER DEFAULT 0, note TEXT
);
"""

# columns added after the first release; applied idempotently in conn()
MIGRATIONS = [
    "ALTER TABLE assets ADD COLUMN policy TEXT",
    "ALTER TABLE assets ADD COLUMN pitch_lang TEXT",
    "ALTER TABLE assets ADD COLUMN src_tag TEXT",
    "ALTER TABLE assets ADD COLUMN pitch_source TEXT",
    "ALTER TABLE assets ADD COLUMN contact_source TEXT",
]

DEFAULT_SETTINGS = {
    "PROJECT_STATUS": "ACTIVE",
    # pivot 2026-09-13: Words Before Coffee is the only active growth project; Worth One is archived
    "ACTIVE_PROJECT": "WBC",
    "WORTH_ONE_STATUS": "ARCHIVED",
    "AI_DAILY_BUDGET_USD": "1.00",
    "WBC_EMAIL_CAP": "2",
    "CLEAN_SENDS_TARGET": "20",
    "WINNING_PATTERN": "",
    "LAST_GROWTH_ACTION": "",
    "PAYMENTS_ENABLED": "false",
    "CAR_TARGET": "30000",
    "REAL_CONTRIBUTIONS": "0",
    "PAUSED_CHANNELS": "[]",
    "BLOCKED_CHANNELS": "[]",
    "BLOCKED_COUNTRIES": "[]",
    "PRIORITY": "DROP-001",
    "CURRENT_ACTION": "Bootstrapping",
    "NEXT_ACTION": "Publish DROP-001 and start distribution",
    "NEXT_AUTONOMOUS_RUN": "",
    "PUBLIC_URL": "",
    "API_URL": "",
    "NEXT_EXPANSION_ACTION": "",
    "LOCALIZED_PAGES": "0",
}

EVENT_COLS = ["page_view", "drop_start", "drop_result", "share", "share_card", "support_intent", "ready_to_support", "click", "referral_visit", "embed_view", "drop_nav"]
ASSET_TYPES = ["directory", "newsletter", "publisher", "backlink", "embed", "press", "resource_page", "localization"]


def connect():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    c = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA synchronous=NORMAL")
    return c


_conn = None


def conn():
    global _conn
    if _conn is None:
        _conn = connect()
        _conn.executescript(SCHEMA)
        for m in MIGRATIONS:
            try:
                _conn.execute(m)
            except sqlite3.OperationalError:
                pass  # already applied
        for k, v in DEFAULT_SETTINGS.items():
            _conn.execute("INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)", (k, v))
        _conn.commit()
    return _conn


@contextmanager
def tx():
    with _lock:
        c = conn()
        try:
            yield c
            c.commit()
        except Exception:
            c.rollback()
            raise


def q(sql, params=()):
    with _lock:
        return [dict(r) for r in conn().execute(sql, params).fetchall()]


def q1(sql, params=()):
    rows = q(sql, params)
    return rows[0] if rows else None


def day_of(ts=None):
    return time.strftime("%Y-%m-%d", time.gmtime(ts or time.time()))


def get_setting(key, default=None):
    r = q1("SELECT value FROM settings WHERE key=?", (key,))
    return r["value"] if r else default


def set_setting(key, value):
    with tx() as c:
        c.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))


def all_settings():
    return {r["key"]: r["value"] for r in q("SELECT key,value FROM settings")}


def log_activity(channel, message, drop_id=None, actor="system"):
    with tx() as c:
        c.execute("INSERT INTO activity(ts,channel,drop_id,message,actor) VALUES(?,?,?,?,?)", (time.time(), channel, drop_id, message, actor))


def add_human_action(title, detail):
    with tx() as c:
        r = c.execute("SELECT id FROM human_actions WHERE title=? AND status='open'", (title,)).fetchone()
        if r:
            c.execute("UPDATE human_actions SET detail=? WHERE id=?", (detail, r["id"]))
        else:
            c.execute("INSERT INTO human_actions(ts,title,detail) VALUES(?,?,?)", (time.time(), title, detail))


def resolve_human_action(id_):
    with tx() as c:
        c.execute("UPDATE human_actions SET status='done', resolved_ts=? WHERE id=?", (time.time(), id_))


def record_run(kind, status, summary, next_ts=None):
    with tx() as c:
        c.execute("INSERT INTO runs(ts,kind,status,summary,next_ts) VALUES(?,?,?,?,?)", (time.time(), kind, status, summary, next_ts))


def record_ai_cost(run, model, input_tokens, output_tokens, usd, note=""):
    with tx() as c:
        c.execute("INSERT INTO ai_cost(ts,day,run,model,input_tokens,output_tokens,usd,note) VALUES(?,?,?,?,?,?,?,?)",
                  (time.time(), day_of(), run, model, input_tokens, output_tokens, usd, note))


def record_event(type_, drop_id=None, sid=None, country=None, ref=None, src=None, campaign=None, amount=None, meta=None):
    ts = time.time()
    with tx() as c:
        c.execute(
            "INSERT INTO events(ts,day,type,drop_id,sid,country,ref,src,campaign,amount,meta) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (ts, day_of(ts), type_, drop_id, sid, country, ref, src, campaign, amount, json.dumps(meta or {})[:2000]),
        )
        is_new = False
        if sid:
            r = c.execute("SELECT sid FROM sessions WHERE sid=?", (sid,)).fetchone()
            if r:
                c.execute("UPDATE sessions SET last_ts=?, visits=visits+? WHERE sid=?", (ts, 1 if type_ == "page_view" else 0, sid))
            else:
                is_new = True
                c.execute("INSERT INTO sessions(sid,first_ts,last_ts,country,ref,src,campaign) VALUES(?,?,?,?,?,?,?)", (sid, ts, ts, country, ref, src, campaign))
        if campaign:
            col = {"page_view": "visitors", "share": "shares", "support_intent": "support_intent", "click": "clicks"}.get(type_)
            if col:
                c.execute(f"UPDATE campaigns SET {col}={col}+1, updated_ts=? WHERE campaign_id=?", (ts, campaign))
        return is_new


def add_supporter(sid, email, amount, drop_id, country):
    with tx() as c:
        c.execute("INSERT INTO supporters(ts,sid,email,amount,drop_id,country) VALUES(?,?,?,?,?,?)", (time.time(), sid, email, amount, drop_id, country))


def upsert_drop(d):
    cols = ["drop_id", "name", "slug", "status", "concept", "target_audience", "emotion", "utility", "share_trigger",
            "viral_mechanism", "expected_market", "difficulty", "build_time", "estimated_cost", "expected_value",
            "monetization_relation", "score", "notes"]
    vals = [d.get(k) for k in cols]
    marks = ",".join(["?"] * len(cols))
    with tx() as c:
        r = c.execute("SELECT drop_id FROM drops WHERE drop_id=?", (d["drop_id"],)).fetchone()
        if r:
            sets = ",".join(k + "=?" for k in cols[1:])
            c.execute("UPDATE drops SET " + sets + ", updated_ts=? WHERE drop_id=?", vals[1:] + [time.time(), d["drop_id"]])
        else:
            c.execute("INSERT INTO drops(" + ",".join(cols) + ",created_ts,updated_ts) VALUES(" + marks + ",?,?)", vals + [time.time(), time.time()])


def upsert_campaign(d):
    cols = ["campaign_id", "drop_id", "platform", "account", "country", "language", "audience", "hypothesis", "content",
            "cta", "url", "date", "status", "result", "community_rules"]
    vals = [d.get(k) for k in cols]
    marks = ",".join(["?"] * len(cols))
    with tx() as c:
        r = c.execute("SELECT campaign_id FROM campaigns WHERE campaign_id=?", (d["campaign_id"],)).fetchone()
        if r:
            sets = ",".join(k + "=?" for k in cols[1:])
            c.execute("UPDATE campaigns SET " + sets + ", updated_ts=? WHERE campaign_id=?", vals[1:] + [time.time(), d["campaign_id"]])
        else:
            c.execute("INSERT INTO campaigns(" + ",".join(cols) + ",created_ts,updated_ts) VALUES(" + marks + ",?,?)", vals + [time.time(), time.time()])


def upsert_asset(d):
    cols = ["asset_id", "type", "name", "url", "drop_id", "status", "why", "pitch", "contact", "submitted_ts", "result", "notes",
            "policy", "pitch_lang", "src_tag", "pitch_source", "contact_source"]
    vals = [d.get(k) for k in cols]
    marks = ",".join(["?"] * len(cols))
    with tx() as c:
        r = c.execute("SELECT asset_id FROM assets WHERE asset_id=?", (d["asset_id"],)).fetchone()
        if r:
            sets = ",".join(k + "=?" for k in cols[1:])
            c.execute("UPDATE assets SET " + sets + ", updated_ts=? WHERE asset_id=?", vals[1:] + [time.time(), d["asset_id"]])
        else:
            c.execute("INSERT INTO assets(" + ",".join(cols) + ",created_ts,updated_ts) VALUES(" + marks + ",?,?)", vals + [time.time(), time.time()])


ACTION_COLS = ["action_id", "asset_id", "type", "target", "url", "drop_id", "campaign_id",
               "expected_users", "confidence", "strategic_value", "effort", "priority",
               "status", "attempts", "last_attempt", "result", "human_required_reason", "human_action_text",
               "estimated_human_time", "payload", "next_verify_at", "telegram_notified_ts"]


def add_action(action_id, type_, **fields):
    """Create an action if it doesn't already exist (idempotent DISCOVER->PREPARE step). Returns True if created."""
    with tx() as c:
        if c.execute("SELECT 1 FROM actions WHERE action_id=?", (action_id,)).fetchone():
            return False
        cols = ["action_id", "type"] + [k for k in fields if k in ACTION_COLS]
        vals = [action_id, type_] + [fields[k] for k in cols[2:]]
        c.execute(
            "INSERT INTO actions(" + ",".join(cols) + ",created_at,updated_ts) VALUES(" + ",".join(["?"] * len(cols)) + ",?,?)",
            vals + [time.time(), time.time()],
        )
        return True


def update_action(action_id, **fields):
    fields = {k: v for k, v in fields.items() if k in ACTION_COLS}
    if not fields:
        return
    sets = ",".join(k + "=?" for k in fields)
    with tx() as c:
        c.execute("UPDATE actions SET " + sets + ", updated_ts=? WHERE action_id=?", list(fields.values()) + [time.time(), action_id])


def log_telegram_batch(human_actions_count, estimated_minutes, action_ids):
    with tx() as c:
        c.execute("INSERT INTO telegram_log(ts,human_actions_count,estimated_minutes,actions) VALUES(?,?,?,?)",
                  (time.time(), human_actions_count, estimated_minutes, json.dumps(action_ids)))


# ---------------- WBC growth engine helpers ----------------

def cache_get(key, max_age=None):
    r = q1("SELECT ts, status, data FROM research_cache WHERE key=?", (key,))
    if not r:
        return None
    if max_age and time.time() - r["ts"] > max_age:
        return None
    try:
        return {"ts": r["ts"], "status": r["status"], "data": json.loads(r["data"] or "null")}
    except Exception:
        return {"ts": r["ts"], "status": r["status"], "data": None}


def cache_set(key, status, data=None):
    with tx() as c:
        c.execute("INSERT INTO research_cache(key,ts,status,data) VALUES(?,?,?,?) ON CONFLICT(key) DO UPDATE SET ts=excluded.ts, status=excluded.status, data=excluded.data",
                  (key, time.time(), status, json.dumps(data) if data is not None else None))


def log_email(asset_id, to_addr, subject, body, checks, status, note=""):
    with tx() as c:
        c.execute("INSERT INTO email_log(ts,asset_id,to_addr,subject,body,checks,status,note) VALUES(?,?,?,?,?,?,?,?)",
                  (time.time(), asset_id, to_addr, subject, body, json.dumps(checks), status, note))


def clean_sends():
    """Emails that went out through the full check pipeline, with no complaint recorded."""
    return q1("SELECT COUNT(*) n FROM email_log WHERE status='sent' AND complaint=0")["n"]


def complaints():
    return q1("SELECT COUNT(*) n FROM email_log WHERE complaint=1")["n"]
