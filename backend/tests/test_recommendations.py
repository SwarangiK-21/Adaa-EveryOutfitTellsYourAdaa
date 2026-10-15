from itertools import count

from recommender import colours
from recommender.engine import recommend
from schemas import RecommendationRequest

_ids = count(1)
ALL = ["Casual", "College", "Office", "Formal", "Party", "Festive", "Wedding",
       "Traditional function", "Date", "Travel"]


def item(name, category, item_type, colour, style="Traditional", occasions=("Festive",)):
    return {"id": next(_ids), "name": name, "category": category, "item_type": item_type,
            "colour": colour, "style": style, "occasions": list(occasions), "notes": ""}


def run(wardrobe, **request):
    return recommend(wardrobe, RecommendationRequest(**request))


def piece_names(outfit):
    return [p["item"]["name"] for p in outfit["pieces"]]


def base_names(outfit):
    return {p["item"]["name"] for p in outfit["pieces"] if p["item"]["category"] == "Clothing"}


# ---------- core rule: only real wardrobe items ----------

def test_outfits_only_use_real_items_and_are_distinct():
    wardrobe = [
        item("Green kurta", "Clothing", "Kurta", "Green"),
        item("Ivory kurti", "Clothing", "Kurti", "Ivory"),
        item("White salwar", "Clothing", "Salwar", "White"),
        item("Blue jeans", "Clothing", "Jeans", "Denim", "Western"),
        item("Black palazzo", "Clothing", "Palazzo", "Black"),
        item("Gold jhumkas", "Jewellery", "Jhumkas", "Gold"),
        item("Tan juttis", "Footwear", "Juttis", "Tan"),
        item("Potli bag", "Bags", "Potli", "Gold"),
    ]
    result = run(wardrobe, occasion="Festive")
    ids = {i["id"] for i in wardrobe}
    assert 3 <= len(result["outfits"]) <= 4
    for outfit in result["outfits"]:
        assert all(p["item"]["id"] in ids for p in outfit["pieces"])
        assert outfit["reasons"]
    bases = [frozenset(base_names(o)) for o in result["outfits"]]
    assert len(set(bases)) == len(bases)


def test_kurta_never_paired_with_western_top_rules_broken():
    wardrobe = [
        item("Crop top", "Clothing", "Crop top", "Black", "Western"),
        item("White churidar", "Clothing", "Churidar", "White"),
    ]
    result = run(wardrobe, occasion="Festive")
    assert result["outfits"] == []  # a crop top doesn't go with a churidar


def test_empty_wardrobe_explains_what_to_add():
    result = run([], occasion="Party")
    assert result["outfits"] == []
    assert "Add some clothes" in result["notes"][0]


def test_tops_without_bottoms_explains_limitation():
    result = run([item("Red top", "Clothing", "Top", "Red", "Western", ALL)], occasion="Party")
    assert result["outfits"] == []
    assert "no bottoms" in result["notes"][0]


# ---------- occasions ----------

def test_prefers_clothes_tagged_for_the_occasion():
    wardrobe = [
        item("Party gown", "Clothing", "Gown", "Black", "Western", ["Party"]),
        item("Office dress", "Clothing", "Dress", "Navy", "Western", ["Office"]),
    ]
    result = run(wardrobe, occasion="Party")
    assert [piece_names(o) for o in result["outfits"]] == [["Party gown"]]
    assert "Only 1 distinct outfit" in " ".join(result["notes"])


def test_relaxes_occasion_when_nothing_is_tagged_and_says_so():
    wardrobe = [item("Black gown", "Clothing", "Gown", "Black", "Western", ["Party"])]
    result = run(wardrobe, occasion="Wedding")
    assert result["relaxed"] is True
    assert piece_names(result["outfits"][0]) == ["Black gown"]
    assert "closest matches" in result["notes"][0]


def test_accessories_must_be_tagged_for_the_occasion():
    wardrobe = [
        item("Red saree", "Clothing", "Saree", "Red", occasions=["Wedding"]),
        item("Gold choker", "Jewellery", "Necklace", "Gold", occasions=["Wedding"]),
        item("Silver studs", "Jewellery", "Earrings", "Silver", occasions=["College"]),
    ]
    names = piece_names(run(wardrobe, occasion="Wedding")["outfits"][0])
    assert "Gold choker" in names
    assert "Silver studs" not in names


# ---------- anchor item ("style my green kurta") ----------

def test_anchor_item_is_in_every_outfit():
    wardrobe = [
        item("Green kurta", "Clothing", "Kurta", "Green", occasions=["Casual"]),
        item("Pink kurta", "Clothing", "Kurta", "Pink"),
        item("White salwar", "Clothing", "Salwar", "White"),
        item("Black palazzo", "Clothing", "Palazzo", "Black"),
    ]
    anchor = wardrobe[0]["id"]
    result = run(wardrobe, occasion="Festive", anchor_item_id=anchor)
    assert len(result["outfits"]) == 2
    assert all("Green kurta" in piece_names(o) for o in result["outfits"])
    assert result["outfits"][0]["reasons"][0] == "Built around your Green kurta"
    assert "isn't tagged for Festive" in result["notes"][0]


