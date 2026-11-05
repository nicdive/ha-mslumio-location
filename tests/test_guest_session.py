"""Guest stay tokens and climate fan/mode mapping."""

from datetime import datetime, timedelta, timezone

from custom_components.usvegliu.guest_session import (
    PREVIEW_KEY,
    alarm_view_state,
    build_preview_record,
    classify_guest_entity,
    climate_activity,
    climate_is_on,
    cover_is_open,
    credential_attribute_key,
    ensure_guest_token,
    find_record_by_token,
    house_mode_from_state,
    house_mode_label,
    infer_fan_speed,
    format_stay_span,
    guest_welcome_message,
    issued_account_view,
    map_fan_modes,
    open_issued_records,
    pick_hvac_on,
    public_guest_url,
    resolve_house_mode,
    stay_is_open,
)

UTC = timezone.utc


def test_token_is_kept_on_later_sync():
    record: dict = {}
    first = ensure_guest_token(record)
    second = ensure_guest_token(record)
    assert first == second
    assert len(first) >= 16


def test_stay_open_until_checkout_including_before_arrival():
    now = datetime(2026, 7, 1, 10, tzinfo=UTC)
    record = {
        "check_in": "2026-07-10T00:00:00+00:00",
        "check_out": "2026-07-17T00:00:00+00:00",
        "guest_token": "a" * 24,
    }
    assert stay_is_open(record, now) is True
    assert stay_is_open(record, datetime(2026, 7, 17, 0, tzinfo=UTC)) is False


def test_find_token_prefers_live_stay_over_expired_preview():
    now = datetime(2026, 7, 12, tzinfo=UTC)
    token = "T" * 24
    stays = {
        "a": {
            "guest_token": token,
            "check_in": "2026-07-10T00:00:00+00:00",
            "check_out": "2026-07-17T00:00:00+00:00",
        }
    }
    preview = {
        "guest_token": token,
        "check_out": "2026-07-01T00:00:00+00:00",
        "preview": True,
    }
    found = find_record_by_token(stays, preview, token, now)
    assert found is stays["a"]


def test_open_issued_records_keeps_active_stays_and_live_preview():
    now = datetime(2026, 7, 12, tzinfo=UTC)
    stays = {
        "past": {
            "key": "past",
            "guest": "Fini",
            "check_in": "2026-06-01T00:00:00+00:00",
            "check_out": "2026-06-08T00:00:00+00:00",
            "username": "loc-fini",
        },
        "live": {
            "key": "live",
            "guest": "Ada",
            "check_in": "2026-07-10T00:00:00+00:00",
            "check_out": "2026-07-17T00:00:00+00:00",
            "username": "loc-ada",
            "voucher_code": "ABCD12",
            "guest_token": "T" * 24,
        },
        "soon": {
            "key": "soon",
            "guest": "Jean",
            "check_in": "2026-07-20T00:00:00+00:00",
            "check_out": "2026-07-27T00:00:00+00:00",
            "username": "loc-jean",
            "guest_token": "U" * 24,
        },
    }
    preview = build_preview_record(now, hours=24)
    records = open_issued_records(stays, preview, now)
    assert [record["key"] for record in records] == ["live", "soon", PREVIEW_KEY]
    row = issued_account_view(
        stays["live"],
        username="loc-ada",
        password="secret-ada",
        lien_maison="https://www.usvegliu.fr/s/TTTT",
        path="/usvegliu/s/TTTT",
        tableau="/usvegliu-sejour",
        wifi_ssid="Usvegliu-Guest",
    )
    assert row["lien_maison"].endswith("/s/TTTT")
    assert row["username"] == "loc-ada"
    assert row["password"] == "secret-ada"
    assert row["mot_de_passe"] == "secret-ada"
    assert row["code_compte"] == "secret-ada"
    assert row["voucher_code"] == "ABCD12"
    assert row["wifi_ssid"] == "Usvegliu-Guest"
    invite = row["message_invite"]
    assert "Bonjour Ada," in invite
    assert "https://www.usvegliu.fr/s/TTTT" in invite
    assert "Usvegliu-Guest" in invite
    assert "ABCD12" in invite
    assert "secret-ada" not in invite
    assert "loc-ada" not in invite
    assert "Home Assistant" not in invite
    assert credential_attribute_key("stay-ada") == "compte_stay_ada"
    assert credential_attribute_key("ada@host/x") == "compte_ada_host_x"
    assert open_issued_records(stays, preview, datetime(2026, 8, 1, tzinfo=UTC)) == []


