"""
Minimal session-cookie authentication. Session tokens are signed and
issued after either real Google OAuth (see /login/google and
/auth/google/callback in main.py, backed by GOOGLE_CLIENT_ID/SECRET) or a
local username/password signup or login against the SQLite user table.
"""
import os
from itsdangerous import URLSafeTimedSerializer, BadSignature
from fastapi import Request, HTTPException

SECRET_KEY = os.environ.get("APP_SECRET_KEY", "cross-payment-platform-dev-secret-change-me")
serializer = URLSafeTimedSerializer(SECRET_KEY)
COOKIE_NAME = "cpp_session"
MAX_AGE = 60 * 60 * 24 * 7  # 7 days


def create_session_token(user_id: int) -> str:
    return serializer.dumps({"user_id": user_id})


def read_session_token(token: str):
    try:
        data = serializer.loads(token, max_age=MAX_AGE)
        return data.get("user_id")
    except BadSignature:
        return None


def get_current_user_id(request: Request):
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    return read_session_token(token)


def require_login(request: Request):
    user_id = get_current_user_id(request)
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user_id
