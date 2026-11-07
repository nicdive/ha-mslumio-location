"""Append-only CSV journal for the Synology archive.

Rows keep the voucher code. They never keep a Home Assistant password.
Nothing in this module writes a row to a logger.
"""

from __future__ import annotations

import asyncio
import csv
from datetime import datetime, timezone
from pathlib import Path

COLUMNS: tuple[str, ...] = (
    "horodatage",
    "action",
    "reservation_id",
    "locataire",
    "debut",
    "fin",
    "voucher_id",
    "voucher_nom",
    "code",
    "mac",
    "detail",
)

_SECRET_HEADERS = {"mot_de_passe", "password", "code_compte", "utilisateur_ha"}

ACTION_LABELS: dict[str, str] = {
    "voucher_cree": "Wi-Fi créé",
    "voucher_adopte": "Wi-Fi repris",
    "voucher_regenere": "Wi-Fi renouvelé",
    "voucher_supprime": "Wi-Fi retiré",
    "acces_cree": "Compte créé",
    "acces_regenere": "Mot de passe renouvelé",
    "acces_supprime": "Compte retiré",
    "acces_desactive": "Compte désactivé",
    "message_envoye": "Mail d'accueil envoyé",
}


class JournalPathError(ValueError):
    """Raised when the journal path escapes the allowed directories."""


def resolve_journal_path(
    config_dir: Path,
    raw: str,
    media_dirs: list[Path] | None = None,
) -> Path:
    """Resolve a journal path under the config dir or a media mount.

    Absolute paths are refused unless they stay inside the HA config directory
    or a configured media directory (the usual place for a Synology mount).
    """
    if not raw or not raw.strip():
        raise JournalPathError("empty journal path")
    roots = [config_dir.resolve()]
    for media in media_dirs or []:
        roots.append(media.resolve())
    candidate_raw = Path(raw.strip())
    if candidate_raw.is_absolute():
        candidate = candidate_raw.resolve()
    else:
        candidate = (config_dir / candidate_raw).resolve()
    for root in roots:
        if candidate == root or root in candidate.parents:
            return candidate
    raise JournalPathError("journal path is outside the allowed directories")


class Journal:
    """CSV writer guarded by an asyncio lock."""

    def __init__(self, path: Path) -> None:
        """Store the destination path."""
        self.path = path
        self._lock = asyncio.Lock()

    async def async_append(self, row: dict[str, str]) -> None:
        """Append one row, creating the header when the file is new."""
        async with self._lock:
            await asyncio.to_thread(self._append, row)

    def recent_public(self, limit: int = 30) -> list[dict[str, str]]:
        """Newest journal rows for the Console. No voucher code."""
        if limit <= 0 or not self.path.exists() or self.path.stat().st_size == 0:
            return []
        with self.path.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        out: list[dict[str, str]] = []
        for raw in rows[-limit:]:
            action = str(raw.get("action") or "")
            stamp = str(raw.get("horodatage") or "")
            out.append(
                {
                    "horodatage": stamp[:16].replace("T", " "),
                    "action": action,
                    "libelle": ACTION_LABELS.get(action, action.replace("_", " ")),
                    "locataire": str(raw.get("locataire") or ""),
                    "debut": str(raw.get("debut") or "")[:10],
                    "fin": str(raw.get("fin") or "")[:10],
                    "detail": str(raw.get("detail") or ""),
                    "reservation_id": str(raw.get("reservation_id") or ""),
                }
            )
        out.reverse()
        return out

    def _append(self, row: dict[str, str]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        _drop_password_columns(self.path)
        new_file = not self.path.exists() or self.path.stat().st_size == 0
        normalized = {column: row.get(column, "") for column in COLUMNS}
        if not normalized["horodatage"]:
            normalized["horodatage"] = datetime.now(timezone.utc).isoformat()
        with self.path.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS, quoting=csv.QUOTE_MINIMAL)
            if new_file:
                writer.writeheader()
            writer.writerow(normalized)


def _drop_password_columns(path: Path) -> None:
    """Rewrite an older journal so passwords do not stay on disk."""
    if not path.exists() or path.stat().st_size == 0:
        return
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames or []
        if not _SECRET_HEADERS.intersection(fieldnames):
            return
        rows = []
        for raw in reader:
            cleaned = {column: raw.get(column, "") or "" for column in COLUMNS}
            for secret in _SECRET_HEADERS:
                raw.pop(secret, None)
            rows.append(cleaned)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS, quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        writer.writerows(rows)
