"""Orchestrates the calendar, UniFi and Home Assistant accounts."""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import ConfigEntryAuthFailed, Unauthorized
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ACCESS_MODE,
    CONF_API_KEY,
    CONF_BASE_PATH,
    CONF_CALENDAR,
    CONF_CLIMATE_ENTITIES,
    CONF_COVER_ENTITIES,
    CONF_DEVICE_LIMIT,
    CONF_DOWNLOAD_MBPS,
    CONF_ENABLE_ACCESS,
    CONF_ENABLE_VOUCHERS,
    CONF_EXTRA_DAYS,
    CONF_HOST,
    CONF_JOURNAL_PATH,
    CONF_LEAD_DAYS,
    CONF_LIGHT_ENTITIES,
    CONF_LOOKAHEAD_DAYS,
    CONF_MAX_STAY_DAYS,
    CONF_NOTIFY_SERVICE,
    CONF_PORT,
    CONF_PRINT_EVENT,
    CONF_SITE_ID,
    CONF_TITLE_BLOCKLIST,
    CONF_UPLOAD_MBPS,
    CONF_VERIFY_SSL,
    DEFAULT_ACCESS_MODE,
    DEFAULT_DEVICE_LIMIT,
    DEFAULT_DOWNLOAD_MBPS,
    DEFAULT_EXTRA_DAYS,
    DEFAULT_JOURNAL_PATH,
    DEFAULT_LEAD_DAYS,
    DEFAULT_LOOKAHEAD_DAYS,
    DEFAULT_MAX_STAY_DAYS,
    DEFAULT_TITLE_BLOCKLIST,
    DEFAULT_UPLOAD_MBPS,
    DOMAIN,
    EVENT_JOURNAL,
    EVENT_PRINT,
    STORAGE_VERSION,
    UPDATE_INTERVAL,
)
from .dashboard import async_ensure_dashboard
from .engine import async_synchronize
from .journal import Journal, JournalPathError, resolve_journal_path
from .planning import (
    build_plan,
    normalize_event,
    parse_blocklist,
    select_current,
    stored_keys_in_window,
)
from .redact import SecretLogFilter, redact
from .unifi import UnifiAuthError, UnifiClient, UnifiError

_LOGGER = logging.getLogger(__name__)


def store_key(entry_id: str) -> str:
    """Storage key for one config entry. The file is private."""
    return f"{DOMAIN}.{entry_id}"


class _AccountBridge:
    """Adapter from the engine to the Home Assistant auth manager."""

    def __init__(self, runtime: LumioRuntime) -> None:
        self._runtime = runtime

    async def async_ensure_user(self, **kwargs: Any) -> dict[str, str | None]:
        from .access import async_ensure_user

        return await async_ensure_user(
            self._runtime.hass,
            entity_ids=self._runtime.tenant_entity_ids(),
            **kwargs,
        )

    async def async_revoke_user(self, user_id: str) -> None:
        from .access import async_revoke_user

        await async_revoke_user(self._runtime.hass, user_id)


