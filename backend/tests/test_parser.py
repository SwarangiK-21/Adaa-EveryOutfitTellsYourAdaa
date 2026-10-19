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


# ---------- Hinglish ----------

@pytest.mark.parametrize("text, expected", [
    ("Aaj college ke liye kuch comfy", {"occasion": "College", "comfort": "Comfort first"}),
    ("Shaadi ke liye kuch lal aur bhaari", {"occasion": "Wedding", "colour": "red", "comfort": "A polished look"}),
    ("Ghoomne ke liye kuch peela", {"occasion": "Casual", "colour": "yellow"}),
    ("Office ke liye kuch halka aur safed", {"occasion": "Office", "colour": "white", "comfort": "Comfort first"}),
    ("Kal sangeet hai, kuch rangeen chahiye", {"occasion": "Wedding", "colour_mood": "Bright & playful"}),
    ("Tyohar ke liye kuch gulabi", {"occasion": "Festive", "colour": "pink"}),
    ("Safar ke liye aasmani", {"occasion": "Travel", "colour": "sky blue"}),
])
def test_hinglish_requests(text, expected):
    result = parse(text)
    for key, value in expected.items():
        assert result[key] == value, (text, key, result[key])
    assert not result["not_found"]


def test_hinglish_my_piece_is_found():
    result = parse("Meri hari kurti diwali ke liye")
    assert result["occasion"] == "Festive"
    assert result["anchor_item_id"] == 5          # the green kurti ("hari" = green)


# ---------- Festivals ----------

@pytest.mark.parametrize("text, festival, occasion", [
    ("Style me for republic day", "republic_day", "Festive"),
    ("style me for ganesh chaturti", "ganesh_chaturthi", "Festive"),       # typo
    ("Style me for Makar Sankranti", "makar_sankranti", "Festive"),
    ("sankranthi ke liye kuch kaala", "makar_sankranti", "Festive"),       # typo + Hinglish
    ("Diwali party look", "diwali", "Party"),                              # party with Diwali colours
    ("Diwali puja outfit", "diwali", "Festive"),
    ("kuch for 15 august", "independence_day", "Festive"),
    ("Holi", "holi", "Casual"),
    ("christmas dinner date", "christmas", "Date"),
    ("christmas", "christmas", "Party"),
])
def test_festivals_are_recognised(text, festival, occasion):
    result = parse(text)
    assert result["festival"] == festival
    assert result["occasion"] == occasion


def test_festival_brings_style_and_navratri_brings_todays_colour():
    from datetime import date
    result = parse_request("something for navratri", WARDROBE, date(2026, 10, 19))
    assert result["style"] == "Traditional"
    assert result["colour"] == "peacock green"
    assert any("Navratri" in u for u in result["understood"])
    typed = parse_request("navratri in western style", WARDROBE, date(2026, 10, 19))
    assert typed["style"] == "Western"


def test_short_words_are_not_mistaken_for_festivals():
    for text in ("style me for a holiday", "said hello", "hold my bag"):
        assert parse(text)["festival"] is None, text
