from itertools import count

from recommender.planner import find_gaps, plan_trip

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
_ids = count(1)


def item(name, category, item_type, colour, style="Western", occasions=("College",)):
    return {"id": next(_ids), "name": name, "category": category, "item_type": item_type,
            "colour": colour, "style": style, "occasions": list(occasions), "notes": "",
            "image_filename": "x.png", "created_at": "", "updated_at": ""}


def add(client, name, item_type, colour="Black", category="Clothing", occasions=("College",)):
    data = {"name": name, "category": category, "item_type": item_type, "colour": colour,
            "style": "Western", "occasions": list(occasions)}
    res = client.post("/api/items", data=data, files={"photo": ("p.png", PNG, "image/png")})
    assert res.status_code == 201, res.text
    return res.json()["id"]


# ---------- What to buy next ----------

def test_missing_bottom_is_the_top_suggestion_for_a_tops_only_wardrobe():
    wardrobe = [item(f"{c} top", "Clothing", "Top", c, occasions=("College", "Casual"))
                for c in ("White", "Pink", "Black", "Green")]
    wardrobe.append(item("Blue jeans", "Clothing", "Jeans", "Denim", occasions=("Party",)))
    report = find_gaps(wardrobe)
    top = report["suggestions"][0]
    assert top["category"] == "Clothing" and top["item_type"] in ("Jeans", "Trousers", "Skirt", "Palazzo")
    assert top["new_outfits"] >= 4
    assert {p["name"] for p in top["pairs_with"]} <= {i["name"] for i in wardrobe}
    assert any("4 tops but only 1 bottom" in n for n in report["notes"])


def test_shoes_are_suggested_when_no_footwear_is_tagged_for_an_occasion():
    wardrobe = [item("White shirt", "Clothing", "Shirt", "White", occasions=("College", "Casual")),
                item("Black trousers", "Clothing", "Trousers", "Black", occasions=("College", "Casual"))]
    shoes = [s for s in find_gaps(wardrobe)["suggestions"] if s["category"] == "Footwear"]
    assert shoes, "a shoe suggestion should always make the list"
    assert shoes[0]["new_outfits"] == 1
    assert "1 outfit that has no shoes tagged for Casual and College" in shoes[0]["reason"]


def test_things_you_already_own_are_not_suggested():
    wardrobe = [item("White shirt", "Clothing", "Shirt", "White", occasions=("College",)),
                item("My sneakers", "Footwear", "Sneakers", "Off white", occasions=("College",)),
                item("Jeans", "Clothing", "Jeans", "Denim", occasions=("College",))]
    names = {s["name"] for s in find_gaps(wardrobe)["suggestions"]}
    assert "White sneakers" not in names
    assert "Blue jeans" not in names
    assert "White shirt" not in names


def test_empty_wardrobe_has_no_suggestions_from_nothing():
    report = find_gaps([])
    assert report["outfits_now"] == 0
    assert report["notes"] == []


def test_gaps_api(client):
    add(client, "Pink top", "Top", "Pink")
    add(client, "Black jeans", "Jeans", "Black")
    res = client.get("/api/insights/gaps")
    assert res.status_code == 200
    body = res.json()
    assert body["outfits_now"] == 1
    assert body["suggestions"], body
    for s in body["suggestions"]:
        assert s["new_outfits"] > 0
        for p in s["pairs_with"]:
            assert p["image_url"].startswith("/api/items/")


# ---------- Trip packing ----------

def capsule():
    return [
        item("White tee", "Clothing", "T-shirt", "White", occasions=("Casual", "Travel")),
        item("Black top", "Clothing", "Top", "Black", occasions=("Casual", "Travel", "Party")),
        item("Striped shirt", "Clothing", "Shirt", "Blue", occasions=("Casual",)),
        item("Blue jeans", "Clothing", "Jeans", "Denim", occasions=("Casual", "Travel")),
        item("Beige shorts", "Clothing", "Shorts", "Beige", occasions=("Casual",)),
        item("Black skirt", "Clothing", "Skirt", "Black", occasions=("Party",)),
        item("Red dress", "Clothing", "Dress", "Red", occasions=("Party",)),
        item("Sneakers", "Footwear", "Sneakers", "White", occasions=("Casual", "Travel")),
        item("Heels", "Footwear", "Heels", "Black", occasions=("Party",)),
    ]


