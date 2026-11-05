"""Constants for the Usvegliu integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Final

DOMAIN: Final = "usvegliu"

# Connection (config entry data — the API key never leaves this store).
CONF_HOST: Final = "host"
CONF_PORT: Final = "port"
CONF_API_KEY: Final = "api_key"
CONF_VERIFY_SSL: Final = "verify_ssl"
CONF_SITE_ID: Final = "site_id"
CONF_SITE_NAME: Final = "site_name"
CONF_BASE_PATH: Final = "base_path"

# Options.
CONF_CALENDAR: Final = "calendar_entity"
CONF_LEAD_DAYS: Final = "lead_days"
CONF_DEVICE_LIMIT: Final = "device_limit"
CONF_DOWNLOAD_MBPS: Final = "download_mbps"
CONF_UPLOAD_MBPS: Final = "upload_mbps"
CONF_EXTRA_DAYS: Final = "extra_days"
CONF_ACCESS_MODE: Final = "access_mode"
CONF_CLIMATE_ENTITIES: Final = "climate_entities"
CONF_COVER_ENTITIES: Final = "cover_entities"
CONF_LIGHT_ENTITIES: Final = "light_entities"
CONF_TENANT_ENTITIES: Final = "tenant_entities"
CONF_TENANT_DEVICES: Final = "tenant_devices"
CONF_ALLOW_REMOTE: Final = "allow_remote"
CONF_CONFIRM_SENSITIVE: Final = "confirm_sensitive"
CONF_NOTIFY_SERVICE: Final = "notify_service"
CONF_JOURNAL_PATH: Final = "journal_path"
CONF_PRINT_EVENT: Final = "print_event"
CONF_ENABLE_VOUCHERS: Final = "enable_vouchers"
CONF_ENABLE_ACCESS: Final = "enable_access"
CONF_TITLE_BLOCKLIST: Final = "title_blocklist"
CONF_MAX_STAY_DAYS: Final = "max_stay_days"
CONF_LOOKAHEAD_DAYS: Final = "lookahead_days"

ACCESS_PER_STAY: Final = "per_stay"
ACCESS_SHARED: Final = "shared"
ACCESS_MODES: Final = (ACCESS_PER_STAY, ACCESS_SHARED)
DEFAULT_ACCESS_MODE: Final = ACCESS_PER_STAY
CONF_GUEST_BASE_URL: Final = "guest_base_url"
CONF_WIFI_SSID: Final = "wifi_ssid"
DEFAULT_WIFI_SSID: Final = "Usvegliu-Guest"
CONF_HOUSE_MODE_ENTITY: Final = "house_mode_entity"
CONF_OUTDOOR_TEMPERATURE: Final = "outdoor_temperature"
CONF_POOL_TEMPERATURE: Final = "pool_temperature"
CONF_POOL_PH: Final = "pool_ph"
CONF_ALARM_CODE: Final = "alarm_code"

DEFAULT_PORT: Final = 443
DEFAULT_LEAD_DAYS: Final = 3
DEFAULT_DEVICE_LIMIT: Final = 10
DEFAULT_DOWNLOAD_MBPS: Final = 100
DEFAULT_UPLOAD_MBPS: Final = 100
DEFAULT_EXTRA_DAYS: Final = 1
DEFAULT_JOURNAL_PATH: Final = "usvegliu/journal.csv"
DEFAULT_TITLE_BLOCKLIST: Final = (
    "not available,unavailable,blocked,blocked dates,indisponible,fermé,ferme"
)
DEFAULT_MAX_STAY_DAYS: Final = 60
DEFAULT_LOOKAHEAD_DAYS: Final = 120
DEFAULT_BASE_PATH: Final = ""

# UniFi OS (UDM) mounts the Network integration API behind the proxy.
# A bare controller exposes it at /integration. Both are probed.
UNIFI_BASE_CANDIDATES: Final = (
    "/proxy/network/integration",
    "/integration",
)
UNIFI_API_HEADER: Final = "X-API-KEY"

# 100 Mbit/s = 100_000 kbit/s (SI), which is the unit of rx/txRateLimitKbps.
KBPS_PER_MBPS: Final = 1000

UPDATE_INTERVAL: Final = timedelta(minutes=15)

# Custom auth group. Never system-admin and never system-users
# (system-users grants every entity).
GROUP_PREFIX: Final = "usvegliu-"
TENANT_GROUP_ID: Final = "usvegliu-locataires"
TENANT_GROUP_NAME: Final = "Usvegliu locataires"
SHARED_USERNAME: Final = "locataire"

# Not selected by default. The owner can add them only after an explicit
# confirmation in the options form or the per-stay service.
SENSITIVE_DOMAINS: Final = frozenset({"camera", "lock", "alarm_control_panel"})

DASHBOARD_URL: Final = "usvegliu-sejour"
DASHBOARD_TITLE: Final = "Séjour"
DASHBOARD_ICON: Final = "mdi:home-account"
OWNER_DASHBOARD_URL: Final = "usvegliu-proprietaire"
OWNER_DASHBOARD_TITLE: Final = "Console"
OWNER_DASHBOARD_ICON: Final = "mdi:desk"

STORAGE_KEY: Final = f"{DOMAIN}.sejours"
STORAGE_VERSION: Final = 1

EVENT_JOURNAL: Final = "usvegliu_journal"
EVENT_PRINT: Final = "usvegliu_print_voucher"

SERVICE_REGENERATE_VOUCHER: Final = "regenerer_voucher"
SERVICE_REVOKE_VOUCHER: Final = "revoquer_voucher"
SERVICE_REGENERATE_ACCESS: Final = "regenerer_acces"
SERVICE_REVOKE_ACCESS: Final = "revoquer_acces"
SERVICE_RESEND: Final = "renvoyer_notification"
SERVICE_PRINT: Final = "imprimer_voucher"
SERVICE_EXPORT_JOURNAL: Final = "exporter_journal"
SERVICE_APPLY_DASHBOARD: Final = "appliquer_tableau"
SERVICE_REFRESH_CALENDAR: Final = "relire_calendrier"
SERVICE_STAY_SETTINGS: Final = "reglages_sejour"
SERVICE_GUEST_LINK: Final = "lien_maison"

ATTR_RESERVATION_KEY: Final = "reservation_key"

PLATFORMS: Final = ["sensor"]
