import config

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 16
PARTY = {"occasion": "Party"}


def add(client, name, item_type, category="Clothing"):
    data = {"name": name, "category": category, "item_type": item_type, "colour": "Black",
            "style": "Western", "occasions": ["Party"]}
    return client.post("/api/items", data=data, files={"photo": ("p.png", PNG, "image/png")}).json()["id"]


def setup_look(client):
    ids = {"top": add(client, "Black top", "Top"), "skirt": add(client, "Black skirt", "Skirt"),
           "shirt": add(client, "White shirt", "Shirt"),
           "heels": add(client, "Black heels", "Heels", "Footwear")}
    look = client.post("/api/looks", json={"prefs": PARTY, "item_ids": [ids["top"], ids["skirt"], ids["heels"]]}).json()
    return ids, look["id"]


def upload(client, look_id, data=JPEG):
    return client.post(f"/api/looks/{look_id}/photo", files={"photo": ("me.jpg", data, "image/jpeg")})


def files():
    return {p.name for p in config.UPLOAD_DIR.iterdir()}


def test_upload_photo_gives_verified_preview(client):
    _, look_id = setup_look(client)
    assert client.get("/api/looks").json()[0]["photo"] is None

    res = upload(client, look_id)
    assert res.status_code == 201
    photo = res.json()["photo"]
    assert photo["matches_current"] is True and photo["changed_pieces"] == []
    got = client.get(photo["url"])
    assert got.status_code == 200 and got.content == JPEG


def test_swapping_a_piece_makes_the_photo_outdated(client):
    ids, look_id = setup_look(client)
    upload(client, look_id)
    res = client.put(f"/api/looks/{look_id}", json={"item_ids": [ids["shirt"], ids["skirt"], ids["heels"]]})
    photo = res.json()["photo"]
    assert photo["matches_current"] is False
    assert photo["changed_pieces"] == ["White shirt"]


def test_deleting_a_piece_makes_the_photo_outdated(client):
    ids, look_id = setup_look(client)
    upload(client, look_id)
    client.delete(f"/api/items/{ids['heels']}")
    photo = client.get("/api/looks").json()[0]["photo"]
    assert photo["matches_current"] is False
    assert photo["changed_pieces"] == []  # nothing new, just a piece gone


def test_replacing_and_removing_photo_cleans_up_files(client):
    _, look_id = setup_look(client)
    before = files()
    upload(client, look_id)
    first = files() - before
    upload(client, look_id, PNG)
    second = files() - before
    assert len(first) == 1 and len(second) == 1 and first != second  # old file removed

    assert client.delete(f"/api/looks/{look_id}/photo").status_code == 204
    assert files() == before
    assert client.get(f"/api/looks/{look_id}/photo").status_code == 404
    assert client.delete(f"/api/looks/{look_id}/photo").status_code == 404


def test_deleting_the_look_removes_its_photo(client):
    _, look_id = setup_look(client)
    before = files()
    upload(client, look_id)
    client.delete(f"/api/looks/{look_id}")
    assert files() == before


def test_rejects_non_image_photo(client):
    _, look_id = setup_look(client)
    res = upload(client, look_id, b"not a photo")
    assert res.status_code == 400
    assert client.get("/api/looks").json()[0]["photo"] is None


def test_photo_for_unknown_look_is_404(client):
    assert upload(client, 999).status_code == 404
