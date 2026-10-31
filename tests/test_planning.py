"""Stay planning: windows, durations, cancellations, blocklist."""

from datetime import date, datetime, timedelta, timezone

from custom_components.ms_lumio.planning import (
    build_plan,
    default_blocklist,
    mbps_to_kbps,
    normalize_event,
    select_current,
    stored_keys_in_window,
    time_limit_minutes,
    voucher_name,
)

UTC = timezone.utc


def _stay(**kwargs):
    params = {
        "summary": "Jean Dupont",
        "start": date(2026, 7, 10),
        "end": date(2026, 7, 17),
        "uid": "airbnb-1",
        "tz": UTC,
    }
    params.update(kwargs)
    return normalize_event(**params)


def test_all_day_duration_includes_extra_day_and_rate_limit():
    stay = _stay()
    assert stay is not None
    assert stay.check_in == datetime(2026, 7, 10, tzinfo=UTC)
    assert stay.check_out == datetime(2026, 7, 17, tzinfo=UTC)
    assert time_limit_minutes(stay.check_in, stay.check_out, extra_days=1) == 8 * 24 * 60
    assert voucher_name(stay.guest, stay.check_in.date(), stay.check_out.date()) == (
        "Jean Dupont 2026-07-10/2026-07-17"
    )
    assert mbps_to_kbps(100) == 100_000


def test_voucher_is_not_created_before_the_lead_window():
    stay = _stay()
    plan = build_plan(
        [stay],
        now=datetime(2026, 7, 1, 8, tzinfo=UTC),
        lead_days=3,
        known_keys=[],
    )
    assert plan.ensure == ()
    assert plan.revoke_keys == ()


def test_voucher_is_planned_inside_the_lead_window():
    stay = _stay()
    plan = build_plan(
        [stay],
        now=datetime(2026, 7, 8, 8, tzinfo=UTC),
        lead_days=3,
        device_limit=10,
        download_mbps=100,
        upload_mbps=100,
        extra_days=1,
    )
    assert len(plan.ensure) == 1
    spec = plan.ensure[0].voucher
    assert spec.authorized_guest_limit == 10
    assert spec.rx_rate_limit_kbps == 100_000
    assert spec.tx_rate_limit_kbps == 100_000
    assert spec.time_limit_minutes == 8 * 24 * 60
    assert plan.ensure[0].username.startswith("loc-jean-dupont-")


def test_checkout_and_cancellation_revoke_a_known_stay():
    stay = _stay()
    now = datetime(2026, 7, 12, tzinfo=UTC)
    active = build_plan([stay], now=now, lead_days=3, known_keys=["airbnb-1|2026-07-10"])
    assert [item.key for item in active.ensure] == ["airbnb-1|2026-07-10"]

    checked_out = build_plan(
        [stay],
        now=datetime(2026, 7, 17, 0, 1, tzinfo=UTC),
        lead_days=3,
        known_keys=[stay.key],
    )
    assert checked_out.ensure == ()
    assert checked_out.revoke_keys == (stay.key,)

    cancelled = build_plan([], now=now, lead_days=3, known_keys=[stay.key])
    assert cancelled.revoke_keys == (stay.key,)


def test_blocked_titles_and_overlong_events_are_ignored():
    blocked = _stay(
        summary="Airbnb (Not available)",
        uid="block-1",
        blocklist=default_blocklist(),
    )
    assert blocked is None
    french = normalize_event(
        summary="Indisponible",
        start=date(2026, 8, 1),
        end=date(2026, 8, 3),
        tz=UTC,
        blocklist=default_blocklist(),
    )
    assert french is None
    too_long = normalize_event(
        summary="Proprio",
        start=date(2026, 1, 1),
        end=date(2026, 6, 1),
        tz=UTC,
        max_stay_days=60,
    )
    assert too_long is None


def test_cancelled_status_is_ignored():
    assert (
        normalize_event(
            summary="Jean",
            start=date(2026, 7, 10),
            end=date(2026, 7, 12),
            status="cancelled",
            tz=UTC,
        )
        is None
    )


def test_quotes_are_stripped_from_the_voucher_name():
    stay = _stay(summary="Jean O'Brien")
    assert stay is not None
    assert "'" not in stay.guest
    assert "'" not in voucher_name(stay.guest, stay.check_in.date(), stay.check_out.date())


def test_stored_keys_outside_the_query_window_are_kept():
    stored = {
        "far": {"check_in": "2027-01-01T00:00:00+00:00", "check_out": "2027-01-08T00:00:00+00:00"},
        "soon": {"check_in": "2026-07-10T00:00:00+00:00", "check_out": "2026-07-17T00:00:00+00:00"},
    }
    keys = stored_keys_in_window(
        stored,
        datetime(2026, 7, 1, tzinfo=UTC),
        datetime(2026, 7, 1, tzinfo=UTC) + timedelta(days=120),
    )
    assert keys == ["soon"]


def test_select_current_prefers_the_stay_in_progress():
    stored = {
        "next": {
            "key": "next",
            "voucher_code": "NEXT",
            "check_in": "2026-08-01T00:00:00+00:00",
            "check_out": "2026-08-05T00:00:00+00:00",
        },
        "now": {
            "key": "now",
            "voucher_code": "NOW",
            "check_in": "2026-07-01T00:00:00+00:00",
            "check_out": "2026-07-08T00:00:00+00:00",
        },
    }
    current = select_current(stored, datetime(2026, 7, 3, tzinfo=UTC))
    assert current is not None
    assert current["voucher_code"] == "NOW"