class LumioRuntime:
    """Runtime state for one config entry."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: UnifiClient,
        journal: Journal,
        store: Store,
        log_filter: SecretLogFilter,
    ) -> None:
        """Bind the long-lived objects. The API key stays inside ``client``."""
        self.hass = hass
        self.entry = entry
        self.client = client
        self.journal = journal
        self.store = store
        self.log_filter = log_filter
        self._stays: dict[str, dict[str, Any]] = {}
        self._shared: dict[str, Any] | None = None
        self._force_voucher: set[str] = set()
        self._force_access: set[str] = set()
        self._resend: set[str] = set()
        self._print: set[str] = set()
        self._lock = asyncio.Lock()
        self.coordinator: DataUpdateCoordinator[dict[str, Any]] | None = None
        self._accounts = _AccountBridge(self)
        self._dashboard_signature: str | None = None

    def tenant_entity_ids(self) -> list[str]:
        """Entities the tenant group is allowed to read and control."""
        options = self.entry.options
        entities: list[str] = []
        for key in (CONF_CLIMATE_ENTITIES, CONF_COVER_ENTITIES, CONF_LIGHT_ENTITIES):
            entities.extend(options.get(key) or [])
        return entities

    async def async_load(self) -> None:
        """Load the private stay store."""
        raw = await self.store.async_load()
        if not isinstance(raw, dict):
            return
        stays = raw.get("stays")
        if isinstance(stays, dict):
            self._stays = stays
        shared = raw.get("shared_user")
        if isinstance(shared, dict):
            self._shared = shared
        self._refresh_log_filter()

    async def _persist(
        self,
        stays: dict[str, dict[str, Any]],
        shared: dict[str, Any] | None,
    ) -> None:
        self._stays = stays
        self._shared = shared
        await self.store.async_save({"stays": stays, "shared_user": shared})
        self._refresh_log_filter()

    def _refresh_log_filter(self) -> None:
        secrets = [str(self.entry.data.get(CONF_API_KEY) or "")]
        for record in self._stays.values():
            secrets.append(str(record.get("voucher_code") or ""))
            secrets.append(str(record.get("password") or ""))
        if self._shared:
            secrets.append(str(self._shared.get("password") or ""))
        self.log_filter.update(secrets, owner=self.entry.entry_id)

    def _option_int(self, key: str, default: int) -> int:
        try:
            return int(self.entry.options.get(key, default))
        except (TypeError, ValueError):
            return default

    async def async_sync(self) -> dict[str, Any]:
        """Run one cycle. Notifications are sent after the lock is released."""
        async with self._lock:
            snapshot, result = await self._sync_locked()
        await self._emit(result)
        if self.coordinator is not None:
            self.coordinator.async_set_updated_data(snapshot)
        return snapshot

    async def _sync_locked(self) -> tuple[dict[str, Any], Any]:
        options = self.entry.options
        now = dt_util.now()
        lookahead = self._option_int(CONF_LOOKAHEAD_DAYS, DEFAULT_LOOKAHEAD_DAYS)
        window_start = now - timedelta(days=2)
        window_end = now + timedelta(days=lookahead)
        calendar_events = await _async_calendar_events(
            self.hass,
            options.get(CONF_CALENDAR),
            window_start,
            window_end,
        )
        blocklist = parse_blocklist(
            options.get(CONF_TITLE_BLOCKLIST, DEFAULT_TITLE_BLOCKLIST)
        )
        max_stay = self._option_int(CONF_MAX_STAY_DAYS, DEFAULT_MAX_STAY_DAYS)
        parsed = []
        for event in calendar_events:
            status = getattr(event, "status", None)
            status_text = getattr(status, "value", status)
            stay = normalize_event(
                summary=getattr(event, "summary", "") or "",
                start=event.start,
                end=event.end,
                uid=getattr(event, "uid", None),
                recurrence_id=getattr(event, "recurrence_id", None),
                status=str(status_text) if status_text is not None else None,
                blocklist=blocklist,
                max_stay_days=max_stay,
                tz=now.tzinfo,
            )
            if stay is not None:
                parsed.append(stay)
        known = stored_keys_in_window(self._stays, window_start, window_end)
        plan = build_plan(
            parsed,
            now=now,
            lead_days=self._option_int(CONF_LEAD_DAYS, DEFAULT_LEAD_DAYS),
            extra_days=self._option_int(CONF_EXTRA_DAYS, DEFAULT_EXTRA_DAYS),
            device_limit=self._option_int(CONF_DEVICE_LIMIT, DEFAULT_DEVICE_LIMIT),
            download_mbps=self._option_int(CONF_DOWNLOAD_MBPS, DEFAULT_DOWNLOAD_MBPS),
            upload_mbps=self._option_int(CONF_UPLOAD_MBPS, DEFAULT_UPLOAD_MBPS),
            access_mode=options.get(CONF_ACCESS_MODE, DEFAULT_ACCESS_MODE),
            known_keys=known,
        )
        enable_vouchers = bool(options.get(CONF_ENABLE_VOUCHERS, True))
        enable_access = bool(options.get(CONF_ENABLE_ACCESS, True))
        try:
            result = await async_synchronize(
                plan,
                self._stays,
                self._shared,
                vouchers=self.client if enable_vouchers else None,
                accounts=self._accounts if enable_access else None,
                enable_vouchers=enable_vouchers,
                enable_access=enable_access,
                force_rotate_keys=set(self._force_access),
                force_voucher_keys=set(self._force_voucher),
                print_keys=set(self._print),
                resend_keys=set(self._resend),
                emit_print_on_create=bool(options.get(CONF_PRINT_EVENT, False)),
                on_progress=self._persist,
            )
        except UnifiAuthError as err:
            raise ConfigEntryAuthFailed from err
        except UnifiError as err:
            raise UpdateFailed(str(err)) from err
        finally:
            self._force_access.clear()
            self._force_voucher.clear()
            self._print.clear()
            self._resend.clear()

        self._stays = result.stays
        self._shared = result.shared_user
        await self._persist(result.stays, result.shared_user)
        for row in result.journal:
            await self.journal.async_append(row)
        await self._async_dashboard()
        snapshot = _snapshot(result.stays, result.shared_user, now, self)
        return snapshot, result

    async def _emit(self, result: object) -> None:
        """Fire events and notifications outside the sync lock."""
        for event in result.events:  # type: ignore[attr-defined]
            self.hass.bus.async_fire(EVENT_JOURNAL, event)
            if event.get("action") in {
                "voucher_supprime",
                "acces_supprime",
                "acces_desactive",
            }:
                await self._async_dismiss(str(event.get("reservation_id") or ""))
        for event in result.print_events:  # type: ignore[attr-defined]
            self.hass.bus.async_fire(EVENT_PRINT, event)
        for note in result.notifications:  # type: ignore[attr-defined]
            await self._async_notify(note)

    async def _async_notify(self, note: dict[str, str]) -> None:
        lines = [
            f"Locataire : {note.get('guest') or '—'}",
            f"Séjour : {note.get('check_in') or '—'} → {note.get('check_out') or '—'}",
        ]
        if note.get("code"):
            lines.append(f"Code Wi-Fi : {note['code']}")
        if note.get("username"):
            lines.append(f"Utilisateur Home Assistant : {note['username']}")
        if note.get("password"):
            lines.append(f"Mot de passe : {note['password']}")
        lines.append("Tableau de bord : /ms-lumio")
        message = "\n".join(lines)
        notification_id = f"ms_lumio_{note.get('reservation_id') or 'sejour'}"
        await self.hass.services.async_call(
            "persistent_notification",
            "create",
            {
                "title": f"MS Lumio — {note.get('guest') or 'Séjour'}",
                "message": message,
                "notification_id": notification_id,
            },
            blocking=True,
        )
        target = self.entry.options.get(CONF_NOTIFY_SERVICE) or ""
        if target:
            await self.hass.services.async_call(
                "notify",
                _notify_service_name(str(target)),
                {"title": f"MS Lumio — {note.get('guest') or 'Séjour'}", "message": message},
                blocking=False,
            )

    async def _async_dismiss(self, key: str) -> None:
        if not self.hass.services.has_service("persistent_notification", "dismiss"):
            return
        await self.hass.services.async_call(
            "persistent_notification",
            "dismiss",
            {"notification_id": f"ms_lumio_{key}"},
            blocking=False,
        )

    async def _async_dashboard(self) -> None:
        from homeassistant.helpers import issue_registry as ir

        options = self.entry.options
        signature = repr(self.tenant_entity_ids())
        if signature == self._dashboard_signature:
            return
        try:
            created = await async_ensure_dashboard(
                self.hass,
                climate=list(options.get(CONF_CLIMATE_ENTITIES) or []),
                covers=list(options.get(CONF_COVER_ENTITIES) or []),
                lights=list(options.get(CONF_LIGHT_ENTITIES) or []),
            )
        except Exception:  # noqa: BLE001 — dashboard failure must not revoke access
            _LOGGER.warning("Tableau de bord MS Lumio non mis à jour")
            created = False
        if created:
            self._dashboard_signature = signature
            ir.async_delete_issue(self.hass, DOMAIN, "dashboard_missing")
        else:
            ir.async_create_issue(
                self.hass,
                DOMAIN,
                "dashboard_missing",
                is_fixable=False,
                severity=ir.IssueSeverity.WARNING,
                translation_key="dashboard_missing",
                translation_placeholders={"url_path": "ms-lumio"},
            )

    def _resolve_key(self, key: str | None) -> str:
        if key:
            if key not in self._stays and not (
                self._shared and key == "shared"
            ):
                raise UpdateFailed("unknown_reservation")
            return key
        now = dt_util.now()
        current = select_current(self._stays, now)
        if current is None:
            raise UpdateFailed("no_active_stay")
        return str(current["key"])

    async def async_handle_service(self, call: ServiceCall) -> dict[str, Any]:
        """Execute an admin service and return a response without extra secrets."""
        await _async_require_admin(self.hass, call)
        key = call.data.get("reservation_key")
        action = call.service
        async with self._lock:
            resolved = None
            if action not in {"appliquer_tableau", "exporter_journal"}:
                resolved = self._resolve_key(key)
            if action == "regenerer_voucher" and resolved:
                self._force_voucher.add(resolved)
            elif action == "regenerer_acces" and resolved:
                self._force_access.add(resolved)
            elif action == "renvoyer_notification" and resolved:
                self._resend.add(resolved)
            elif action == "imprimer_voucher" and resolved:
                self._print.add(resolved)
            elif action == "appliquer_tableau":
                self._dashboard_signature = None
            snapshot, result = await self._sync_locked()
            printed = self._stays.get(resolved) if resolved else None
        await self._emit(result)
        if self.coordinator is not None:
            self.coordinator.async_set_updated_data(snapshot)
        if action == "exporter_journal":
            return {"path": str(self.journal.path)}
        if action == "imprimer_voucher":
            return {
                "reservation_id": resolved,
                "guest": None if printed is None else printed.get("guest"),
                "code": None if printed is None else printed.get("voucher_code"),
            }
        return {
            "reservation_id": snapshot.get("reservation_id"),
            "guest": snapshot.get("guest"),
            "delivered": True,
        }

    def diagnostics(self) -> dict[str, Any]:
        """Redacted diagnostics. Codes, passwords and the API key are removed."""
        return redact(
            {
                "entry_data": dict(self.entry.data),
                "options": dict(self.entry.options),
                "stay_count": len(self._stays),
                "stays": list(self._stays.values()),
                "shared_user": self._shared,
                "snapshot": None
                if self.coordinator is None
                else self.coordinator.data,
            }
        )


def _snapshot(
    stays: dict[str, dict[str, Any]],
    shared: dict[str, Any] | None,
    now: object,
    runtime: LumioRuntime,
) -> dict[str, Any]:
    current = select_current(stays, now)  # type: ignore[arg-type]
    if current is None:
        return {
            "voucher_code": None,
            "guest": None,
            "check_in": None,
            "check_out": None,
            "voucher_id": None,
            "username": None,
            "reservation_id": None,
            "stay_count": len(stays),
            "devices": runtime._option_int(CONF_DEVICE_LIMIT, DEFAULT_DEVICE_LIMIT),
            "download_mbps": runtime._option_int(
                CONF_DOWNLOAD_MBPS, DEFAULT_DOWNLOAD_MBPS
            ),
            "upload_mbps": runtime._option_int(CONF_UPLOAD_MBPS, DEFAULT_UPLOAD_MBPS),
        }
    return {
        "voucher_code": current.get("voucher_code"),
        "guest": current.get("guest"),
        "check_in": current.get("check_in"),
        "check_out": current.get("check_out"),
        "voucher_id": current.get("voucher_id"),
        "username": (shared or {}).get("username") or current.get("username"),
        "reservation_id": current.get("key"),
        "stay_count": len(stays),
        "devices": runtime._option_int(CONF_DEVICE_LIMIT, DEFAULT_DEVICE_LIMIT),
        "download_mbps": runtime._option_int(CONF_DOWNLOAD_MBPS, DEFAULT_DOWNLOAD_MBPS),
        "upload_mbps": runtime._option_int(CONF_UPLOAD_MBPS, DEFAULT_UPLOAD_MBPS),
    }


def _notify_service_name(target: str) -> str:
    """Accept ``notify.mobile_app_phone`` or ``mobile_app_phone``."""
    if target.startswith("notify."):
        return target.split(".", 1)[1]
    return target


async def _async_require_admin(hass: HomeAssistant, call: ServiceCall) -> None:
    user_id = call.context.user_id
    if not user_id:
        return
    user = await hass.auth.async_get_user(user_id)
    if user is None or not user.is_admin:
        raise Unauthorized()


async def _async_calendar_events(
    hass: HomeAssistant,
    entity_id: str | None,
    start: object,
    end: object,
) -> list[Any]:
    if not entity_id:
        raise UpdateFailed("calendar_missing")
    component = hass.data.get("calendar")
    entity = None
    if component is not None:
        getter = getattr(component, "get_entity", None)
        if callable(getter):
            entity = getter(entity_id)
    if entity is None:
        raise UpdateFailed("calendar_missing")
    try:
        return list(await entity.async_get_events(hass, start, end))
    except Exception as err:  # noqa: BLE001
        raise UpdateFailed("calendar_unavailable") from err


def build_client(hass: HomeAssistant, entry: ConfigEntry, session: object) -> UnifiClient:
    """Build the UniFi client from a config entry. The key is not logged."""
    data = entry.data
    return UnifiClient(
        session,  # type: ignore[arg-type]
        host=str(data[CONF_HOST]),
        port=int(data.get(CONF_PORT, 443)),
        api_key=str(data[CONF_API_KEY]),
        verify_ssl=bool(data.get(CONF_VERIFY_SSL, False)),
        base_path=str(data.get(CONF_BASE_PATH) or ""),
        site_id=str(data.get(CONF_SITE_ID) or ""),
    )


def build_journal(hass: HomeAssistant, entry: ConfigEntry) -> Journal:
    """Resolve the journal path inside the config or media directories."""
    media: list[Path] = []
    media_dirs = getattr(hass.config, "media_dirs", None) or {}
    if isinstance(media_dirs, dict):
        media = [Path(path) for path in media_dirs.values()]
    try:
        path = resolve_journal_path(
            Path(hass.config.config_dir),
            str(entry.options.get(CONF_JOURNAL_PATH) or DEFAULT_JOURNAL_PATH),
            media,
        )
    except JournalPathError as err:
        raise UpdateFailed("journal_path") from err
    return Journal(path)


def coordinator_interval() -> object:
    """Expose the poll interval for tests."""
    return UPDATE_INTERVAL


# Re-exported so service registration can name the response support without
# importing it from two places.
SERVICE_RESPONSE = SupportsResponse
