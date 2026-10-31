"""Journal path, CSV archive, redaction and tenant policy."""

from datetime import datetime, timezone
import logging
from pathlib import Path

import pytest

from custom_components.ms_lumio.access import (
    ADMIN_GROUP_ID,
    TenantAccessError,
    assert_not_privileged,
    build_tenant_policy,
    generate_password,
)
from custom_components.ms_lumio.const import FORBIDDEN_DOMAINS, TENANT_GROUP_ID
from custom_components.ms_lumio.dashboard import build_dashboard_config
from custom_components.ms_lumio.journal import Journal, JournalPathError, resolve_journal_path
from custom_components.ms_lumio.redact import SecretLogFilter, redact


def test_journal_stays_inside_config_or_media(tmp_path: Path):
    config = tmp_path / "config"
    media = tmp_path / "media"
    config.mkdir()
    media.mkdir()
    inside = resolve_journal_path(config, "ms_lumio/journal.csv", [media])
    assert inside == (config / "ms_lumio" / "journal.csv").resolve()
    mounted = resolve_journal_path(config, str(media / "synology" / "journal.csv"), [media])
    assert mounted.is_relative_to(media.resolve())
    with pytest.raises(JournalPathError):
        resolve_journal_path(config, "../etc/passwd", [media])
    with pytest.raises(JournalPathError):
        resolve_journal_path(config, "/etc/passwd", [media])


@pytest.mark.asyncio
async def test_csv_contains_the_code_and_nothing_is_logged(tmp_path: Path, caplog):
    journal = Journal(tmp_path / "ms_lumio" / "journal.csv")
    with caplog.at_level(logging.DEBUG):
        await journal.async_append(
            {
                "action": "voucher_cree",
                "reservation_id": "stay-1",
                "locataire": "Jean Dupont",
                "debut": "2026-07-10",
                "fin": "2026-07-17",
                "voucher_id": "voucher-1",
                "code": "ABCD12",
                "utilisateur_ha": "loc-jean",
                "mot_de_passe": "s3cret-password",
                "detail": "",
            }
        )
    text = journal.path.read_text(encoding="utf-8")
    assert "ABCD12" in text
    assert "s3cret-password" in text
    assert "Jean Dupont" in text
    assert "ABCD12" not in caplog.text
    assert "s3cret-password" not in caplog.text
    await journal.async_append({"action": "voucher_supprime", "reservation_id": "stay-1"})
    lines = journal.path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 3
    assert lines[0].startswith("horodatage")


def test_diagnostics_and_logs_redact_secrets():
    payload = redact(
        {
            "entry_data": {"api_key": "super-secret-key", "host": "192.168.1.1"},
            "stays": [
                {
                    "guest": "Jean Dupont",
                    "voucher_code": "ABCD12",
                    "password": "s3cret-password",
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
    assert payload["stays"][0]["guest"] == "**REDACTED**"
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


def test_tenant_policy_excludes_cameras_locks_and_admin():
    policy = build_tenant_policy(
        ["climate.salon", "cover.chambre", "light.entree"]
    )
    entities = policy["entities"]["entity_ids"]
    assert set(entities) == {"climate.salon", "cover.chambre", "light.entree"}
    assert entities["climate.salon"] == {"read": True, "control": True, "edit": False}
    for domain in ("camera", "lock", "alarm_control_panel"):
        with pytest.raises(TenantAccessError):
            build_tenant_policy([f"{domain}.entree"])
    assert "camera" in FORBIDDEN_DOMAINS
    assert TENANT_GROUP_ID != ADMIN_GROUP_ID

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
        ["climate.salon"],
        ["cover.sejour"],
        ["light.salon"],
    )
    cards = config["views"][0]["cards"]
    dumped = str(cards)
    assert "climate.salon" in dumped
    assert "cover.sejour" in dumped
    assert "light.salon" in dumped
    assert "camera" not in dumped
    assert "lock" not in dumped


def test_sources_do_not_embed_a_credential():
    root = Path(__file__).resolve().parents[1] / "custom_components" / "ms_lumio"
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert "X-API-KEY" in text or "api_key" in text or path.name != "unifi.py"
        assert "BEGIN PRIVATE KEY" not in text
        assert "super-secret-key" not in text
