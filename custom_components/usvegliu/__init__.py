"""Usvegliu: vouchers UniFi and tenant access driven by a calendar.

Home Assistant imports stay inside the setup functions so the pure modules
(planning, UniFi client, journal) can be unit-tested without Home Assistant.
"""

from __future__ import annotations

import logging
from typing import Any

from .const import (
    ATTR_RESERVATION_KEY,
    CONF_API_KEY,
    CONF_VERIFY_SSL,
    DOMAIN,
    PLATFORMS,
    SERVICE_APPLY_DASHBOARD,
    SERVICE_EXPORT_JOURNAL,
    SERVICE_PRINT,
    SERVICE_REGENERATE_ACCESS,
    SERVICE_REGENERATE_VOUCHER,
    SERVICE_RESEND,
    SERVICE_STAY_SETTINGS,
    SERVICE_GUEST_LINK,
    STORAGE_VERSION,
)
from .redact import SecretLogFilter

_LOGGER = logging.getLogger(__name__)
_LOG_FILTER = SecretLogFilter()
_FILTERS_INSTALLED = False


async def async_setup_entry(hass: Any, entry: Any) -> bool:
    """Set up Usvegliu from a config entry."""
    import aiohttp

    from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
    from homeassistant.helpers.storage import Store
    from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

    from .const import UPDATE_INTERVAL
    from .coordinator import UsvegliuRuntime, build_client, build_journal, store_key
    from .unifi import UnifiAuthError, UnifiError
    _install_log_filter()
    _LOG_FILTER.update([str(entry.data.get(CONF_API_KEY) or "")], owner=entry.entry_id)
    if not entry.data.get(CONF_VERIFY_SSL, False):
        _LOGGER.warning(
            "Vérification TLS désactivée pour %s. Réservé au certificat "
            "auto-signé de l'UDM, sur le réseau local uniquement.",
            entry.data.get("host"),
        )

    session = aiohttp.ClientSession()
    client = build_client(hass, entry, session)
    try:
        if not client.base_path:
            await client.async_probe_base_path()
        else:
            await client.async_get_info()
    except UnifiAuthError as err:
        await session.close()
        raise ConfigEntryAuthFailed from err
    except UnifiError as err:
        if client.base_path:
            client.base_path = ""
            try:
                await client.async_probe_base_path()
            except UnifiError as probe_err:
                await session.close()
                raise ConfigEntryNotReady from probe_err
        else:
            await session.close()
            raise ConfigEntryNotReady from err

    journal = build_journal(hass, entry)
    store: Store = Store(hass, STORAGE_VERSION, store_key(entry.entry_id), private=True)
    runtime = UsvegliuRuntime(hass, entry, client, journal, store, _LOG_FILTER)
    runtime.session = session
    await runtime.async_load()

    from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

    from .const import UPDATE_INTERVAL

    async def _async_update() -> dict[str, Any]:
        async with runtime._lock:  # noqa: SLF001
            snapshot, result = await runtime._sync_locked()  # noqa: SLF001
        await runtime._emit(result)  # noqa: SLF001
        return snapshot

    coordinator: DataUpdateCoordinator[dict[str, Any]] = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_interval=UPDATE_INTERVAL,
        update_method=_async_update,
    )
    runtime.coordinator = coordinator
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = runtime
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        await session.close()
        hass.data[DOMAIN].pop(entry.entry_id, None)
        _LOG_FILTER.clear(entry.entry_id)
        raise
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    from .http import async_setup_http

    async_setup_http(hass)
    _async_register_services(hass)
    entry.async_on_unload(entry.add_update_listener(_async_reload))
    return True


