from __future__ import annotations

import logging
import os
from datetime import UTC, datetime as _dt
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import asyncpg
import pytest
import pytest_asyncio

from src.domain.user import User, UserRole, UserStatus
from src.schema import init_db
from src.services.email import (
    EmailService,
    MissingTemplateError,
    RenderedEmail,
    render_email,
)
from src.user_repository import UserRepository

# Recipient-resolution tests exercise asyncpg; template render tests are sync.
# Async tests use the explicit marker on the function instead of a module-wide
# pytestmark so the sync render tests do not trip the asyncio warning.

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://turbo_tonic@localhost:5432/turbo_tonic_test",
)


# Context fixture shared across template render tests. Tests define their own
# extras when needed; the common keys are `po_number`, `po_url`, `vendor_name`.
_BASE_CONTEXT: dict[str, str] = {
    "po_number": "PO-0001",
    "po_url": "https://turbotonic.example/po/abc",
    "vendor_name": "Acme Ltd",
    "line_detail": "",
    "round_indicator": "",
}


@pytest_asyncio.fixture
async def user_repo() -> UserRepository:
    # Dedicated connection scoped to each recipient-resolution test; rolled back
    # at teardown so no seed pollution leaks across tests.
    conn = await asyncpg.connect(TEST_DATABASE_URL)
    await init_db(conn)
    tx = conn.transaction()
    await tx.start()
    try:
        yield UserRepository(conn)
    finally:
        await tx.rollback()
        await conn.close()


@pytest_asyncio.fixture
async def conn_with_vendors() -> asyncpg.Connection:
    # Same pattern as user_repo but also inserts two vendor rows so vendor-scoped
    # recipient tests can hang vendor_id off VENDOR-role users.
    conn = await asyncpg.connect(TEST_DATABASE_URL)
    await init_db(conn)
    tx = conn.transaction()
    await tx.start()
    try:
        yield conn
    finally:
        await tx.rollback()
        await conn.close()


# ---------------------------------------------------------------------------
# Unit: template rendering
# ---------------------------------------------------------------------------


def test_po_accepted_template_renders_required_fields() -> None:
    rendered = render_email("po_accepted", dict(_BASE_CONTEXT))
    assert isinstance(rendered, RenderedEmail)
    assert "PO-0001" in rendered.body_html
    assert "PO-0001" in rendered.body_text
    assert "Acme Ltd" in rendered.body_html
    assert rendered.subject == "[TurboTonic] PO PO-0001 accepted", (
        f"subject must match the iter-060 pattern, got {rendered.subject!r}"
    )


def test_po_modified_template_renders_round_indicator() -> None:
    ctx = dict(_BASE_CONTEXT, round_indicator="Round 1")
    rendered = render_email("po_modified", ctx)
    assert "Round 1" in rendered.body_text
    assert "modified by counterparty" in rendered.subject


def test_po_line_modified_template_renders_line_detail() -> None:
    ctx = dict(_BASE_CONTEXT, line_detail="PN-001: quantity, unit_price", round_indicator="Round 2")
    rendered = render_email("po_line_modified", ctx)
    assert "PN-001: quantity, unit_price" in rendered.body_text
    assert "Round 2" in rendered.body_text


def test_po_advance_paid_template_renders_po_url() -> None:
    rendered = render_email("po_advance_paid", dict(_BASE_CONTEXT))
    assert _BASE_CONTEXT["po_url"] in rendered.body_html
    assert "advance payment recorded" in rendered.subject


def test_missing_template_raises_clear_error() -> None:
    with pytest.raises(MissingTemplateError) as excinfo:
        render_email("not_a_real_template", dict(_BASE_CONTEXT))
    msg = str(excinfo.value)
    assert "not_a_real_template" in msg
    assert "registered templates" in msg


# ---------------------------------------------------------------------------
# Unit: EmailService.send paths
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_in_development_mode_logs_and_returns(caplog: pytest.LogCaptureFixture) -> None:
    # No SMTP_HOST => service runs in dev mode: it must log, not raise, and not
    # attempt a network send. Patch aiosmtplib.send to prove it is not called.
    service = EmailService(host=None)
    assert service.enabled is False

    with patch("src.services.email.aiosmtplib.send", new=AsyncMock()) as mock_send:
        with caplog.at_level(logging.INFO, logger="src.services.email"):
            await service.send(
                to=["dev@example.com"],
                subject="[TurboTonic] PO PO-42 accepted",
                body_html="<p>hi</p>",
                body_text="hi",
            )

    assert mock_send.await_count == 0, (
        f"aiosmtplib.send must not be called in dev mode, got {mock_send.await_count} calls"
    )
    assert any("development mode" in rec.getMessage() for rec in caplog.records), (
        f"dev-mode send must log a development-mode line; records: "
        f"{[rec.getMessage() for rec in caplog.records]}"
    )


