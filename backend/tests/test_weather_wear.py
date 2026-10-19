from datetime import date, timedelta
from itertools import count

from recommender.engine import recommend
from recommender.planner import wear_stats
from schemas import RecommendationRequest

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
_ids = count(1)


def item(name, category, item_type, colour, style="Western", occasions=("College",), price=None, created="2026-01-01"):
    return {"id": next(_ids), "name": name, "category": category, "item_type": item_type,
            "colour": colour, "style": style, "occasions": list(occasions), "notes": "",
            "image_filename": "x.png", "created_at": created, "updated_at": created, "price": price}


def add(client, name, item_type, colour="Black", category="Clothing", occasions=("College",), price=""):
    data = {"name": name, "category": category, "item_type": item_type, "colour": colour,
            "style": "Western", "occasions": list(occasions), "price": price}
    res = client.post("/api/items", data=data, files={"photo": ("p.png", PNG, "image/png")})
    assert res.status_code == 201, res.text
    return res.json()


def clothes(outfit):
    return {p["item"]["name"] for p in outfit["pieces"] if p["item"]["category"] == "Clothing"}


# ---------- Weather ----------

def weather_wardrobe():
    return [
        item("Linen crop top", "Clothing", "Crop top", "White"),
        item("Wool sweater", "Clothing", "Sweater", "Grey"),
        item("Denim shorts", "Clothing", "Shorts", "Denim"),
        item("Black jeans", "Clothing", "Jeans", "Black"),
        item("Denim jacket", "Clothing", "Jacket", "Denim"),
        item("Sandals", "Footwear", "Sandals", "Tan"),
        item("Ankle boots", "Footwear", "Boots", "Black"),
    ]


def test_hot_day_prefers_light_pieces_and_skips_layers():
    result = recommend(weather_wardrobe(), RecommendationRequest(
        occasion="College", weather={"temp_c": 36, "rain": False}))
    best = result["outfits"][0]
    assert clothes(best) == {"Linen crop top", "Denim shorts"}
    assert all(p["item"]["name"] != "Denim jacket" for o in result["outfits"] for p in o["pieces"])
    assert any("36°C" in r for r in best["reasons"])


def test_cold_day_prefers_warm_pieces_and_adds_a_layer():
    result = recommend(weather_wardrobe(), RecommendationRequest(
        occasion="College", weather={"temp_c": 9, "rain": False}))
    best = result["outfits"][0]
    names = {p["item"]["name"] for p in best["pieces"]}
    assert "Wool sweater" in names and "Black jeans" in names
    assert "Ankle boots" in names
    assert any("warm" in r for r in best["reasons"])


def test_rain_warns_about_heels_and_light_bottoms():
    wardrobe = [item("Black top", "Clothing", "Top", "Black"),
                item("White trousers", "Clothing", "Trousers", "White"),
                item("Stilettos", "Footwear", "Stilettos", "Black")]
    best = recommend(wardrobe, RecommendationRequest(
        occasion="College", weather={"temp_c": 24, "rain": True}))["outfits"][0]
    assert any("Rain is expected" in c for c in best["cautions"])


def test_no_weather_changes_nothing():
    wardrobe = weather_wardrobe()
    plain = recommend(wardrobe, RecommendationRequest(occasion="College"))
    mild = recommend(wardrobe, RecommendationRequest(occasion="College", weather={"temp_c": 24, "rain": False}))
    assert [clothes(o) for o in plain["outfits"]] == [clothes(o) for o in mild["outfits"]]


def test_weather_is_validated(client):
    res = client.post("/api/recommendations", json={"occasion": "College", "weather": {"temp_c": 200}})
    assert res.status_code == 422


# ---------- Wear stats ----------

def test_wear_stats_not_worn_most_worn_and_cost_per_wear():
    today = date(2026, 10, 19)
    jeans = item("Jeans", "Clothing", "Jeans", "Denim", price=2000)
    top = item("Top", "Clothing", "Top", "White", price=600)
    dress = item("Dress", "Clothing", "Dress", "Red", price=3000)
    scarf = item("Scarf", "Accessories", "Scarf", "Red")
    wear = {jeans["id"]: (10, (today - timedelta(days=2)).isoformat()),
            top["id"]: (3, (today - timedelta(days=45)).isoformat())}
    stats = wear_stats([jeans, top, dress, scarf], wear, today, days=30)
    assert stats["worn_recently"] == 1
    assert [r["item"]["name"] for r in stats["not_worn"]] == ["Dress", "Scarf", "Top"]  # never worn first
    assert stats["not_worn"][2]["days_since"] == 45
    assert [r["item"]["name"] for r in stats["most_worn"]] == ["Jeans", "Top"]
    assert [(r["item"]["name"], r["cost_per_wear"]) for r in stats["cost_per_wear"]] == [
        ("Jeans", 200.0), ("Top", 200.0), ("Dress", 3000.0)]
    assert stats["total_spent"] == 5600
    assert stats["priced_items"] == 3
    assert stats["average_cost_per_wear"] == round(5600 / 14, 2)


def test_wear_stats_without_prices_or_history():
    stats = wear_stats([item("Kurta", "Clothing", "Kurta", "Green")], {}, date(2026, 10, 19))
    assert stats["total_spent"] is None and stats["average_cost_per_wear"] is None
    assert stats["not_worn"][0]["days_since"] is None


def test_price_is_saved_edited_and_validated(client):
    created = add(client, "Blue jeans", "Jeans", "Denim", price="1,499")
    assert created["price"] == 1499
    data = {"name": "Blue jeans", "category": "Clothing", "item_type": "Jeans", "colour": "Denim",
            "style": "Western", "occasions": ["College"], "price": ""}
    edited = client.put(f"/api/items/{created['id']}", data=data).json()
    assert edited["price"] is None
    bad = {**data, "price": "-5"}
    assert client.put(f"/api/items/{created['id']}", data=bad).status_code == 422


def test_wearing_an_unsaved_outfit_counts_in_stats(client):
    top = add(client, "Pink top", "Top", "Pink", price="800")
    jeans = add(client, "Black jeans", "Jeans", "Black", price="1600")
    add(client, "Never worn skirt", "Skirt", "Black")
    res = client.post("/api/history", json={"item_ids": [top["id"], jeans["id"]], "occasion": "College"})
    assert res.status_code == 201, res.text
    entry = res.json()
    assert entry["look_id"] is None and entry["look_name"] == "Pink top + Black jeans"
    assert {p["item"]["id"] for p in entry["pieces"]} == {top["id"], jeans["id"]}
    client.post("/api/history", json={"item_ids": [top["id"]], "occasion": "College"})

    stats = client.get("/api/insights/wear").json()
    assert stats["worn_recently"] == 2
    assert [r["item"]["name"] for r in stats["not_worn"]] == ["Never worn skirt"]
    assert stats["most_worn"][0]["item"]["name"] == "Pink top" and stats["most_worn"][0]["wears"] == 2
    assert {r["item"]["name"]: r["cost_per_wear"] for r in stats["cost_per_wear"]} == {
        "Pink top": 400.0, "Black jeans": 1600.0}
    assert client.post("/api/history", json={"item_ids": [9999], "occasion": "College"}).status_code == 400
    assert client.get("/api/insights/wear?days=3").status_code == 422
