"""Pure planning of stays, vouchers and tenant accounts.

No Home Assistant or network imports: the coordinator applies the plan.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
import hashlib
import re

from .const import (
    ACCESS_PER_STAY,
    ACCESS_SHARED,
    DEFAULT_DEVICE_LIMIT,
    DEFAULT_DOWNLOAD_MBPS,
    DEFAULT_EXTRA_DAYS,
    DEFAULT_LEAD_DAYS,
    DEFAULT_MAX_STAY_DAYS,
    DEFAULT_TITLE_BLOCKLIST,
    DEFAULT_UPLOAD_MBPS,
    KBPS_PER_MBPS,
    SHARED_USERNAME,
)


@dataclass(frozen=True)
class CalendarStay:
    """One reservation read from a calendar entity."""

    key: str
    guest: str
    check_in: datetime
    check_out: datetime
    summary: str


@dataclass(frozen=True)
class VoucherSpec:
    """Parameters for one UniFi hotspot voucher."""

    name: str
    time_limit_minutes: int
    authorized_guest_limit: int
    rx_rate_limit_kbps: int
    tx_rate_limit_kbps: int

    def signature(self) -> str:
        """Stable signature used to skip unchanged vouchers."""
        raw = (
            f"{self.name}|{self.time_limit_minutes}|{self.authorized_guest_limit}|"
            f"{self.rx_rate_limit_kbps}|{self.tx_rate_limit_kbps}"
        )
        return hashlib.sha256(raw.encode()).hexdigest()[:16]


@dataclass(frozen=True)
class StayPlan:
    """A stay that should have a voucher and, optionally, an HA user."""

    key: str
    guest: str
    check_in: datetime
    check_out: datetime
    voucher: VoucherSpec
    username: str


@dataclass(frozen=True)
class SyncPlan:
    """What the engine should converge to."""

    ensure: tuple[StayPlan, ...]
    revoke_keys: tuple[str, ...]
    shared_username: str | None


def parse_blocklist(raw: str | None) -> tuple[str, ...]:
    """Split a comma-separated blocklist into lowercase needles."""
    if not raw:
        return ()
    return tuple(
        piece.strip().casefold() for piece in raw.split(",") if piece.strip()
    )


def is_blocked_title(summary: str, needles: tuple[str, ...]) -> bool:
    """Return True when the event title looks like a calendar block."""
    folded = summary.casefold()
    return any(needle and needle in folded for needle in needles)


def sanitize_guest(summary: str) -> str:
    """Turn a calendar title into a voucher note fragment."""
    text = summary.replace("'", "").replace('"', "").replace("\\", "")
    text = re.sub(r"\s+", " ", text).strip()
    text = text[:60].strip()
    return text or "Locataire"


def voucher_name(guest: str, check_in: date, check_out: date) -> str:
    """Build the UniFi voucher note: ``<locataire> <dates>``."""
    safe = sanitize_guest(guest)
    label = f"{safe} {check_in.isoformat()}/{check_out.isoformat()}"
    return label[:80]


def slug_username(guest: str, key: str) -> str:
    """Build a lowercase HA username unique to this stay.

    The built-in provider rejects a username that is not already casefolded.
    """
    base = re.sub(r"[^a-z0-9]+", "-", sanitize_guest(guest).casefold()).strip("-")
    base = base[:18]
    suffix = hashlib.sha256(key.encode()).hexdigest()[:6]
    if base:
        username = f"loc-{base}-{suffix}"
    else:
        username = f"loc-{suffix}"
    return username[:32]


def stay_key(
    *,
    uid: str | None,
    recurrence_id: str | None,
    guest: str,
    check_in: date,
    check_out: date,
) -> str:
    """Stable id. UID is preferred; otherwise guest and dates."""
    if uid:
        rid = recurrence_id or check_in.isoformat()
        return f"{uid}|{rid}"
    raw = f"{guest.casefold()}|{check_in.isoformat()}|{check_out.isoformat()}"
    return hashlib.sha256(raw.encode()).hexdigest()[:20]


def time_limit_minutes(check_in: datetime, check_out: datetime, extra_days: int) -> int:
    """Stay length plus the configured extra day, in minutes.

    UniFi starts this clock at the first portal authorization, not at
    check-in. See the README.
    """
    delta = (check_out - check_in) + timedelta(days=extra_days)
    minutes = int(delta.total_seconds() // 60)
    return max(minutes, 60)


def mbps_to_kbps(mbps: float | int) -> int:
    """Convert Mbit/s to the kbit/s unit of the Integration API."""
    return max(int(float(mbps) * KBPS_PER_MBPS), 1)


def _as_local_midnight(value: date, tzinfo: datetime.tzinfo | None) -> datetime:
    midnight = datetime.combine(value, time.min)
    if tzinfo is not None:
        return midnight.replace(tzinfo=tzinfo)
    return midnight


def _aware(value: datetime, tz: datetime.tzinfo | None) -> datetime:
    if value.tzinfo is None and tz is not None:
        return value.replace(tzinfo=tz)
    return value


def normalize_event(
    *,
    summary: str,
    start: datetime | date,
    end: datetime | date,
    uid: str | None = None,
    recurrence_id: str | None = None,
    status: str | None = None,
    blocklist: tuple[str, ...] = (),
    max_stay_days: int = DEFAULT_MAX_STAY_DAYS,
    tz: datetime.tzinfo | None = None,
) -> CalendarStay | None:
    """Convert one calendar event into a stay, or drop it.

    All-day events use an exclusive end date, which is the checkout morning.
    ``tz`` is applied to floating values so they can be compared with ``now``.
    """
    if status and str(status).casefold() in {"cancelled", "canceled"}:
        return None
    if is_blocked_title(summary or "", blocklist):
        return None

    if isinstance(start, datetime):
        check_in = _aware(start, tz)
    else:
        check_in = _as_local_midnight(start, tz)

    if isinstance(end, datetime):
        check_out = _aware(end, tz)
    else:
        check_out = _as_local_midnight(end, tz)

    if check_out <= check_in:
        return None
    if check_out - check_in > timedelta(days=max_stay_days):
        return None

    guest = sanitize_guest(summary or "")
    key = stay_key(
        uid=uid,
        recurrence_id=recurrence_id,
        guest=guest,
        check_in=check_in.date(),
        check_out=check_out.date(),
    )
    return CalendarStay(
        key=key,
        guest=guest,
        check_in=check_in,
        check_out=check_out,
        summary=summary or guest,
    )


def build_plan(
    stays: list[CalendarStay],
    *,
    now: datetime,
    lead_days: int = DEFAULT_LEAD_DAYS,
    extra_days: int = DEFAULT_EXTRA_DAYS,
    device_limit: int = DEFAULT_DEVICE_LIMIT,
    download_mbps: float | int = DEFAULT_DOWNLOAD_MBPS,
    upload_mbps: float | int = DEFAULT_UPLOAD_MBPS,
    access_mode: str = ACCESS_PER_STAY,
    known_keys: list[str] | None = None,
) -> SyncPlan:
    """Decide which stays are active and which stored keys must be revoked.

    A stay is provisioned from ``lead_days`` before check-in until check-out.
    A known key that disappeared from the calendar is treated as a cancellation
    when it was previously stored (the caller only passes keys it still tracks).
    """
    ensure: list[StayPlan] = []
    active_keys: set[str] = set()
    lead = timedelta(days=lead_days)

    for stay in stays:
        active_keys.add(stay.key)
        window_open = stay.check_in - lead
        if now < window_open or now >= stay.check_out:
            continue
        spec = VoucherSpec(
            name=voucher_name(stay.guest, stay.check_in.date(), stay.check_out.date()),
            time_limit_minutes=time_limit_minutes(
                stay.check_in, stay.check_out, extra_days
            ),
            authorized_guest_limit=max(int(device_limit), 1),
            rx_rate_limit_kbps=mbps_to_kbps(download_mbps),
            tx_rate_limit_kbps=mbps_to_kbps(upload_mbps),
        )
        if access_mode == ACCESS_SHARED:
            username = SHARED_USERNAME
        else:
            username = slug_username(stay.guest, stay.key)
        ensure.append(
            StayPlan(
                key=stay.key,
                guest=stay.guest,
                check_in=stay.check_in,
                check_out=stay.check_out,
                voucher=spec,
                username=username,
            )
        )

    ensured_keys = {item.key for item in ensure}
    revoke_list: list[str] = []
    for key in known_keys or []:
        if key in ensured_keys:
            continue
        # Disappeared from the calendar (cancellation) or no longer inside
        # the provisioning window (checkout, or check-in postponed).
        revoke_list.append(key)

    shared = SHARED_USERNAME if access_mode == ACCESS_SHARED and ensure else None
    return SyncPlan(
        ensure=tuple(ensure),
        revoke_keys=tuple(dict.fromkeys(revoke_list)),
        shared_username=shared,
    )


def default_blocklist() -> tuple[str, ...]:
    """Blocklist applied when the option is left at its default."""
    return parse_blocklist(DEFAULT_TITLE_BLOCKLIST)


def select_current(stored: dict[str, dict], now: datetime) -> dict | None:
    """Pick the stay whose code the sensor should show."""
    covering: list[tuple[datetime, dict]] = []
    upcoming: list[tuple[datetime, dict]] = []
    for record in stored.values():
        if not record.get("voucher_code"):
            continue
        try:
            start = datetime.fromisoformat(str(record.get("check_in")))
            end = datetime.fromisoformat(str(record.get("check_out")))
        except (TypeError, ValueError):
            continue
        if start.tzinfo is None and now.tzinfo is not None:
            start = start.replace(tzinfo=now.tzinfo)
        if end.tzinfo is None and now.tzinfo is not None:
            end = end.replace(tzinfo=now.tzinfo)
        if start <= now < end:
            covering.append((start, record))
        elif now < start:
            upcoming.append((start, record))
    if covering:
        covering.sort(key=lambda item: item[0])
        return covering[0][1]
    if upcoming:
        upcoming.sort(key=lambda item: item[0])
        return upcoming[0][1]
    return None


def stored_keys_in_window(
    stored: dict[str, dict],
    window_start: datetime,
    window_end: datetime,
) -> list[str]:
    """Return stored stay keys that overlap the calendar query window.

    Keys outside the window are left untouched: the calendar was not asked
    about them, so their absence must not be treated as a cancellation.
    """
    keys: list[str] = []
    for key, record in stored.items():
        try:
            start = datetime.fromisoformat(str(record.get("check_in")))
            end = datetime.fromisoformat(str(record.get("check_out")))
        except (TypeError, ValueError):
            keys.append(key)
            continue
        if start.tzinfo is None and window_start.tzinfo is not None:
            start = start.replace(tzinfo=window_start.tzinfo)
        if end.tzinfo is None and window_start.tzinfo is not None:
            end = end.replace(tzinfo=window_start.tzinfo)
        if end >= window_start and start <= window_end:
            keys.append(key)
    return keys
