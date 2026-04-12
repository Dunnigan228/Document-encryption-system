"""
Tests for Phase 2 FileService — JSON sidecar persistence and thread safety.
TDD: tests written first (RED), then implementation fills them (GREEN).
"""
import json
import tempfile
import threading
from pathlib import Path

import pytest

from app.services.file_service import FileService


@pytest.fixture
def jobs_dir(tmp_path):
    return tmp_path / "jobs"


@pytest.fixture
def svc(jobs_dir):
    return FileService(jobs_dir=jobs_dir)


@pytest.fixture
def sample_meta():
    return {
        "status": "queued",
        "job_type": "encrypt",
        "original_filename": "test.pdf",
        "file_type": "pdf",
        "created_at": "2026-04-12T00:00:00Z",
        "expires_at": "2026-04-12T01:00:00Z",
        "error": None,
        "result_paths": {},
        "original_path": "files/test.pdf",
    }


# --- Constructor ---

def test_init_creates_jobs_dir(jobs_dir):
    """FileService(jobs_dir=...) should create the directory."""
    assert not jobs_dir.exists()
    FileService(jobs_dir=jobs_dir)
    assert jobs_dir.exists()


def test_init_accepts_jobs_dir_kwarg(jobs_dir):
    """New signature must take jobs_dir as keyword argument."""
    svc = FileService(jobs_dir=jobs_dir)
    assert svc is not None


# --- register ---

def test_register_stores_in_memory(svc, sample_meta):
    svc.register("abc123", sample_meta)
    result = svc.get("abc123")
    assert result is not None
    assert result["original_filename"] == "test.pdf"


def test_register_writes_sidecar(svc, jobs_dir, sample_meta):
    svc.register("abc123", sample_meta)
    sidecar = jobs_dir / "abc123.json"
    assert sidecar.exists()
    data = json.loads(sidecar.read_text())
    assert data["status"] == "queued"


# --- update_status ---

def test_update_status_changes_status(svc, sample_meta):
    svc.register("abc123", sample_meta)
    svc.update_status("abc123", "processing")
    assert svc.get("abc123")["status"] == "processing"


def test_update_status_writes_sidecar(svc, jobs_dir, sample_meta):
    svc.register("abc123", sample_meta)
    svc.update_status("abc123", "processing")
    data = json.loads((jobs_dir / "abc123.json").read_text())
    assert data["status"] == "processing"


def test_update_status_merges_kwargs(svc, sample_meta):
    svc.register("abc123", sample_meta)
    svc.update_status("abc123", "complete", result_paths={"encrypted_file": "files/out.enc"})
    entry = svc.get("abc123")
    assert entry["status"] == "complete"
    assert entry["result_paths"] == {"encrypted_file": "files/out.enc"}


def test_update_status_noop_on_missing_id(svc):
    """update_status on unknown file_id should not raise."""
    svc.update_status("nonexistent", "processing")


# --- get ---

def test_get_returns_none_for_missing(svc):
    assert svc.get("missing") is None


def test_get_returns_copy(svc, sample_meta):
    """get() must return a copy so callers cannot mutate internal state."""
    svc.register("abc123", sample_meta)
    entry = svc.get("abc123")
    entry["status"] = "MUTATED"
    assert svc.get("abc123")["status"] == "queued"


# --- delete ---

def test_delete_removes_from_memory(svc, sample_meta):
    svc.register("abc123", sample_meta)
    svc.delete("abc123")
    assert svc.get("abc123") is None


def test_delete_unlinks_sidecar(svc, jobs_dir, sample_meta):
    svc.register("abc123", sample_meta)
    svc.delete("abc123")
    assert not (jobs_dir / "abc123.json").exists()


def test_delete_noop_on_missing(svc):
    """delete() on an unknown id should not raise."""
    svc.delete("nonexistent")


# --- all_ids ---

def test_all_ids_returns_list(svc, sample_meta):
    svc.register("a1", sample_meta)
    svc.register("b2", {**sample_meta, "original_filename": "b.pdf"})
    ids = svc.all_ids()
    assert set(ids) == {"a1", "b2"}


def test_all_ids_is_snapshot(svc, sample_meta):
    """Mutating the returned list must not affect internal storage."""
    svc.register("a1", sample_meta)
    ids = svc.all_ids()
    ids.append("PHANTOM")
    assert "PHANTOM" not in svc.all_ids()


# --- restore_from_disk ---

def test_restore_loads_existing_jobs(jobs_dir, sample_meta):
    svc1 = FileService(jobs_dir=jobs_dir)
    svc1.register("abc123", sample_meta)
    # New instance (simulates restart)
    svc2 = FileService(jobs_dir=jobs_dir)
    count = svc2.restore_from_disk(jobs_dir.parent)
    assert count == 1
    assert svc2.get("abc123") is not None


def test_restore_marks_processing_as_failed(jobs_dir, sample_meta):
    svc1 = FileService(jobs_dir=jobs_dir)
    meta_processing = {**sample_meta, "status": "processing"}
    svc1.register("abc123", meta_processing)
    # New instance
    svc2 = FileService(jobs_dir=jobs_dir)
    svc2.restore_from_disk(jobs_dir.parent)
    entry = svc2.get("abc123")
    assert entry["status"] == "failed"
    assert entry.get("error") is not None
    assert "restart" in entry["error"].lower() or "restarted" in entry["error"].lower()


def test_restore_updates_sidecar_on_processing_reset(jobs_dir, sample_meta):
    svc1 = FileService(jobs_dir=jobs_dir)
    svc1.register("abc123", {**sample_meta, "status": "processing"})
    svc2 = FileService(jobs_dir=jobs_dir)
    svc2.restore_from_disk(jobs_dir.parent)
    data = json.loads((jobs_dir / "abc123.json").read_text())
    assert data["status"] == "failed"


def test_restore_skips_corrupt_sidecar(jobs_dir):
    (jobs_dir / "bad.json").write_text("NOT JSON", encoding="utf-8")
    jobs_dir.mkdir(parents=True, exist_ok=True)
    svc = FileService(jobs_dir=jobs_dir)
    count = svc.restore_from_disk(jobs_dir.parent)
    assert count == 0
    assert not (jobs_dir / "bad.json").exists()


def test_restore_returns_count(jobs_dir, sample_meta):
    svc1 = FileService(jobs_dir=jobs_dir)
    for i in range(3):
        svc1.register(f"id{i}", {**sample_meta, "original_filename": f"f{i}.pdf"})
    svc2 = FileService(jobs_dir=jobs_dir)
    count = svc2.restore_from_disk(jobs_dir.parent)
    assert count == 3


# --- Thread safety ---

def test_concurrent_registers_do_not_crash(jobs_dir, sample_meta):
    svc = FileService(jobs_dir=jobs_dir)
    errors = []

    def register_one(i):
        try:
            svc.register(f"id{i}", {**sample_meta, "original_filename": f"f{i}.pdf"})
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=register_one, args=(i,)) for i in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    assert len(svc.all_ids()) == 20


# --- Module singleton ---

def test_module_singleton_exists():
    from app.services.file_service import file_service, FileService
    assert isinstance(file_service, FileService)


def test_module_singleton_uses_default_path():
    from app.services.file_service import file_service
    assert "enc_service" in str(file_service._jobs_dir)