@pytest.mark.asyncio
async def test_send_in_production_mode_dispatches_multipart_alternative() -> None:
    # Any SMTP_HOST flips the service into production mode. aiosmtplib.send is
    # mocked; we assert it received a multipart/alternative EmailMessage with
    # both the text and html parts.
    service = EmailService(
        host="smtp.example.com",
        port=587,
        user="user",
        password="pass",
        from_addr="no-reply@turbotonic.example",
        use_tls=True,
    )
    assert service.enabled is True

    with patch("src.services.email.aiosmtplib.send", new=AsyncMock()) as mock_send:
        await service.send(
            to=["vendor@acme.example"],
            subject="[TurboTonic] PO PO-1 accepted",
            body_html="<p>hello</p>",
            body_text="hello",
        )

    assert mock_send.await_count == 1
    call_args = mock_send.await_args
    assert call_args is not None
    message = call_args.args[0]
    # Structural checks on the email.message.EmailMessage the service built.
    assert message["To"] == "vendor@acme.example"
    assert message["From"] == "no-reply@turbotonic.example"
    assert message["Subject"] == "[TurboTonic] PO PO-1 accepted"
    # multipart/alternative with exactly the two expected subtypes.
    assert message.is_multipart(), "production send must be multipart"
    payload = message.get_payload()
    content_types = sorted(part.get_content_type() for part in payload)
    assert content_types == ["text/html", "text/plain"], (
        f"multipart must carry text/plain + text/html, got {content_types}"
    )
    # Named kwargs passed through to aiosmtplib.send.
    kwargs = call_args.kwargs
    assert kwargs["hostname"] == "smtp.example.com"
    assert kwargs["port"] == 587
    assert kwargs["username"] == "user"
    assert kwargs["password"] == "pass"
    assert kwargs["start_tls"] is True


# ---------------------------------------------------------------------------
# Unit: recipient resolution via UserRepository
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolver_returns_sm_and_admin_for_sm_targeted_events(
    user_repo: UserRepository,
) -> None:
    sm = User.create(
        username="sm1", display_name="SM One", role=UserRole.SM,
        email="sm1@turbotonic.example",
    )
    admin = User.create(
        username="admin1", display_name="Admin One", role=UserRole.ADMIN,
        email="admin1@turbotonic.example",
    )
    quality = User.create(
        username="ql1", display_name="QL One", role=UserRole.QUALITY_LAB,
        email="ql1@turbotonic.example",
    )
    await user_repo.save(sm)
    await user_repo.save(admin)
    await user_repo.save(quality)

    emails = await user_repo.list_active_emails_by_roles(("SM", "ADMIN"))
    assert set(emails) == {"sm1@turbotonic.example", "admin1@turbotonic.example"}, (
        f"SM-targeted events receive only SM+ADMIN; got {emails}"
    )


@pytest.mark.asyncio
async def test_resolver_returns_vendor_scoped_users_for_vendor_targeted_events(
    conn_with_vendors: asyncpg.Connection,
) -> None:
    vendor_a = str(uuid4())
    vendor_b = str(uuid4())
    now = _dt.now(UTC).isoformat()
    for vid, name in ((vendor_a, "Vendor A"), (vendor_b, "Vendor B")):
        await conn_with_vendors.execute(
            """
            INSERT INTO vendors (id, name, country, status, vendor_type, created_at, updated_at)
            VALUES ($1, $2, 'US', 'ACTIVE', 'PROCUREMENT', $3, $3)
            """,
            vid, name, now,
        )

    repo = UserRepository(conn_with_vendors)
    vendor_user_a = User.create(
        username="vua", display_name="V A", role=UserRole.VENDOR,
        vendor_id=vendor_a, email="va@acme.example",
    )
    vendor_user_b = User.create(
        username="vub", display_name="V B", role=UserRole.VENDOR,
        vendor_id=vendor_b, email="vb@beta.example",
    )
    await repo.save(vendor_user_a)
    await repo.save(vendor_user_b)

    emails_a = await repo.list_active_emails_by_vendor(vendor_a)
    emails_b = await repo.list_active_emails_by_vendor(vendor_b)

    assert emails_a == ["va@acme.example"], f"vendor A scope, got {emails_a}"
    assert emails_b == ["vb@beta.example"], f"vendor B scope, got {emails_b}"


@pytest.mark.asyncio
async def test_resolver_excludes_inactive_users(user_repo: UserRepository) -> None:
    active_sm = User.create(
        username="sm-active", display_name="Active SM", role=UserRole.SM,
        email="active@turbotonic.example",
    )
    inactive_sm = User.create(
        username="sm-inactive", display_name="Inactive SM", role=UserRole.SM,
        email="inactive@turbotonic.example",
    )
    inactive_sm.status = UserStatus.INACTIVE
    await user_repo.save(active_sm)
    await user_repo.save(inactive_sm)

    emails = await user_repo.list_active_emails_by_roles(("SM",))
    assert emails == ["active@turbotonic.example"], (
        f"inactive users must be excluded; got {emails}"
    )


@pytest.mark.asyncio
async def test_resolver_excludes_users_with_no_email(user_repo: UserRepository) -> None:
    with_email = User.create(
        username="sm-with", display_name="With", role=UserRole.SM,
        email="with@turbotonic.example",
    )
    no_email = User.create(
        username="sm-without", display_name="Without", role=UserRole.SM,
        email=None,
    )
    empty_email = User.create(
        username="sm-empty", display_name="Empty", role=UserRole.SM,
        email="",
    )
    await user_repo.save(with_email)
    await user_repo.save(no_email)
    await user_repo.save(empty_email)

    emails = await user_repo.list_active_emails_by_roles(("SM",))
    assert emails == ["with@turbotonic.example"], (
        f"users with null or empty email must be excluded; got {emails}"
    )
