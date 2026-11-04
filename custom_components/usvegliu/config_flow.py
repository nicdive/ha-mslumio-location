"""Config flow for Usvegliu."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    DeviceSelector,
    DeviceSelectorConfig,
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    CONF_ACCESS_MODE,
    CONF_ALLOW_REMOTE,
    CONF_API_KEY,
    CONF_BASE_PATH,
    CONF_CALENDAR,
    CONF_CLIMATE_ENTITIES,
    CONF_CONFIRM_SENSITIVE,
    CONF_COVER_ENTITIES,
    CONF_DEVICE_LIMIT,
    CONF_DOWNLOAD_MBPS,
    CONF_ENABLE_ACCESS,
    CONF_ENABLE_VOUCHERS,
    CONF_EXTRA_DAYS,
    CONF_GUEST_BASE_URL,
    CONF_HOUSE_MODE_ENTITY,
    CONF_JOURNAL_PATH,
    CONF_LEAD_DAYS,
    CONF_LIGHT_ENTITIES,
    CONF_LOOKAHEAD_DAYS,
    CONF_MAX_STAY_DAYS,
    CONF_NOTIFY_SERVICE,
    CONF_PRINT_EVENT,
    CONF_SITE_ID,
    CONF_SITE_NAME,
    CONF_TENANT_DEVICES,
    CONF_TENANT_ENTITIES,
    CONF_TITLE_BLOCKLIST,
    CONF_UPLOAD_MBPS,
    CONF_VERIFY_SSL,
    DEFAULT_DEVICE_LIMIT,
    DEFAULT_DOWNLOAD_MBPS,
    DEFAULT_EXTRA_DAYS,
    DEFAULT_JOURNAL_PATH,
    DEFAULT_LEAD_DAYS,
    DEFAULT_LOOKAHEAD_DAYS,
    DEFAULT_MAX_STAY_DAYS,
    DEFAULT_PORT,
    DEFAULT_TITLE_BLOCKLIST,
    DEFAULT_UPLOAD_MBPS,
    DOMAIN,
    ACCESS_PER_STAY,
)
from .access import sensitive_entity_ids
from .journal import JournalPathError, resolve_journal_path
from .unifi import (
    UnifiAuthError,
    UnifiClient,
    UnifiConnectionError,
    UnifiError,
    split_host_port,
)

_LOGGER = logging.getLogger(__name__)

_CONNECTION_KEYS = {
    CONF_HOST,
    CONF_PORT,
    CONF_API_KEY,
    CONF_VERIFY_SSL,
    CONF_SITE_ID,
    CONF_SITE_NAME,
    CONF_BASE_PATH,
}


def _number(min_value: int, max_value: int) -> NumberSelector:
    return NumberSelector(
        NumberSelectorConfig(
            min=min_value,
            max=max_value,
            step=1,
            mode=NumberSelectorMode.BOX,
        )
    )


def _default_entities(defaults: Mapping[str, Any]) -> list[str]:
    """Keep a previous climate/cover/light selection visible after the upgrade."""
    selected = list(defaults.get(CONF_TENANT_ENTITIES) or [])
    if selected:
        return selected
    legacy: list[str] = []
    for key in (CONF_CLIMATE_ENTITIES, CONF_COVER_ENTITIES, CONF_LIGHT_ENTITIES):
        legacy.extend(defaults.get(key) or [])
    return legacy


def _house_schema(defaults: Mapping[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(
                CONF_CALENDAR, default=defaults.get(CONF_CALENDAR, "")
            ): EntitySelector(EntitySelectorConfig(domain="calendar")),
            vol.Required(
                CONF_LEAD_DAYS, default=defaults.get(CONF_LEAD_DAYS, DEFAULT_LEAD_DAYS)
            ): _number(0, 30),
            vol.Required(
                CONF_DEVICE_LIMIT,
                default=defaults.get(CONF_DEVICE_LIMIT, DEFAULT_DEVICE_LIMIT),
            ): _number(1, 200),
            vol.Required(
                CONF_DOWNLOAD_MBPS,
                default=defaults.get(CONF_DOWNLOAD_MBPS, DEFAULT_DOWNLOAD_MBPS),
            ): _number(1, 10000),
            vol.Required(
                CONF_UPLOAD_MBPS,
                default=defaults.get(CONF_UPLOAD_MBPS, DEFAULT_UPLOAD_MBPS),
            ): _number(1, 10000),
            vol.Required(
                CONF_EXTRA_DAYS, default=defaults.get(CONF_EXTRA_DAYS, DEFAULT_EXTRA_DAYS)
            ): _number(0, 14),
            vol.Required(
                CONF_ACCESS_MODE,
                default=defaults.get(CONF_ACCESS_MODE, ACCESS_PER_STAY),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=[ACCESS_PER_STAY, "shared"],
                    translation_key="access_mode",
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(
                CONF_TENANT_ENTITIES,
                default=_default_entities(defaults),
            ): EntitySelector(EntitySelectorConfig(multiple=True)),
            vol.Optional(
                CONF_TENANT_DEVICES,
                default=defaults.get(CONF_TENANT_DEVICES, []),
            ): DeviceSelector(DeviceSelectorConfig(multiple=True)),
            vol.Required(
                CONF_CONFIRM_SENSITIVE,
                default=False,
            ): BooleanSelector(),
            vol.Required(
                CONF_ALLOW_REMOTE,
                default=defaults.get(CONF_ALLOW_REMOTE, False),
            ): BooleanSelector(),
            vol.Optional(
                CONF_NOTIFY_SERVICE, default=defaults.get(CONF_NOTIFY_SERVICE, "")
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
            vol.Optional(
                CONF_GUEST_BASE_URL,
                default=defaults.get(CONF_GUEST_BASE_URL, ""),
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
            **_house_mode_field(defaults),
            vol.Required(
                CONF_JOURNAL_PATH,
                default=defaults.get(CONF_JOURNAL_PATH, DEFAULT_JOURNAL_PATH),
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
            vol.Required(
                CONF_TITLE_BLOCKLIST,
                default=defaults.get(CONF_TITLE_BLOCKLIST, DEFAULT_TITLE_BLOCKLIST),
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
            vol.Required(
                CONF_MAX_STAY_DAYS,
                default=defaults.get(CONF_MAX_STAY_DAYS, DEFAULT_MAX_STAY_DAYS),
            ): _number(1, 365),
            vol.Required(
                CONF_LOOKAHEAD_DAYS,
                default=defaults.get(CONF_LOOKAHEAD_DAYS, DEFAULT_LOOKAHEAD_DAYS),
            ): _number(7, 365),
            vol.Required(
                CONF_ENABLE_VOUCHERS, default=defaults.get(CONF_ENABLE_VOUCHERS, True)
            ): BooleanSelector(),
            vol.Required(
                CONF_ENABLE_ACCESS, default=defaults.get(CONF_ENABLE_ACCESS, True)
            ): BooleanSelector(),
            vol.Required(
                CONF_PRINT_EVENT, default=defaults.get(CONF_PRINT_EVENT, False)
            ): BooleanSelector(),
        }
    )


def _clean_options(user_input: Mapping[str, Any]) -> dict[str, Any]:
    """Coerce selector numbers and drop connection secrets from options."""
    cleaned = dict(user_input)
    for key in (
        CONF_LEAD_DAYS,
        CONF_DEVICE_LIMIT,
        CONF_DOWNLOAD_MBPS,
        CONF_UPLOAD_MBPS,
        CONF_EXTRA_DAYS,
        CONF_MAX_STAY_DAYS,
        CONF_LOOKAHEAD_DAYS,
    ):
        if key in cleaned and cleaned[key] is not None:
            cleaned[key] = int(cleaned[key])
    legacy = []
    for key in (CONF_CLIMATE_ENTITIES, CONF_COVER_ENTITIES, CONF_LIGHT_ENTITIES):
        legacy.extend(cleaned.get(key) or [])
    selected = list(cleaned.get(CONF_TENANT_ENTITIES) or [])
    if not selected and legacy:
        selected = legacy
    cleaned[CONF_TENANT_ENTITIES] = selected
    cleaned[CONF_TENANT_DEVICES] = list(cleaned.get(CONF_TENANT_DEVICES) or [])
    cleaned[CONF_ALLOW_REMOTE] = bool(cleaned.get(CONF_ALLOW_REMOTE, False))
    cleaned.pop(CONF_CONFIRM_SENSITIVE, None)
    for key in (CONF_CLIMATE_ENTITIES, CONF_COVER_ENTITIES, CONF_LIGHT_ENTITIES):
        cleaned.pop(key, None)
    cleaned[CONF_NOTIFY_SERVICE] = str(cleaned.get(CONF_NOTIFY_SERVICE) or "").strip()
    cleaned[CONF_GUEST_BASE_URL] = str(cleaned.get(CONF_GUEST_BASE_URL) or "").strip()
    cleaned[CONF_HOUSE_MODE_ENTITY] = str(
        cleaned.get(CONF_HOUSE_MODE_ENTITY) or ""
    ).strip()
    return {key: value for key, value in cleaned.items() if key not in _CONNECTION_KEYS}


def _house_mode_field(defaults: Mapping[str, Any]) -> dict[Any, Any]:
    """Optional owner switch: on = climatisation, off = chauffage."""
    selector = EntitySelector(
        EntitySelectorConfig(
            domain=["switch", "input_boolean", "select", "input_select"],
            multiple=False,
        )
    )
    current = str(defaults.get(CONF_HOUSE_MODE_ENTITY) or "").strip()
    if current:
        return {vol.Optional(CONF_HOUSE_MODE_ENTITY, default=current): selector}
    return {vol.Optional(CONF_HOUSE_MODE_ENTITY): selector}


class UsvegliuConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Usvegliu."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize transient step state. The API key is not logged."""
        self._host = ""
        self._port = DEFAULT_PORT
        self._api_key = ""
        self._verify_ssl = False
        self._base_path = ""
        self._sites: list[tuple[str, str]] = []
        self._reauth = False

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect the controller address and the API key."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host, port = split_host_port(
                str(user_input[CONF_HOST]), int(user_input.get(CONF_PORT, DEFAULT_PORT))
            )
            api_key = str(user_input[CONF_API_KEY]).strip()
            verify_ssl = bool(user_input.get(CONF_VERIFY_SSL, False))
            if not host or not api_key:
                errors["base"] = "invalid_auth"
            else:
                try:
                    base_path, sites = await _async_connect(
                        host, port, api_key, verify_ssl, ""
                    )
                except UnifiAuthError:
                    errors["base"] = "invalid_auth"
                except UnifiConnectionError as err:
                    errors["base"] = (
                        "ssl_error" if str(err) == "tls_error" else "cannot_connect"
                    )
                except UnifiError:
                    errors["base"] = "cannot_connect"
                else:
                    if not sites:
                        errors["base"] = "no_sites"
                    else:
                        self._host = host
                        self._port = port
                        self._api_key = api_key
                        self._verify_ssl = verify_ssl
                        self._base_path = base_path
                        self._sites = [(site.id, site.name) for site in sites]
                        return await self.async_step_site()
        suggested = {
            CONF_HOST: user_input.get(CONF_HOST) if user_input else "",
            CONF_PORT: DEFAULT_PORT,
            CONF_VERIFY_SSL: False,
        }
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Required(CONF_HOST): str,
                        vol.Required(CONF_PORT, default=DEFAULT_PORT): _number(1, 65535),
                        vol.Required(CONF_API_KEY): TextSelector(
                            TextSelectorConfig(type=TextSelectorType.PASSWORD)
                        ),
                        vol.Required(CONF_VERIFY_SSL, default=False): BooleanSelector(),
                    }
                ),
                suggested,
            ),
            errors=errors,
        )

    async def async_step_site(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Pick the UniFi site. A single site is selected automatically."""
        if user_input is None and len(self._sites) == 1:
            user_input = {CONF_SITE_ID: self._sites[0][0]}
        if user_input is not None:
            site_id = str(user_input[CONF_SITE_ID])
            names = dict(self._sites)
            if site_id not in names:
                return self.async_show_form(
                    step_id="site",
                    data_schema=self._site_schema(),
                    errors={"base": "no_sites"},
                )
            await self.async_set_unique_id(f"{self._host}:{self._port}:{site_id}")
            if self._reauth:
                self._abort_if_unique_id_mismatch(reason="wrong_account")
            else:
                self._abort_if_unique_id_configured()
            self._connection = {
                CONF_HOST: self._host,
                CONF_PORT: self._port,
                CONF_API_KEY: self._api_key,
                CONF_VERIFY_SSL: self._verify_ssl,
                CONF_BASE_PATH: self._base_path,
                CONF_SITE_ID: site_id,
                CONF_SITE_NAME: names[site_id],
            }
            if self._reauth:
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(),
                    data_updates=self._connection,
                )
            return await self.async_step_house()
        return self.async_show_form(step_id="site", data_schema=self._site_schema())

    async def async_step_house(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect the calendar, voucher limits and tenant entities."""
        if user_input is not None:
            options = _clean_options(user_input)
            error = _house_error(
                self.hass,
                options,
                confirmed=bool(user_input.get(CONF_CONFIRM_SENSITIVE)),
            )
            if error:
                return self.async_show_form(
                    step_id="house",
                    data_schema=_house_schema(user_input),
                    errors={"base": error},
                )
            title = f"Usvegliu ({self._connection[CONF_SITE_NAME]})"
            return self.async_create_entry(
                title=title,
                data=self._connection,
                options=options,
            )
        return self.async_show_form(step_id="house", data_schema=_house_schema({}))

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start reauthentication when the API key is rejected."""
        self._reauth = True
        return await self.async_step_user()

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Replace the controller connection without logging the key."""
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()
        if user_input is not None:
            host, port = split_host_port(
                str(user_input[CONF_HOST]), int(user_input.get(CONF_PORT, DEFAULT_PORT))
            )
            api_key = str(user_input[CONF_API_KEY]).strip()
            verify_ssl = bool(user_input.get(CONF_VERIFY_SSL, False))
            try:
                base_path, sites = await _async_connect(
                    host, port, api_key, verify_ssl, ""
                )
            except UnifiAuthError:
                errors["base"] = "invalid_auth"
            except UnifiConnectionError as err:
                errors["base"] = (
                    "ssl_error" if str(err) == "tls_error" else "cannot_connect"
                )
            except UnifiError:
                errors["base"] = "cannot_connect"
            else:
                wanted = str(entry.data.get(CONF_SITE_ID) or "")
                match = next((site for site in sites if site.id == wanted), None)
                if match is None:
                    errors["base"] = "no_sites"
                else:
                    return self.async_update_reload_and_abort(
                        entry,
                        data_updates={
                            CONF_HOST: host,
                            CONF_PORT: port,
                            CONF_API_KEY: api_key,
                            CONF_VERIFY_SSL: verify_ssl,
                            CONF_BASE_PATH: base_path,
                            CONF_SITE_ID: match.id,
                            CONF_SITE_NAME: match.name,
                        },
                    )
        suggested = {
            CONF_HOST: entry.data.get(CONF_HOST, ""),
            CONF_PORT: entry.data.get(CONF_PORT, DEFAULT_PORT),
            CONF_VERIFY_SSL: entry.data.get(CONF_VERIFY_SSL, False),
        }
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema(
                    {
                        vol.Required(CONF_HOST): str,
                        vol.Required(CONF_PORT, default=DEFAULT_PORT): _number(1, 65535),
                        vol.Required(CONF_API_KEY): TextSelector(
                            TextSelectorConfig(type=TextSelectorType.PASSWORD)
                        ),
                        vol.Required(CONF_VERIFY_SSL, default=False): BooleanSelector(),
                    }
                ),
                suggested,
            ),
            errors=errors,
        )

    def _site_schema(self) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required(CONF_SITE_ID): SelectSelector(
                    SelectSelectorConfig(
                        options=[
                            {"label": name, "value": site_id}
                            for site_id, name in self._sites
                        ],
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                )
            }
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> UsvegliuOptionsFlow:
        """Return the options flow."""
        return UsvegliuOptionsFlow()


