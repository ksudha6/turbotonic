from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from src.auth.session import COOKIE_NAME, read_session_cookie
from src.db import get_db
from src.user_repository import UserRepository
from src.domain.user import UserStatus


class SessionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request.state.current_user = None
        cookie_value = request.cookies.get(COOKIE_NAME)
        if cookie_value:
            user_id = read_session_cookie(cookie_value)
            if user_id:
                async with get_db() as conn:
                    repo = UserRepository(conn)
                    user = await repo.get_by_id(user_id)
                    if user and user.status is UserStatus.ACTIVE:
                        request.state.current_user = user
        return await call_next(request)
