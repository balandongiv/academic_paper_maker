"""Advisory file lock using a companion .lock file.

Guards shared-folder operations (e.g. output JSON writes to a network drive)
that fall outside SQLite transactions. This is a lightweight supplement to the
database row-claiming logic in database.py — not a replacement.

Usage:
    with file_lock(Path("output/a94f2c8b.json"), machine_id="computer_1"):
        save_output(output_file, data)
"""

from __future__ import annotations

import json
import logging
import os
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator

log = logging.getLogger(__name__)

_LOCK_EXT      = ".lock"
_POLL_INTERVAL = 0.5   # seconds between retries


def _lock_path(target: Path) -> Path:
    return target.with_suffix(target.suffix + _LOCK_EXT)


def _write_lock(lock_file: Path, machine_id: str) -> None:
    lock_file.write_text(
        json.dumps({
            "machine_id": machine_id,
            "acquired_at": datetime.utcnow().isoformat(),
        }),
        encoding="utf-8",
    )


def _read_lock(lock_file: Path) -> dict:
    try:
        return json.loads(lock_file.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _is_stale(lock_file: Path, stale_hours: float) -> bool:
    acquired = _read_lock(lock_file).get("acquired_at")
    if not acquired:
        return True
    try:
        age_hours = (datetime.utcnow() - datetime.fromisoformat(acquired)).total_seconds() / 3600
        return age_hours > stale_hours
    except Exception:
        return True


@contextmanager
def file_lock(
    target: Path,
    machine_id: str,
    timeout: float = 30.0,
    stale_hours: float = 2.0,
) -> Generator[None, None, None]:
    """Acquire an advisory .lock file beside *target*.

    Raises RuntimeError if the lock cannot be acquired within *timeout* seconds.
    Automatically recovers stale locks older than *stale_hours*.
    """
    lock_file = _lock_path(target)
    deadline  = time.monotonic() + timeout

    while True:
        if not lock_file.exists() or _is_stale(lock_file, stale_hours):
            try:
                tmp = lock_file.with_suffix(".tmp")
                _write_lock(tmp, machine_id)
                os.replace(tmp, lock_file)  # atomic on POSIX; best-effort on Windows
                break
            except Exception as exc:
                log.debug("Lock creation race: %s", exc)
        else:
            owner = _read_lock(lock_file).get("machine_id", "?")
            log.debug("Lock held by %s — waiting…", owner)

        if time.monotonic() > deadline:
            info = _read_lock(lock_file)
            raise RuntimeError(
                f"Could not acquire lock on {target} within {timeout}s "
                f"(held by {info.get('machine_id', 'unknown')} "
                f"since {info.get('acquired_at', 'unknown')})"
            )
        time.sleep(_POLL_INTERVAL)

    try:
        yield
    finally:
        try:
            lock_file.unlink(missing_ok=True)
        except Exception as exc:
            log.warning("Failed to release lock %s: %s", lock_file, exc)