class UsvegliuOptionsFlow(OptionsFlow):
    """Adjust calendar, limits and tenant entities. The API key stays put."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the house options."""
        if user_input is not None:
            options = _clean_options(user_input)
            error = _house_error(
                self.hass,
                options,
                confirmed=bool(user_input.get(CONF_CONFIRM_SENSITIVE)),
            )
            if error:
                return self.async_show_form(
                    step_id="init",
                    data_schema=_house_schema(user_input),
                    errors={"base": error},
                )
            return self.async_create_entry(title="", data=options)
        return self.async_show_form(
            step_id="init",
            data_schema=_house_schema(self.config_entry.options),
        )


def _sensitive_device_entities(hass: Any, device_ids: list[str]) -> list[str]:
    """Entity ids of cameras, locks or alarms that belong to the chosen devices."""
    if not device_ids:
        return []
    try:
        from homeassistant.helpers import entity_registry as er
    except ImportError:
        return []
    registry = er.async_get(hass)
    wanted = set(device_ids)
    found: list[str] = []
    for entry in registry.entities.values():
        if entry.device_id in wanted and entry.domain in {"camera", "lock", "alarm_control_panel"}:
            found.append(entry.entity_id)
    return found


def _house_error(
    hass: Any,
    options: Mapping[str, Any],
    *,
    confirmed: bool,
) -> str | None:
    """Validate the calendar, the journal path and sensitive entities."""
    from pathlib import Path

    if not options.get(CONF_CALENDAR):
        return "calendar_missing"
    sensitive = sensitive_entity_ids(list(options.get(CONF_TENANT_ENTITIES) or []))
    sensitive.extend(
        _sensitive_device_entities(hass, list(options.get(CONF_TENANT_DEVICES) or []))
    )
    if sensitive and not confirmed:
        return "sensitive_entities"
    media: list[Path] = []
    media_dirs = getattr(hass.config, "media_dirs", None) or {}
    if isinstance(media_dirs, dict):
        media = [Path(path) for path in media_dirs.values()]
    try:
        resolve_journal_path(
            Path(hass.config.config_dir),
            str(options.get(CONF_JOURNAL_PATH) or ""),
            media,
        )
    except JournalPathError:
        return "invalid_path"
    return None


async def _async_connect(
    host: str,
    port: int,
    api_key: str,
    verify_ssl: bool,
    base_path: str,
) -> tuple[str, list[Any]]:
    """Probe the controller. The key is only placed in the request header."""
    async with aiohttp.ClientSession() as session:
        client = UnifiClient(
            session,
            host=host,
            port=port,
            api_key=api_key,
            verify_ssl=verify_ssl,
            base_path=base_path,
        )
        resolved = await client.async_probe_base_path()
        sites = await client.async_list_sites()
        _LOGGER.debug(
            "Contrôleur UniFi joint sur %s:%s (préfixe %s, %s site(s))",
            host,
            port,
            resolved,
            len(sites),
        )
        return resolved, sites
