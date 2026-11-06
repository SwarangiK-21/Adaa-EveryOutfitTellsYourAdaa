"""Public-ready accounts: privacy consent, change / forgot password, deleting an account, limits."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

import config
import database
import mailer
from main import app
from tests.conftest import TEST_USER

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


def add_item(client, name="Green saree"):
    data = {"name": name, "category": "Clothing", "item_type": "Saree", "colour": "Green",
            "style": "Traditional", "occasions": ["Festive"]}
    return client.post("/api/items", data=data, files={"photo": ("p.png", PNG, "image/png")})


@pytest.fixture()
def outbox(monkeypatch):
    """Emails Adaa would send, instead of sending them."""
    sent = []
    monkeypatch.setattr(mailer, "send_email", lambda to, subject, body: sent.append({"to": to, "subject": subject, "body": body}))
    return sent


def reset_token(email):
    return email["body"].split("#reset=")[1].split()[0]


# ---------- privacy consent ----------

def test_signup_needs_privacy_consent(anon):
    res = anon.post("/api/auth/signup", json={**TEST_USER, "accept_privacy": False})
    assert res.status_code == 422
    assert "privacy note" in res.text


def test_signup_records_when_privacy_was_accepted(client):
    with database.connect() as conn:
        row = conn.execute("SELECT privacy_accepted_at, created_at FROM users").fetchone()
    assert row["privacy_accepted_at"] == row["created_at"]


def test_about_is_public(anon, monkeypatch):
    monkeypatch.setattr(config, "CONTACT_EMAIL", "hello@adaa.example")
    res = anon.get("/api/auth/about")
    assert res.status_code == 200
    assert res.json() == {"contact_email": "hello@adaa.example", "max_items": config.MAX_ITEMS_PER_USER,
                          "max_looks": config.MAX_LOOKS_PER_USER}


# ---------- change password ----------

def test_change_password(client):
    with TestClient(app) as other_browser:   # the same person, signed in on another device
        assert other_browser.post("/api/auth/login", json={"email": TEST_USER["email"], "password": TEST_USER["password"]}).status_code == 200
        res = client.put("/api/auth/password", json={"current_password": TEST_USER["password"], "new_password": "a-newer-password"})
        assert res.status_code == 204
        assert client.get("/api/auth/me").status_code == 200          # this browser stays signed in
        assert other_browser.get("/api/auth/me").status_code == 401   # the other one is signed out
    client.post("/api/auth/logout")
    assert client.post("/api/auth/login", json={"email": TEST_USER["email"], "password": TEST_USER["password"]}).status_code == 401
    assert client.post("/api/auth/login", json={"email": TEST_USER["email"], "password": "a-newer-password"}).status_code == 200


def test_change_password_needs_the_current_one(client):
    res = client.put("/api/auth/password", json={"current_password": "wrong-password", "new_password": "a-newer-password"})
    assert res.status_code == 400
    res = client.put("/api/auth/password", json={"current_password": TEST_USER["password"], "new_password": "short"})
    assert res.status_code == 422


# ---------- forgot password ----------

def test_forgot_and_reset_password(client, outbox, monkeypatch):
    monkeypatch.setattr(config, "PUBLIC_URL", "https://adaa.example")
    client.post("/api/auth/logout")
    res = client.post("/api/auth/forgot", json={"email": " TEST@example.com "})
    assert res.status_code == 202
    assert len(outbox) == 1 and outbox[0]["to"] == TEST_USER["email"]
    assert "Hi Test," in outbox[0]["body"] and "https://adaa.example/#reset=" in outbox[0]["body"]

    token = reset_token(outbox[0])
    assert client.post("/api/auth/reset", json={"token": token, "password": "brand-new-password"}).status_code == 204
    assert client.post("/api/auth/login", json={"email": TEST_USER["email"], "password": TEST_USER["password"]}).status_code == 401
    assert client.post("/api/auth/login", json={"email": TEST_USER["email"], "password": "brand-new-password"}).status_code == 200
    # A link works once.
    res = client.post("/api/auth/reset", json={"token": token, "password": "another-password"})
    assert res.status_code == 400 and "expired or was already used" in res.json()["detail"]


def test_forgot_reply_is_the_same_for_unknown_emails(anon, outbox):
    known = anon.post("/api/auth/signup", json=TEST_USER)
    anon.post("/api/auth/logout")
    a = anon.post("/api/auth/forgot", json={"email": TEST_USER["email"]})
    b = anon.post("/api/auth/forgot", json={"email": "nobody@example.com"})
    assert known.status_code == 201
    assert (a.status_code, a.json()) == (b.status_code, b.json())
    resets = [m["to"] for m in outbox if "new password" in m["subject"]]
    assert resets == [TEST_USER["email"]]   # nothing is sent to unknown addresses


def test_reset_signs_out_everywhere(client, outbox):
    client.post("/api/auth/forgot", json={"email": TEST_USER["email"]})
    assert client.get("/api/auth/me").status_code == 200
    client.post("/api/auth/reset", json={"token": reset_token(outbox[0]), "password": "brand-new-password"})
    assert client.get("/api/auth/me").status_code == 401


def test_expired_reset_link(client, outbox):
    client.post("/api/auth/forgot", json={"email": TEST_USER["email"]})
    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    with database.connect() as conn:
        conn.execute("UPDATE password_resets SET expires_at = ?", (past,))
    res = client.post("/api/auth/reset", json={"token": reset_token(outbox[0]), "password": "brand-new-password"})
    assert res.status_code == 400


def test_at_most_three_reset_emails_an_hour(client, outbox):
    for _ in range(5):
        assert client.post("/api/auth/forgot", json={"email": TEST_USER["email"]}).status_code == 202
    assert len(outbox) == 3


def test_new_password_cancels_older_reset_links(client, outbox):
    client.post("/api/auth/forgot", json={"email": TEST_USER["email"]})
    client.put("/api/auth/password", json={"current_password": TEST_USER["password"], "new_password": "a-newer-password"})
    assert client.post("/api/auth/reset", json={"token": reset_token(outbox[0]), "password": "x-password-2"}).status_code == 400


# ---------- delete my account ----------

def test_delete_account_erases_everything(client, other_client, data_dir):
    item = add_item(client).json()
    look = client.post("/api/looks", json={"item_ids": [item["id"]], "prefs": {"occasion": "Festive"}}).json()
    client.post(f"/api/looks/{look['id']}/wear")
    client.post(f"/api/looks/{look['id']}/photo", files={"photo": ("me.png", PNG, "image/png")})
    theirs = add_item(other_client, "Their kurta").json()
    files_before = set((data_dir / "uploads").iterdir())
    assert len(files_before) == 3   # my item, my look photo, their item

    res = client.request("DELETE", "/api/auth/me", json={"password": TEST_USER["password"]})
    assert res.status_code == 204
    assert client.get("/api/auth/me").status_code == 401
    with database.connect() as conn:
        counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                  for t in ("users", "wardrobe_items", "looks", "look_items", "look_photos", "wear_log", "wear_items",
                            "sessions")}
    assert counts == {"users": 1, "wardrobe_items": 1, "looks": 0, "look_items": 0, "look_photos": 0,
                      "wear_log": 0, "wear_items": 0, "sessions": 1}
    assert len(list((data_dir / "uploads").iterdir())) == 1                       # only their photo is left
    assert other_client.get(f"/api/items/{theirs['id']}/photo").status_code == 200
    # The email is free again.
    assert client.post("/api/auth/signup", json=TEST_USER).status_code == 201
    assert client.get("/api/items").json() == []


def test_delete_account_needs_the_password(client):
    res = client.request("DELETE", "/api/auth/me", json={"password": "wrong-password"})
    assert res.status_code == 400
    assert client.get("/api/auth/me").status_code == 200


# ---------- limits and secure cookies ----------

def test_wardrobe_limit(client, monkeypatch):
    monkeypatch.setattr(config, "MAX_ITEMS_PER_USER", 2)
    assert add_item(client, "One").status_code == 201
    assert add_item(client, "Two").status_code == 201
    res = add_item(client, "Three")
    assert res.status_code == 403 and "wardrobe is full (2 pieces)" in res.json()["detail"]


def test_saved_looks_limit(client, monkeypatch):
    monkeypatch.setattr(config, "MAX_LOOKS_PER_USER", 1)
    a, b = add_item(client, "One").json(), add_item(client, "Two").json()
    assert client.post("/api/looks", json={"item_ids": [a["id"]], "prefs": {"occasion": "Festive"}}).status_code == 201
    res = client.post("/api/looks", json={"item_ids": [b["id"]], "prefs": {"occasion": "Festive"}})
    assert res.status_code == 403


def test_account_cap(client, monkeypatch):
    monkeypatch.setattr(config, "MAX_USERS", 1)
    with TestClient(app) as second:
        res = second.post("/api/auth/signup", json={**TEST_USER, "email": "second@example.com"})
    assert res.status_code == 403


@pytest.mark.parametrize("secure", [False, True])
def test_secure_cookie_setting(anon, monkeypatch, secure):
    monkeypatch.setattr(config, "SECURE_COOKIES", secure)
    res = anon.post("/api/auth/signup", json=TEST_USER)
    cookie = res.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
    assert ("secure" in cookie.replace("samesite", "")) is secure
