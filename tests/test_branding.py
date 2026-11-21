"""Guest brand themes: U Svegliu (default) and 49 Ledbury."""

from pathlib import Path
import struct

from custom_components.usvegliu.branding import (
    THEME_LEDBURY,
    THEME_USVEGLIU,
    brand_from_options,
    guest_brand,
    normalize_guest_theme,
)
from custom_components.usvegliu.guest_session import guest_welcome_message


def test_normalize_guest_theme():
    assert normalize_guest_theme(None) == THEME_USVEGLIU
    assert normalize_guest_theme("usvegliu") == THEME_USVEGLIU
    assert normalize_guest_theme("ledbury") == THEME_LEDBURY
    assert normalize_guest_theme("49 Ledbury") == THEME_LEDBURY
    assert normalize_guest_theme("unknown") == THEME_USVEGLIU


def test_unifi_configured_helper():
    from custom_components.usvegliu.branding import unifi_configured

    assert unifi_configured({"host": "192.168.1.1", "api_key": "secret"})
    assert not unifi_configured({"host": "", "api_key": ""})
    assert not unifi_configured({"host": "192.168.1.1", "api_key": ""})
    assert not unifi_configured(None)


def test_ledbury_brand_payload():
    brand = guest_brand(THEME_LEDBURY)
    assert brand["name"] == "49 Ledbury"
    assert brand["place"] == "Notting Hill"
    assert brand["banner"].endswith("logo-banner-ledbury.png")
    assert brand["logo"].endswith("logo-ledbury.png")
    assert brand["wifi_ssid_default"] == "49Ledbury-Guest"
    assert brand_from_options({"guest_theme": "ledbury"})["id"] == THEME_LEDBURY


def test_welcome_message_uses_house_and_team():
    note = guest_welcome_message(
        guest="Ada Lovelace",
        check_in="2026-07-10",
        check_out="2026-07-17",
        lien_maison="https://example.test/s/token",
        wifi_ssid="49Ledbury-Guest",
        voucher_code="ABCD12",
        voucher_revoked=False,
        preview=False,
        house_name="49 Ledbury",
        team_name="The 49 Ledbury team",
    )
    assert "accueillir à 49 Ledbury" in note
    assert "The 49 Ledbury team" in note
    assert "L'équipe Usvegliu" not in note


def test_ledbury_logo_assets_ship():
    www = Path(__file__).resolve().parents[1] / "custom_components" / "usvegliu" / "www"

    def png_size(path: Path) -> tuple[int, int]:
        with path.open("rb") as handle:
            assert handle.read(8) == b"\x89PNG\r\n\x1a\n"
            length, chunk = struct.unpack(">I4s", handle.read(8))
            assert chunk == b"IHDR" and length == 13
            width, height = struct.unpack(">II", handle.read(8))
        return width, height

    mark = www / "logo-ledbury.png"
    banner = www / "logo-banner-ledbury.png"
    assert mark.is_file() and banner.is_file()
    assert png_size(mark) == (256, 256)
    assert png_size(banner)[0] >= 1400
    css = (www / "app.css").read_text(encoding="utf-8")
    js = (www / "app.js").read_text(encoding="utf-8")
    assert 'data-theme="ledbury"' in css or "data-theme=\"ledbury\"" in css
    assert "body[data-theme=\"ledbury\"]" in css
    assert "applyBrandChrome" in js
    assert "logo-banner-ledbury.png" in js or "brand.banner" in js
    flow = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "usvegliu"
        / "config_flow.py"
    ).read_text(encoding="utf-8")
    assert "guest_theme" in flow
    assert "async_step_cambium" in flow
    assert "async_show_menu" not in flow
    assert "Cambium EasyPass — sans UDM" in flow
    assert "_async_probe_cambium" in flow
    assert "SelectSelectorMode.LIST" in flow
