"""Cross-site requests are blocked, the app page has a security policy, the model needs login."""
import config


def test_changes_from_another_website_are_blocked(client):
    res = client.post("/api/looks", json={"item_ids": [1], "prefs": {"occasion": "Casual"}},
                      headers={"Origin": "https://evil.example"})
    assert res.status_code == 403 and "another website" in res.json()["detail"]
    res = client.request("DELETE", "/api/auth/me", json={"password": "x"}, headers={"Origin": "https://evil.example"})
    assert res.status_code == 403


def test_changes_from_peheraav_itself_are_allowed(client):
    assert client.patch("/api/profile/style", json={}, headers={"Origin": "http://testserver"}).status_code == 200


def test_public_address_counts_as_peheraav(client, monkeypatch):
    monkeypatch.setattr(config, "PUBLIC_URL", "https://peheraav.example")
    assert client.patch("/api/profile/style", json={}, headers={"Origin": "https://peheraav.example"}).status_code == 200


def test_reading_is_never_blocked(client):
    assert client.get("/api/items", headers={"Origin": "https://evil.example"}).status_code == 200


def test_app_page_has_a_security_policy(anon, tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<!doctype html><div id=root></div>")
    monkeypatch.setattr(config, "FRONTEND_DIR", dist)
    csp = anon.get("/").headers["content-security-policy"]
    assert "default-src 'self'" in csp and "frame-ancestors 'none'" in csp and "object-src 'none'" in csp
    assert "fonts.googleapis" not in csp        # fonts are served by Peheraav itself


def test_model_download_needs_login(anon):
    assert anon.get("/api/models/isnet").status_code == 401
    assert anon.get("/api/cutout-model").status_code == 401
