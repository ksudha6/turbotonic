from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request

from src.domain.purchase_order import POType, PurchaseOrder
from src.domain.user import User, UserRole, UserStatus


def can_view_invoice_attachments(user: User) -> bool:
    """Return True if user may read documents attached to any invoice.

    VENDOR, SM, ADMIN, PROCUREMENT_MANAGER: view. FREIGHT_MANAGER: view.
    QUALITY_LAB: hidden.
    Returns False for inactive/pending users as a defense-in-depth guard.
    """
    if user.status is not UserStatus.ACTIVE:
        return False
    return user.role in (
        UserRole.ADMIN,
        UserRole.SM,
        UserRole.VENDOR,
        UserRole.PROCUREMENT_MANAGER,
        UserRole.FREIGHT_MANAGER,
    )


def can_manage_invoice_attachments(user: User) -> bool:
    """Return True if user may upload or delete invoice documents.

    VENDOR (own invoice, enforced via check_vendor_access), SM, ADMIN: manage.
    PROCUREMENT_MANAGER: read-only.
    FREIGHT_MANAGER: read-only.
    QUALITY_LAB: hidden.
    Returns False for inactive/pending users as a defense-in-depth guard.
    """
    if user.status is not UserStatus.ACTIVE:
        return False
    return user.role in (UserRole.ADMIN, UserRole.SM, UserRole.VENDOR)


def check_vendor_access(user: User, vendor_id: str) -> None:
    """Raise 404 if VENDOR user doesn't own this entity. Non-VENDOR roles pass through."""
    if user.role is UserRole.VENDOR and user.vendor_id != vendor_id:
        raise HTTPException(status_code=404, detail="Not found")


def can_view_po_attachments(user: User, po: PurchaseOrder) -> bool:
    """Return True if user may read documents attached to po.

    PROCUREMENT: ADMIN, SM, PROCUREMENT_MANAGER, FREIGHT_MANAGER, QUALITY_LAB,
    and VENDOR (own). OPEX: ADMIN, FREIGHT_MANAGER, and VENDOR (own). Returns
    False for inactive/pending users as a defense-in-depth guard — session
    middleware already enforces ACTIVE status at the request boundary.
    """
    if user.status is not UserStatus.ACTIVE:
        return False

    if po.po_type is POType.PROCUREMENT:
        if user.role in (
            UserRole.ADMIN,
            UserRole.SM,
            UserRole.PROCUREMENT_MANAGER,
            UserRole.FREIGHT_MANAGER,
            UserRole.QUALITY_LAB,
        ):
            return True
        if user.role is UserRole.VENDOR:
            return user.vendor_id == po.vendor_id
        return False

    if po.po_type is POType.OPEX:
        if user.role in (UserRole.ADMIN, UserRole.FREIGHT_MANAGER):
            return True
        if user.role is UserRole.VENDOR:
            return user.vendor_id == po.vendor_id
        return False

    return False


def can_manage_po_attachments(user: User, po: PurchaseOrder) -> bool:
    """Return True if user may upload or delete documents attached to po.

    PROCUREMENT: ADMIN, SM, and VENDOR (own). OPEX: ADMIN and FREIGHT_MANAGER.
    Returns False for inactive/pending users as a defense-in-depth guard.
    """
    if user.status is not UserStatus.ACTIVE:
        return False

    if po.po_type is POType.PROCUREMENT:
        if user.role in (UserRole.ADMIN, UserRole.SM):
            return True
        if user.role is UserRole.VENDOR:
            return user.vendor_id == po.vendor_id
        return False

    if po.po_type is POType.OPEX:
        return user.role in (UserRole.ADMIN, UserRole.FREIGHT_MANAGER)

    return False


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
