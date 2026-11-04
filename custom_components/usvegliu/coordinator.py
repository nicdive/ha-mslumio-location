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
    CONF_ALLOW_REMOTE,
    CONF_CLIMATE_ENTITIES,
    CONF_COVER_ENTITIES,
    CONF_DEVICE_LIMIT,
    CONF_DOWNLOAD_MBPS,
    CONF_ENABLE_ACCESS,
    CONF_ENABLE_VOUCHERS,
    CONF_EXTRA_DAYS,
    CONF_GUEST_BASE_URL,
    CONF_HOST,
    CONF_JOURNAL_PATH,
    CONF_LEAD_DAYS,
    CONF_LIGHT_ENTITIES,
    CONF_TENANT_DEVICES,
    CONF_TENANT_ENTITIES,
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
    DASHBOARD_URL,
    DOMAIN,
    EVENT_JOURNAL,
    EVENT_PRINT,
    STORAGE_VERSION,
    UPDATE_INTERVAL,
)
from .dashboard import async_ensure_dashboard
from .engine import async_synchronize
from .guest_session import (
    PREVIEW_KEY,
    build_preview_record,
    find_record_by_token,
    guest_path,
    issued_account_view,
    open_issued_records,
    public_guest_url,
    stay_is_open,
)
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

    def __init__(self, runtime: UsvegliuRuntime) -> None:
        self._runtime = runtime

    async def async_ensure_user(self, **kwargs: Any) -> dict[str, str | None]:
        from .access import async_ensure_user

        return await async_ensure_user(self._runtime.hass, **kwargs)

    async def async_revoke_user(self, user_id: str) -> None:
        from .access import async_revoke_user

        await async_revoke_user(self._runtime.hass, user_id)


