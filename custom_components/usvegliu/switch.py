"""Owner switch that fills the guest web app with a demo villa."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .coordinator import UsvegliuRuntime
from .sensor import _device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: object,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create the demo-mode switch on the Usvegliu device."""
    runtime: UsvegliuRuntime = hass.data[DOMAIN][entry.entry_id]  # type: ignore[attr-defined]
    async_add_entities([DemoModeSwitch(runtime)])


class DemoModeSwitch(SwitchEntity, RestoreEntity):
    """Turn on a full fake villa in Maison (ten climates, car charging, …)."""

    _attr_has_entity_name = True
    _attr_translation_key = "demo_mode"
    _attr_icon = "mdi:theater"

    def __init__(self, runtime: UsvegliuRuntime) -> None:
        """Bind the coordinator runtime."""
        self._runtime = runtime
        self._attr_unique_id = f"{runtime.entry.entry_id}_demo_mode"
        self._attr_device_info = _device_info(runtime)

    @property
    def is_on(self) -> bool:
        """True while the guest app shows the synthetic villa."""
        return self._runtime.demo_mode()

    async def async_added_to_hass(self) -> None:
        """Restore the last switch state after a Home Assistant restart."""
        await super().async_added_to_hass()
        if self._runtime.demo_mode():
            return
        last = await self.async_get_last_state()
        if last is not None and last.state == "on":
            await self._runtime.async_set_demo_mode(True)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Fill Maison with the demo catalog."""
        await self._runtime.async_set_demo_mode(True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Return Maison to the real (possibly empty) entity lists."""
        await self._runtime.async_set_demo_mode(False)
        self.async_write_ha_state()
