from __future__ import annotations

import time

import pytest

from src.auth.session import create_session_cookie, read_session_cookie


def test_create_returns_nonempty_string():
    cookie = create_session_cookie("user-123")
    assert isinstance(cookie, str)
    assert len(cookie) > 0


def test_roundtrip():
    user_id = "abc-def-123"
    cookie = create_session_cookie(user_id)
    result = read_session_cookie(cookie)
    assert result == user_id


def test_tampered_cookie_returns_none():
    cookie = create_session_cookie("user-123")
    tampered = cookie + "x"
    assert read_session_cookie(tampered) is None


def test_expired_cookie_returns_none():
    cookie = create_session_cookie("user-123")
    time.sleep(1)
    assert read_session_cookie(cookie, max_age=0) is None
