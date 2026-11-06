"""Per-address request limits: too many sign-ups, log-ins, reset emails or model downloads get a 429."""
import pytest
from fastapi.testclient import TestClient

import config
import ratelimit
from main import app
from tests.conftest import TEST_USER


def signup(client, n):
    return client.post("/api/auth/signup", json={**TEST_USER, "email": f"person{n}@example.com"})


def test_sign_ups_are_limited_per_address(anon):
    for n in range(10):
        assert signup(anon, n).status_code == 201
        anon.post("/api/auth/logout")
    res = signup(anon, 99)
    assert res.status_code == 429
    assert "Too many new accounts" in res.json()["detail"] and int(res.headers["retry-after"]) > 0


def test_log_ins_are_limited_across_emails(anon):
    for n in range(20):
        anon.post("/api/auth/login", json={"email": f"guess{n}@example.com", "password": "wrong-password"})
    res = anon.post("/api/auth/login", json={"email": "another@example.com", "password": "wrong-password"})
    assert res.status_code == 429


def test_reset_requests_are_limited(anon):
    for _ in range(5):
        assert anon.post("/api/auth/forgot", json={"email": "someone@example.com"}).status_code == 202
    assert anon.post("/api/auth/forgot", json={"email": "someone@example.com"}).status_code == 429


def test_limits_are_per_address(anon):
    for n in range(10):
        signup(anon, n)
        anon.post("/api/auth/logout")
    with TestClient(app, client=("203.0.113.9", 50000)) as elsewhere:   # another visitor
        assert signup(elsewhere, 50).status_code == 201


def test_ordinary_use_is_not_limited(client):
    for _ in range(50):
        assert client.get("/api/items").status_code == 200


def test_limits_can_be_switched_off(anon, monkeypatch):
    monkeypatch.setattr(config, "RATE_LIMITS", False)
    for n in range(12):
        assert signup(anon, n).status_code == 201
        anon.post("/api/auth/logout")


@pytest.mark.parametrize("method, path, name", [
    ("POST", "/api/items", "upload"), ("PUT", "/api/items/3", "upload"), ("PUT", "/api/items/3/cutout", "upload"),
    ("POST", "/api/looks/7/photo", "upload"), ("GET", "/api/models/isnet", "model"), ("GET", "/api/items", "api"),
    ("GET", "/", None), ("GET", "/assets/app.js", None),
])
def test_which_rule_applies(method, path, name):
    rule = ratelimit._rule_for(method, path)
    assert (rule[2] if rule else None) == name
