"""Journal path, CSV archive, redaction and tenant policy."""

from datetime import datetime, timezone
import logging
from pathlib import Path

import pytest

from custom_components.usvegliu.access import (
    ADMIN_GROUP_ID,
    READ_ONLY_GROUP_ID,
    TenantAccessError,
    USERS_GROUP_ID,
    assert_not_privileged,
    build_tenant_policy,
    generate_password,
    group_id_for_username,
    is_tenant_user,
    resolve_shared_access,
    resolve_stay_access,
    sensitive_entity_ids,
    user_can_manage_stays,
)
from custom_components.usvegliu.const import SENSITIVE_DOMAINS
from custom_components.usvegliu.dashboard import (
    async_apply_console_visibility,
    async_ensure_dashboard,
    async_ensure_owner_dashboard,
    async_set_tenant_default_panel,
    build_dashboard_config,
    build_owner_dashboard_config,
    dashboard_card_count,
    find_dashboard_collection,
    frontend_core_with_tenant_panel,
    frontend_sidebar_with_console,
)
from custom_components.usvegliu.journal import Journal, JournalPathError, resolve_journal_path
from custom_components.usvegliu.redact import SecretLogFilter, redact


def test_journal_stays_inside_config_or_media(tmp_path: Path):
    config = tmp_path / "config"
    media = tmp_path / "media"
    config.mkdir()
    media.mkdir()
    inside = resolve_journal_path(config, "usvegliu/journal.csv", [media])
    assert inside == (config / "usvegliu" / "journal.csv").resolve()
    mounted = resolve_journal_path(config, str(media / "synology" / "journal.csv"), [media])
    assert mounted.is_relative_to(media.resolve())
    with pytest.raises(JournalPathError):
        resolve_journal_path(config, "../etc/passwd", [media])
    with pytest.raises(JournalPathError):
        resolve_journal_path(config, "/etc/passwd", [media])


@pytest.mark.asyncio
async def test_csv_keeps_the_code_and_drops_passwords(tmp_path: Path, caplog):
    journal = Journal(tmp_path / "usvegliu" / "journal.csv")
    legacy = tmp_path / "legacy.csv"
    legacy.write_text(
        "horodatage,action,reservation_id,locataire,debut,fin,voucher_id,code,"
        "utilisateur_ha,mot_de_passe,detail\n"
        "2026-07-01T00:00:00+00:00,voucher_cree,stay-0,Ada,2026-07-10,2026-07-17,"
        "voucher-0,OLDCODE,loc-ada,s3cret-password,note\n",
        encoding="utf-8",
    )
    old = Journal(legacy)
    with caplog.at_level(logging.DEBUG):
        await old.async_append(
            {
                "action": "voucher_cree",
                "reservation_id": "stay-1",
                "locataire": "Jean Dupont",
                "debut": "2026-07-10",
                "fin": "2026-07-17",
                "voucher_id": "voucher-1",
                "voucher_nom": "Jean Dupont 2026-07-10/2026-07-17",
                "code": "ABCD12",
                "mac": "aa:bb:cc:dd:ee:ff",
                "mot_de_passe": "another-secret",
                "utilisateur_ha": "loc-jean",
                "detail": "",
            }
        )
        await journal.async_append(
            {
                "action": "voucher_cree",
                "reservation_id": "stay-1",
                "locataire": "Jean Dupont",
                "debut": "2026-07-10",
                "fin": "2026-07-17",
                "voucher_id": "voucher-1",
                "voucher_nom": "Jean Dupont 2026-07-10/2026-07-17",
                "code": "ABCD12",
                "mac": "",
                "mot_de_passe": "should-not-stick",
            }
        )
    fresh = journal.path.read_text(encoding="utf-8")
    migrated = legacy.read_text(encoding="utf-8")
    assert "ABCD12" in fresh
    assert "Jean Dupont" in fresh
    assert "should-not-stick" not in fresh
    assert "mot_de_passe" not in fresh
    assert "s3cret-password" not in migrated
    assert "another-secret" not in migrated
    assert "OLDCODE" in migrated
    assert "aa:bb:cc:dd:ee:ff" in migrated
    assert "mot_de_passe" not in migrated.splitlines()[0]
    assert "ABCD12" not in caplog.text
    assert "s3cret-password" not in caplog.text


