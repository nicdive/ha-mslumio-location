"""Lumio weather mapping for the guest home screen."""

from datetime import datetime, timedelta, timezone

from custom_components.usvegliu.weather import (
    parse_open_meteo,
    weather_is_fresh,
    weather_look,
)


def test_wmo_codes_have_villa_icons():
    assert weather_look(0) == ("sun", "Ensoleillé")
    assert weather_look(0, locale="en") == ("sun", "Sunny")
    assert weather_look(2)[0] == "sun_cloud"
    assert weather_look(3)[0] == "cloud"
    assert weather_look(61)[0] == "rain"
    assert weather_look(95)[0] == "storm"
    assert weather_look(95, locale="en") == ("storm", "Thunderstorm")


def test_parse_open_meteo_uses_current_and_daily():
    note = parse_open_meteo(
        {
            "current": {
                "temperature_2m": 17.6,
                "weather_code": 1,
                "wind_speed_10m": 14.2,
            },
            "daily": {
                "temperature_2m_max": [20.4],
                "temperature_2m_min": [11.8],
                "weather_code": [1],
            },
        }
    )
    assert note == {
        "place": "Lumio",
        "label": "Peu nuageux",
        "icon": "sun_cloud",
        "code": 1,
        "temperature": 18,
        "high": 20,
        "low": 12,
        "wind": 14,
    }


def test_parse_open_meteo_london_english():
    note = parse_open_meteo(
        {
            "current": {
                "temperature_2m": 11.2,
                "weather_code": 95,
                "wind_speed_10m": 40,
            },
            "daily": {
                "temperature_2m_max": [14.0],
                "temperature_2m_min": [8.0],
                "weather_code": [95],
            },
        },
        place="london",
        locale="en",
    )
    assert note["place"] == "London"
    assert note["label"] == "Thunderstorm"
    assert note["icon"] == "storm"
    assert note["temperature"] == 11


def test_weather_cache_ttl():
    now = datetime(2026, 11, 5, 12, tzinfo=timezone.utc)
    assert weather_is_fresh(now - timedelta(minutes=10), now) is True
    assert weather_is_fresh(now - timedelta(minutes=25), now) is False
    assert weather_is_fresh(None, now) is False
