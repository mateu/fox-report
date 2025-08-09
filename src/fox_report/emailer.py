"""
Lightweight email sender with retry logic.

This module provides a minimal send(msg) helper that uses a context manager
and retries on transient SMTP failures to avoid silent email loss.
"""

from __future__ import annotations

import itertools
import logging
import smtplib
import time

from .config import settings

logger = logging.getLogger(__name__)


def send(msg, max_attempts: int = 3) -> None:
    """
    Send an email.message.Message using SMTP over SSL with basic retries.

    Args:
        msg: The email message to send (email.message.Message or compatible).
        max_attempts: Maximum number of attempts before giving up.

    Raises:
        smtplib.SMTPException: If sending fails after max_attempts.
    """
    for attempt in itertools.count(1):
        try:
            with smtplib.SMTP_SSL(settings.smtp_host) as server:
                server.login(settings.smtp_user, settings.smtp_pass)
                server.send_message(msg)
            return
        except smtplib.SMTPException as exc:  # pragma: no cover - network dependent
            if attempt >= max_attempts:
                raise
            logger.warning(
                "SMTP failure (%s), retrying %d/%d", exc, attempt, max_attempts
            )
            time.sleep(2**attempt)
