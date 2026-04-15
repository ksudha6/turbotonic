from __future__ import annotations

import os

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

SECRET_KEY = os.environ.get("SESSION_SECRET_KEY", "dev-secret-key-change-in-production")
COOKIE_NAME = "tt_session"
MAX_AGE = 86400  # 24 hours

_serializer = URLSafeTimedSerializer(SECRET_KEY)


def create_session_cookie(user_id: str) -> str:
    return _serializer.dumps(user_id)


def read_session_cookie(cookie_value: str, max_age: int = MAX_AGE) -> str | None:
    try:
        return _serializer.loads(cookie_value, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
