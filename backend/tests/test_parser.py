import pytest

from recommender.parser import parse_request


def item(id, name, item_type, colour, category="Clothing"):
    return {"id": id, "name": name, "item_type": item_type, "colour": colour,
            "category": category, "style": "Western", "occasions": [], "notes": ""}


WARDROBE = [
    item(1, "Long one piece", "Gown", "Black"),
    item(2, "Crop top", "Top", "Black"),
    item(3, "Gown", "Gown", "Black"),
    item(4, "Black sandels", "Sandals", "Black", "Footwear"),
    item(5, "Green kurti", "Kurti", "Green"),
    item(6, "White kurti", "Kurti", "White"),
]


def parse(text):
    return parse_request(text, WARDROBE)


@pytest.mark.parametrize("text, occasion", [
    ("Style me for a party", "Party"),
    ("what should I wear to my cousin's sangeet?", "Wedding"),
    ("traditional family function at home", "Traditional function"),
    ("Diwali puja outfit", "Festive"),          # first occasion mentioned wins
    ("job interview tomorrow", "Formal"),
    ("going to college", "College"),
    ("dinner date tonight", "Date"),
    ("airport look", "Travel"),
    ("movie with friends", "Casual"),
])
def test_finds_the_occasion(text, occasion):
    assert parse(text)["occasion"] == occasion


def test_example_from_the_brief():
    r = parse("Style my black crop top for a party")
    assert r["occasion"] == "Party"
    assert r["anchor_item_id"] == 2
    assert r["colour"] is None  # "black" described the crop top, it isn't a separate wish
    assert "Building around your Crop top" in r["understood"]


def test_reads_style_comfort_and_colour_mood():
    r = parse("something comfy and indo-western in pastels for college")
    assert (r["style"], r["comfort"], r["colour_mood"]) == ("Indo-Western", "Comfort first", "Pastels")
    assert parse("elegant ethnic look for a wedding")["style"] == "Traditional"
    assert parse("elegant ethnic look for a wedding")["comfort"] == "A polished look"


def test_colour_on_its_own_is_a_preference_not_an_item():
    r = parse("something black for a party")
    assert r["colour"] == "black"
    assert r["anchor_item_id"] is None


def test_name_match_beats_type_match():
    assert parse("style my gown")["anchor_item_id"] == 3


def test_tolerates_typos_in_item_names():
    assert parse("style my black sandals for a movie")["anchor_item_id"] == 4


def test_ambiguous_items_are_reported_not_guessed():
    r = parse("style my kurti for diwali")
    assert r["anchor_item_id"] is None
    assert {a["id"] for a in r["ambiguous"]} == {5, 6}
    assert parse("style my green kurti for diwali")["anchor_item_id"] == 5


def test_piece_not_in_wardrobe_is_reported():
    r = parse("Style my green kurta for a traditional family function")
    assert r["anchor_item_id"] is None
    assert r["not_found"] == ["green kurta"]
    assert r["occasion"] == "Traditional function"


def test_missing_occasion_is_reported():
    r = parse("style my crop top")
    assert r["missing"] == ["occasion"]
    assert r["anchor_item_id"] == 2


def test_parse_api(client):
    res = client.post("/api/stylist/parse", json={"text": "comfy look for college"})
    assert res.status_code == 200
    assert res.json()["occasion"] == "College"
    assert client.post("/api/stylist/parse", json={"text": ""}).status_code == 422
