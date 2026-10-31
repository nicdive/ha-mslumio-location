"""Append-only CSV journal for the Synology archive.

Rows contain the voucher code and the tenant password because that is the
point of the archive. Nothing in this module writes those values to a logger.
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
    "code",
    "utilisateur_ha",
    "mot_de_passe",
    "detail",
)


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

    def _append(self, row: dict[str, str]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        new_file = not self.path.exists() or self.path.stat().st_size == 0
        normalized = {column: row.get(column, "") for column in COLUMNS}
        if not normalized["horodatage"]:
            normalized["horodatage"] = datetime.now(timezone.utc).isoformat()
        with self.path.open("a", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=COLUMNS, quoting=csv.QUOTE_MINIMAL)
            if new_file:
                writer.writeheader()
            writer.writerow(normalized)
