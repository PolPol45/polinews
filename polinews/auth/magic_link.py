"""Magic link — generate one-use tokens and dispatch via configured delivery."""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from polinews.config import (
    MAGIC_LINK_DELIVERY,
    MAGIC_LINK_EXPIRE_MINUTES,
    RESEND_API_KEY,
    RESEND_FROM_EMAIL,
)


def generate_token() -> str:
    return str(uuid.uuid4())


def expiry_iso() -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=MAGIC_LINK_EXPIRE_MINUTES)
    return exp.isoformat()


def is_expired(expires_at_iso: str) -> bool:
    try:
        exp = datetime.fromisoformat(expires_at_iso)
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return datetime.now(timezone.utc) > exp
    except ValueError:
        return True


def send_magic_link(email: str, token: str, base_url: str = "http://localhost:8000") -> None:
    """
    Dispatch the magic link according to MAGIC_LINK_DELIVERY config.

    Modes:
      - "log"    → print URL to stdout (dev)
      - "resend" → send email via Resend API
    """
    link = f"{base_url}/auth/verify?token={token}"

    if MAGIC_LINK_DELIVERY == "resend":
        _send_via_resend(email, link)
    else:
        # Default: log to stdout — useful in dev / test
        print(f"[MAGIC_LINK] email={email} link={link}")


def _send_via_resend(email: str, link: str) -> None:
    """Send magic link via Resend API (https://resend.com)."""
    import json
    from urllib.request import Request, urlopen

    if not RESEND_API_KEY:
        raise RuntimeError("RESEND_API_KEY is not set — cannot send magic link via Resend")

    payload = {
        "from": RESEND_FROM_EMAIL,
        "to": [email],
        "subject": "Your Poli-News sign-in link",
        "html": (
            f"<p>Click the link below to sign in to Poli-News:</p>"
            f"<p><a href='{link}'>{link}</a></p>"
            f"<p>This link expires in {MAGIC_LINK_EXPIRE_MINUTES} minutes.</p>"
        ),
    }
    req = Request(
        "https://api.resend.com/emails",
        data=json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urlopen(req, timeout=10) as resp:
        if resp.status not in (200, 201):
            raise RuntimeError(f"Resend API error: {resp.status}")