def test_diagnostics_and_logs_redact_secrets():
    payload = redact(
        {
            "entry_data": {"api_key": "super-secret-key", "host": "192.168.1.1"},
            "stays": [
                {
                    "guest": "Jean Dupont",
                    "voucher_code": "ABCD12",
                    "password": "s3cret-password",
                    "mot_de_passe": "s3cret-password",
                    "code_compte": "s3cret-password",
                    "guest_token": "stay-token-secret",
                    "voucher_id": "voucher-1",
                }
            ],
            "empty": {"api_key": ""},
        }
    )
    assert payload["entry_data"]["api_key"] == "**REDACTED**"
    assert payload["entry_data"]["host"] == "192.168.1.1"
    assert payload["stays"][0]["voucher_code"] == "**REDACTED**"
    assert payload["stays"][0]["password"] == "**REDACTED**"
    assert payload["stays"][0]["mot_de_passe"] == "**REDACTED**"
    assert payload["stays"][0]["code_compte"] == "**REDACTED**"
    assert payload["stays"][0]["guest_token"] == "**REDACTED**"
    assert payload["stays"][0]["guest"] == "**REDACTED**"
    linked = redact({"lien_maison": "https://www.usvegliu.fr/s/stay-token-secret"})
    assert linked["lien_maison"] == "**REDACTED**"
    assert payload["stays"][0]["voucher_id"] == "voucher-1"
    assert payload["empty"]["api_key"] == ""

    filt = SecretLogFilter()
    filt.update(["super-secret-key", "ABCD12"], owner="entry-a")
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="header super-secret-key code ABCD12",
        args=(),
        exc_info=None,
    )
    assert filt.filter(record) is True
    message = record.getMessage()
    assert "super-secret-key" not in message
    assert "ABCD12" not in message
    assert "**REDACTED**" in message


def test_tenant_policy_is_explicit_and_sensitive_domains_are_flagged():
    policy = build_tenant_policy(
        ["climate.salon", "media_player.salon", "switch.prise"],
        ["device-1"],
    )
    entities = policy["entities"]["entity_ids"]
    assert set(entities) == {"climate.salon", "media_player.salon", "switch.prise"}
    assert entities["switch.prise"] == {"read": True, "control": True, "edit": False}
    assert policy["entities"]["device_ids"]["device-1"]["edit"] is False
    assert "all" not in policy["entities"]
    assert "domains" not in policy["entities"]
    empty = build_tenant_policy([], [])
    assert empty["entities"]["entity_ids"] == {}
    flagged = sensitive_entity_ids(
        ["light.salon", "camera.entree", "lock.porte", "alarm_control_panel.maison"]
    )
    assert flagged == ["camera.entree", "lock.porte", "alarm_control_panel.maison"]
    confirmed = build_tenant_policy(["camera.entree"])
    assert "camera.entree" in confirmed["entities"]["entity_ids"]
    assert SENSITIVE_DOMAINS == {"camera", "lock", "alarm_control_panel"}
    assert group_id_for_username("loc-jean") != ADMIN_GROUP_ID
    assert group_id_for_username("Locataire") == "usvegliu-locataire"
    entities_only, devices_only, remote = resolve_stay_access(
        "stay",
        overrides={"stay": {"entity_ids": ["cover.x"], "allow_remote": True}},
        entity_ids=["light.global"],
        device_ids=["device-global"],
        allow_remote=False,
    )
    assert entities_only == ["cover.x"]
    assert devices_only == []
    assert remote is True
    shared_entities, _, shared_remote = resolve_shared_access(
        ["a", "b"],
        overrides={"b": {"entity_ids": ["fan.chambre"], "allow_remote": True}},
        entity_ids=["light.salon"],
        device_ids=[],
        allow_remote=False,
    )
    assert shared_entities == ["light.salon", "fan.chambre"]
    assert shared_remote is True

    class _Group:
        def __init__(self, group_id):
            self.id = group_id

    class _Admin:
        is_owner = False
        is_admin = True
        groups = []

    class _Manager:
        is_owner = False
        is_admin = False
        system_generated = False
        groups = [_Group(USERS_GROUP_ID)]

    class _Tenant:
        is_owner = False
        is_admin = False
        system_generated = False
        groups = [_Group(group_id_for_username("ada"))]

    class _ReadOnly:
        is_owner = False
        is_admin = False
        system_generated = False
        groups = [_Group(READ_ONLY_GROUP_ID)]

    with pytest.raises(TenantAccessError):
        assert_not_privileged(_Admin())
    with pytest.raises(TenantAccessError):
        assert_not_privileged(_Manager())
    assert_not_privileged(_Tenant())
    assert user_can_manage_stays(_Admin()) is True
    assert user_can_manage_stays(_Manager()) is True
    assert user_can_manage_stays(_Tenant()) is False
    assert user_can_manage_stays(_ReadOnly()) is False
    assert is_tenant_user(_Tenant()) is True
    assert is_tenant_user(_Manager()) is False

    password = generate_password()
    assert len(password.encode()) < 72
    assert " " not in password


