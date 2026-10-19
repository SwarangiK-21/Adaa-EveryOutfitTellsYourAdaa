from datetime import date
from itertools import count

from recommender import festivals
from recommender.engine import recommend
from schemas import RecommendationRequest

_ids = count(1)


def item(name, category, item_type, colour, style="Traditional", occasions=("Festive",)):
    return {"id": next(_ids), "name": name, "category": category, "item_type": item_type,
            "colour": colour, "style": style, "occasions": list(occasions), "notes": ""}


def wardrobe():
    return [
        item("Saffron kurta", "Clothing", "Kurta", "Orange"),
        item("Navy kurta", "Clothing", "Kurta", "Navy"),
        item("White palazzo", "Clothing", "Palazzo", "White"),
        item("Black salwar", "Clothing", "Salwar", "Black"),
        item("Yellow saree", "Clothing", "Saree", "Yellow"),
        item("Gold blouse", "Clothing", "Blouse", "Gold"),
    ]


def clothes(outfit):
    return {p["item"]["name"] for p in outfit["pieces"] if p["item"]["category"] == "Clothing"}


def test_republic_day_prefers_tricolour_and_says_so():
    best = recommend(wardrobe(), RecommendationRequest(occasion="Festive", festival="republic_day"))["outfits"][0]
    assert clothes(best) == {"Saffron kurta", "White palazzo"}
    assert any("Saffron, white and green for Republic Day" in r for r in best["reasons"])


def test_makar_sankranti_prefers_black_or_yellow():
    best = recommend(wardrobe(), RecommendationRequest(occasion="Festive", festival="makar_sankranti"))["outfits"][0]
    assert clothes(best) & {"Black salwar", "Yellow saree"}


def test_no_festival_colours_is_explained():
    plain = [item("Navy kurta", "Clothing", "Kurta", "Navy"), item("Navy salwar", "Clothing", "Salwar", "Navy")]
    best = recommend(plain, RecommendationRequest(occasion="Festive", festival="holi"))["outfits"][0]
    assert any("usual colours for Holi" in c for c in best["cautions"])


def test_festival_now_today_and_upcoming():
    navratri = festivals.now(date(2026, 10, 19))
    assert navratri["key"] == "navratri" and navratri["today"]
    assert navratri["colour"] == "peacock green" and navratri["day_label"].startswith("Day 9")
    diwali = festivals.now(date(2026, 10, 25))
    assert diwali["key"] == "dhanteras" and diwali["in_days"] == 12 and not diwali["today"]
    assert festivals.now(date(2027, 5, 1)) is None   # nothing within three weeks


def test_festival_api(client):
    assert client.post("/api/recommendations", json={"occasion": "Festive", "festival": "nope"}).status_code == 422
    parsed = client.post("/api/stylist/parse", json={"text": "Style me for Ganesh Chaturthi"}).json()
    assert parsed["festival"] == "ganesh_chaturthi" and parsed["occasion"] == "Festive"
    res = client.get("/api/festivals/now")
    assert res.status_code == 200


def colour_wardrobe():
    return [
        item("Black kurta", "Clothing", "Kurta", "Black"),
        item("Grey kurta", "Clothing", "Kurta", "Grey"),
        item("Black salwar", "Clothing", "Salwar", "Black"),
        item("Pink saree", "Clothing", "Saree", "Pink"),
        item("Pink crop top", "Clothing", "Crop top", "Pink", "Western", ("Party",)),   # not tagged Festive
        item("Black skirt", "Clothing", "Skirt", "Black", "Western", ("Party",)),
    ]


def test_asking_for_a_colour_shows_only_outfits_in_it():
    result = recommend(colour_wardrobe(), RecommendationRequest(occasion="Festive", colour="pink", festival="raksha_bandhan"))
    looks = [clothes(o) for o in result["outfits"]]
    assert looks[0] == {"Pink saree"}
    assert all(look & {"Pink saree", "Pink crop top"} for look in looks)       # no black/grey-only looks
    untagged = next(o for o in result["outfits"] if "Pink crop top" in clothes(o))
    assert any("isn't tagged for Festive" in c or "aren't tagged for Festive" in c for c in untagged["cautions"])


def test_whole_outfit_in_colour_ranks_first():
    wardrobe = [item("Green saree", "Clothing", "Saree", "Green"),
                item("White top", "Clothing", "Top", "White", "Western"),
                item("Black jeans", "Clothing", "Jeans", "Black", "Western"),
                item("Gold blouse", "Clothing", "Blouse", "Gold")]
    best = recommend(wardrobe, RecommendationRequest(occasion="Festive", festival="independence_day"))["outfits"][0]
    assert "Green saree" in clothes(best)


def test_nothing_in_the_colour_says_so_and_shows_the_closest():
    result = recommend(colour_wardrobe()[:3], RecommendationRequest(occasion="Festive", colour="yellow"))
    assert result["outfits"]
    assert any("Nothing in your wardrobe is yellow" in n for n in result["notes"])
