"""
In-memory file registry.
Maps file_id (str) to file metadata dict.
Phase 2 will replace this with JSON-sidecar persistence.
"""
from datetime import datetime
from typing import Any, Dict, Optional


class FileService:
    """Thread-unsafe in-memory store. Acceptable for Phase 1 (single-process, sync endpoints)."""

    def __init__(self) -> None:
        self._storage: Dict[str, Dict[str, Any]] = {}

    def register(self, file_id: str, metadata: Dict[str, Any]) -> None:
        """Store metadata keyed by file_id."""
        metadata.setdefault("created_at", datetime.now())
        self._storage[file_id] = metadata

    def get(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Return metadata or None if not found."""
        return self._storage.get(file_id)

    def delete(self, file_id: str) -> None:
        """Remove an entry. No-op if not found."""
        self._storage.pop(file_id, None)

    def all_ids(self):
        """Return a snapshot of all registered file_ids."""
        return list(self._storage.keys())


# Module-level singleton — shared by all route modules in this process.
file_service = FileService()
