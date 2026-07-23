import os
import random
from datetime import datetime, timedelta

from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth

import database as db
import auth
from platforms import (
    PLATFORMS, TRANSACTION_TYPES, LOCATIONS, PEAK_HOURS, CONGESTION_WINDOWS,
    MARKET_SHARE, PLATFORM_BASE_STATS, current_traffic_period,
)
from models.recommender import recommend as run_recommendation

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), "frontend")

app = FastAPI(title="Cross Payment Platform")
app.mount("/static", StaticFiles(directory=os.path.join(FRONTEND_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(FRONTEND_DIR, "templates"))

# Required by authlib to hold the short-lived OAuth state/nonce between the
# /login/google redirect and the /auth/google/callback round-trip.
app.add_middleware(SessionMiddleware, secret_key=auth.SECRET_KEY)

db.init_db()

# Real Google OAuth - set these two env vars (from Google Cloud Console >
# APIs & Services > Credentials > OAuth client ID, type "Web application",
# with redirect URI {your-domain}/auth/google/callback) to enable it.
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET")

oauth = OAuth()
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    oauth.register(
        name="google",
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def current_user(request: Request):
    user_id = auth.get_current_user_id(request)
    if not user_id:
        return None
    return db.get_user_by_id(user_id)


def render(request: Request, template_name: str, **context):
    user = current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    context.update({
        "request": request,
        "user": user,
        "active_page": context.get("active_page", ""),
    })
    return templates.TemplateResponse(template_name, context)


# ---------------------------------------------------------------------------
# Auth pages
# ---------------------------------------------------------------------------
@app.get("/")
def root(request: Request):
    if current_user(request):
        return RedirectResponse(url="/dashboard")
    return RedirectResponse(url="/login")


@app.get("/login")
def login_page(request: Request):
    if current_user(request):
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@app.post("/login")
def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    user = db.verify_password(username, password)
    if not user:
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "Invalid username or password."}, status_code=401
        )
    token = auth.create_session_token(user["id"])
    resp = RedirectResponse(url="/dashboard", status_code=303)
    resp.set_cookie(auth.COOKIE_NAME, token, max_age=auth.MAX_AGE, httponly=True)
    return resp


@app.post("/signup")
def signup_submit(request: Request, username: str = Form(...), email: str = Form(""),
                   password: str = Form(...), display_name: str = Form("")):
    user_id = db.create_user(username, email, password, display_name or username)
    if not user_id:
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "That username is already taken."}, status_code=400
        )
    token = auth.create_session_token(user_id)
    resp = RedirectResponse(url="/dashboard", status_code=303)
    resp.set_cookie(auth.COOKIE_NAME, token, max_age=auth.MAX_AGE, httponly=True)
    return resp


@app.get("/login/google")
async def login_google(request: Request):
    if not (GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Google sign-in isn't configured on this server yet."},
            status_code=503,
        )
    redirect_uri = request.url_for("auth_google_callback")
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.get("/auth/google/callback")
async def auth_google_callback(request: Request):
    if not (GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET):
        return RedirectResponse(url="/login", status_code=303)
    token = await oauth.google.authorize_access_token(request)
    userinfo = token.get("userinfo") or {}
    email = userinfo.get("email")
    name = userinfo.get("name") or userinfo.get("given_name")
    if not email:
        return templates.TemplateResponse(
            "login.html", {"request": request, "error": "Could not read your Google account email."},
            status_code=400,
        )
    user = db.get_or_create_google_user(email, name)
    token = auth.create_session_token(user["id"])
    resp = RedirectResponse(url="/dashboard", status_code=303)
    resp.set_cookie(auth.COOKIE_NAME, token, max_age=auth.MAX_AGE, httponly=True)
    return resp


