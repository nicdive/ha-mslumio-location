"""Journal path, CSV archive, redaction and tenant policy."""

from datetime import datetime, timezone
import logging
from pathlib import Path

import pytest

from custom_components.usvegliu.access import (
    ADMIN_GROUP_ID,
    TenantAccessError,
    assert_not_privileged,
    build_tenant_policy,
    generate_password,
    group_id_for_username,
    resolve_shared_access,
    resolve_stay_access,
    sensitive_entity_ids,
)
from custom_components.usvegliu.const import SENSITIVE_DOMAINS
from custom_components.usvegliu.dashboard import (
    async_ensure_dashboard,
    async_set_tenant_default_panel,
    build_dashboard_config,
    dashboard_card_count,
    frontend_core_with_tenant_panel,
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

    class _Admin:
        is_owner = False
        is_admin = True
        groups = []

    with pytest.raises(TenantAccessError):
        assert_not_privileged(_Admin())

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
    assert 'translation_key = "sejours"' in sensor
    assert "lien_maison" in sensor
    assert '"password": data.get("password")' in sensor
    assert "_unrecorded_attributes" in sensor
    assert "password" not in http


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


def test_sources_do_not_embed_a_credential():
    root = Path(__file__).resolve().parents[1] / "custom_components" / "usvegliu"
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "X-API-KEY" in text or "api_key" in text or path.name != "unifi.py"
        assert "BEGIN PRIVATE KEY" not in text
        assert "super-secret-key" not in text
