from itertools import count

from recommender.events import FULL_WEDDING, plan_event

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
_ids = count(1)
WED = ("Wedding", "Traditional function", "Party", "Festive")


def item(name, category, item_type, colour, style="Traditional", occasions=WED):
    return {"id": next(_ids), "name": name, "category": category, "item_type": item_type,
            "colour": colour, "style": style, "occasions": list(occasions), "notes": "",
            "image_filename": "x.png", "created_at": "", "updated_at": "", "price": None}


def wardrobe():
    return [
        item("Mustard kurta", "Clothing", "Kurta", "Mustard"),
        item("Green anarkali", "Clothing", "Anarkali", "Green"),
        item("Pink sequin lehenga", "Clothing", "Lehenga", "Pink", "Indo-Western"),
        item("Red silk saree", "Clothing", "Saree", "Red"),
        item("Wine gown", "Clothing", "Gown", "Wine", "Western"),
        item("White kurta", "Clothing", "Kurta", "White"),
        item("White palazzo", "Clothing", "Palazzo", "White"),
        item("Gold blouse", "Clothing", "Blouse", "Gold"),
        item("Gold jhumkas", "Jewellery", "Jhumkas", "Gold"),
        item("Kundan bangles", "Jewellery", "Bangles", "Gold"),
        item("Gold juttis", "Footwear", "Juttis", "Gold"),
    ]


def clothes(day):
    return {p["item"]["name"] for p in day["outfit"]["pieces"] if p["item"]["category"] == "Clothing"}


def test_full_wedding_follows_each_dress_code_without_repeats():
    plan = plan_event(wardrobe(), FULL_WEDDING)
    days = {d["label"]: d for d in plan["days"]}
    assert list(days) == ["Haldi", "Mehendi", "Sangeet", "Wedding ceremony", "Reception"]
    assert "Mustard kurta" in clothes(days["Haldi"])
    assert clothes(days["Mehendi"]) == {"Green anarkali"}
    assert clothes(days["Sangeet"]) == {"Pink sequin lehenga"}
    assert "Red silk saree" in clothes(days["Wedding ceremony"])
    assert clothes(days["Reception"]) == {"Wine gown"}
    worn = [n for d in plan["days"] if d["outfit"] for n in clothes(d)]
    assert len(worn) == len(set(worn))                         # no garment twice
    assert any("Fits the dress code" in r for r in days["Haldi"]["outfit"]["reasons"])
    assert days["Haldi"]["dress_code"].startswith("Yellow")


def test_jewellery_and_shoes_are_reused_across_functions():
    plan = plan_event(wardrobe(), ["haldi", "wedding"])
    reused = {p["item"]["name"]: p["uses"] for p in plan["packing"] if p["item"]["category"] != "Clothing"}
    assert reused.get("Gold juttis") == 2
    assert any(p["role"] == "Bangles / bracelet" for d in plan["days"] for p in d["outfit"]["pieces"])


def test_missing_dress_code_colour_is_explained():
    plan = plan_event([item("Blue kurta", "Clothing", "Kurta", "Blue"),
                       item("White salwar", "Clothing", "Salwar", "White")], ["haldi"])
    outfit = plan["days"][0]["outfit"]
    assert any("closest match" in c for c in outfit["cautions"])


def test_wedding_avoids_all_white():
    plan = plan_event(wardrobe(), ["wedding"])
    assert "White kurta" not in clothes(plan["days"][0])


def test_events_api(client):
    functions = client.get("/api/events/functions").json()
    assert {f["key"] for f in functions} >= set(FULL_WEDDING)
    data = {"name": "Yellow kurta", "category": "Clothing", "item_type": "Kurta", "colour": "Yellow",
            "style": "Traditional", "occasions": ["Wedding"]}
    client.post("/api/items", data=data, files={"photo": ("p.png", PNG, "image/png")})
    data = {**data, "name": "White salwar", "item_type": "Salwar", "colour": "White"}
    client.post("/api/items", data=data, files={"photo": ("p.png", PNG, "image/png")})
    res = client.post("/api/events/plan", json={"functions": ["haldi", "mehendi"]})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["days"][0]["label"] == "Haldi" and body["days"][0]["outfit"]
    assert body["days"][1]["outfit"] is None                  # only one outfit's worth of clothes
    assert client.post("/api/events/plan", json={"functions": ["picnic"]}).status_code == 422
    assert client.post("/api/events/plan", json={"functions": []}).status_code == 422


def test_jeans_are_a_last_resort_at_a_reception():
    wardrobe = [item("Party top", "Clothing", "Top", "Wine", "Western"),
                item("Blue jeans", "Clothing", "Jeans", "Denim", "Western"),
                item("Satin skirt", "Clothing", "Skirt", "Black", "Western")]
    day = plan_event(wardrobe, ["reception"])["days"][0]
    assert clothes(day) == {"Party top", "Satin skirt"}
    only_jeans = plan_event(wardrobe[:2], ["reception"])["days"][0]
    assert any("A bit casual" in c for c in only_jeans["outfit"]["cautions"])
