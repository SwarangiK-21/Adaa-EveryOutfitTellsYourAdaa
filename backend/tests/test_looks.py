from datetime import date, timedelta

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
PARTY = {"occasion": "Party"}


def add(client, name, item_type, colour="Black", category="Clothing", occasions=("Party",)):
    data = {"name": name, "category": category, "item_type": item_type, "colour": colour,
            "style": "Western", "occasions": list(occasions)}
    res = client.post("/api/items", data=data, files={"photo": ("p.png", PNG, "image/png")})
    assert res.status_code == 201, res.text
    return res.json()["id"]


def wardrobe(client):
    return {
        "top": add(client, "Black top", "Top"),
        "white_top": add(client, "White shirt", "Shirt", "White"),
        "skirt": add(client, "Black skirt", "Skirt"),
        "heels": add(client, "Black heels", "Heels", category="Footwear"),
        "flats": add(client, "Tan flats", "Flats", "Tan", category="Footwear", occasions=["College"]),
        "churidar": add(client, "White churidar", "Churidar", "White"),
    }


def save(client, ids, name=None, prefs=PARTY):
    return client.post("/api/looks", json={"prefs": prefs, "item_ids": ids, "name": name})


# ---------- saving looks ----------

def test_save_and_list_look(client):
    w = wardrobe(client)
    res = save(client, [w["top"], w["skirt"], w["heels"]])
    assert res.status_code == 201
    look = res.json()
    assert look["name"] == "Black top + Black skirt"   # default name from the clothes
    assert [p["role"] for p in look["pieces"]] == ["Top", "Bottom", "Footwear"]
    assert look["reasons"] and look["wear_count"] == 0
    assert [l["id"] for l in client.get("/api/looks").json()] == [look["id"]]


def test_cannot_save_the_same_look_twice(client):
    w = wardrobe(client)
    assert save(client, [w["top"], w["skirt"]]).status_code == 201
    res = save(client, [w["skirt"], w["top"]])
    assert res.status_code == 409


def test_cannot_save_unknown_or_duplicate_items(client):
    w = wardrobe(client)
    assert save(client, [w["top"], 9999]).status_code == 400
    assert save(client, [w["top"], w["top"]]).status_code == 400
    assert save(client, []).status_code == 422


def test_rename_and_delete_look(client):
    w = wardrobe(client)
    look_id = save(client, [w["top"], w["skirt"]]).json()["id"]
    res = client.put(f"/api/looks/{look_id}", json={"name": "Friday night"})
    assert res.json()["name"] == "Friday night"
    assert client.delete(f"/api/looks/{look_id}").status_code == 204
    assert client.get("/api/looks").json() == []


def test_deleting_a_wardrobe_item_keeps_the_look_and_flags_it(client):
    w = wardrobe(client)
    look_id = save(client, [w["top"], w["skirt"], w["heels"]]).json()["id"]
    assert client.delete(f"/api/items/{w['heels']}").status_code == 204
    look = client.get("/api/looks").json()[0]
    assert look["id"] == look_id
    assert look["missing_pieces"] == 1
    assert [p["item"]["name"] for p in look["pieces"]] == ["Black top", "Black skirt"]


# ---------- swaps ----------

def test_swap_options_keep_the_outfit_wearable(client):
    w = wardrobe(client)
    res = client.post("/api/outfits/alternatives", json={
        "prefs": PARTY, "item_ids": [w["top"], w["skirt"], w["heels"]], "replace_item_id": w["skirt"]})
    assert res.status_code == 200
    # A churidar doesn't go with a western top, so it's not offered.
    assert [o["item"]["name"] for o in res.json()] == []

    res = client.post("/api/outfits/alternatives", json={
        "prefs": PARTY, "item_ids": [w["top"], w["skirt"], w["heels"]], "replace_item_id": w["top"]})
    assert [o["item"]["name"] for o in res.json()] == ["White shirt"]


def test_swap_options_rank_tagged_pieces_first(client):
    w = wardrobe(client)
    res = client.post("/api/outfits/alternatives", json={
        "prefs": PARTY, "item_ids": [w["top"], w["skirt"], w["heels"]], "replace_item_id": w["heels"]})
    options = res.json()
    assert [o["item"]["name"] for o in options] == ["Tan flats"]
    assert options[0]["tagged"] is False
    assert options[0]["reason"].startswith("Not tagged for Party")


def test_evaluate_after_swap_explains_problems(client):
    w = wardrobe(client)
    res = client.post("/api/outfits/evaluate", json={
        "prefs": PARTY, "item_ids": [w["top"], w["skirt"], w["flats"]]})
    assert res.status_code == 200
    assert any("Not tagged for Party: Tan flats" in c for c in res.json()["cautions"])
    res = client.post("/api/outfits/evaluate", json={"prefs": PARTY, "item_ids": [w["top"]]})
    assert any("needs a top and a bottom" in c for c in res.json()["cautions"])


def test_swap_inside_a_saved_look(client):
    w = wardrobe(client)
    look_id = save(client, [w["top"], w["skirt"], w["heels"]]).json()["id"]
    res = client.put(f"/api/looks/{look_id}", json={"item_ids": [w["white_top"], w["skirt"], w["heels"]]})
    assert res.status_code == 200
    assert res.json()["pieces"][0]["item"]["name"] == "White shirt"


# ---------- history ----------

def test_wear_history(client):
    w = wardrobe(client)
    look_id = save(client, [w["top"], w["skirt"]], name="Date night").json()["id"]
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    assert client.post(f"/api/looks/{look_id}/wear", json={"worn_on": yesterday}).status_code == 201
    today_entry = client.post(f"/api/looks/{look_id}/wear").json()
    assert today_entry["worn_on"] == date.today().isoformat()

    history = client.get("/api/history").json()
    assert [h["worn_on"] for h in history] == [date.today().isoformat(), yesterday]
    assert history[0]["look_name"] == "Date night" and history[0]["pieces"]

    look = client.get("/api/looks").json()[0]
    assert look["wear_count"] == 2 and look["last_worn_on"] == date.today().isoformat()

    assert client.delete(f"/api/history/{today_entry['id']}").status_code == 204
    assert len(client.get("/api/history").json()) == 1


def test_history_survives_deleting_the_look(client):
    w = wardrobe(client)
    look_id = save(client, [w["top"], w["skirt"]], name="Office Monday").json()["id"]
    client.post(f"/api/looks/{look_id}/wear")
    client.delete(f"/api/looks/{look_id}")
    entry = client.get("/api/history").json()[0]
    assert entry["look_id"] is None
    assert entry["look_name"] == "Office Monday"
    assert entry["pieces"] == []


def test_cannot_log_a_future_date(client):
    w = wardrobe(client)
    look_id = save(client, [w["top"], w["skirt"]]).json()["id"]
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    assert client.post(f"/api/looks/{look_id}/wear", json={"worn_on": tomorrow}).status_code == 422


def test_duplicate_look_names_are_numbered(client):
    w = wardrobe(client)
    first = save(client, [w["top"], w["skirt"], w["heels"]]).json()
    second = save(client, [w["top"], w["skirt"]]).json()
    assert first["name"] == "Black top + Black skirt"
    assert second["name"] == "Black top + Black skirt 2"
