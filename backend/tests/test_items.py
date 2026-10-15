import config

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64

KURTA = {
    "name": "Green chikankari kurta",
    "category": "Clothing",
    "item_type": "Kurta",
    "colour": "Green",
    "style": "Traditional",
    "occasions": ["Festive", "Traditional function"],
    "notes": "Cotton",
}


def add_item(client, data=KURTA, photo=PNG, filename="kurta.png"):
    return client.post("/api/items", data=data, files={"photo": (filename, photo, "image/png")})


def uploaded_files():
    return sorted(p.name for p in config.UPLOAD_DIR.iterdir())


def test_create_list_and_view_item(client):
    res = add_item(client)
    assert res.status_code == 201
    item = res.json()
    assert item["name"] == "Green chikankari kurta"
    assert item["occasions"] == ["Festive", "Traditional function"]
    assert len(uploaded_files()) == 1

    assert [i["id"] for i in client.get("/api/items").json()] == [item["id"]]
    assert client.get(f"/api/items/{item['id']}").json()["colour"] == "Green"

    photo = client.get(item["image_url"])
    assert photo.status_code == 200
    assert photo.content == PNG


def test_search_and_category_filter(client):
    add_item(client)
    add_item(client, data={**KURTA, "name": "Gold jhumkas", "category": "Jewellery",
                           "item_type": "Jhumkas", "colour": "Gold"})
    names = lambda res: [i["name"] for i in res.json()]
    assert names(client.get("/api/items", params={"search": "GOLD"})) == ["Gold jhumkas"]
    assert names(client.get("/api/items", params={"search": "festive"})) == [
        "Gold jhumkas", "Green chikankari kurta"]
    assert names(client.get("/api/items", params={"category": "Clothing"})) == [
        "Green chikankari kurta"]
    assert client.get("/api/items", params={"search": "%"}).json() == []


def test_rejects_file_that_is_not_an_image(client):
    res = add_item(client, photo=b"hello, not a photo", filename="fake.jpg")
    assert res.status_code == 400
    assert "JPEG, PNG or WebP" in res.json()["detail"]
    assert client.get("/api/items").json() == []
    assert uploaded_files() == []


def test_rejects_photo_over_size_limit(client, monkeypatch):
    monkeypatch.setattr(config, "MAX_UPLOAD_BYTES", 50)
    res = add_item(client)
    assert res.status_code == 400
    assert "larger than" in res.json()["detail"]
    assert uploaded_files() == []


def test_rejects_invalid_details(client):
    res = add_item(client, data={**KURTA, "category": "Furniture", "name": "  "})
    assert res.status_code == 422
    detail = " ".join(res.json()["detail"])
    assert "category must be one of" in detail
    assert "name" in detail
    assert uploaded_files() == []


def test_update_details_keeps_photo(client):
    item = add_item(client).json()
    res = client.put(f"/api/items/{item['id']}", data={**KURTA, "colour": "Sage green"})
    assert res.status_code == 200
    assert res.json()["colour"] == "Sage green"
    assert res.json()["image_url"] == item["image_url"]
    assert len(uploaded_files()) == 1


def test_update_with_new_photo_replaces_old_file(client):
    item = add_item(client).json()
    old_files = uploaded_files()
    res = client.put(f"/api/items/{item['id']}", data=KURTA,
                     files={"photo": ("new.jpg", JPEG, "image/jpeg")})
    assert res.status_code == 200
    new_files = uploaded_files()
    assert len(new_files) == 1 and new_files != old_files
    assert new_files[0].endswith(".jpg")
    assert client.get(res.json()["image_url"]).content == JPEG


def test_delete_removes_record_and_photo(client):
    item = add_item(client).json()
    assert client.delete(f"/api/items/{item['id']}").status_code == 204
    assert client.get(f"/api/items/{item['id']}").status_code == 404
    assert uploaded_files() == []
    assert client.delete(f"/api/items/{item['id']}").status_code == 404


def test_options_endpoint(client):
    options = client.get("/api/options").json()
    assert "Jewellery" in options["categories"]
    assert "Indo-Western" in options["styles"]
    assert "Kurta" in options["item_type_suggestions"]["Clothing"]


def test_many_photos_at_once(client):
    """The outfit screen loads many photos together; none of them may fail."""
    from concurrent.futures import ThreadPoolExecutor

    item = add_item(client).json()
    with ThreadPoolExecutor(max_workers=16) as pool:
        statuses = list(pool.map(lambda _: client.get(item["image_url"]).status_code, range(64)))
    assert set(statuses) == {200}
