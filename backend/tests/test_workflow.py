"""The whole Peheraav workflow, start to finish, through the API (README section 2, steps A-I)."""
import config

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32


def add(client, name, category, item_type, colour, style, occasions):
    res = client.post(
        "/api/items",
        data={"name": name, "category": category, "item_type": item_type, "colour": colour,
              "style": style, "occasions": occasions},
        files={"photo": (f"{name}.png", PNG, "image/png")},
    )
    assert res.status_code == 201, res.text
    return res.json()


def test_full_workflow(client):
    # A. Opening Peheraav with an empty wardrobe: nothing to style yet, and it says so.
    assert client.get("/api/items").json() == []
    empty = client.post("/api/recommendations", json={"occasion": "Traditional function"}).json()
    assert empty["outfits"] == [] and "Add some clothes" in empty["notes"][0]

    # B-D. Register clothes and accessories with photos and details; they persist.
    festive = ["Festive", "Traditional function", "Wedding"]
    kurta = add(client, "Green kurta", "Clothing", "Kurta", "Green", "Traditional", festive)
    add(client, "Pink kurta", "Clothing", "Kurta", "Pink", "Traditional", festive)
    add(client, "White churidar", "Clothing", "Churidar", "White", "Traditional", festive)
    add(client, "Gold palazzo", "Clothing", "Palazzo", "Gold", "Traditional", festive)
    add(client, "Cream dupatta", "Clothing", "Dupatta", "Cream", "Traditional", festive)
    add(client, "Gold jhumkas", "Jewellery", "Jhumkas", "Gold", "Traditional", festive)
    add(client, "Silver studs", "Jewellery", "Earrings", "Silver", "Western", ["College"])
    juttis = add(client, "Tan juttis", "Footwear", "Juttis", "Tan", "Traditional", festive)
    add(client, "Gold kolhapuris", "Footwear", "Kolhapuris", "Gold", "Traditional", festive)
    add(client, "Potli bag", "Bags", "Potli", "Gold", "Traditional", festive)
    assert len(client.get("/api/items").json()) == 10
    assert len(list(config.UPLOAD_DIR.iterdir())) == 10

    # E-F. "Style my green kurta for a traditional family function."
    parsed = client.post("/api/stylist/parse",
                         json={"text": "Style my green kurta for a traditional family function"}).json()
    assert parsed["occasion"] == "Traditional function"
    assert parsed["anchor_item_id"] == kurta["id"]
    assert parsed["style"] == "Traditional"

    # G-H. Real recommendations: 2 distinct looks, all built around the kurta, only real items.
    request = {k: parsed[k] for k in ("occasion", "style", "colour", "colour_mood", "comfort", "anchor_item_id")}
    result = client.post("/api/recommendations", json=request).json()
    wardrobe_ids = {i["id"] for i in client.get("/api/items").json()}
    assert len(result["outfits"]) == 2
    for outfit in result["outfits"]:
        ids = [p["item"]["id"] for p in outfit["pieces"]]
        assert set(ids) <= wardrobe_ids
        assert kurta["id"] in ids
        assert "Silver studs" not in [p["item"]["name"] for p in outfit["pieces"]]  # not tagged
        assert outfit["reasons"]
        assert client.get(outfit["pieces"][0]["item"]["image_url"]).status_code == 200

    # I. Swap the footwear, save the look, wear it, and see it in history.
    prefs = {k: request[k] for k in ("occasion", "style", "colour", "colour_mood", "comfort")}
    look_ids = [p["item"]["id"] for p in result["outfits"][0]["pieces"]]
    shoes = next(p["item"] for p in result["outfits"][0]["pieces"] if p["role"] == "Footwear")
    options = client.post("/api/outfits/alternatives",
                          json={"prefs": prefs, "item_ids": look_ids, "replace_item_id": shoes["id"]}).json()
    assert options and options[0]["tagged"]
    look_ids = [options[0]["item"]["id"] if i == shoes["id"] else i for i in look_ids]

    look = client.post("/api/looks", json={"prefs": prefs, "item_ids": look_ids, "name": "Puja at home"}).json()
    assert look["name"] == "Puja at home"
    assert client.post(f"/api/looks/{look['id']}/wear").status_code == 201
    history = client.get("/api/history").json()
    assert [h["look_name"] for h in history] == ["Puja at home"]

    # Data integrity: deleting a piece from the wardrobe keeps the look and flags it.
    worn_shoes = options[0]["item"]["id"]
    assert client.delete(f"/api/items/{worn_shoes}").status_code == 204
    saved = client.get("/api/looks").json()[0]
    assert saved["missing_pieces"] == 1
    assert worn_shoes not in [p["item"]["id"] for p in saved["pieces"]]
    assert juttis["id"] in wardrobe_ids
