import pytest

import tryon

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


def png(tag: str) -> bytes:
    return b"\x89PNG\r\n\x1a\n" + tag.encode()


def add(client, name, category, item_type, colour="Black"):
    data = {"name": name, "category": category, "item_type": item_type, "colour": colour,
            "style": "Western", "occasions": ["Party"]}
    return client.post("/api/items", data=data, files={"photo": (f"{name}.png", png(name), "image/png")}).json()["id"]


@pytest.fixture()
def fake_server(monkeypatch):
    """Stands in for the Colab try-on server: records calls and 'dresses' the image with a label."""
    calls = []

    def call_server(url, token, person, cloth, cloth_type, steps=50):
        calls.append((cloth_type, cloth, steps))
        return png(f"{person.decode('latin1')[-30:]}+{cloth_type}")

    monkeypatch.setattr(tryon, "call_server", call_server)
    monkeypatch.setattr(tryon, "check_server", lambda url, token: "CatVTON on Tesla T4")
    return calls


def setup(client):
    client.post("/api/profile/photo", files={"photo": ("me.png", png("ME"), "image/png")})
    client.put("/api/tryon/settings", json={"url": "https://example.trycloudflare.com/", "token": "secret",
                                            "quality": "high", "try_shoes": True})
    return {
        "top": add(client, "Black top", "Clothing", "Top"),
        "shirt": add(client, "White shirt", "Clothing", "Shirt", "White"),
        "jeans": add(client, "Blue jeans", "Clothing", "Jeans", "Denim"),
        "gown": add(client, "Red gown", "Clothing", "Gown", "Red"),
        "heels": add(client, "Black heels", "Footwear", "Heels"),
        "studs": add(client, "Silver studs", "Jewellery", "Earrings", "Silver"),
    }


def test_profile_and_settings(client):
    profile = client.get("/api/profile").json()
    assert profile == {"photo_url": None, "photo_updated_at": None, "tryon_configured": False, "tryon_url": None,
                       "tryon_quality": "standard", "tryon_shoes": False}

    res = client.post("/api/profile/photo", files={"photo": ("me.png", PNG, "image/png")})
    assert res.status_code == 201 and res.json()["photo_url"].startswith("/api/profile/photo")
    assert client.get("/api/profile/photo").content == PNG

    res = client.put("/api/tryon/settings", json={"url": "https://abc.trycloudflare.com/", "token": " t0k "})
    assert res.json()["tryon_configured"] is True
    assert res.json()["tryon_url"] == "https://abc.trycloudflare.com"
    assert client.put("/api/tryon/settings", json={"url": "abc.com", "token": "x"}).status_code == 422

    assert client.delete("/api/profile/photo").status_code == 204
    assert client.get("/api/profile").json()["photo_url"] is None


def test_status(client, fake_server):
    assert client.get("/api/tryon/status").json()["configured"] is False
    setup(client)
    status = client.get("/api/tryon/status").json()
    assert status == {"configured": True, "online": True, "message": "Connected: CatVTON on Tesla T4."}


def test_top_and_bottom_are_applied_bottom_first(client, fake_server):
    ids = setup(client)
    res = client.post("/api/tryon", json={"item_ids": [ids["top"], ids["jeans"], ids["heels"], ids["studs"]]})
    assert res.status_code == 200, res.text
    body = res.json()
    assert [c[0] for c in fake_server] == ["lower", "upper", "shoes"]
    assert {c[2] for c in fake_server} == {50}  # "high" quality by default
    assert body["garments"] == ["Blue jeans", "Black top", "Black heels"]
    assert body["skipped"] == ["Silver studs"]
    assert body["cached"] is False and body["notes"] == []
    image = client.get(body["url"])
    assert image.status_code == 200 and image.content.endswith(b"+shoes")


def test_dress_is_one_overall_pass(client, fake_server):
    ids = setup(client)
    body = client.post("/api/tryon", json={"item_ids": [ids["gown"], ids["heels"]]}).json()
    assert [c[0] for c in fake_server] == ["overall", "shoes"]
    assert body["garments"] == ["Red gown", "Black heels"]


def test_same_outfit_is_cached_and_swap_makes_a_new_image(client, fake_server):
    ids = setup(client)
    first = client.post("/api/tryon", json={"item_ids": [ids["top"], ids["jeans"]]}).json()
    # Same clothes plus a piece that can't be tried on (earrings) -> same picture, from the cache.
    again = client.post("/api/tryon", json={"item_ids": [ids["top"], ids["jeans"], ids["studs"]]}).json()
    assert again["cached"] is True and again["url"] == first["url"]
    assert len(fake_server) == 2  # no new GPU work

    swapped = client.post("/api/tryon", json={"item_ids": [ids["shirt"], ids["jeans"]]}).json()
    assert swapped["cached"] is False and swapped["url"] != first["url"]


def test_new_profile_photo_clears_old_tryons(client, fake_server):
    ids = setup(client)
    first = client.post("/api/tryon", json={"item_ids": [ids["top"]]}).json()
    client.post("/api/profile/photo", files={"photo": ("me2.png", png("ME2"), "image/png")})
    assert client.get(first["url"]).status_code == 404
    second = client.post("/api/tryon", json={"item_ids": [ids["top"]]}).json()
    assert second["url"] != first["url"]


