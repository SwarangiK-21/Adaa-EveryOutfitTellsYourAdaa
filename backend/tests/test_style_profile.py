"""The optional style profile: saving it safely, and how it nudges and explains outfits."""
import sqlite3
from itertools import count

import pytest

import database
from recommender import profile_fit
from recommender.engine import evaluate, recommend
from recommender.planner import find_gaps
from schemas import RecommendationRequest, StylePrefs

_ids = count(1000)


def item(name, item_type, colour, category="Clothing", style="Western", occasions=("Casual",)):
    return {"id": next(_ids), "name": name, "category": category, "item_type": item_type,
            "colour": colour, "style": style, "occasions": list(occasions), "notes": ""}


def run(wardrobe, profile=None, **request):
    return recommend(wardrobe, RecommendationRequest(**{"occasion": "Casual", **request}), profile)


def clothes(outfit):
    return {p["item"]["name"] for p in outfit["pieces"] if p["item"]["category"] == "Clothing"}


# ---------- saving the profile ----------

def test_empty_profile_until_saved(client):
    res = client.get("/api/profile/style")
    assert res.status_code == 200
    body = res.json()
    assert body["height_cm"] is None and body["avoid"] == [] and body["onboarded"] is False


def test_save_and_read_back(client):
    profile = {"height_cm": 152, "body_shape": "pear", "fit": "relaxed", "undertone": "warm",
               "avoid": ["sleeveless", "sleeveless"], "love_colours": ["Mustard", "olive"],
               "avoid_colours": ["Yellow"], "style": "Indo-western", "onboarded": True}
    res = client.patch("/api/profile/style", json=profile)
    assert res.status_code == 200, res.text
    saved = client.get("/api/profile/style").json()
    assert saved["height_cm"] == 152 and saved["body_shape"] == "pear" and saved["undertone"] == "warm"
    assert saved["avoid"] == ["sleeveless"]                       # repeats removed
    assert saved["love_colours"] == ["mustard", "olive"]          # colour names tidied
    assert saved["avoid_colours"] == ["yellow"] and saved["onboarded"] is True and saved["updated_at"]


def test_only_sent_fields_change(client):
    client.patch("/api/profile/style", json={"body_shape": "pear", "height_cm": 160})
    client.patch("/api/profile/style", json={"style": "Western"})             # e.g. from the Preferences page
    saved = client.get("/api/profile/style").json()
    assert saved["body_shape"] == "pear" and saved["height_cm"] == 160 and saved["style"] == "Western"
    client.patch("/api/profile/style", json={"body_shape": None})
    assert client.get("/api/profile/style").json()["body_shape"] is None


def test_skipping_everything_is_fine(client):
    res = client.patch("/api/profile/style", json={"onboarded": True})
    assert res.status_code == 200 and res.json()["body_shape"] is None


@pytest.mark.parametrize("bad", [
    {"height_cm": 90}, {"height_cm": 260}, {"body_shape": "triangle"}, {"fit": "tight"},
    {"undertone": "olive"}, {"gender": "x"}, {"avoid": ["nothing"]}, {"love_colours": ["zzzz"]},
    {"love_colours": ["red"] * 9},
])
def test_profile_validation(client, bad):
    assert client.patch("/api/profile/style", json=bad).status_code == 422


def test_profile_needs_login(anon):
    assert anon.get("/api/profile/style").status_code == 401
    assert anon.patch("/api/profile/style", json={}).status_code == 401


def test_profiles_are_private(client, other_client):
    client.patch("/api/profile/style", json={"body_shape": "apple", "height_cm": 160})
    assert other_client.get("/api/profile/style").json()["body_shape"] is None


def test_profile_is_deleted_with_the_account(client):
    from tests.conftest import TEST_USER
    client.patch("/api/profile/style", json={"body_shape": "apple"})
    client.request("DELETE", "/api/auth/me", json={"password": TEST_USER["password"]})
    with database.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM style_profiles").fetchone()[0] == 0


def test_database_rejects_impossible_values(client):
    with database.connect() as conn, pytest.raises(sqlite3.IntegrityError):
        conn.execute("INSERT INTO style_profiles (user_id, height_cm, updated_at) VALUES (1, 400, 'now')")


# ---------- reading a piece's cut ----------

@pytest.mark.parametrize("name, item_type, expected", [
    ("Black palazzo", "Palazzo", {"flowy", "wide_leg", "long"}),
    ("skin fit jeans", "Jeans", {"fitted"}),
    ("Black bodycon skirt", "Skirt", {"bodycon", "fitted"}),
    ("Ruffle crop top", "Top", {"cropped"}),
    ("Green anarkali", "Kurta", {"flowy", "a_line", "long", "tunic"}),
    ("High waist jeans", "Jeans", {"high_waist"}),
    ("Strappy cami", "Top", {"sleeveless"}),
])
def test_traits(name, item_type, expected):
    assert expected <= profile_fit.traits(item(name, item_type, "Black"))


def test_bags_named_sling_are_not_sleeveless():
    assert profile_fit.traits(item("black sling", "Sling bag", "Black", category="Bags")) == set()


# ---------- how the profile changes outfits ----------

