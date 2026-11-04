"""Sensors exposing the current voucher code to the administrator."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import UsvegliuRuntime


async def async_setup_entry(
    hass: HomeAssistant,
    entry: object,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the voucher sensor."""
    runtime: UsvegliuRuntime = hass.data[DOMAIN][entry.entry_id]  # type: ignore[attr-defined]
    async_add_entities([VoucherCodeSensor(runtime)])


class VoucherCodeSensor(CoordinatorEntity, SensorEntity):
    """Current hotspot code. Not granted to the tenant policy."""

    _attr_has_entity_name = True
    _attr_translation_key = "voucher_code"
    _attr_icon = "mdi:ticket-confirmation"

    def __init__(self, runtime: UsvegliuRuntime) -> None:
        """Bind the coordinator."""
        super().__init__(runtime.coordinator)
        self._runtime = runtime
        self._attr_unique_id = f"{runtime.entry.entry_id}_voucher_code"
        site = runtime.entry.data.get("site_name") or "UniFi"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, runtime.entry.entry_id)},
            name="Usvegliu",
            manufacturer="Usvegliu",
            model=f"Location courte durée ({site})",
        )

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
        """Stay context. The tenant password is intentionally absent."""
        data = self.coordinator.data or {}
        return {
            "guest": data.get("guest"),
            "check_in": data.get("check_in"),
            "check_out": data.get("check_out"),
            "voucher_id": data.get("voucher_id"),
            "username": data.get("username"),
            "reservation_id": data.get("reservation_id"),
            "devices": data.get("devices"),
            "download_mbps": data.get("download_mbps"),
            "upload_mbps": data.get("upload_mbps"),
            "stay_count": data.get("stay_count"),
        }
