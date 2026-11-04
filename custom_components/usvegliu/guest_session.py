"""Stay tokens and climate/lock helpers for the guest web app.

Pure Python: no Home Assistant import, so the mapping can be unit-tested.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import secrets
from typing import Any

from .const import DOMAIN

PREVIEW_KEY = "__usvegliu_preview__"
PREVIEW_HOURS = 24
TOKEN_MIN_LENGTH = 16

_OFF_HVAC = frozenset({"off", "idle"})
_HVAC_ON_ORDER = ("heat", "cool", "heat_cool", "fan_only", "dry", "auto")
_FAN_ALIASES: dict[int, tuple[str, ...]] = {
    1: ("low", "low_breeze", "min", "1", "level_1", "level1", "doux"),
    2: ("medium", "mid", "middle", "med", "2", "level_2", "level2", "moyen"),
    3: ("high", "max", "3", "level_3", "level3", "fort"),
}
_FAN_SKIP = frozenset({"auto", "off", "on"})


def generate_guest_token() -> str:
    """Opaque stay token. Long enough to share in a URL."""
    return secrets.token_urlsafe(24)


def ensure_guest_token(record: dict[str, Any]) -> str:
    """Keep an existing token; mint one when the stay is first provisioned."""
    token = record.get("guest_token")
    if isinstance(token, str) and len(token) >= TOKEN_MIN_LENGTH:
        return token
    minted = generate_guest_token()
    record["guest_token"] = minted
    return minted


def parse_iso(value: Any, tzinfo: timezone | None = None) -> datetime | None:
    """Parse an ISO datetime stored on a stay record."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        try:
            parsed = datetime.fromisoformat(str(value))
        except (TypeError, ValueError):
            return None
    if parsed.tzinfo is None and tzinfo is not None:
        return parsed.replace(tzinfo=tzinfo)
    return parsed


def stay_is_open(record: dict[str, Any], now: datetime) -> bool:
    """True while the link may be used.

    A provisioned stay (already in storage) is usable until check-out,
    including the days before arrival. A preview expires at check_out.
    """
    end = parse_iso(record.get("check_out"), now.tzinfo)
    if end is None:
        return False
    return now < end


def open_issued_records(
    stays: dict[str, dict[str, Any]],
    preview: dict[str, Any] | None,
    now: datetime,
) -> list[dict[str, Any]]:
    """Provisioned stays still usable, then a live preview, by check-in."""
    records = [record for record in stays.values() if stay_is_open(record, now)]
    records.sort(key=lambda record: str(record.get("check_in") or ""))
    if isinstance(preview, dict) and stay_is_open(preview, now):
        records.append(preview)
    return records


def issued_account_view(
    record: dict[str, Any],
    *,
    username: str | None,
    lien_maison: str,
    path: str,
    tableau: str,
) -> dict[str, Any]:
    """Admin row for one issued stay. The HA password is never included."""
    return {
        "guest": str(record.get("guest") or ""),
        "check_in": str(record.get("check_in") or ""),
        "check_out": str(record.get("check_out") or ""),
        "username": str(username or record.get("username") or ""),
        "voucher_code": str(record.get("voucher_code") or "") or None,
        "lien_maison": lien_maison,
        "path": path,
        "reservation_id": str(record.get("key") or ""),
        "essai": bool(record.get("preview")),
        "tableau": tableau,
    }


def find_record_by_token(
    stays: dict[str, dict[str, Any]],
    preview: dict[str, Any] | None,
    token: str,
    now: datetime,
) -> dict[str, Any] | None:
    """Return the stay or preview bound to ``token``, if it is still open."""
    if not token or len(token) < TOKEN_MIN_LENGTH:
        return None
    if isinstance(preview, dict) and preview.get("guest_token") == token:
        if stay_is_open(preview, now):
            return preview
    for record in stays.values():
        if record.get("guest_token") == token and stay_is_open(record, now):
            return record
    return None


def build_preview_record(now: datetime, hours: int = PREVIEW_HOURS) -> dict[str, Any]:
    """Admin test session, independent from the calendar."""
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    end = now + timedelta(hours=hours)
    record: dict[str, Any] = {
        "key": PREVIEW_KEY,
        "guest": "Essai",
        "check_in": now.isoformat(),
        "check_out": end.isoformat(),
        "preview": True,
    }
    ensure_guest_token(record)
    return record


def normalize_fan_label(value: str) -> str:
    """Compare fan mode names without punctuation."""
    return value.casefold().replace(" ", "_").replace("-", "_")


def map_fan_modes(available: list[str]) -> dict[int, str]:
    """Map guest speeds 1/2/3 onto the climate entity's fan_mode values."""
    mapping: dict[int, str] = {}
    unused = [
        mode
        for mode in available
        if mode and normalize_fan_label(mode) not in _FAN_SKIP
    ]
    for speed, aliases in _FAN_ALIASES.items():
        for mode in unused:
            if normalize_fan_label(mode) in aliases:
                mapping[speed] = mode
                break
    leftovers = [mode for mode in unused if mode not in mapping.values()]
    for speed in (1, 2, 3):
        if speed not in mapping and leftovers:
            mapping[speed] = leftovers.pop(0)
    return mapping


def infer_fan_speed(current: str | None, mapping: dict[int, str]) -> int:
    """Best-effort 1/2/3 from the live fan_mode."""
    if current:
        needle = normalize_fan_label(current)
        for speed, mode in mapping.items():
            if normalize_fan_label(mode) == needle:
                return speed
    return 2 if 2 in mapping else next(iter(mapping), 2)


def climate_is_on(hvac_mode: str | None) -> bool:
    """Treat off/idle as stopped."""
    if not hvac_mode:
        return False
    return hvac_mode.casefold() not in _OFF_HVAC


def pick_hvac_on(available: list[str], preferred: str | None = None) -> str:
    """Choose a non-off HVAC mode when the guest turns the unit on."""
    by_fold = {mode.casefold(): mode for mode in available if mode}
    if preferred:
        fold = preferred.casefold()
        if fold not in _OFF_HVAC and fold in by_fold:
            return by_fold[fold]
    for candidate in _HVAC_ON_ORDER:
        if candidate in by_fold:
            return by_fold[candidate]
    for mode in available:
        if mode and mode.casefold() not in _OFF_HVAC:
            return mode
    return "heat"


def guest_path(token: str) -> str:
    """Path served by this integration (local HA test URL)."""
    return f"/{DOMAIN}/s/{token}"


def public_guest_url(base_url: str | None, token: str) -> str:
    """Public locataire URL. ``base_url`` is the vitrine origin, without /s."""
    path = guest_path(token)
    origin = (base_url or "").strip().rstrip("/")
    if not origin:
        return path
    if origin.endswith("/s"):
        return f"{origin}/{token}"
    return f"{origin}/s/{token}"
