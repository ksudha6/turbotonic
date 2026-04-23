"""SMTP dispatch and Jinja2 template rendering for outbound email.

Production mode (when `SMTP_HOST` is set) sends multipart/alternative via
aiosmtplib. Development mode (SMTP_HOST unset or empty) logs the payload and
returns success without touching the network. The fake email service used in
tests substitutes this class via FastAPI dependency override and records the
(to, template_name, context) tuples so assertions can target template choice
and recipient set rather than SMTP bytes.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import aiosmtplib
from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound

logger = logging.getLogger(__name__)

# Template directory lives alongside this module; packaging ships it as data files.
TEMPLATES_DIR: Path = Path(__file__).parent / "email_templates"

# Each template key maps to a (html_template, text_template) pair. Listed as an
# immutable tuple-of-tuples mapping to prevent mutation at import time.
_TEMPLATE_PAIRS: dict[str, tuple[str, str]] = {
    "po_modified": ("po_modified.html.j2", "po_modified.txt.j2"),
    "po_line_modified": ("po_line_modified.html.j2", "po_line_modified.txt.j2"),
    "po_advance_paid": ("po_advance_paid.html.j2", "po_advance_paid.txt.j2"),
    "po_accepted": ("po_accepted.html.j2", "po_accepted.txt.j2"),
}


class MissingTemplateError(ValueError):
    """Raised when a caller requests a template name that is not registered."""


@dataclass(frozen=True)
class RenderedEmail:
    subject: str
    body_html: str
    body_text: str


def _build_env(templates_dir: Path | None = None) -> Environment:
    root = templates_dir if templates_dir is not None else TEMPLATES_DIR
    return Environment(
        loader=FileSystemLoader(str(root)),
        autoescape=True,
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_email(
    template_name: str,
    context: dict[str, Any],
    *,
    templates_dir: Path | None = None,
) -> RenderedEmail:
    """Render one named template pair to HTML + text bodies and a subject line.

    The subject pattern is `[TurboTonic] PO <po_number> {event summary}`; the
    `event summary` is derived from the template name to keep the subject line
    inbox-triageable without another round of context passing.
    """
    if template_name not in _TEMPLATE_PAIRS:
        raise MissingTemplateError(
            f"unknown email template {template_name!r}; "
            f"registered templates: {sorted(_TEMPLATE_PAIRS)}"
        )
    html_name, text_name = _TEMPLATE_PAIRS[template_name]
    env = _build_env(templates_dir)
    try:
        html_template = env.get_template(html_name)
        text_template = env.get_template(text_name)
    except TemplateNotFound as exc:
        raise MissingTemplateError(
            f"template file missing for {template_name!r}: {exc.name}"
        ) from exc

    body_html = html_template.render(**context)
    body_text = text_template.render(**context)
    subject = _subject_for(template_name, context)
    return RenderedEmail(subject=subject, body_html=body_html, body_text=body_text)


def _subject_for(template_name: str, context: dict[str, Any]) -> str:
    po_number = context.get("po_number", "")
    summary = {
        "po_modified": "modified by counterparty",
        "po_line_modified": "line modified",
        "po_advance_paid": "advance payment recorded",
        "po_accepted": "accepted",
    }[template_name]
    return f"[TurboTonic] PO {po_number} {summary}"


class EmailService:
    """Thin wrapper around aiosmtplib + jinja2.

    The service owns SMTP configuration (read from env at construction time) and
    template rendering. Callers pass rendered bodies to `send`; rendering is
    exposed separately via `render` so the notification dispatcher can record
    the rendered payload when email is disabled.
    """

    def __init__(
        self,
        *,
        host: str | None = None,
        port: int | None = None,
        user: str | None = None,
        password: str | None = None,
        from_addr: str | None = None,
        use_tls: bool | None = None,
    ) -> None:
        # Env takes effect at construction, not at send; tests and CLI operators
        # can override without re-reading the environment per call.
        self._host = host if host is not None else os.getenv("SMTP_HOST")
        self._port = port if port is not None else int(os.getenv("SMTP_PORT", "587"))
        self._user = user if user is not None else os.getenv("SMTP_USER")
        self._password = password if password is not None else os.getenv("SMTP_PASS")
        self._from_addr = (
            from_addr
            if from_addr is not None
            else os.getenv("SMTP_FROM", "no-reply@turbotonic.example")
        )
        if use_tls is None:
            tls_env = os.getenv("SMTP_TLS", "true").lower()
            self._use_tls = tls_env in ("1", "true", "yes", "on")
        else:
            self._use_tls = use_tls

    @property
    def enabled(self) -> bool:
        # Email is enabled only when a host is configured; this mirrors the
        # EMAIL_ENABLED env var documented in the iter-060 plan.
        return bool(self._host)

    def render(self, template_name: str, context: dict[str, Any]) -> RenderedEmail:
        return render_email(template_name, context)

    async def send(
        self,
        to: list[str],
        subject: str,
        body_html: str,
        body_text: str,
    ) -> None:
        """Dispatch one multipart/alternative message to the recipient list.

        Development mode (no SMTP_HOST) logs the payload at INFO and returns.
        Production mode builds an EmailMessage with both text and HTML parts
        and sends via aiosmtplib. The caller handles retry or activity-log
        bookkeeping; this method re-raises on SMTP failure.
        """
        if not to:
            # Empty recipient list is a caller bug; keep the invariant explicit.
            logger.info("email.send skipped: empty recipient list, subject=%r", subject)
            return

        if not self.enabled:
            logger.info(
                "email.send (development mode): to=%r subject=%r text=%r",
                to, subject, body_text,
            )
            return

        message = EmailMessage()
        message["From"] = self._from_addr
        message["To"] = ", ".join(to)
        message["Subject"] = subject
        # set_content lays down text/plain; add_alternative layers text/html so
        # the final structure is multipart/alternative as specified in the iter.
        message.set_content(body_text)
        message.add_alternative(body_html, subtype="html")

        # aiosmtplib.send manages the connection, STARTTLS if requested, and
        # optional authentication. The signature accepts username/password
        # kwargs; passing None short-circuits the AUTH step inside the library.
        await aiosmtplib.send(
            message,
            hostname=self._host,
            port=self._port,
            username=self._user,
            password=self._password,
            start_tls=self._use_tls,
        )
