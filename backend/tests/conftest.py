import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config  # noqa: E402
from main import app  # noqa: E402


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """A test client using a fresh, temporary database and photo folder."""
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(config, "UPLOAD_DIR", tmp_path / "uploads")
    with TestClient(app) as test_client:
        yield test_client