class UsvegliuRuntime:
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
        self._overrides: dict[str, dict[str, Any]] = {}
        self._preview: dict[str, Any] | None = None
        self._lock = asyncio.Lock()
        self.coordinator: DataUpdateCoordinator[dict[str, Any]] | None = None
        self._accounts = _AccountBridge(self)
        self._dashboard_signature: str | None = None
        self._last_dashboard: dict[str, Any] = {}

    def tenant_entity_ids(self) -> list[str]:
        """Entities selected for tenants, including the previous three lists."""
        options = self.entry.options
        selected = list(options.get(CONF_TENANT_ENTITIES) or [])
        if selected:
            return selected
        legacy: list[str] = []
        for key in (CONF_CLIMATE_ENTITIES, CONF_COVER_ENTITIES, CONF_LIGHT_ENTITIES):
            legacy.extend(options.get(key) or [])
        return legacy

    def tenant_device_ids(self) -> list[str]:
        """Devices whose entities the tenant may use."""
        return list(self.entry.options.get(CONF_TENANT_DEVICES) or [])

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
            self._shared = _scrub_secrets(shared)
        overrides = raw.get("overrides")
        if isinstance(overrides, dict):
            self._overrides = overrides
        preview = raw.get("guest_preview")
        if isinstance(preview, dict):
            self._preview = _scrub_secrets(preview)
        self._stays = {key: _scrub_secrets(value) for key, value in self._stays.items()}
        self._refresh_log_filter()

    async def _persist(
        self,
        stays: dict[str, dict[str, Any]],
        shared: dict[str, Any] | None,
    ) -> None:
        self._stays = {key: _scrub_secrets(value) for key, value in stays.items()}
        self._shared = _scrub_secrets(shared) if isinstance(shared, dict) else shared
        await self.store.async_save(
            {
                "stays": self._stays,
                "shared_user": self._shared,
                "overrides": self._overrides,
                "guest_preview": self._preview,
            }
        )
        self._refresh_log_filter()

    def _refresh_log_filter(self) -> None:
        secrets = [str(self.entry.data.get(CONF_API_KEY) or "")]
        for record in self._stays.values():
            secrets.append(str(record.get("voucher_code") or ""))
            secrets.append(str(record.get("guest_token") or ""))
            secrets.append(str(record.get("password") or ""))
        if self._shared:
            secrets.append(str(self._shared.get("password") or ""))
        if self._preview:
            secrets.append(str(self._preview.get("guest_token") or ""))
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
                allow_remote=bool(options.get(CONF_ALLOW_REMOTE, False)),
                entity_ids=self.tenant_entity_ids(),
                device_ids=self.tenant_device_ids(),
                overrides=self._overrides,
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
            lines.append(
                "Ce mot de passe n'est pas archivé. Notez-le maintenant : "
                "il disparaît avec cette notification."
            )
        elif note.get("username"):
            lines.append(
                "Le mot de passe n'est pas conservé. "
                "Régénérez l'accès pour en afficher un nouveau."
            )
        lines.append(f"Tableau de bord : /{DASHBOARD_URL}")
        stay = self._stays.get(note.get("reservation_id") or "")
        token = (stay or {}).get("guest_token") or note.get("guest_token")
        if token:
            link = self.guest_link({"guest_token": token, "key": note.get("reservation_id")})
            lines.append(f"Lien maison : {link['url']}")
        message = "\n".join(lines)
        notification_id = f"{DOMAIN}_{note.get('reservation_id') or 'sejour'}"
        await self.hass.services.async_call(
            "persistent_notification",
            "create",
            {
                "title": f"Usvegliu — {note.get('guest') or 'Séjour'}",
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
                {"title": f"Usvegliu — {note.get('guest') or 'Séjour'}", "message": message},
                blocking=False,
            )

    async def _async_dismiss(self, key: str) -> None:
        if not self.hass.services.has_service("persistent_notification", "dismiss"):
            return
        await self.hass.services.async_call(
            "persistent_notification",
            "dismiss",
            {"notification_id": f"{DOMAIN}_{key}"},
            blocking=False,
        )

    async def _async_dashboard(self) -> None:
        from homeassistant.helpers import issue_registry as ir

        entities = self._dashboard_entity_ids()
        signature = repr(entities)
        if signature == self._dashboard_signature:
            return
        try:
            outcome = await async_ensure_dashboard(self.hass, entities)
        except Exception:  # noqa: BLE001 — dashboard failure must not revoke access
            _LOGGER.warning("Tableau de bord Usvegliu non mis à jour")
            outcome = {"ok": False, "reason": "exception", "url": DASHBOARD_URL}
        self._last_dashboard = outcome
        if outcome.get("ok"):
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
                translation_placeholders={"url_path": DASHBOARD_URL},
            )

    def _dashboard_entity_ids(self) -> list[str]:
        """Entities to show, plus every entity of a selected device."""
        return self.expand_entity_ids(self.tenant_entity_ids(), self.tenant_device_ids())

    def expand_entity_ids(self, entity_ids: list[str], device_ids: list[str]) -> list[str]:
        """Merge explicit entities with every entity of the chosen devices."""
        from .access import unique_strings

        entities = unique_strings(entity_ids)
        devices = set(device_ids or [])
        if not devices:
            return entities
        try:
            from homeassistant.helpers import entity_registry as er

            registry = er.async_get(self.hass)
        except Exception:  # noqa: BLE001 — registry is optional for the cards
            return entities
        for entry in registry.entities.values():
            if entry.device_id not in devices or entry.disabled_by is not None:
                continue
            if entry.entity_id not in entities:
                entities.append(entry.entity_id)
        return entities

    def allowed_entity_ids(self, record: dict[str, Any]) -> list[str]:
        """Entities this stay (or the preview) may read and control."""
        from .access import resolve_stay_access

        if record.get("preview") or record.get("key") == PREVIEW_KEY:
            entities, devices = self.tenant_entity_ids(), self.tenant_device_ids()
        else:
            entities, devices, _remote = resolve_stay_access(
                str(record.get("key") or ""),
                overrides=self._overrides,
                entity_ids=self.tenant_entity_ids(),
                device_ids=self.tenant_device_ids(),
                allow_remote=bool(self.entry.options.get(CONF_ALLOW_REMOTE, False)),
            )
        return self.expand_entity_ids(entities, devices)

    def guest_record(self, token: str) -> dict[str, Any] | None:
        """Stay or preview bound to the URL token, if still valid."""
        return find_record_by_token(self._stays, self._preview, token, dt_util.now())

    def guest_link(self, record: dict[str, Any]) -> dict[str, str]:
        """Admin-facing path and public URL for one token."""
        token = str(record.get("guest_token") or "")
        path = guest_path(token) if token else ""
        configured = str(self.entry.options.get(CONF_GUEST_BASE_URL) or "").strip()
        url = public_guest_url(configured, token) if token else ""
        if token and url.startswith("/"):
            origin = getattr(self.hass.config, "internal_url", None) or getattr(
                self.hass.config, "external_url", None
            )
            if origin:
                url = f"{str(origin).rstrip('/')}{path}"
        return {
            "path": path,
            "url": url,
            "reservation_id": str(record.get("key") or ""),
            "guest": str(record.get("guest") or ""),
            "check_out": str(record.get("check_out") or ""),
        }

    async def _async_guest_link(self, data: dict[str, Any]) -> dict[str, Any]:
        """Return (and optionally mint) a guest URL without talking to UniFi."""
        if data.get("essai"):
            self._preview = build_preview_record(dt_util.now())
            await self._persist(self._stays, self._shared)
            link = self.guest_link(self._preview)
            await self._async_notify(
                {
                    "reservation_id": PREVIEW_KEY,
                    "guest": "Essai",
                    "check_in": str(self._preview.get("check_in") or ""),
                    "check_out": str(self._preview.get("check_out") or ""),
                    "guest_token": str(self._preview.get("guest_token") or ""),
                }
            )
            return {**link, "essai": True}
        key = data.get("reservation_key")
        resolved = self._resolve_key(str(key) if key else None)
        record = self._stays.get(resolved)
        if record is None:
            raise UpdateFailed("unknown_reservation")
        from .guest_session import ensure_guest_token

        ensure_guest_token(record)
        await self._persist(self._stays, self._shared)
        return {**self.guest_link(record), "essai": False}

    def _device_sensitive(self, device_ids: list[str]) -> list[str]:
        if not device_ids:
            return []
        try:
            from homeassistant.helpers import entity_registry as er

            registry = er.async_get(self.hass)
        except Exception:  # noqa: BLE001
            return []
        from .const import SENSITIVE_DOMAINS

        wanted = set(device_ids)
        return [
            entry.entity_id
            for entry in registry.entities.values()
            if entry.device_id in wanted and entry.domain in SENSITIVE_DOMAINS
        ]

    def _apply_stay_settings(self, data: dict[str, Any]) -> None:
        """Store a per-reservation override. Empty lists replace the global choice."""
        from .access import sensitive_entity_ids

        key = str(data.get("reservation_key") or "").strip()
        if not key:
            raise UpdateFailed("unknown_reservation")
        if data.get("reset"):
            self._overrides.pop(key, None)
            return
        current = dict(self._overrides.get(key) or {})
        if "entity_ids" in data:
            current["entity_ids"] = list(data.get("entity_ids") or [])
        if "device_ids" in data:
            current["device_ids"] = list(data.get("device_ids") or [])
        if "allow_remote" in data:
            mode = str(data.get("allow_remote") or "inherit")
            if mode == "remote":
                current["allow_remote"] = True
            elif mode == "local":
                current["allow_remote"] = False
            else:
                current.pop("allow_remote", None)
        sensitive = sensitive_entity_ids(list(current.get("entity_ids") or []))
        sensitive.extend(self._device_sensitive(list(current.get("device_ids") or [])))
        if sensitive and not data.get("confirm_sensitive"):
            raise UpdateFailed("sensitive_entities")
        self._overrides[key] = current

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
            for record in self._stays.values():
                if record.get("guest_token") and stay_is_open(record, now):
                    return str(record["key"])
            raise UpdateFailed("no_active_stay")
        return str(current["key"])

    async def async_handle_service(self, call: ServiceCall) -> dict[str, Any]:
        """Execute an admin service and return a response without extra secrets."""
        await _async_require_admin(self.hass, call)
        key = call.data.get("reservation_key")
        action = call.service
        if action == "lien_maison":
            async with self._lock:
                return await self._async_guest_link(call.data)
        async with self._lock:
            resolved = None
            if action == "reglages_sejour":
                self._apply_stay_settings(call.data)
            elif action not in {"appliquer_tableau", "exporter_journal"}:
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
        if action == "appliquer_tableau":
            return {
                "delivered": True,
                **(self._last_dashboard or {}),
            }
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


