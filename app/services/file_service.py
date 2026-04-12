"""
Thread-safe file job registry with JSON sidecar persistence.

Phase 2 upgrade: FileService now persists every job to temp_dir/jobs/{file_id}.json
so that job state survives container restarts (FILE-08, D-04, D-05).

threading.Lock (not asyncio.Lock) is used because background encryption/decryption
tasks run in a ThreadPoolExecutor where asyncio primitives are not safe to await.
"""
import json
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional


class FileService:
    """Thread-safe job registry backed by JSON sidecar files on disk.

    All public methods acquire self._lock before touching _storage.
    _write_sidecar() MUST be called with the lock already held.
    """

    def __init__(self, jobs_dir: Path) -> None:
        self._storage: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._jobs_dir = jobs_dir
        self._jobs_dir.mkdir(parents=True, exist_ok=True)

    def register(self, file_id: str, metadata: Dict[str, Any]) -> None:
        """Store metadata and write JSON sidecar.

        Called from async endpoint before 202 is returned so the sidecar exists
        before any background task starts — prevents orphaned file_ids on crash.
        """
        with self._lock:
            self._storage[file_id] = metadata
            self._write_sidecar(file_id, metadata)

    def update_status(self, file_id: str, status: str, **kwargs: Any) -> None:
        """Merge status + extra kwargs into stored entry and flush sidecar.

        Called from background tasks (in ThreadPoolExecutor threads).
        If file_id is unknown the update is silently ignored so callers
        do not need to guard against race-at-deletion.
        """
        with self._lock:
            entry = dict(self._storage.get(file_id, {}))
            entry["status"] = status
            entry.update(kwargs)
            self._storage[file_id] = entry
            self._write_sidecar(file_id, entry)

    def get(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Return a shallow copy of the entry or None.

        Returns a copy so callers cannot accidentally mutate internal state.
        """
        with self._lock:
            entry = self._storage.get(file_id)
            return dict(entry) if entry is not None else None

    def delete(self, file_id: str) -> None:
        """Remove entry from memory and disk. No-op if not found."""
        with self._lock:
            self._storage.pop(file_id, None)
            (self._jobs_dir / f"{file_id}.json").unlink(missing_ok=True)

    def all_ids(self) -> List[str]:
        """Return a snapshot list of all registered file_ids."""
        with self._lock:
            return list(self._storage.keys())

    def restore_from_disk(self, temp_dir: Path) -> int:
        """Scan jobs_dir on startup and load all valid sidecars into memory.

        Any job found with status "processing" is immediately reset to "failed"
        because the worker thread is gone after a restart (FILE-08, D-06).
        Corrupt or unreadable sidecar files are unlinked to prevent poison entries
        being loaded into _storage (T-02-01-01 mitigation).

        Returns the count of successfully loaded jobs.
        """
        count = 0
        for sidecar in self._jobs_dir.glob("*.json"):
            try:
                data = json.loads(sidecar.read_text(encoding="utf-8"))
                file_id = sidecar.stem
                if data.get("status") == "processing":
                    data["status"] = "failed"
                    data["error"] = "Server restarted while job was processing"
                    sidecar.write_text(
                        json.dumps(data, default=str), encoding="utf-8"
                    )
                with self._lock:
                    self._storage[file_id] = data
                count += 1
            except (json.JSONDecodeError, KeyError, OSError):
                # Corrupt sidecar — unlink to avoid polluting storage on next restart.
                sidecar.unlink(missing_ok=True)
        return count

    def _write_sidecar(self, file_id: str, data: Dict[str, Any]) -> None:
        """Write serialized job metadata to disk.

        MUST be called with self._lock held. Uses json.dumps(default=str) so that
        datetime objects from older code paths are serialized gracefully.
        """
        (self._jobs_dir / f"{file_id}.json").write_text(
            json.dumps(data, default=str), encoding="utf-8"
        )


# ---------------------------------------------------------------------------
# Module-level singleton — shared by all route modules in this process.
# ---------------------------------------------------------------------------
_DEFAULT_JOBS_DIR = Path("/tmp/enc_service/jobs")
file_service = FileService(jobs_dir=_DEFAULT_JOBS_DIR)
