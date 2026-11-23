"""QR code for the guest web-app share link.

Uses segno (pure Python, listed in the integration requirements).
"""

from __future__ import annotations

import logging

from .guest_session import guest_path

_LOGGER = logging.getLogger(__name__)

_DARK = "#2b241c"
_LIGHT = "#f7f3ec"


def guest_share_url(
    token: str,
    scheme: str | None = None,
    host: str | None = None,
) -> str:
    """Absolute Maison URL for the host that served this request."""
    cleaned = str(token or "").strip()
    if not cleaned:
        return ""
    path = guest_path(cleaned)
    proto = str(scheme or "http").split(",")[0].strip() or "http"
    origin = str(host or "").split(",")[0].strip()
    if not origin:
        return path
    return f"{proto}://{origin}{path}"


def make_share_qr_svg(url: str) -> str:
    """Inline SVG for ``url``, or empty if the encoder is unavailable."""
    text = str(url or "").strip()
    if not text:
        return ""
    try:
        import segno
    except ImportError:
        _LOGGER.debug("segno is not installed; skip guest QR")
        return ""
    try:
        qr = segno.make(text, error="m")
        return str(
            qr.svg_inline(scale=5, border=2, dark=_DARK, light=_LIGHT) or ""
        )
    except Exception:  # noqa: BLE001 — a missing QR must not break the stay API
        _LOGGER.debug("guest QR encoding failed", exc_info=True)
        return ""