WARDROBE = [
    item("White top", "Top", "White"),
    item("Black palazzo", "Palazzo", "Black"),
    item("Skinny jeans", "Jeans", "Denim"),
]


def test_no_profile_changes_nothing():
    plain = run(WARDROBE)
    assert all(o["personal"] == [] for o in plain["outfits"])
    assert [clothes(o) for o in run(WARDROBE, {})["outfits"]] == [clothes(o) for o in plain["outfits"]]


def test_pear_shape_prefers_flowing_bottoms_and_says_why():
    best = run(WARDROBE, {"body_shape": "pear"})["outfits"][0]
    assert "Black palazzo" in clothes(best)
    assert any("balances a pear shape" in r for r in best["personal"])


def test_preferred_fit():
    best = run(WARDROBE, {"fit": "fitted"})["outfits"][0]
    assert "Skinny jeans" in clothes(best) and any("fitted look you prefer" in r for r in best["personal"])


def test_avoided_styles_rank_lower_but_are_still_shown():
    wardrobe = [item("Strappy cami", "Top", "Black"), item("White shirt", "Shirt", "White"), item("Blue jeans", "Jeans", "Denim")]
    result = run(wardrobe, {"avoid": ["sleeveless"]})["outfits"]
    assert clothes(result[0]) == {"White shirt", "Blue jeans"}
    cami = next(o for o in result if "Strappy cami" in clothes(o))
    assert any("sleeveless styles you said you usually skip" in c for c in cami["cautions"])
    only = run([item("Strappy cami", "Top", "Black"), item("Blue jeans", "Jeans", "Denim")], {"avoid": ["sleeveless"]})
    assert len(only["outfits"]) == 1                              # never hidden when it's all there is


def test_undertone_only_adds_colour_notes():
    wardrobe = [item("Mustard top", "Top", "Mustard"), item("Lavender top", "Top", "Lavender"), item("Blue jeans", "Jeans", "Denim")]
    warm = run(wardrobe, {"undertone": "warm"})["outfits"]
    assert "Mustard top" in clothes(warm[0])
    assert any("glow on warm undertones" in r for r in warm[0]["personal"])
    lavender = next(o for o in warm if "Lavender top" in clothes(o))
    assert not any("undertone" in c for c in lavender["cautions"])   # never a warning about colour


def test_loved_and_avoided_colours():
    wardrobe = [item("Olive top", "Top", "Olive"), item("Pink top", "Top", "Pink"), item("Blue jeans", "Jeans", "Denim")]
    result = run(wardrobe, {"love_colours": ["olive"], "avoid_colours": ["pink"]})["outfits"]
    assert "Olive top" in clothes(result[0]) and "a colour you love" in " ".join(result[0]["personal"])
    pink = next(o for o in result if "Pink top" in clothes(o))
    assert any("rather avoid" in c for c in pink["cautions"])


def test_height_notes():
    wardrobe = [item("White top", "Top", "White"), item("High waist jeans", "Jeans", "Denim")]
    petite = run(wardrobe, {"height_cm": 150})["outfits"][0]
    assert any("adds length to the legs" in r for r in petite["personal"])
    tall = run([item("White top", "Top", "White"), item("Black palazzo", "Palazzo", "Black")], {"height_cm": 178})["outfits"][0]
    assert any("suits your height" in r for r in tall["personal"])


def test_jewellery_metal_for_undertone():
    wardrobe = [item("Green kurta", "Kurta", "Green", style="Traditional", occasions=("Festive",)),
                item("White salwar", "Salwar", "White", style="Traditional", occasions=("Festive",)),
                item("Gold jhumkas", "Jhumkas", "Gold", category="Jewellery", style="Traditional", occasions=("Festive",))]
    best = run(wardrobe, {"undertone": "warm"}, occasion="Festive")["outfits"][0]
    assert any("Gold jewellery like your Gold jhumkas suits warm undertones" == r for r in best["personal"])


def test_evaluate_after_a_swap_explains_too():
    result = evaluate(WARDROBE, [WARDROBE[0]["id"], WARDROBE[1]["id"]], StylePrefs(occasion="Casual"), {"body_shape": "pear"})
    assert any("pear shape" in r for r in result["personal"])


def test_recommendations_api_uses_the_saved_profile(client):
    from tests.test_auth import add_item
    add_item(client, "White top", "Top", "White")
    add_item(client, "Black palazzo", "Palazzo", "Black")
    client.patch("/api/profile/style", json={"body_shape": "pear"})
    res = client.post("/api/recommendations", json={"occasion": "Festive"})
    assert res.status_code == 200, res.text
    assert any("pear shape" in r for o in res.json()["outfits"] for r in o["personal"])


def test_shop_ideas_respect_gender():
    wardrobe = [item("White top", "Top", "White"), item("Blue jeans", "Jeans", "Denim")]
    names = lambda report: {s["name"] for s in report["suggestions"]}   # noqa: E731
    everyone = names(find_gaps(wardrobe, limit=20))
    men = names(find_gaps(wardrobe, limit=20, profile={"gender": "man"}))
    assert not any(w in n.lower() for n in men for w in profile_fit.WOMENSWEAR)
    assert men <= everyone
