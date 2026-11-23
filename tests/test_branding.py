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
    from custom_components.usvegliu.branding import brand_climate_fans, brand_heat_only

    brand = guest_brand(THEME_LEDBURY)
    assert brand["name"] == "49 Ledbury"
    assert brand["place"] == "London"
    assert brand["locale"] == "en"
    assert brand["weather_place"] == "london"
    assert "Portobello" in brand["tagline"]
    assert brand["banner"].endswith("logo-banner-ledbury.png")
    assert brand["logo"].endswith("logo-ledbury.png")
    assert brand["wifi_ssid_default"] == "49Ledbury-Guest"
    assert brand["climate_fans"] == "0"
    assert brand["climate_heat_only"] == "1"
    assert not brand_climate_fans(brand)
    assert brand_heat_only(brand)
    assert brand_climate_fans(guest_brand(THEME_USVEGLIU))
    assert not brand_heat_only(guest_brand(THEME_USVEGLIU))
    assert brand_from_options({"guest_theme": "ledbury"})["id"] == THEME_LEDBURY
    assert brand_from_options({"guest_theme": "ledbury"})["locale"] == "en"
    assert (
        brand_from_options({"guest_theme": "ledbury", "guest_locale": "fr"})["locale"]
        == "fr"
    )
    assert (
        brand_from_options({"guest_theme": "usvegliu", "guest_locale": "en"})["locale"]
        == "en"
    )


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

    def png_info(path: Path) -> tuple[int, int, int]:
        with path.open("rb") as handle:
            assert handle.read(8) == b"\x89PNG\r\n\x1a\n"
            length, chunk = struct.unpack(">I4s", handle.read(8))
            assert chunk == b"IHDR" and length == 13
            width, height, bit_depth, color_type = struct.unpack(">IIBB", handle.read(10))
        return width, height, color_type

    mark = www / "logo-ledbury.png"
    banner = www / "logo-banner-ledbury.png"
    assert mark.is_file() and banner.is_file()
    mark_w, mark_h, mark_ct = png_info(mark)
    ban_w, ban_h, ban_ct = png_info(banner)
    assert (mark_w, mark_h) == (256, 256)
    # Horizontal Ledbury banner: door left + wordmark right
    assert ban_w >= 1400
    assert 350 <= ban_h <= 450
    # 6 = RGBA — transparent like the Usvegliu banner
    assert mark_ct == 6
    assert ban_ct == 6
    css = (www / "app.css").read_text(encoding="utf-8")
    js = (www / "app.js").read_text(encoding="utf-8")
    assert 'data-theme="ledbury"' in css or "data-theme=\"ledbury\"" in css
    assert "body[data-theme=\"ledbury\"]" in css
    assert "#258d60" in css
    assert "--bg: #e8f4ee" in css
    assert "fan-line" in css
    assert "display: none !important" in css
    assert "roomHasFan" in js
    assert "climateFans" in js
    assert 'I18N' in js and 'Good afternoon' in js
    assert "applyBrandChrome" in js
    assert "logo-banner-ledbury.png" in js or "brand.banner" in js
    flow = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "usvegliu"
        / "config_flow.py"
    ).read_text(encoding="utf-8")
    assert "guest_theme" in flow
    assert "guest_locale" in flow
    assert "CONF_GUEST_LOCALE" in flow
    assert "async_step_cambium" in flow
    assert "async_step_manual" in flow
    assert "async_show_menu" not in flow
    assert "VOUCHER_PROVIDER_MANUAL" in flow
    assert "_async_probe_cambium" in flow
    assert "SelectSelectorMode.LIST" in flow
    assert "CONF_MANUAL_WIFI_CODE" in flow
    assert "TargetSelector()" in flow
    assert "entity={}" not in flow
    assert "area={}" not in flow
    strings = (
        Path(__file__).resolve().parents[1]
        / "custom_components"
        / "usvegliu"
        / "strings.json"
    ).read_text(encoding="utf-8")
    assert '"manual": "Voucher manuel (sans API)"' in strings
    assert '"step": {\n      "manual"' in strings or '"manual": {' in strings
