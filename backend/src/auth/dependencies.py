from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request

from src.domain.user import User, UserRole


async def get_current_user(request: Request) -> User:
    user = getattr(request.state, "current_user", None)
    if user is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: UserRole):
    """Return a FastAPI dependency that checks the user has one of the given roles.
    ADMIN always passes.
    """
    async def _check(user: CurrentUser) -> User:
        if user.role is UserRole.ADMIN:
            return user
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return Depends(_check)


# Convenience: any authenticated user, no role check
require_auth = Depends(get_current_user)
