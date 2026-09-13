"""PROJECT WORTH ONE - API + public site + private control center.

Endpoints
  POST /v1/e            event ingest (page_view, drop_start, drop_result, share, share_card, click)
  POST /v1/support      support intent (amount 1/3/5/other/0) + optional "notify me" email
  GET  /v1/stats        public aggregate numbers (car fund, users, shares, countries, drops)
  GET  /healthz
  GET  /admin           private control center (LAN only + token)
  GET  /admin/api/state control center data
  POST /admin/cmd       human override commands
  /                     public site (same files as GitHub Pages)
"""
import json
import os
import re
import secrets
import time

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

import db
import stats
import commands

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE_DIR = os.environ.get("WORTH_SITE", os.path.join(ROOT, "..", "docs"))
ADMIN_TOKEN = os.environ.get("WORTH_ADMIN_TOKEN", "")
ALLOWED_TYPES = {"page_view", "drop_start", "drop_result", "share", "share_card", "click", "referral_visit", "embed_view", "drop_nav"}
SID_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

app = FastAPI(title="Worth One", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["*"], max_age=86400)

# very small in-memory rate limiter: per ip, 120 events / 10 min
_rl = {}


def _rate_ok(ip):
    now = time.time()
    hits = [t for t in _rl.get(ip, []) if now - t < 600]
    if len(hits) >= 120:
        _rl[ip] = hits
        return False
    hits.append(now)
    _rl[ip] = hits
    if len(_rl) > 5000:
        _rl.clear()
    return True


def _ctx(request: Request):
    h = request.headers
    country = (h.get("cf-ipcountry") or h.get("x-country") or "").upper()[:2]
    ip = h.get("cf-connecting-ip") or h.get("x-forwarded-for", "").split(",")[0].strip() or (request.client.host if request.client else "")
    return country, ip


def _clean(v, n=120):
    if v is None:
        return None
    return str(v)[:n]


@app.get("/healthz")
def healthz():
    return {"ok": True, "ts": time.time(), "status": db.get_setting("PROJECT_STATUS")}


@app.post("/v1/e")
async def event(request: Request):
    country, ip = _ctx(request)
    if not _rate_ok(ip):
        return JSONResponse({"ok": False, "rl": True}, status_code=429)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "bad json")
    t = body.get("t")
    sid = body.get("sid")
    if t not in ALLOWED_TYPES or not sid or not SID_RE.match(sid):
        raise HTTPException(400, "bad event")
    meta = body.get("m") if isinstance(body.get("m"), dict) else {}
    ref = _clean(body.get("ref"), 64)
    if ref and not SID_RE.match(ref):
        ref = None
    if ref == sid:
        ref = None
    is_new = db.record_event(t, drop_id=_clean(body.get("d"), 32), sid=sid, country=country, ref=ref,
                             src=_clean(body.get("src"), 40), campaign=_clean(body.get("c"), 40), amount=None, meta=meta)
    if is_new and ref:
        db.record_event("referral_visit", drop_id=_clean(body.get("d"), 32), sid=sid, country=country, ref=ref, src=_clean(body.get("src"), 40), campaign=_clean(body.get("c"), 40))
    return {"ok": True}


@app.post("/v1/support")
async def support(request: Request):
    country, ip = _ctx(request)
    if not _rate_ok(ip):
        return JSONResponse({"ok": False, "rl": True}, status_code=429)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "bad json")
    sid = body.get("sid")
    if not sid or not SID_RE.match(sid):
        raise HTTPException(400, "bad sid")
    try:
        amount = float(body.get("amount", 0))
    except (TypeError, ValueError):
        amount = 0.0
    amount = max(0.0, min(amount, 1000.0))
    drop_id = _clean(body.get("d"), 32)
    email = _clean(body.get("email"), 120)
    if email and not EMAIL_RE.match(email):
        email = None
    if not body.get("only_email"):
        db.record_event("support_intent", drop_id=drop_id, sid=sid, country=country, src=_clean(body.get("src"), 40),
                        campaign=_clean(body.get("c"), 40), amount=amount)
    if email:
        db.add_supporter(sid, email, amount, drop_id, country)
        db.record_event("ready_to_support", drop_id=drop_id, sid=sid, country=country, amount=amount)
        n = db.q1("SELECT COUNT(*) n FROM supporters WHERE email IS NOT NULL AND status='intent'")["n"]
        db.add_human_action("People are ready to support: open a payment account",
                            f"{n} people left an email asking to be told when supporting is possible. "
                            "Open Stripe (or similar), then set PAYMENTS_ENABLED=true via worthctl.")
        commands.notify(f"Worth One: {n} people are READY TO SUPPORT (left email). Time to consider opening payments.")
    return {"ok": True, "payments_enabled": db.get_setting("PAYMENTS_ENABLED") == "true"}


