import json
import sqlite3

import pytest

import auth
import config
from tests.conftest import TEST_USER

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


def add_item(client, name="Green saree", item_type="Saree", colour="Green"):
    data = {"name": name, "category": "Clothing", "item_type": item_type, "colour": colour,
            "style": "Traditional", "occasions": ["Festive"]}
    res = client.post("/api/items", data=data, files={"photo": ("p.png", PNG, "image/png")})
    assert res.status_code == 201, res.text
    return res.json()["id"]


# ---------- sign up, log in, log out ----------

def test_signup_signs_you_in_and_knows_your_first_name(anon):
    res = anon.post("/api/auth/signup", json={**TEST_USER, "name": "  Swarangi   Kothawade ", "phone": "+91 98765 43210"})
    assert res.status_code == 201, res.text
    user = res.json()
    assert user["name"] == "Swarangi Kothawade" and user["first_name"] == "Swarangi"
    assert user["phone"] == "+919876543210" and user["email"] == "test@example.com"
    assert "password" not in json.dumps(user) and "hash" not in json.dumps(user)
    assert anon.get("/api/auth/me").json()["first_name"] == "Swarangi"


@pytest.mark.parametrize("change, field", [
    ({"email": "not-an-email"}, "email"),
    ({"phone": "12345"}, "phone"),
    ({"password": "short"}, "password"),
    ({"name": "   "}, "name"),
])
def test_signup_checks_the_details(anon, change, field):
    res = anon.post("/api/auth/signup", json={**TEST_USER, **change})
    assert res.status_code == 422
    assert field in json.dumps(res.json())


def test_same_email_cannot_sign_up_twice(client):
    res = client.post("/api/auth/signup", json={**TEST_USER, "email": "TEST@example.com"})
    assert res.status_code == 409


def test_logout_then_login(client):
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401
    assert client.post("/api/auth/login", json={"email": "test@example.com", "password": "wrong-one"}).status_code == 401
    res = client.post("/api/auth/login", json={"email": " Test@Example.com ", "password": TEST_USER["password"]})
    assert res.status_code == 200 and res.json()["first_name"] == "Test"
    assert client.get("/api/items").status_code == 200


def test_too_many_wrong_passwords_waits(client):
    client.post("/api/auth/logout")
    for _ in range(auth.MAX_FAILURES):
        assert client.post("/api/auth/login", json={"email": TEST_USER["email"], "password": "nope-nope"}).status_code == 401
    res = client.post("/api/auth/login", json={"email": TEST_USER["email"], "password": TEST_USER["password"]})
    assert res.status_code == 429


def test_passwords_and_sessions_are_never_stored_in_plain_text(client):
    conn = sqlite3.connect(config.DB_PATH)
    stored = conn.execute("SELECT password_hash FROM users").fetchone()[0]
    token = client.cookies.get(auth.COOKIE)
    assert TEST_USER["password"] not in stored and stored.startswith("scrypt$")
    assert auth.check_password(TEST_USER["password"], stored) and not auth.check_password("wrong", stored)
    assert conn.execute("SELECT COUNT(*) FROM sessions WHERE token_hash = ?", (token,)).fetchone()[0] == 0


def test_you_can_change_your_name_and_phone(client):
    res = client.put("/api/auth/me", json={"name": "Swarangi K", "phone": "9123456789"})
    assert res.status_code == 200 and res.json()["first_name"] == "Swarangi"
    assert client.put("/api/auth/me", json={"name": "Swarangi", "phone": "12"}).status_code == 422


# ---------- everything needs you to be signed in ----------

@pytest.mark.parametrize("method, path", [
    ("get", "/api/items"), ("get", "/api/looks"), ("get", "/api/history"),
    ("get", "/api/insights/wear"), ("get", "/api/insights/gaps"), ("get", "/api/events/functions"),
    ("post", "/api/recommendations"), ("post", "/api/stylist/parse"), ("post", "/api/trips/plan"),
])
def test_your_data_needs_you_to_sign_in(anon, method, path):
    res = getattr(anon, method)(path, json={}) if method == "post" else anon.get(path)
    assert res.status_code == 401
    assert res.json()["detail"] == "Please log in to continue."


def test_public_pages_still_work_signed_out(anon):
    for path in ("/api/health", "/api/options", "/api/festivals/now"):
        assert anon.get(path).status_code == 200, path


def test_health_answers_uptime_monitors_head_request(anon):
    assert anon.head("/api/health").status_code == 200


# ---------- each account only sees its own wardrobe ----------

def test_two_accounts_never_see_each_others_things(client, other_client):
    mine = add_item(client)
    theirs = add_item(other_client, "Red saree", colour="Red")
    assert [i["name"] for i in client.get("/api/items").json()] == ["Green saree"]
    assert [i["name"] for i in other_client.get("/api/items").json()] == ["Red saree"]
    for path in (f"/api/items/{mine}", f"/api/items/{mine}/photo"):
        assert other_client.get(path).status_code == 404
    assert other_client.delete(f"/api/items/{mine}").status_code == 404
    assert client.get(f"/api/items/{mine}").status_code == 200

    look = {"prefs": {"occasion": "Festive"}, "item_ids": [mine]}
    assert other_client.post("/api/looks", json=look).status_code == 400          # not their piece
    look_id = client.post("/api/looks", json=look).json()["id"]
    assert other_client.get("/api/looks").json() == []
    assert other_client.delete(f"/api/looks/{look_id}").status_code == 404
    client.post(f"/api/looks/{look_id}/wear")
    assert other_client.get("/api/history").json() == []
    assert other_client.get("/api/insights/wear").json()["total_items"] == 1      # only their red saree
    parsed = other_client.post("/api/stylist/parse", json={"text": "style my green saree"}).json()
    assert parsed["anchor_item_id"] != mine                                       # only ever their own pieces
    assert theirs != mine


def test_first_account_receives_the_wardrobe_from_before_accounts(anon):
    import database
    database.init_db()
    conn = database.connect()
    conn.execute("INSERT INTO wardrobe_items (name, category, item_type, colour, style, occasions, notes, "
                 "image_filename, created_at, updated_at) VALUES ('Old kurta', 'Clothing', 'Kurta', 'Green', "
                 "'Traditional', '[\"Festive\"]', '', 'x.png', '2026-01-01', '2026-01-01')")
    conn.commit()
    conn.close()
    first = anon.post("/api/auth/signup", json=TEST_USER).json()
    assert first["moved_items"] == 1
    assert [i["name"] for i in anon.get("/api/items").json()] == ["Old kurta"]
    anon.post("/api/auth/logout")
    second = anon.post("/api/auth/signup", json={**TEST_USER, "email": "second@example.com"}).json()
    assert second["moved_items"] == 0
    assert anon.get("/api/items").json() == []
