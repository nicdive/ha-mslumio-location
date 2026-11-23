"""Owner text helpers for the Console (manual Wi-Fi code draft)."""

from __future__ import annotations

from homeassistant.components.text import TextEntity, TextMode
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import UsvegliuRuntime


async def async_setup_entry(
    hass: HomeAssistant,
    entry: object,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Expose a draft field for pasting EasyPass codes into a stay."""
    runtime: UsvegliuRuntime = hass.data[DOMAIN][entry.entry_id]  # type: ignore[attr-defined]
    entity = WifiCodeDraftText(runtime)
    runtime.wifi_draft_entity = entity
    async_add_entities([entity])


class WifiCodeDraftText(TextEntity):
    """Scratchpad: paste an EasyPass code, then apply it on a stay card."""

    _attr_has_entity_name = True
    _attr_translation_key = "wifi_code_draft"
    _attr_icon = "mdi:wifi-cog"
    _attr_mode = TextMode.TEXT
    _attr_native_max = 64
    _attr_native_min = 0

    def __init__(self, runtime: UsvegliuRuntime) -> None:
        self._runtime = runtime
        self._attr_unique_id = f"{runtime.entry.entry_id}_wifi_code_draft"
        site = runtime.entry.data.get("site_name") or "Usvegliu"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, runtime.entry.entry_id)},
            name="Usvegliu",
            manufacturer="Usvegliu",
            model=f"Location courte durée ({site})",
        )
        self._attr_native_value = ""

    async def async_set_value(self, value: str) -> None:
        self._attr_native_value = str(value or "").strip()
        self.async_write_ha_state()

    async def async_take_value(self) -> str:
        """Return the draft and clear it (used when applying to a stay)."""
        code = str(self._attr_native_value or "").strip()
        self._attr_native_value = ""
        self.async_write_ha_state()
        return code