def _scrub_secrets(record: dict[str, Any]) -> dict[str, Any]:
    """Keep the owner password on the private stay store; drop aliases."""
    cleaned = dict(record)
    if not cleaned.get("password") and cleaned.get("mot_de_passe"):
        cleaned["password"] = cleaned["mot_de_passe"]
    cleaned.pop("mot_de_passe", None)
    return cleaned


def _issued_rows(
    runtime: UsvegliuRuntime,
    stays: dict[str, dict[str, Any]],
    shared: dict[str, Any] | None,
    now: object,
) -> list[dict[str, Any]]:
    """Admin roster: every issued stay still open, plus a live preview."""
    rows: list[dict[str, Any]] = []
    for record in open_issued_records(stays, runtime._preview, now):  # type: ignore[arg-type]
        link = runtime.guest_link(record)
        username = (shared or {}).get("username") or record.get("username")
        password = (shared or {}).get("password") or record.get("password")
        rows.append(
            issued_account_view(
                record,
                username=None if username is None else str(username),
                password=None if password is None else str(password),
                lien_maison=str(link.get("url") or ""),
                path=str(link.get("path") or ""),
                tableau=f"/{DASHBOARD_URL}",
            )
        )
    return rows


def _snapshot(
    stays: dict[str, dict[str, Any]],
    shared: dict[str, Any] | None,
    now: object,
    runtime: UsvegliuRuntime,
) -> dict[str, Any]:
    rows = _issued_rows(runtime, stays, shared, now)
    current = select_current(stays, now)  # type: ignore[arg-type]
    lien_maison = None
    password = None
    if current is not None:
        key = str(current.get("key") or "")
        for row in rows:
            if row.get("reservation_id") == key:
                lien_maison = row.get("lien_maison")
                password = row.get("password")
                break
    common = {
        "stays": rows,
        "stay_count": len(rows),
        "lien_maison": lien_maison,
        "password": password,
        "devices": runtime._option_int(CONF_DEVICE_LIMIT, DEFAULT_DEVICE_LIMIT),
        "download_mbps": runtime._option_int(CONF_DOWNLOAD_MBPS, DEFAULT_DOWNLOAD_MBPS),
        "upload_mbps": runtime._option_int(CONF_UPLOAD_MBPS, DEFAULT_UPLOAD_MBPS),
    }
    if current is None:
        return {
            "voucher_code": None,
            "guest": None,
            "check_in": None,
            "check_out": None,
            "voucher_id": None,
            "username": None,
            "reservation_id": None,
            **common,
        }
    return {
        "voucher_code": current.get("voucher_code"),
        "guest": current.get("guest"),
        "check_in": current.get("check_in"),
        "check_out": current.get("check_out"),
        "voucher_id": current.get("voucher_id"),
        "username": (shared or {}).get("username") or current.get("username"),
        "reservation_id": current.get("key"),
        **common,
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