def test_anchor_accessory_is_included_even_if_untagged():
    wardrobe = [
        item("Black gown", "Clothing", "Gown", "Black", "Western", ["Party"]),
        item("Pearl earrings", "Jewellery", "Earrings", "Pearl", occasions=["Office"]),
    ]
    result = run(wardrobe, occasion="Party", anchor_item_id=wardrobe[1]["id"])
    assert "Pearl earrings" in piece_names(result["outfits"][0])


def test_unknown_anchor_is_an_error():
    import pytest
    from recommender.engine import RecommendationError
    with pytest.raises(RecommendationError):
        run([], occasion="Party", anchor_item_id=999)


# ---------- preferences ----------

def test_colour_preference_ranks_matching_outfit_first():
    wardrobe = [
        item("Red top", "Clothing", "Top", "Red", "Western", ["Casual"]),
        item("Sage top", "Clothing", "Top", "Sage green", "Western", ["Casual"]),
        item("Blue jeans", "Clothing", "Jeans", "Denim", "Western", ["Casual"]),
    ]
    result = run(wardrobe, occasion="Casual", colour="green")
    assert "Sage top" in piece_names(result["outfits"][0])
    assert any("preferred colour" in r for r in result["outfits"][0]["reasons"])


def test_comfort_first_chooses_flats_over_heels():
    wardrobe = [
        item("Black gown", "Clothing", "Gown", "Black", "Western", ["Party"]),
        item("Stilettos", "Footwear", "Heels", "Black", "Western", ["Party"]),
        item("Flat sandals", "Footwear", "Sandals", "Black", "Western", ["Party"]),
    ]
    comfy = piece_names(run(wardrobe, occasion="Party", comfort="Comfort first")["outfits"][0])
    polished = piece_names(run(wardrobe, occasion="Party", comfort="A polished look")["outfits"][0])
    assert "Flat sandals" in comfy
    assert "Stilettos" in polished


def test_requested_style_unavailable_is_flagged():
    wardrobe = [item("Black gown", "Clothing", "Gown", "Black", "Western", ["Wedding"])]
    outfit = run(wardrobe, occasion="Wedding", style="Traditional")["outfits"][0]
    assert any(c.startswith("Not Traditional") for c in outfit["cautions"])


# ---------- styling rules ----------

def test_jewellery_metals_stay_consistent():
    wardrobe = [
        item("Red saree", "Clothing", "Saree", "Red", occasions=["Wedding"]),
        item("Gold jhumkas", "Jewellery", "Jhumkas", "Gold", occasions=["Wedding"]),
        item("Silver necklace", "Jewellery", "Necklace", "Silver", occasions=["Wedding"]),
        item("Gold bangles", "Jewellery", "Bangles", "Gold", occasions=["Wedding"]),
    ]
    names = piece_names(run(wardrobe, occasion="Wedding")["outfits"][0])
    assert "Gold jhumkas" in names and "Gold bangles" in names
    assert "Silver necklace" not in names


def test_saree_gets_a_blouse_or_a_caution():
    saree = item("Red saree", "Clothing", "Saree", "Red", occasions=["Wedding"])
    blouse = item("Gold blouse", "Clothing", "Blouse", "Gold", occasions=["Festive"])
    with_blouse = run([saree, blouse], occasion="Wedding")["outfits"][0]
    assert "Gold blouse" in piece_names(with_blouse)
    without = run([saree], occasion="Wedding")["outfits"][0]
    assert any("blouse" in c for c in without["cautions"])


def test_casual_looks_keep_jewellery_minimal():
    wardrobe = [item("Blue dress", "Clothing", "Dress", "Blue", "Western", ["College"])] + [
        item(f"Piece {t}", "Jewellery", t, "Silver", "Western", ["College"])
        for t in ("Earrings", "Necklace", "Bracelet", "Ring")
    ]
    outfit = run(wardrobe, occasion="College")["outfits"][0]
    assert sum(p["item"]["category"] == "Jewellery" for p in outfit["pieces"]) == 2


def test_colour_parsing_handles_free_text_and_typos():
    assert colours.parse("Sage green").name == "sage"
    assert colours.parse("Off-White").name == "off white"
    assert colours.parse("daimond").name == "diamond"
    assert colours.parse("Bottle green").name == "bottle green"
    assert colours.parse("sparkly unicorn") is None


# ---------- API ----------

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


def add(client, **fields):
    data = {"category": "Clothing", "style": "Western", "occasions": ["Party"], **fields}
    return client.post("/api/items", data=data, files={"photo": ("p.png", PNG, "image/png")}).json()


def test_recommendations_api_returns_real_items_with_photos(client):
    gown = add(client, name="Black gown", item_type="Gown", colour="Black")
    add(client, name="Silver studs", category="Jewellery", item_type="Earrings", colour="Silver")
    res = client.post("/api/recommendations", json={"occasion": "Party", "style": ""})
    assert res.status_code == 200
    outfit = res.json()["outfits"][0]
    assert outfit["pieces"][0]["item"]["id"] == gown["id"]
    assert outfit["pieces"][0]["item"]["image_url"].startswith(f"/api/items/{gown['id']}/photo")
    assert [p["role"] for p in outfit["pieces"]] == ["Outfit", "Earrings"]


def test_recommendations_api_validates_input(client):
    assert client.post("/api/recommendations", json={"occasion": "Picnic on Mars"}).status_code == 422
    res = client.post("/api/recommendations", json={"occasion": "Party", "anchor_item_id": 42})
    assert res.status_code == 400
    assert "no longer in your wardrobe" in res.json()["detail"]