@app.get("/logout")
def logout():
    resp = RedirectResponse(url="/login", status_code=303)
    resp.delete_cookie(auth.COOKIE_NAME)
    return resp


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------
@app.get("/dashboard")
def dashboard(request: Request):
    user = current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    savings = db.get_monthly_savings(user["id"])
    txs = db.get_transactions(user["id"], limit=5)
    settings = db.get_settings(user["id"])
    return render(request, "dashboard.html", active_page="dashboard",
                  savings=savings, recent_transactions=txs, platform_count=len(PLATFORMS),
                  transaction_types=TRANSACTION_TYPES, locations=LOCATIONS, settings=settings,
                  platforms=PLATFORMS)


@app.get("/new-transaction")
def new_transaction_page(request: Request):
    user = current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    settings = db.get_settings(user["id"])
    last_txs = db.get_transactions(user["id"], limit=3)
    return render(request, "new_transaction.html", active_page="new_transaction",
                  transaction_types=TRANSACTION_TYPES, locations=LOCATIONS,
                  settings=settings, last_transactions=last_txs)


@app.get("/recommendations")
def recommendations_page(request: Request):
    user = current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    txs = db.get_transactions(user["id"], limit=200)
    return render(request, "recommendations.html", active_page="recommendations", transactions=txs)


@app.get("/analytics")
def analytics_page(request: Request):
    user = current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return render(request, "analytics.html", active_page="analytics", platforms=PLATFORMS)


@app.get("/history")
def history_page(request: Request):
    user = current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    txs = db.get_transactions(user["id"], limit=200)
    savings = db.get_monthly_savings(user["id"])
    return render(request, "history.html", active_page="history", transactions=txs, savings=savings)


@app.get("/compare")
def compare_page(request: Request):
    user = current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return render(request, "compare.html", active_page="compare", platforms=PLATFORMS)


@app.get("/industry-details")
def industry_page(request: Request):
    user = current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return render(request, "industry.html", active_page="industry",
                  peak_hours=PEAK_HOURS, congestion=CONGESTION_WINDOWS)


@app.get("/settings")
def settings_page(request: Request):
    user = current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    settings = db.get_settings(user["id"])
    return render(request, "settings.html", active_page="settings",
                  settings=settings, transaction_types=TRANSACTION_TYPES, locations=LOCATIONS)


@app.get("/about")
def about_page(request: Request):
    user = current_user(request)
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    return render(request, "about.html", active_page="about", platforms=PLATFORMS)


# ---------------------------------------------------------------------------
# JSON API
# ---------------------------------------------------------------------------
@app.post("/api/recommend")
async def api_recommend(request: Request):
    user_id = auth.require_login(request)
    body = await request.json()
    amount = float(body.get("amount", 0))
    transaction_type = body.get("transaction_type", TRANSACTION_TYPES[0])
    location = body.get("location", LOCATIONS[0])

    result = run_recommendation(amount, transaction_type, location)
    best = result["recommended"]

    db.add_transaction(
        user_id=user_id,
        amount=amount,
        transaction_type=transaction_type,
        location=location,
        recommended_platform=best["platform"],
        pri_score=best["pri_score"],
        fee=best["fee"],
        speed_seconds=best["speed_seconds"],
        savings=result["savings"],
    )
    return JSONResponse(result)


@app.get("/api/transactions")
def api_transactions(request: Request):
    user_id = auth.require_login(request)
    txs = db.get_transactions(user_id, limit=200)
    return [dict(t) for t in txs]


@app.delete("/api/transactions")
def api_clear_transactions(request: Request):
    user_id = auth.require_login(request)
    db.clear_transactions(user_id)
    return {"status": "cleared"}


@app.get("/api/export")
def api_export(request: Request):
    user_id = auth.require_login(request)
    txs = db.get_transactions(user_id, limit=1000)
    return {"recommendation_history": [dict(t) for t in txs]}


