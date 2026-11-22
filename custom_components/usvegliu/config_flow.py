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
    EntitySelector,
    EntitySelectorConfig,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TargetSelector,
    TargetSelectorConfig,
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
    CONF_CAMBIUM_CLIENT_ID,
    CONF_CAMBIUM_CLIENT_SECRET,
    CONF_CAMBIUM_PORTAL,
    CONF_CAMBIUM_VOUCHER_PLAN,
    CONF_ENABLE_ACCESS,
    CONF_ENABLE_NUKI,
    CONF_ENABLE_VOUCHERS,
    CONF_VOUCHER_PROVIDER,
    CONF_MANUAL_WIFI_CODE,
    CONF_NUKI_SMARTLOCK_ID,
    CONF_NUKI_TOKEN,
    CONF_EXTRA_DAYS,
    CONF_GUEST_BASE_URL,
    CONF_GUEST_MAIL_DAYS,
    CONF_GUEST_MAIL_SERVICE,
    CONF_GUEST_THEME,
    CONF_WIFI_SSID,
    DEFAULT_GUEST_THEME,
    THEME_LEDBURY,
    THEME_USVEGLIU,
    CONF_ALARM_CODE,
    CONF_HOUSE_MODE_ENTITY,
    CONF_OUTDOOR_TEMPERATURE,
    CONF_POOL_PH,
    CONF_POOL_TEMPERATURE,
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
    CONF_TENANT_TARGET,
    CONF_TITLE_BLOCKLIST,
    CONF_UPLOAD_MBPS,
    CONF_VERIFY_SSL,
    DEFAULT_DEVICE_LIMIT,
    DEFAULT_DOWNLOAD_MBPS,
    DEFAULT_EXTRA_DAYS,
    DEFAULT_GUEST_MAIL_DAYS,
    DEFAULT_JOURNAL_PATH,
    DEFAULT_LEAD_DAYS,
    DEFAULT_LOOKAHEAD_DAYS,
    DEFAULT_MAX_STAY_DAYS,
    DEFAULT_PORT,
    DEFAULT_TITLE_BLOCKLIST,
    DEFAULT_UPLOAD_MBPS,
    DEFAULT_VOUCHER_PROVIDER,
    DEFAULT_WIFI_SSID,
    DOMAIN,
    ACCESS_PER_STAY,
    VOUCHER_PROVIDER_CAMBIUM,
    VOUCHER_PROVIDER_MANUAL,
    VOUCHER_PROVIDER_UNIFI,
)
from .access import sensitive_entity_ids
from .journal import JournalPathError, resolve_journal_path
from .target_options import (
    as_id_list as _as_id_list,
    default_entities as _default_entities,
    expand_tenant_target as _expand_tenant_target,
    tenant_target_default as _tenant_target_default,
)
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
                CONF_TENANT_TARGET,
                default=_tenant_target_default(defaults),
            ): TargetSelector(
                TargetSelectorConfig(
                    entity={},
                    device={},
                    area={},
                )
            ),
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
                CONF_GUEST_MAIL_SERVICE,
                default=defaults.get(CONF_GUEST_MAIL_SERVICE, ""),
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
            vol.Required(
                CONF_GUEST_MAIL_DAYS,
                default=defaults.get(CONF_GUEST_MAIL_DAYS, DEFAULT_GUEST_MAIL_DAYS),
            ): _number(0, 30),
            vol.Optional(
                CONF_GUEST_BASE_URL,
                default=defaults.get(CONF_GUEST_BASE_URL, ""),
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
            vol.Required(
                CONF_GUEST_THEME,
                default=defaults.get(CONF_GUEST_THEME, DEFAULT_GUEST_THEME),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=[THEME_USVEGLIU, THEME_LEDBURY],
                    translation_key="guest_theme",
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(
                CONF_WIFI_SSID,
                default=defaults.get(CONF_WIFI_SSID, DEFAULT_WIFI_SSID),
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
            **_optional_entity_field(
                CONF_HOUSE_MODE_ENTITY,
                defaults,
                ["switch", "input_boolean", "select", "input_select"],
            ),
            **_optional_entity_field(
                CONF_OUTDOOR_TEMPERATURE, defaults, ["sensor", "weather"]
            ),
            **_optional_entity_field(CONF_POOL_TEMPERATURE, defaults, ["sensor"]),
            **_optional_entity_field(CONF_POOL_PH, defaults, ["sensor"]),
            vol.Optional(
                CONF_ALARM_CODE, default=""
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
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
                CONF_VOUCHER_PROVIDER,
                default=defaults.get(CONF_VOUCHER_PROVIDER, DEFAULT_VOUCHER_PROVIDER),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=[
                        VOUCHER_PROVIDER_UNIFI,
                        VOUCHER_PROVIDER_CAMBIUM,
                        VOUCHER_PROVIDER_MANUAL,
                    ],
                    translation_key="voucher_provider",
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(
                CONF_CAMBIUM_CLIENT_ID,
                default=defaults.get(CONF_CAMBIUM_CLIENT_ID, ""),
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
            vol.Optional(
                CONF_CAMBIUM_CLIENT_SECRET, default=""
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
            vol.Optional(
                CONF_CAMBIUM_PORTAL,
                default=defaults.get(CONF_CAMBIUM_PORTAL, ""),
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
            vol.Optional(
                CONF_CAMBIUM_VOUCHER_PLAN,
                default=defaults.get(CONF_CAMBIUM_VOUCHER_PLAN, ""),
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
            vol.Optional(
                CONF_MANUAL_WIFI_CODE, default=""
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
            vol.Required(
                CONF_ENABLE_ACCESS, default=defaults.get(CONF_ENABLE_ACCESS, True)
            ): BooleanSelector(),
            vol.Required(
                CONF_ENABLE_NUKI,
                default=defaults.get(CONF_ENABLE_NUKI, False),
            ): BooleanSelector(),
            vol.Optional(
                CONF_NUKI_TOKEN, default=""
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD)),
            vol.Optional(
                CONF_NUKI_SMARTLOCK_ID,
                default=defaults.get(CONF_NUKI_SMARTLOCK_ID, ""),
            ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
            vol.Required(
                CONF_PRINT_EVENT, default=defaults.get(CONF_PRINT_EVENT, False)
            ): BooleanSelector(),
        }
    )


def _clean_options(
    user_input: Mapping[str, Any], hass: Any | None = None
) -> dict[str, Any]:
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
        CONF_GUEST_MAIL_DAYS,
    ):
        if key in cleaned and cleaned[key] is not None:
            cleaned[key] = int(cleaned[key])
    legacy: list[str] = []
    for key in (CONF_CLIMATE_ENTITIES, CONF_COVER_ENTITIES, CONF_LIGHT_ENTITIES):
        legacy.extend(_as_id_list(cleaned.get(key)))
    target = cleaned.pop(CONF_TENANT_TARGET, None)
    if isinstance(target, Mapping):
        selected, devices = _expand_tenant_target(hass, target)
    else:
        selected = _as_id_list(cleaned.get(CONF_TENANT_ENTITIES))
        devices = _as_id_list(cleaned.get(CONF_TENANT_DEVICES))
    if not selected and legacy:
        selected = legacy
    cleaned[CONF_TENANT_ENTITIES] = selected
    cleaned[CONF_TENANT_DEVICES] = devices
    cleaned[CONF_ALLOW_REMOTE] = bool(cleaned.get(CONF_ALLOW_REMOTE, False))
    cleaned.pop(CONF_CONFIRM_SENSITIVE, None)
    for key in (CONF_CLIMATE_ENTITIES, CONF_COVER_ENTITIES, CONF_LIGHT_ENTITIES):
        cleaned.pop(key, None)
    cleaned[CONF_NOTIFY_SERVICE] = str(cleaned.get(CONF_NOTIFY_SERVICE) or "").strip()
    cleaned[CONF_GUEST_MAIL_SERVICE] = str(
        cleaned.get(CONF_GUEST_MAIL_SERVICE) or ""
    ).strip()
    cleaned[CONF_GUEST_BASE_URL] = str(cleaned.get(CONF_GUEST_BASE_URL) or "").strip()
    from .branding import normalize_guest_theme

    cleaned[CONF_GUEST_THEME] = normalize_guest_theme(
        cleaned.get(CONF_GUEST_THEME) or DEFAULT_GUEST_THEME
    )
    cleaned[CONF_WIFI_SSID] = str(cleaned.get(CONF_WIFI_SSID) or "").strip()
    cleaned[CONF_HOUSE_MODE_ENTITY] = str(
        cleaned.get(CONF_HOUSE_MODE_ENTITY) or ""
    ).strip()
    for key in (
        CONF_OUTDOOR_TEMPERATURE,
        CONF_POOL_TEMPERATURE,
        CONF_POOL_PH,
    ):
        cleaned[key] = str(cleaned.get(key) or "").strip()
    cleaned[CONF_ALARM_CODE] = str(cleaned.get(CONF_ALARM_CODE) or "").strip()
    cleaned[CONF_VOUCHER_PROVIDER] = str(
        cleaned.get(CONF_VOUCHER_PROVIDER) or DEFAULT_VOUCHER_PROVIDER
    ).strip() or DEFAULT_VOUCHER_PROVIDER
    cleaned[CONF_CAMBIUM_CLIENT_ID] = str(
        cleaned.get(CONF_CAMBIUM_CLIENT_ID) or ""
    ).strip()
    cleaned[CONF_CAMBIUM_CLIENT_SECRET] = str(
        cleaned.get(CONF_CAMBIUM_CLIENT_SECRET) or ""
    ).strip()
    cleaned[CONF_CAMBIUM_PORTAL] = str(cleaned.get(CONF_CAMBIUM_PORTAL) or "").strip()
    cleaned[CONF_CAMBIUM_VOUCHER_PLAN] = str(
        cleaned.get(CONF_CAMBIUM_VOUCHER_PLAN) or ""
    ).strip()
    cleaned[CONF_MANUAL_WIFI_CODE] = str(
        cleaned.get(CONF_MANUAL_WIFI_CODE) or ""
    ).strip()
    if cleaned.get(CONF_VOUCHER_PROVIDER) == VOUCHER_PROVIDER_MANUAL:
        cleaned[CONF_ENABLE_VOUCHERS] = False
    return {key: value for key, value in cleaned.items() if key not in _CONNECTION_KEYS}


def _optional_entity_field(
    key: str, defaults: Mapping[str, Any], domains: list[str]
) -> dict[Any, Any]:
    """Optional single-entity selector that keeps a previous choice."""
    selector = EntitySelector(EntitySelectorConfig(domain=domains, multiple=False))
    current = str(defaults.get(key) or "").strip()
    if current:
        return {vol.Optional(key, default=current): selector}
    return {vol.Optional(key): selector}


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
        self._connection: dict[str, Any] = {}
        self._house_defaults: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Choose UniFi (U Svegliu) or Cambium-only (49 Ledbury)."""
        if self._reauth:
            if not str(self._get_reauth_entry().data.get(CONF_API_KEY) or "").strip():
                return await self.async_step_cambium()
            return await self.async_step_unifi()
        if user_input is not None:
            choice = str(user_input.get(CONF_VOUCHER_PROVIDER) or "").strip()
            if choice == VOUCHER_PROVIDER_CAMBIUM:
                return await self.async_step_cambium()
            if choice == VOUCHER_PROVIDER_MANUAL:
                return await self.async_step_manual()
            return await self.async_step_unifi()
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_VOUCHER_PROVIDER,
                        default=DEFAULT_VOUCHER_PROVIDER,
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                {
                                    "label": "UniFi — hotspot UDM (auto)",
                                    "value": VOUCHER_PROVIDER_UNIFI,
                                },
                                {
                                    "label": "Cambium EasyPass — API cnMaestro X (auto)",
                                    "value": VOUCHER_PROVIDER_CAMBIUM,
                                },
                                {
                                    "label": "Voucher manuel — Cambium/autre sans API",
                                    "value": VOUCHER_PROVIDER_MANUAL,
                                },
                            ],
                            mode=SelectSelectorMode.LIST,
                        )
                    ),
                }
            ),
        )

    async def async_step_unifi(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect the UniFi controller address and the API key."""
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
            step_id="unifi",
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

    async def async_step_cambium(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Cambium EasyPass only — no UniFi controller required."""
        errors: dict[str, str] = {}
        if user_input is not None:
            client_id = str(user_input.get(CONF_CAMBIUM_CLIENT_ID) or "").strip()
            client_secret = str(user_input.get(CONF_CAMBIUM_CLIENT_SECRET) or "").strip()
            portal = str(user_input.get(CONF_CAMBIUM_PORTAL) or "").strip()
            plan = str(user_input.get(CONF_CAMBIUM_VOUCHER_PLAN) or "").strip()
            if not (client_id and client_secret and portal and plan):
                errors["base"] = "cambium_incomplete"
            else:
                from .cambium import CambiumAuthError, CambiumError

                try:
                    await _async_probe_cambium(client_id, client_secret, portal, plan)
                except CambiumAuthError:
                    errors["base"] = "invalid_auth"
                except CambiumError:
                    errors["base"] = "cannot_connect"
                else:
                    await self.async_set_unique_id(f"cambium:{portal}:{plan}")
                    self._abort_if_unique_id_configured()
                    self._connection = {
                        CONF_HOST: "",
                        CONF_PORT: DEFAULT_PORT,
                        CONF_API_KEY: "",
                        CONF_VERIFY_SSL: True,
                        CONF_BASE_PATH: "",
                        CONF_SITE_ID: f"cambium:{portal}",
                        CONF_SITE_NAME: portal,
                    }
                    self._house_defaults = {
                        CONF_VOUCHER_PROVIDER: VOUCHER_PROVIDER_CAMBIUM,
                        CONF_CAMBIUM_CLIENT_ID: client_id,
                        CONF_CAMBIUM_CLIENT_SECRET: client_secret,
                        CONF_CAMBIUM_PORTAL: portal,
                        CONF_CAMBIUM_VOUCHER_PLAN: plan,
                        CONF_GUEST_THEME: THEME_LEDBURY,
                        CONF_WIFI_SSID: "49Ledbury-Guest",
                        CONF_ENABLE_VOUCHERS: True,
                    }
                    return await self.async_step_house()
        return self.async_show_form(
            step_id="cambium",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_CAMBIUM_CLIENT_ID): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.TEXT)
                    ),
                    vol.Required(CONF_CAMBIUM_CLIENT_SECRET): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.PASSWORD)
                    ),
                    vol.Required(CONF_CAMBIUM_PORTAL): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.TEXT)
                    ),
                    vol.Required(CONF_CAMBIUM_VOUCHER_PLAN): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.TEXT)
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """No UniFi / Cambium API — owner pastes EasyPass codes by hand."""
        if user_input is not None:
            site = str(user_input.get(CONF_SITE_NAME) or "Maison").strip() or "Maison"
            code = str(user_input.get(CONF_MANUAL_WIFI_CODE) or "").strip()
            ssid = str(user_input.get(CONF_WIFI_SSID) or "").strip()
            await self.async_set_unique_id(f"manual:{site.casefold()}")
            self._abort_if_unique_id_configured()
            self._connection = {
                CONF_HOST: "",
                CONF_PORT: DEFAULT_PORT,
                CONF_API_KEY: "",
                CONF_VERIFY_SSL: True,
                CONF_BASE_PATH: "",
                CONF_SITE_ID: f"manual:{site.casefold()}",
                CONF_SITE_NAME: site,
            }
            self._house_defaults = {
                CONF_VOUCHER_PROVIDER: VOUCHER_PROVIDER_MANUAL,
                CONF_ENABLE_VOUCHERS: False,
                CONF_GUEST_THEME: THEME_LEDBURY,
                CONF_WIFI_SSID: ssid or "49Ledbury-Guest",
                CONF_MANUAL_WIFI_CODE: code,
            }
            return await self.async_step_house()
        return self.async_show_form(
            step_id="manual",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_SITE_NAME, default="49 Ledbury"): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.TEXT)
                    ),
                    vol.Optional(
                        CONF_WIFI_SSID, default="49Ledbury-Guest"
                    ): TextSelector(TextSelectorConfig(type=TextSelectorType.TEXT)),
                    vol.Optional(CONF_MANUAL_WIFI_CODE, default=""): TextSelector(
                        TextSelectorConfig(type=TextSelectorType.TEXT)
                    ),
                }
            ),
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
            options = _clean_options(user_input, self.hass)
            for key, value in self._house_defaults.items():
                if not options.get(key) and value not in (None, ""):
                    options[key] = value
            error = _house_error(
                self.hass,
                options,
                confirmed=bool(user_input.get(CONF_CONFIRM_SENSITIVE)),
            )
            if error:
                return self.async_show_form(
                    step_id="house",
                    data_schema=_house_schema({**self._house_defaults, **user_input}),
                    errors={"base": error},
                )
            site = str(self._connection.get(CONF_SITE_NAME) or "Maison")
            title = f"Usvegliu ({site})"
            return self.async_create_entry(
                title=title,
                data=self._connection,
                options=options,
            )
        return self.async_show_form(
            step_id="house",
            data_schema=_house_schema(self._house_defaults),
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start reauthentication when the API key is rejected."""
        self._reauth = True
        if not str(entry_data.get(CONF_API_KEY) or "").strip():
            return await self.async_step_cambium()
        return await self.async_step_unifi()

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Replace the controller connection without logging the key."""
        errors: dict[str, str] = {}
        entry = self._get_reconfigure_entry()
        if not str(entry.data.get(CONF_API_KEY) or "").strip():
            return self.async_abort(reason="reconfigure_not_unifi")
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
            options = _clean_options(user_input, self.hass)
            if not options.get(CONF_ALARM_CODE):
                options[CONF_ALARM_CODE] = str(
                    self.config_entry.options.get(CONF_ALARM_CODE) or ""
                )
            if not options.get(CONF_NUKI_TOKEN):
                options[CONF_NUKI_TOKEN] = str(
                    self.config_entry.options.get(CONF_NUKI_TOKEN) or ""
                )
            if not options.get(CONF_CAMBIUM_CLIENT_SECRET):
                options[CONF_CAMBIUM_CLIENT_SECRET] = str(
                    self.config_entry.options.get(CONF_CAMBIUM_CLIENT_SECRET) or ""
                )
            if not options.get(CONF_MANUAL_WIFI_CODE):
                options[CONF_MANUAL_WIFI_CODE] = str(
                    self.config_entry.options.get(CONF_MANUAL_WIFI_CODE) or ""
                )
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
    provider = str(
        options.get(CONF_VOUCHER_PROVIDER) or DEFAULT_VOUCHER_PROVIDER
    ).strip()
    if (
        bool(options.get(CONF_ENABLE_VOUCHERS, True))
        and provider == VOUCHER_PROVIDER_CAMBIUM
    ):
        missing = not all(
            str(options.get(key) or "").strip()
            for key in (
                CONF_CAMBIUM_CLIENT_ID,
                CONF_CAMBIUM_CLIENT_SECRET,
                CONF_CAMBIUM_PORTAL,
                CONF_CAMBIUM_VOUCHER_PLAN,
            )
        )
        if missing:
            return "cambium_incomplete"
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


async def _async_probe_cambium(
    client_id: str,
    client_secret: str,
    portal: str,
    plan: str,
) -> None:
    """Fetch an EasyPass token so bad credentials fail during setup."""
    from .cambium import CambiumClient

    async with aiohttp.ClientSession() as session:
        client = CambiumClient(
            session,
            client_id=client_id,
            client_secret=client_secret,
            portal_name=portal,
            voucher_plan=plan,
        )
        await client.async_ensure_token()