def test_clear_errors(client, fake_server, monkeypatch):
    ids = setup(client)
    # Only accessories: nothing the model can put on.
    res = client.post("/api/tryon", json={"item_ids": [ids["heels"], ids["studs"]]})
    assert res.status_code == 400 and "no clothing" in res.json()["detail"]

    # Server switched off / Colab disconnected.
    def offline(*args):
        raise tryon.TryOnError(tryon.UNREACHABLE)
    monkeypatch.setattr(tryon, "call_server", offline)
    res = client.post("/api/tryon", json={"item_ids": [ids["shirt"]]})
    assert res.status_code == 503 and "Colab" in res.json()["detail"]

    # Not set up.
    client.put("/api/tryon/settings", json={"url": "", "token": ""})
    res = client.post("/api/tryon", json={"item_ids": [ids["gown"]]})
    assert res.status_code == 409 and "Preferences" in res.json()["detail"]


def test_needs_your_photo_first(client, fake_server):
    gown = add(client, "Red gown", "Clothing", "Gown", "Red")
    res = client.post("/api/tryon", json={"item_ids": [gown]})
    assert res.status_code == 409 and "photo" in res.json()["detail"]


def test_image_names_are_validated(client):
    assert client.get("/api/tryon/images/..%2Fadaa.db").status_code == 404
    assert client.get("/api/tryon/images/notahash.png").status_code == 404


def test_real_http_client_reports_unreachable_server():
    with pytest.raises(tryon.TryOnError) as err:
        tryon.call_server("http://127.0.0.1:9", "t", PNG, PNG, "upper")
    assert "Colab" in str(err.value)


def test_changing_only_the_link_keeps_the_token(client):
    client.put("/api/tryon/settings", json={"url": "https://a.trycloudflare.com", "token": "secret"})
    client.put("/api/tryon/settings", json={"url": "https://b.trycloudflare.com", "token": ""})
    settings = tryon.load_settings()
    assert (settings["url"], settings["token"]) == ("https://b.trycloudflare.com", "secret")
    client.put("/api/tryon/settings", json={"url": "", "token": ""})
    assert tryon.is_configured() is False


def test_safety_filter_block_is_reported_and_not_cached(client, monkeypatch):
    """The Colab notebook answers 451 when its safety filter blocks a result."""
    class Blocked:
        status_code = 451
        content = b""
    monkeypatch.setattr(tryon.httpx, "post", lambda *a, **k: Blocked())
    client.post("/api/profile/photo", files={"photo": ("me.png", png("ME"), "image/png")})
    client.put("/api/tryon/settings", json={"url": "https://x.trycloudflare.com", "token": "t"})
    skirt = add(client, "Brown short skirt", "Clothing", "Skirt", "Brown")
    res = client.post("/api/tryon", json={"item_ids": [skirt]})
    assert res.status_code == 422
    assert "safety filter" in res.json()["detail"]
    assert list(tryon.cache_dir().glob("*.png")) == []


def test_shoes_can_be_switched_off_and_quality_lowered(client, fake_server):
    ids = setup(client)
    client.put("/api/tryon/settings", json={"url": "https://example.trycloudflare.com", "token": "",
                                            "quality": "standard", "try_shoes": False})
    profile = client.get("/api/profile").json()
    assert (profile["tryon_quality"], profile["tryon_shoes"]) == ("standard", False)
    body = client.post("/api/tryon", json={"item_ids": [ids["top"], ids["jeans"], ids["heels"]]}).json()
    assert [c[0] for c in fake_server] == ["lower", "upper"]
    assert {c[2] for c in fake_server} == {30}
    assert "Black heels" in body["skipped"]


def test_failed_shoes_keep_the_clothes_and_explain(client, fake_server, monkeypatch):
    ids = setup(client)

    def shoes_fail(url, token, person, cloth, cloth_type, steps=50):
        if cloth_type == "shoes":
            raise tryon.TryOnError("Couldn't find your feet", 422)
        return png(f"+{cloth_type}")
    monkeypatch.setattr(tryon, "call_server", shoes_fail)
    body = client.post("/api/tryon", json={"item_ids": [ids["top"], ids["jeans"], ids["heels"]]}).json()
    assert body["garments"] == ["Blue jeans", "Black top"]
    assert "Black heels" in body["skipped"]
    assert "couldn't be added" in body["notes"][0]
    assert client.get(body["url"]).content.endswith(b"+upper")
    again = client.post("/api/tryon", json={"item_ids": [ids["top"], ids["jeans"], ids["heels"]]}).json()
    assert again["cached"] is True and again["notes"] == body["notes"]  # the note is remembered


def test_shoes_alone_are_not_a_try_on(client, fake_server):
    ids = setup(client)
    res = client.post("/api/tryon", json={"item_ids": [ids["heels"], ids["studs"]]})
    assert res.status_code == 400


def test_defaults_are_fast_and_shoe_free(client):
    client.put("/api/tryon/settings", json={"url": "https://x.trycloudflare.com", "token": "t"})
    s = tryon.load_settings()
    assert (s["quality"], s["shoes"]) == ("standard", False)


def test_cached_only_never_starts_a_new_try_on(client, fake_server):
    ids = setup(client)
    res = client.post("/api/tryon", json={"item_ids": [ids["top"], ids["jeans"]], "cached_only": True})
    assert res.status_code == 404 and fake_server == []
    made = client.post("/api/tryon", json={"item_ids": [ids["top"], ids["jeans"]]}).json()
    peek = client.post("/api/tryon", json={"item_ids": [ids["top"], ids["jeans"]], "cached_only": True}).json()
    assert peek["url"] == made["url"] and peek["cached"] is True