def test_dashboard_only_lists_selected_entities():
    config = build_dashboard_config(
        ["climate.salon", "cover.sejour", "light.salon", "media_player.salon"]
    )
    cards = config["views"][0]["sections"][0]["cards"]
    dumped = str(cards)
    assert "climate.salon" in dumped
    assert "cover.sejour" in dumped
    assert "light.salon" in dumped
    assert "media_player.salon" in dumped
    assert "camera." not in dumped
    assert "lock." not in dumped
    assert config["views"][0]["type"] == "sections"
    assert dashboard_card_count(config) == 5


def test_tenant_frontend_core_opens_sejour():
    core = frontend_core_with_tenant_panel({"language": "fr"})
    assert core["default_panel"] == "usvegliu-sejour"
    assert core["language"] == "fr"
    assert frontend_core_with_tenant_panel(None)["default_panel"] == "usvegliu-sejour"
    access = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "usvegliu"
        / "access.py"
    ).read_text(encoding="utf-8")
    assert "async_set_tenant_default_panel" in access


@pytest.mark.asyncio
async def test_tenant_default_panel_is_written_to_frontend_store():
    saved: dict = {}

    class _Store:
        data: dict = {"core": {"language": "fr"}}

        async def async_set_item(self, key, value):
            saved[key] = value
            self.data = {**self.data, key: value}

    store = _Store()

    async def _load_store(hass, user_id):
        assert user_id == "user-1"
        return store

    await async_set_tenant_default_panel(object(), None, load_store=_load_store)
    assert saved == {}
    await async_set_tenant_default_panel(object(), "user-1", load_store=_load_store)
    assert saved["core"]["default_panel"] == "usvegliu-sejour"
    assert saved["core"]["language"] == "fr"
    assert "usvegliu-proprietaire" in saved["sidebar"]["hiddenPanels"]


def test_console_sidebar_is_hidden_only_for_tenants():
    hidden = frontend_sidebar_with_console({"hiddenPanels": ["map"]}, hidden=True)
    assert hidden["hiddenPanels"] == ["map", "usvegliu-proprietaire"]
    shown = frontend_sidebar_with_console(hidden, hidden=False)
    assert shown["hiddenPanels"] == ["map"]


def test_owner_console_dashboard_has_live_credentials_and_actions():
    stays = [
        {
            "guest": "Ada",
            "reservation_id": "stay-ada",
            "password": "secret-should-not-be-baked",
            "lien_maison": "https://www.usvegliu.fr/s/TOKEN",
        },
        {
            "guest": "Essai",
            "reservation_id": "__usvegliu_preview__",
            "essai": True,
        },
    ]
    config = build_owner_dashboard_config(
        stays,
        sejours_entity_id="sensor.usvegliu_sejours",
        reglages_entity_id="sensor.usvegliu_reglages",
    )
    dumped = str(config)
    assert config["views"][0]["type"] == "sections"
    assert config["views"][0]["path"] == "console"
    assert config["views"][1]["path"] == "reglages"
    assert "Nouveau mot de passe" in dumped
    assert "Révoquer le compte" in dumped
    assert "Nouveau code Wi-Fi" in dumped
    assert "Révoquer le Wi-Fi" in dumped
    assert "usvegliu.regenerer_acces" in dumped
    assert "usvegliu.revoquer_acces" in dumped
    assert "usvegliu.regenerer_voucher" in dumped
    assert "usvegliu.revoquer_voucher" in dumped
    assert "stay-ada" in dumped
    assert "secret-should-not-be-baked" not in dumped
    assert "TOKEN" not in dumped
    assert "state_attr('sensor.usvegliu_sejours', 'stays')" in dumped
    assert "mot_de_passe" in dumped
    assert "code_compte" in dumped
    assert "Mot de passe Home Assistant" in dumped
    assert "compte_stay_ada" in dumped
    assert "s.password" not in dumped
    assert "comptes" in dumped
    assert dumped.count("usvegliu.regenerer_acces") == 1
    assert "usvegliu.relire_calendrier" in dumped
    assert "Relire le calendrier" in dumped
    assert "Réglages Usvegliu" in dumped
    assert "state_attr('sensor.usvegliu_reglages', 'settings')" in dumped


