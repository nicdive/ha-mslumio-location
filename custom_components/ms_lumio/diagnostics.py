"""Diagnostics with secrets removed."""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import LumioRuntime


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: object
) -> dict[str, Any]:
    """Return redacted diagnostics for a config entry."""
    runtime: LumioRuntime = hass.data[DOMAIN][entry.entry_id]  # type: ignore[attr-defined]
    return runtime.diagnostics()