async def _async_reload(hass: Any, entry: Any) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: Any, entry: Any) -> bool:
    """Unload the entry. Vouchers and accounts are left in place."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        runtime = hass.data[DOMAIN].pop(entry.entry_id, None)
        if runtime is not None:
            await runtime.session.close()
        _LOG_FILTER.clear(entry.entry_id)
        if not hass.data[DOMAIN]:
            for service in (
                SERVICE_REGENERATE_VOUCHER,
                SERVICE_REGENERATE_ACCESS,
                SERVICE_RESEND,
                SERVICE_PRINT,
                SERVICE_EXPORT_JOURNAL,
                SERVICE_APPLY_DASHBOARD,
                SERVICE_STAY_SETTINGS,
                SERVICE_GUEST_LINK,
            ):
                hass.services.async_remove(DOMAIN, service)
    return unloaded


async def async_remove_entry(hass: Any, entry: Any) -> None:
    """Delete vouchers and tenant users created by this entry."""
    import aiohttp

    from homeassistant.helpers.storage import Store

    from .coordinator import build_client, store_key
    from .unifi import UnifiError

    store: Store = Store(hass, STORAGE_VERSION, store_key(entry.entry_id), private=True)
    raw = await store.async_load()
    if not isinstance(raw, dict):
        return
    session = aiohttp.ClientSession()
    try:
        client = build_client(hass, entry, session)
        if not client.base_path:
            try:
                await client.async_probe_base_path()
            except UnifiError:
                client = None  # type: ignore[assignment]
                _LOGGER.warning(
                    "UniFi injoignable : les vouchers restent sur le contrôleur"
                )
        stays = raw.get("stays") if isinstance(raw.get("stays"), dict) else {}
        for record in stays.values():
            voucher_id = record.get("voucher_id")
            if client is not None and voucher_id:
                try:
                    await client.async_delete_voucher(str(voucher_id))
                except UnifiError:
                    _LOGGER.warning("Voucher non supprimé à la désinstallation")
            user_id = record.get("user_id")
            if user_id:
                from .access import TenantAccessError, async_revoke_user

                try:
                    await async_revoke_user(hass, str(user_id))
                except TenantAccessError:
                    _LOGGER.error("Compte administrateur ignoré à la désinstallation")
        shared = raw.get("shared_user")
        if isinstance(shared, dict) and shared.get("user_id"):
            from .access import TenantAccessError, async_revoke_user

            try:
                await async_revoke_user(hass, str(shared["user_id"]))
            except TenantAccessError:
                _LOGGER.error("Compte administrateur ignoré à la désinstallation")
    finally:
        await session.close()
    await store.async_remove()


def _async_register_services(hass: Any) -> None:
    import voluptuous as vol

    from homeassistant.core import ServiceCall, SupportsResponse

    service_schema = vol.Schema({vol.Optional(ATTR_RESERVATION_KEY): str})
    stay_schema = vol.Schema(
        {
            vol.Required(ATTR_RESERVATION_KEY): str,
            vol.Optional("entity_ids"): [str],
            vol.Optional("device_ids"): [str],
            vol.Optional("allow_remote"): vol.In(["inherit", "local", "remote"]),
            vol.Optional("confirm_sensitive"): bool,
            vol.Optional("reset"): bool,
        }
    )
    guest_schema = vol.Schema(
        {
            vol.Optional(ATTR_RESERVATION_KEY): str,
            vol.Optional("essai"): bool,
        }
    )
    if hass.services.has_service(DOMAIN, SERVICE_REGENERATE_VOUCHER):
        return

    async def _handle(call: ServiceCall) -> dict[str, Any]:
        runtime = _runtime_for_call(hass)
        return await runtime.async_handle_service(call)

    for service, response in (
        (SERVICE_REGENERATE_VOUCHER, SupportsResponse.OPTIONAL),
        (SERVICE_REGENERATE_ACCESS, SupportsResponse.OPTIONAL),
        (SERVICE_RESEND, SupportsResponse.OPTIONAL),
        (SERVICE_PRINT, SupportsResponse.OPTIONAL),
        (SERVICE_EXPORT_JOURNAL, SupportsResponse.OPTIONAL),
        (SERVICE_APPLY_DASHBOARD, SupportsResponse.OPTIONAL),
        (SERVICE_STAY_SETTINGS, SupportsResponse.OPTIONAL),
        (SERVICE_GUEST_LINK, SupportsResponse.OPTIONAL),
    ):
        if service == SERVICE_STAY_SETTINGS:
            schema = stay_schema
        elif service == SERVICE_GUEST_LINK:
            schema = guest_schema
        elif service in {SERVICE_APPLY_DASHBOARD, SERVICE_EXPORT_JOURNAL}:
            schema = vol.Schema({})
        else:
            schema = service_schema
        hass.services.async_register(
            DOMAIN,
            service,
            _handle,
            schema=schema,
            supports_response=response,
        )


def _runtime_for_call(hass: Any) -> Any:
    runtimes = list(hass.data.get(DOMAIN, {}).values())
    if not runtimes:
        from homeassistant.exceptions import HomeAssistantError

        raise HomeAssistantError("usvegliu_not_loaded")
    return runtimes[0]


def _install_log_filter() -> None:
    global _FILTERS_INSTALLED
    if _FILTERS_INSTALLED:
        return
    logging.getLogger(__name__).addFilter(_LOG_FILTER)
    logging.getLogger("aiohttp.client").addFilter(_LOG_FILTER)
    _FILTERS_INSTALLED = True
