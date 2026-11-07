"""Sensors exposing issued stays to the administrator."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import MATCH_ALL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import UsvegliuRuntime
from .guest_session import credential_attribute_key


async def async_setup_entry(
    hass: HomeAssistant,
    entry: object,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the admin voucher, stay and settings sensors."""
    runtime: UsvegliuRuntime = hass.data[DOMAIN][entry.entry_id]  # type: ignore[attr-defined]
    async_add_entities(
        [
            VoucherCodeSensor(runtime),
            IssuedAccountsSensor(runtime),
            OwnerSettingsSensor(runtime),
        ]
    )


def _device_info(runtime: UsvegliuRuntime) -> DeviceInfo:
    site = runtime.entry.data.get("site_name") or "UniFi"
    return DeviceInfo(
        identifiers={(DOMAIN, runtime.entry.entry_id)},
        name="Usvegliu",
        manufacturer="Usvegliu",
        model=f"Location courte durée ({site})",
    )


class VoucherCodeSensor(CoordinatorEntity, SensorEntity):
    """Current hotspot code. Not granted to the tenant policy."""

    _attr_has_entity_name = True
    _attr_translation_key = "voucher_code"
    _attr_icon = "mdi:ticket-confirmation"
    _unrecorded_attributes = frozenset(
        {"password", "mot_de_passe", "code_compte", "lien_maison", "username"}
    )

    def __init__(self, runtime: UsvegliuRuntime) -> None:
        """Bind the coordinator."""
        super().__init__(runtime.coordinator)
        self._runtime = runtime
        self._attr_unique_id = f"{runtime.entry.entry_id}_voucher_code"
        self._attr_device_info = _device_info(runtime)

    @property
    def native_value(self) -> str | None:
        """Return the code, or ``aucun`` when no stay is provisioned."""
        data = self.coordinator.data or {}
        code = data.get("voucher_code")
        if not code:
            return "aucun"
        return str(code)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Stay context for the owner, including the tenant password."""
        data = self.coordinator.data or {}
        secret = data.get("password")
        return {
            "guest": data.get("guest"),
            "check_in": data.get("check_in"),
            "check_out": data.get("check_out"),
            "voucher_id": data.get("voucher_id"),
            "username": data.get("username"),
            "password": secret,
            "mot_de_passe": secret,
            "code_compte": secret,
            "reservation_id": data.get("reservation_id"),
            "lien_maison": data.get("lien_maison"),
            "devices": data.get("devices"),
            "download_mbps": data.get("download_mbps"),
            "upload_mbps": data.get("upload_mbps"),
            "stay_count": data.get("stay_count"),
        }


class IssuedAccountsSensor(CoordinatorEntity, SensorEntity):
    """Every issued stay still open: username, password, Wi-Fi code, Maison link.

    Owner-only. Dismissing the persistent notification does not drop this
    roster; checkout does. Logs, diagnostics and the CSV still hide the
    password. Attributes are not recorded (they include plaintext secrets).
    """

    _attr_has_entity_name = True
    _attr_translation_key = "sejours"
    _attr_icon = "mdi:account-group"
    _unrecorded_attributes = frozenset({MATCH_ALL})

    def __init__(self, runtime: UsvegliuRuntime) -> None:
        """Bind the coordinator."""
        super().__init__(runtime.coordinator)
        self._runtime = runtime
        self._attr_unique_id = f"{runtime.entry.entry_id}_sejours"
        self._attr_device_info = _device_info(runtime)

    @property
    def native_value(self) -> str:
        """Guest of the first stay, or ``aucun``."""
        stays = list((self.coordinator.data or {}).get("stays") or [])
        if not stays:
            return "aucun"
        first = str(stays[0].get("guest") or "Séjour")
        extra = len(stays) - 1
        if extra:
            return f"{first} (+{extra})"
        return first

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Roster for the owner, including tenant passwords."""
        data = self.coordinator.data or {}
        stays = list(data.get("stays") or [])
        comptes: dict[str, dict[str, str]] = {}
        attrs: dict[str, Any] = {
            "count": len(stays),
            "stays": stays,
            "historique": list(data.get("historique") or []),
            "journal": list(data.get("journal") or []),
            "comptes": comptes,
            "wifi_ssid": self._runtime.wifi_ssid(),
            "reseau_wifi": self._runtime.wifi_ssid(),
        }
        for row in stays:
            reservation_id = str(row.get("reservation_id") or "")
            if not reservation_id:
                continue
            secret = str(
                row.get("code_compte")
                or row.get("mot_de_passe")
                or row.get("password")
                or ""
            )
            identifiant = str(row.get("username") or "")
            comptes[reservation_id] = {
                "identifiant": identifiant,
                "mot_de_passe": secret,
                "code_compte": secret,
            }
            # Flattened: the Lovelace entity card cannot read nested keys,
            # and the frontend hides the attribute name ``password``.
            attrs[credential_attribute_key(reservation_id)] = secret
        return attrs


class OwnerSettingsSensor(CoordinatorEntity, SensorEntity):
    """Live Usvegliu options for the owner console. No secrets."""

    _attr_has_entity_name = True
    _attr_translation_key = "reglages"
    _attr_icon = "mdi:tune"
    _unrecorded_attributes = frozenset({"settings"})

    def __init__(self, runtime: UsvegliuRuntime) -> None:
        """Bind the coordinator."""
        super().__init__(runtime.coordinator)
        self._runtime = runtime
        self._attr_unique_id = f"{runtime.entry.entry_id}_reglages"
        self._attr_device_info = _device_info(runtime)

    @property
    def native_value(self) -> str:
        """Calendar entity id, or ``réglages``."""
        settings = self._runtime.owner_settings()
        return str(settings.get("calendar") or "réglages")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Options currently in force, without API key or alarm code."""
        return {"settings": self._runtime.owner_settings()}