@pytest.mark.asyncio
async def test_owner_dashboard_saves_when_lovelace_already_has_the_path():
    saved: list[dict] = []

    class _Dash:
        async def async_save(self, config):
            saved.append(config)

    class _Hass:
        data = {"lovelace": {"dashboards": {"usvegliu-proprietaire": _Dash()}}}

    result = await async_ensure_owner_dashboard(
        _Hass(),
        [{"guest": "Ada", "reservation_id": "stay-ada"}],
        sejours_entity_id="sensor.usvegliu_sejours",
    )
    assert result["ok"] is True
    assert result["url"] == "usvegliu-proprietaire"
    assert saved and saved[0]["views"][0]["path"] == "console"


@pytest.mark.asyncio
async def test_owner_dashboard_saves_when_url_path_is_on_the_object():
    saved: list[dict] = []

    class _Dash:
        url_path = "usvegliu-proprietaire"
        config = {"url_path": "usvegliu-proprietaire", "id": "dashboard_abc"}

        async def async_save(self, config):
            saved.append(config)

    class _Hass:
        data = {"lovelace": {"dashboards": {None: object(), "dashboard_abc": _Dash()}}}

    result = await async_ensure_owner_dashboard(
        _Hass(),
        [{"guest": "Ada", "reservation_id": "stay-ada"}],
        sejours_entity_id="sensor.usvegliu_sejours",
    )
    assert result["ok"] is True
    assert saved


@pytest.mark.asyncio
async def test_owner_dashboard_is_created_from_websocket_collection():
    saved: list[dict] = []

    class _Dash:
        async def async_save(self, config):
            saved.append(config)

    dashboards: dict[str, object] = {}

    class _Collection:
        def __init__(self):
            self.items: list[dict] = []

        def async_items(self):
            return list(self.items)

        async def async_create_item(self, data):
            item = {**data, "id": data["url_path"]}
            self.items.append(item)
            dashboards[data["url_path"]] = _Dash()
            return item

    class _Websocket:
        def __init__(self, collection):
            self.storage_collection = collection

        def ws_create_item(self):
            return None

    collection = _Collection()
    websocket = _Websocket(collection)

    class _Hass:
        data = {
            "lovelace": {"dashboards": dashboards},
            "websocket_api": {
                "lovelace/dashboards/create": (websocket.ws_create_item, {})
            },
        }

    result = await async_ensure_owner_dashboard(
        _Hass(),
        [{"guest": "Ada", "reservation_id": "stay-ada"}],
        sejours_entity_id="sensor.usvegliu_sejours",
    )
    assert result["ok"] is True
    assert collection.items[0]["url_path"] == "usvegliu-proprietaire"
    assert collection.items[0]["require_admin"] is False
    assert saved


@pytest.mark.asyncio
async def test_owner_dashboard_drops_admin_only_flag_on_existing_console():
    updated: list[tuple] = []

    class _Dash:
        async def async_save(self, config):
            return None

    class _Collection:
        def async_items(self):
            return [
                {
                    "id": "usvegliu-proprietaire",
                    "url_path": "usvegliu-proprietaire",
                    "require_admin": True,
                    "show_in_sidebar": True,
                }
            ]

        async def async_update_item(self, item_id, data):
            updated.append((item_id, data))

        async def async_create_item(self, data):
            raise AssertionError("should update, not create")

    class _Websocket:
        def __init__(self, collection):
            self.storage_collection = collection

        def ws_create_item(self):
            return None

    websocket = _Websocket(_Collection())

    class _Hass:
        data = {
            "lovelace": {"dashboards": {"usvegliu-proprietaire": _Dash()}},
            "websocket_api": {
                "lovelace/dashboards/create": (websocket.ws_create_item, {})
            },
        }

    result = await async_ensure_owner_dashboard(
        _Hass(),
        [{"guest": "Ada", "reservation_id": "stay-ada"}],
        sejours_entity_id="sensor.usvegliu_sejours",
    )
    assert result["ok"] is True
    assert updated == [
        (
            "usvegliu-proprietaire",
            {"require_admin": False, "show_in_sidebar": True},
        )
    ]


