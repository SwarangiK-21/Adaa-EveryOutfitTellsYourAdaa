import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import auth  # noqa: E402
import ratelimit  # noqa: E402
import config  # noqa: E402
from main import app  # noqa: E402

TEST_USER = {"name": "Test User", "email": "test@example.com", "phone": "9876543210", "password": "a-good-password",
             "accept_privacy": True}


@pytest.fixture()
def data_dir(tmp_path, monkeypatch):
    """A fresh, temporary database and photo folder for each test."""
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(config, "UPLOAD_DIR", tmp_path / "uploads")
    auth._failures.clear()
    auth._reset_emails.clear()
    ratelimit.clear()
    return tmp_path


@pytest.fixture()
def anon(data_dir):
    """A browser that hasn't signed in."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def client(anon):
    """A browser signed in as the test user (most tests just use this)."""
    res = anon.post("/api/auth/signup", json=TEST_USER)
    assert res.status_code == 201, res.text
    return anon


@pytest.fixture()
def other_client(client):
    """A second browser, signed in as a different person, sharing the same database."""
    with TestClient(app) as second:
        res = second.post("/api/auth/signup", json={**TEST_USER, "name": "Other Person", "email": "other@example.com"})
        assert res.status_code == 201, res.text
        yield second