@app.post("/v1/subscribe")
async def subscribe(request: Request):
    """'If you want, I'll send the next one.' Stored with status newdrop; never counted as support intent."""
    country, ip = _ctx(request)
    if not _rate_ok(ip):
        return JSONResponse({"ok": False, "rl": True}, status_code=429)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(400, "bad json")
    sid = body.get("sid")
    email = _clean(body.get("email"), 120)
    if not sid or not SID_RE.match(sid) or not email or not EMAIL_RE.match(email):
        raise HTTPException(400, "bad request")
    if not db.q1("SELECT id FROM supporters WHERE email=? AND status='newdrop'", (email,)):
        with db.tx() as c:
            c.execute("INSERT INTO supporters(ts,sid,email,amount,drop_id,country,status) VALUES(?,?,?,?,?,?,?)",
                      (time.time(), sid, email, 0, _clean(body.get("lang"), 5), country, "newdrop"))
        db.record_event("click", drop_id="", sid=sid, country=country, meta={"what": "subscribe"})
    return {"ok": True}


@app.get("/v1/stats")
def public_stats():
    return JSONResponse(stats.public_stats(), headers={"Cache-Control": "public, max-age=60"})


@app.get("/v1/compare")
def compare(d: str, v: float):
    """Anonymous aggregate: how a value compares with everyone else's results for a drop. Only when n is large enough."""
    if d not in ("DROP-001", "DROP-002"):
        raise HTTPException(404)
    key = {"DROP-001": "$.h", "DROP-002": "$.m"}[d]
    return JSONResponse(stats.compare(d, key, v), headers={"Cache-Control": "public, max-age=300"})


# ---------------- private control center ----------------

def _is_lan(request: Request):
    if request.headers.get("cf-connecting-ip") or request.headers.get("cf-ray"):
        return False
    host = request.client.host if request.client else ""
    return host.startswith(("192.168.", "10.", "127.", "172.")) or host == "::1"


def _auth(request: Request):
    if not ADMIN_TOKEN:
        raise HTTPException(503, "admin token not configured")
    if not _is_lan(request):
        raise HTTPException(404)
    tok = request.query_params.get("token") or request.cookies.get("wo_admin")
    if not tok or not secrets.compare_digest(tok, ADMIN_TOKEN):
        raise HTTPException(401, "token required: /admin?token=...")
    return tok


@app.get("/admin")
def admin(request: Request):
    tok = _auth(request)
    with open(os.path.join(ROOT, "admin.html"), encoding="utf-8") as f:
        html = f.read()
    resp = HTMLResponse(html)
    resp.set_cookie("wo_admin", tok, httponly=True, samesite="strict", max_age=90 * 86400)
    return resp


@app.get("/admin/api/state")
def admin_state(request: Request):
    _auth(request)
    s = db.all_settings()
    open_actions = db.q("SELECT * FROM human_actions WHERE status='open' ORDER BY ts DESC")
    return {
        "settings": s,
        "fund": stats.car_fund(),
        "all": stats.counts(),
        "d1": stats.counts(days=1),
        "d7": stats.counts(days=7),
        "ai_cost": {"all": stats.ai_cost(), "d1": stats.ai_cost(1), "d30": stats.ai_cost(30)},
        "countries": stats.by_country(),
        "channels": stats.by_channel(),
        "drops_metrics": stats.by_drop(),
        "drops": db.q("SELECT * FROM drops ORDER BY score DESC"),
        "campaigns": db.q("SELECT * FROM campaigns ORDER BY updated_ts DESC LIMIT 200"),
        "activity": db.q("SELECT * FROM activity ORDER BY ts DESC LIMIT 100"),
        "human_actions": open_actions,
        "runs": db.q("SELECT * FROM runs ORDER BY ts DESC LIMIT 20"),
        "series": stats.daily_series(14),
        "reports": db.q("SELECT day FROM daily_reports ORDER BY day DESC LIMIT 30"),
        "supporters": db.q("SELECT ts, amount, drop_id, country, status, substr(email,1,3)||'***' email FROM supporters ORDER BY ts DESC LIMIT 50"),
        "newdrop_subscribers": db.q1("SELECT COUNT(*) n FROM supporters WHERE status='newdrop'")["n"],
        "expansion": stats.expansion(),
        "scorecard": stats.scorecard(1),
        "winners": stats.winners(14)["experiments"][:15],
        "growth_today": db.q("SELECT channel, message, drop_id, ts FROM activity WHERE actor='agent' AND ts>=? ORDER BY ts DESC LIMIT 25", (time.time() - 86400,)),
        "assets": db.q("SELECT * FROM assets ORDER BY updated_ts DESC LIMIT 300"),
        "expansion_feed": db.q("SELECT * FROM activity WHERE channel IN ('seo','directory','outreach','referral','embed','backlink','newsletter','press','localization','publisher','site') ORDER BY ts DESC LIMIT 60"),
        "executor": stats.executor_summary(),
        "now": time.time(),
    }


@app.get("/admin/api/report/{day}")
def admin_report(day: str, request: Request):
    _auth(request)
    r = db.q1("SELECT report FROM daily_reports WHERE day=?", (day,))
    if not r:
        raise HTTPException(404)
    return PlainTextResponse(r["report"])


@app.post("/admin/cmd")
async def admin_cmd(request: Request):
    _auth(request)
    body = await request.json()
    cmd = (body.get("cmd") or "").strip()
    arg = (body.get("arg") or "").strip()
    try:
        msg = commands.run(cmd, arg, actor="owner")
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"ok": True, "msg": msg}


app.mount("/", StaticFiles(directory=SITE_DIR, html=True), name="site")
