import config

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 16


def add(client):
    data = {"name": "Black skirt", "category": "Clothing", "item_type": "Skirt", "colour": "Black",
            "style": "Western", "occasions": ["Party"]}
    return client.post("/api/items", data=data, files={"photo": ("p.jpg", JPEG, "image/jpeg")}).json()


def files():
    return {p.name for p in config.UPLOAD_DIR.iterdir()}


def test_save_and_serve_cutout(client):
    item = add(client)
    assert item["cutout_url"] is None
    res = client.put(f"/api/items/{item['id']}/cutout", files={"cutout": ("c.png", PNG, "image/png")})
    assert res.status_code == 200
    url = res.json()["cutout_url"]
    assert url.startswith(f"/api/items/{item['id']}/cutout")
    assert client.get(url).content == PNG
    assert client.get("/api/items").json()[0]["cutout_url"] == url


def test_cutout_must_be_png(client):
    item = add(client)
    res = client.put(f"/api/items/{item['id']}/cutout", files={"cutout": ("c.jpg", JPEG, "image/jpeg")})
    assert res.status_code == 400


def test_replacing_cutout_removes_old_file(client):
    item = add(client)
    before = files()
    client.put(f"/api/items/{item['id']}/cutout", files={"cutout": ("c.png", PNG, "image/png")})
    first = files() - before
    client.put(f"/api/items/{item['id']}/cutout", files={"cutout": ("c.png", PNG + b"x", "image/png")})
    assert len(files() - before) == 1 and (files() - before) != first


def test_new_photo_clears_cutout(client):
    item = add(client)
    client.put(f"/api/items/{item['id']}/cutout", files={"cutout": ("c.png", PNG, "image/png")})
    data = {"name": "Black skirt", "category": "Clothing", "item_type": "Skirt", "colour": "Black",
            "style": "Western", "occasions": ["Party"]}
    res = client.put(f"/api/items/{item['id']}", data=data, files={"photo": ("n.png", PNG, "image/png")})
    assert res.json()["cutout_url"] is None
    # details-only edit keeps the cut-out
    client.put(f"/api/items/{item['id']}/cutout", files={"cutout": ("c.png", PNG, "image/png")})
    res = client.put(f"/api/items/{item['id']}", data={**data, "colour": "Jet black"})
    assert res.json()["cutout_url"] is not None


def test_deleting_item_removes_cutout(client):
    before = files()
    item = add(client)
    client.put(f"/api/items/{item['id']}/cutout", files={"cutout": ("c.png", PNG, "image/png")})
    client.delete(f"/api/items/{item['id']}")
    assert files() == before


def test_delete_cutout(client):
    item = add(client)
    client.put(f"/api/items/{item['id']}/cutout", files={"cutout": ("c.png", PNG, "image/png")})
    assert client.delete(f"/api/items/{item['id']}/cutout").status_code == 204
    assert client.get(f"/api/items/{item['id']}/cutout").status_code == 404



def test_cutout_version_is_stored(client):
    item = add(client)
    res = client.put(f"/api/items/{item['id']}/cutout", data={"version": "2m"},
                     files={"cutout": ("c.png", PNG, "image/png")})
    assert res.json()["cutout_version"] == "2m"
    client.delete(f"/api/items/{item['id']}/cutout")
    assert client.get("/api/items").json()[0]["cutout_version"] is None


def test_unknown_model_is_404(client):
    assert client.get("/api/models/nope").status_code == 404