@app.post("/api/settings")
async def api_update_settings(request: Request):
    user_id = auth.require_login(request)
    body = await request.json()
    allowed = {
        "default_transaction_type", "default_location", "email_savings_reports",
        "peak_hour_alerts", "sms_alerts", "language", "date_format", "theme",
        "privacy_mode", "data_retention_days",
    }
    updates = {k: v for k, v in body.items() if k in allowed}
    db.update_settings(user_id, **updates)
    return {"status": "saved"}


@app.get("/api/compare")
def api_compare(request: Request, platforms: str = ""):
    auth.require_login(request)
    names = [p.strip() for p in platforms.split(",") if p.strip()]
    if len(names) < 2:
        raise HTTPException(status_code=400, detail="Select at least 2 platforms")
    sample_amount = 50000
    result = run_recommendation(sample_amount, TRANSACTION_TYPES[0], LOCATIONS[0])
    ranked = {r["platform"]: r for r in result["all_ranked"]}
    rows = []
    for name in names:
        if name in ranked:
            rows.append(ranked[name])
        elif name in PLATFORMS:
            cfg = PLATFORMS[name]
            fee = round(min(max(sample_amount * cfg["fee_percent"], cfg["min_fee"]), cfg["max_fee"]))
            rows.append({
                "platform": name, "network": cfg["network"], "category": cfg["category"],
                "pri_score": cfg["base_success_rate"], "success_rate": cfg["base_success_rate"],
                "fee": fee, "speed_seconds": cfg["base_speed_seconds"], "efficiency": cfg["base_success_rate"],
            })
    return {"comparison": rows}


@app.get("/api/analytics")
def api_analytics(request: Request):
    auth.require_login(request)
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul"]
    random.seed(7)
    monthly = [{"month": m, "success_rate": round(random.uniform(94, 99), 1),
                "failure_rate": round(random.uniform(1, 6), 1)} for m in months]

    platform_stats = []
    result = run_recommendation(50000, TRANSACTION_TYPES[0], LOCATIONS[0])
    for r in result["all_ranked"]:
        platform_stats.append({
            "platform": r["platform"],
            "success_rate": r["success_rate"],
            "pri_score": r["pri_score"],
        })
    return {"monthly": monthly, "platform_stats": platform_stats}


@app.get("/api/dashboard-stats")
def api_dashboard_stats(request: Request):
    user_id = auth.require_login(request)
    txs = db.get_transactions(user_id, limit=1000)
    savings = db.get_monthly_savings(user_id)

    total_transactions = PLATFORM_BASE_STATS["total_transactions_baseline"] + len(txs)
    happy_users = PLATFORM_BASE_STATS["happy_users_baseline"]

    if txs:
        fee_pcts = [
            (t["savings"] / (t["fee"] + t["savings"]) * 100) if (t["fee"] + t["savings"]) > 0 else 0
            for t in txs
        ]
        avg_fee_saved_pct = round(sum(fee_pcts) / len(fee_pcts), 1)
        time_saved_seconds = sum(max(0, 25 - t["speed_seconds"]) for t in txs)
    else:
        avg_fee_saved_pct = 0
        time_saved_seconds = 0

    now = datetime.now()
    week_ago = now - timedelta(days=7)
    txs_this_week = [t for t in txs if datetime.fromisoformat(t["created_at"]) >= week_ago]

    traffic = current_traffic_period(now.hour)

    return {
        "total_transactions": total_transactions,
        "user_transactions": len(txs),
        "avg_fee_saved_pct": avg_fee_saved_pct,
        "time_saved_seconds": time_saved_seconds,
        "transactions_this_week": len(txs_this_week),
        "happy_users": happy_users,
        "market_share": MARKET_SHARE,
        "traffic": traffic,
        "monthly_savings": savings["total"],
    }


@app.get("/api/industry/congestion")
def api_congestion(request: Request):
    auth.require_login(request)
    return {"congestion": CONGESTION_WINDOWS, "peak_hours": PEAK_HOURS}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