def test_guest_welcome_message_is_villa_copy_without_ha_login():
    assert format_stay_span(
        "2026-07-10T00:00:00+00:00", "2026-07-17T00:00:00+00:00"
    ) == "10 au 17 juillet"
    note = guest_welcome_message(
        guest="Jean Dupont",
        check_in="2026-07-10T00:00:00+00:00",
        check_out="2026-07-17T00:00:00+00:00",
        lien_maison="https://www.usvegliu.fr/s/LINK",
        wifi_ssid="Usvegliu-Guest",
        voucher_code="WIFIXY",
        voucher_revoked=False,
        preview=False,
    )
    assert note.startswith("Bonjour Jean,")
    assert "séjour du 10 au 17 juillet" in note
    assert "https://www.usvegliu.fr/s/LINK" in note
    assert "Réseau Wi-Fi : Usvegliu-Guest" in note
    assert "Code d'accès : WIFIXY" in note
    assert "séjour d'exception" in note
    assert "L'équipe Usvegliu" in note
    assert "mot de passe" not in note.lower()
    preview = guest_welcome_message(
        guest="Essai",
        check_in="",
        check_out="",
        lien_maison="https://www.usvegliu.fr/s/PREVIEW",
        wifi_ssid="Usvegliu-Guest",
        voucher_code="TEMP",
        voucher_revoked=False,
        preview=True,
    )
    assert "lien d'essai" in preview
    assert "24 heures" in preview
    assert "TEMP" not in preview
    revoked = guest_welcome_message(
        guest="Ada",
        check_in="2026-07-10",
        check_out="2026-07-17",
        lien_maison="https://www.usvegliu.fr/s/ADA",
        wifi_ssid="",
        voucher_code="OLD",
        voucher_revoked=True,
        preview=False,
    )
    assert "OLD" not in revoked
    assert "révoqué" in revoked
    assert "Réseau Wi-Fi :" in revoked
    bare = guest_welcome_message(
        guest="Bob",
        check_in="2026-11-07T00:00:00+00:00",
        check_out="2026-11-17T00:00:00+00:00",
        lien_maison="http://192.168.23.115:8123/usvegliu/s/TOKEN",
        wifi_ssid="",
        voucher_code="8065941041",
        voucher_revoked=False,
        preview=False,
    )
    assert "Réseau Wi-Fi :" in bare
    assert "Code d'accès : 8065941041" in bare


def test_expired_preview_is_rejected():
    now = datetime(2026, 7, 12, tzinfo=UTC)
    preview = build_preview_record(now - timedelta(hours=30), hours=24)
    assert find_record_by_token({}, preview, preview["guest_token"], now) is None
    assert preview["key"] == PREVIEW_KEY


def test_fan_mapping_mh8_style():
    mapping = map_fan_modes(["auto", "low", "medium", "high"])
    assert mapping == {1: "low", 2: "medium", 3: "high"}
    assert infer_fan_speed("medium", mapping) == 2


def test_fan_mapping_numeric_and_partial():
    mapping = map_fan_modes(["1", "3"])
    assert mapping[1] == "1"
    assert mapping[3] == "3"


def test_hvac_helpers():
    assert climate_is_on("heat") is True
    assert climate_is_on("off") is False
    assert pick_hvac_on(["off", "cool", "heat"], None) == "heat"
    assert pick_hvac_on(["off", "cool", "heat"], "cool") == "cool"
    assert pick_hvac_on(["off", "fan_only"], "fan_only") == "fan_only"


def test_house_mode_from_owner_switch():
    assert house_mode_from_state("on") == "cool"
    assert house_mode_from_state("off") == "heat"
    assert house_mode_from_state("climatisation") == "cool"
    assert house_mode_from_state("Chauffage") == "heat"
    assert house_mode_from_state("unavailable") is None
    assert resolve_house_mode("on") == "cool"
    assert resolve_house_mode("off") == "heat"
    assert resolve_house_mode(None, ["heat", "off"]) == "heat"
    assert resolve_house_mode(None, ["cool"]) == "cool"
    assert resolve_house_mode(None, ["off"]) == "cool"
    assert house_mode_label("heat") == "Chauffage"
    assert house_mode_label("cool") == "Climatisation"


def test_climate_activity_follows_setpoint_gap():
    assert (
        climate_activity(on=True, house_mode="heat", measured=20, setpoint=22)
        == "heating"
    )
    assert (
        climate_activity(on=True, house_mode="heat", measured=22, setpoint=20)
        == "idle"
    )
    assert (
        climate_activity(on=True, house_mode="cool", measured=26, setpoint=23)
        == "cooling"
    )
    assert (
        climate_activity(on=True, house_mode="cool", measured=22, setpoint=24)
        == "idle"
    )
    assert (
        climate_activity(on=True, house_mode="heat", measured=21, setpoint=21)
        == "idle"
    )
    assert (
        climate_activity(on=False, house_mode="heat", measured=18, setpoint=22)
        == "off"
    )


def test_guest_entity_classification():
    assert classify_guest_entity("climate.salon") == "climate"
    assert classify_guest_entity("lock.entree") == "lock"
    assert classify_guest_entity("alarm_control_panel.maison") == "alarm"
    assert classify_guest_entity("light.cuisine") == "light"
    assert classify_guest_entity("scene.soiree") == "scene"
    assert classify_guest_entity("script.tout_eteindre") == "scene"
    assert (
        classify_guest_entity("cover.garage", device_class="garage") == "garage"
    )
    assert classify_guest_entity("cover.portail_sud", name="Portail") == "gate"
    assert classify_guest_entity("cover.chambre", device_class="shutter") == "shutter"
    assert (
        classify_guest_entity("sensor.jardin", device_class="temperature", name="Extérieur")
        == "outdoor"
    )
    assert (
        classify_guest_entity(
            "sensor.piscine_temp", device_class="temperature", name="Piscine"
        )
        == "pool_temp"
    )
    assert classify_guest_entity("sensor.piscine_ph", unit="pH", name="pH piscine") == (
        "pool_ph"
    )
    assert classify_guest_entity("switch.prise_salon") is None
    assert alarm_view_state("armed_away") == "armed"
    assert alarm_view_state("disarmed") == "disarmed"
    assert cover_is_open("opening") is True


def test_public_url_uses_s_path():
    assert public_guest_url("https://www.usvegliu.fr", "Ab3") == (
        "https://www.usvegliu.fr/s/Ab3"
    )
    assert public_guest_url("", "Ab3") == "/usvegliu/s/Ab3"