@pytest.mark.asyncio
async def test_console_visibility_hides_from_tenants_not_managers():
    saved: dict[str, dict] = {}

    class _Group:
        def __init__(self, group_id):
            self.id = group_id

    class _Store:
        def __init__(self, user_id, hidden=None):
            self.user_id = user_id
            self.data: dict = {
                "core": {},
                "sidebar": {"hiddenPanels": list(hidden or [])},
            }

        async def async_set_item(self, key, value):
            saved.setdefault(self.user_id, {})[key] = value
            self.data = {**self.data, key: value}

    stores = {
        "tenant-1": _Store("tenant-1"),
        "user-1": _Store("user-1", hidden=["usvegliu-proprietaire"]),
    }

    async def _load_store(hass, user_id):
        return stores[user_id]

    class _Tenant:
        id = "tenant-1"
        is_admin = False
        is_owner = False
        system_generated = False
        groups = [_Group(group_id_for_username("ada"))]

    class _Manager:
        id = "user-1"
        is_admin = False
        is_owner = False
        system_generated = False
        groups = [_Group(USERS_GROUP_ID)]

    async def _list_users():
        return [_Tenant(), _Manager()]

    await async_apply_console_visibility(
        object(), load_store=_load_store, list_users=_list_users
    )
    assert saved["tenant-1"]["core"]["default_panel"] == "usvegliu-sejour"
    assert "usvegliu-proprietaire" in saved["tenant-1"]["sidebar"]["hiddenPanels"]
    assert "usvegliu-proprietaire" not in saved["user-1"]["sidebar"]["hiddenPanels"]


def test_dashboard_collection_is_found_on_websocket_commands_object():
    class _Collection:
        def async_items(self):
            return [{"url_path": "usvegliu-sejour"}]

        async def async_create_item(self, data):
            return data

    class _Websocket:
        def __init__(self, collection):
            self.storage_collection = collection

        def ws_create_item(self):
            return None

    class _Commands:
        def __init__(self, websocket):
            self.commands = {
                "lovelace/dashboards/create": (websocket.ws_create_item, {})
            }

    collection = _Collection()

    class _Hass:
        data = {"websocket_api": _Commands(_Websocket(collection))}

    assert find_dashboard_collection(_Hass()) is collection


@pytest.mark.asyncio
async def test_dashboard_saves_when_lovelace_already_has_the_path():
    saved: list[dict] = []

    class _Dash:
        async def async_save(self, config):
            saved.append(config)

    class _Hass:
        data = {"lovelace": {"dashboards": {"usvegliu-sejour": _Dash()}}}

    result = await async_ensure_dashboard(_Hass(), ["climate.salon"])
    assert result["ok"] is True
    assert result["reason"] == "saved"
    assert result["cards"] == 2
    assert saved and saved[0]["views"][0]["sections"][0]["cards"]


def test_admin_roster_sensor_lists_stays_and_passwords():
    root = Path(__file__).resolve().parents[1] / "custom_components" / "usvegliu"
    sensor = (root / "sensor.py").read_text(encoding="utf-8")
    http = (root / "http.py").read_text(encoding="utf-8")
    assert "IssuedAccountsSensor" in sensor
    assert "OwnerSettingsSensor" in sensor
    assert 'translation_key = "sejours"' in sensor
    assert "lien_maison" in sensor
    assert "mot_de_passe" in sensor
    assert "code_compte" in sensor
    assert "comptes" in sensor
    assert "credential_attribute_key" in sensor
    assert "_unrecorded_attributes" in sensor
    assert "password" not in http
    assert "mot_de_passe" not in http
    assert "code_compte" not in http


def test_guest_app_javascript_parses():
    import subprocess

    js = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "usvegliu"
        / "www"
        / "app.js"
    )
    subprocess.run(["node", "--check", str(js)], check=True)


def test_guest_stream_is_server_sent_events():
    text = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "usvegliu"
        / "http.py"
    ).read_text(encoding="utf-8")
    assert "/guest/stream" in text
    assert "text/event-stream" in text
    js = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "usvegliu"
        / "www"
        / "app.js"
    ).read_text(encoding="utf-8")
    assert "EventSource" in js
    assert "guest/stream" in js
    assert "pendingClimate" in js
    assert "flushClimate" in js
    assert "modeLabel" in js
    assert "heating" in js
    assert "cooling" in js
    assert "house_mode_entity_id" in text
    assert "mode_label" in text
    assert "/guest/command" in text
    assert "Lumière" in js
    assert "Accès" in js
    assert "metrics" in js
    assert "atmosphere" in js
    assert "Allumée" in js
    assert "wordmark" in js
    assert "Bonsoir" in js
    assert "alarm_code" in text


def test_sources_do_not_embed_a_credential():
    root = Path(__file__).resolve().parents[1] / "custom_components" / "usvegliu"
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "X-API-KEY" in text or "api_key" in text or path.name != "unifi.py"
        assert "BEGIN PRIVATE KEY" not in text
        assert "super-secret-key" not in text