def test_trip_gives_every_day_an_outfit_without_repeats():
    plan = plan_trip(capsule(), ["Travel", "Casual", "Casual", "Party"])
    assert plan["outfits"] == 4
    looks = [frozenset(p["item"]["id"] for p in d["outfit"]["pieces"] if p["item"]["category"] == "Clothing")
             for d in plan["days"]]
    assert len(set(looks)) == 4
    assert [d["occasion"] for d in plan["days"]] == ["Travel", "Casual", "Casual", "Party"]


def test_trip_never_repeats_a_garment_but_reuses_shoes():
    plan = plan_trip(capsule(), ["Casual", "Casual", "Casual"])
    assert plan["outfits"] == 3
    clothes = [p for p in plan["packing"] if p["item"]["category"] == "Clothing"]
    assert clothes and all(p["uses"] == 1 for p in clothes)
    shoes = [p for p in plan["packing"] if p["item"]["category"] == "Footwear"]
    assert len(shoes) == 1 and shoes[0]["uses"] == 3
    # Only two bottoms are tagged Casual, so the third day honestly uses an untagged one.
    assert any("nothing new is tagged for Casual" in n for n in plan["notes"])


def test_trip_finds_a_plan_where_picking_day_by_day_would_fail():
    wardrobe = [item("Sequin top", "Clothing", "Top", "Black", occasions=("Casual", "Party")),
                item("Plain tee", "Clothing", "T-shirt", "White", occasions=("Casual",)),
                item("Jeans", "Clothing", "Jeans", "Denim", occasions=("Casual",)),
                item("Satin skirt", "Clothing", "Skirt", "Black", occasions=("Party",))]
    plan = plan_trip(wardrobe, ["Casual", "Party"])
    assert plan["outfits"] == 2
    names = lambda d: {p["item"]["name"] for p in d["outfit"]["pieces"]}
    assert names(plan["days"][1]) == {"Sequin top", "Satin skirt"}
    assert names(plan["days"][0]) == {"Plain tee", "Jeans"}


def test_trip_only_uses_real_wardrobe_items():
    wardrobe = capsule()
    ids = {i["id"] for i in wardrobe}
    plan = plan_trip(wardrobe, ["Party", "Casual"])
    assert {p["item"]["id"] for p in plan["packing"]} <= ids


def test_trip_leaves_a_day_empty_rather_than_repeating_clothes():
    wardrobe = [item("Kurta", "Clothing", "Kurta", "Green", "Traditional", ("Festive",)),
                item("Salwar", "Clothing", "Salwar", "White", "Traditional", ("Festive",))]
    plan = plan_trip(wardrobe, ["Festive", "Festive"])
    assert plan["outfits"] == 1
    assert sum(d["outfit"] is None for d in plan["days"]) == 1
    assert any("Day 2: not enough different clothes" in n and "Festive" in n for n in plan["notes"])
    empty = plan_trip([], ["Casual"])
    assert empty["outfits"] == 0 and empty["days"][0]["outfit"] is None


def test_trip_api(client):
    add(client, "Pink top", "Top", "Pink", occasions=("Travel",))
    add(client, "Black jeans", "Jeans", "Black", occasions=("Travel",))
    add(client, "Sneakers", "Sneakers", "White", category="Footwear", occasions=("Travel",))
    res = client.post("/api/trips/plan", json={"days": ["Travel"]})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["outfits"] == 1 and body["pieces"] == 3
    assert body["packing"][0]["item"]["image_url"].startswith("/api/items/")
    assert client.post("/api/trips/plan", json={"days": []}).status_code == 422
    assert client.post("/api/trips/plan", json={"days": ["Beach"]}).status_code == 422
    assert client.post("/api/trips/plan", json={"days": ["Casual"] * 15}).status_code == 422


def test_blue_jeans_count_as_denim_and_bags_rank_below_clothes():
    wardrobe = [item(f"{c} top", "Clothing", "Top", c, occasions=("College", "Casual", "Travel"))
                for c in ("White", "Pink", "Black")]
    wardrobe.append(item("Straight jeans", "Clothing", "Jeans", "Blue", occasions=("College", "Casual", "Travel")))
    suggestions = find_gaps(wardrobe, limit=20)["suggestions"]
    names = [s["name"] for s in suggestions]
    assert "Blue jeans" not in names
    bag = next(s for s in suggestions if s["category"] == "Bags")
    assert "Adds a matching bag" in bag["reason"]
    clothes = [i for i, s in enumerate(suggestions) if s["category"] == "Clothing"]
    assert clothes and min(clothes) < names.index(bag["name"])
