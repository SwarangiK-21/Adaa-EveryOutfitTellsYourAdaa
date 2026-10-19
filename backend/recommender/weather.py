"""Today's weather as a gentle nudge in styling: light pieces on hot days, warm layers on cold
days, and a word of caution about heels and light colours in the rain.

Weather never removes a piece from the wardrobe or overrides the occasion; it only shifts scores
a little and explains itself (a reason or a caution on the outfit).
"""
import re

HOT_C = 30      # daily high at or above this: dress light
COLD_C = 17     # daily high at or below this: add warmth

# Kinds of piece, by type word (as matched by garments.classify) or words in the name.
WARM_TYPES = {"sweater", "sweatshirt", "hoodie", "jacket", "coat", "blazer", "cardigan", "shrug",
              "cape", "nehru jacket", "boots"}
WARM_WORDS = {"full sleeve", "full sleeves", "full sleves", "long sleeve", "wool", "woollen", "woolen",
              "velvet", "knit", "thermal", "fleece", "turtleneck"}
LIGHT_TYPES = {"crop top", "tank top", "tee", "t shirt", "tshirt", "shorts", "skirt", "dress", "kurti",
               "palazzo", "culottes", "sandals", "flats", "kolhapuris", "kolhapuri", "slippers"}
LIGHT_WORDS = {"sleeveless", "cotton", "linen", "chiffon", "georgette", "half sleeve", "crop", "strappy"}
BARE_LEG_TYPES = {"shorts", "skirt"}
HEELS = {"heels", "stilettos", "pumps", "block heels", "platforms"}
LIGHT_COLOURS = {"white", "off white", "ivory", "cream", "beige"}


def _words(piece) -> str:
    return " ".join(re.sub(r"[^a-z ]", " ", f"{piece.item['name']} {piece.item['item_type']}".lower()).split())


def is_warm(piece) -> bool:
    text = _words(piece)
    return piece.type_key in WARM_TYPES or any(w in text for w in WARM_WORDS)


def is_light(piece) -> bool:
    text = _words(piece)
    return (piece.type_key in LIGHT_TYPES or any(w in text for w in LIGHT_WORDS)) and not is_warm(piece)


def points(piece, weather) -> float:
    """Small score nudge for one piece in today's weather."""
    if weather is None:
        return 0.0
    layer = piece.role == "Layer"
    score = 0.0
    if weather.temp_c >= HOT_C:
        if is_warm(piece):
            score -= 3.0 if layer else 1.5
        elif is_light(piece):
            score += 1.0
    elif weather.temp_c <= COLD_C:
        if is_warm(piece):
            score += 2.0 if layer else 1.0
        elif piece.type_key in BARE_LEG_TYPES or piece.type_key in {"sandals", "slippers", "flats"}:
            score -= 1.5
        elif is_light(piece):
            score -= 0.5
    if weather.rain:
        if piece.type_key in HEELS:
            score -= 1.0
        if piece.role == "Bottom" and piece.colour and piece.colour.name in LIGHT_COLOURS:
            score -= 0.5
    return score


def _degrees(weather) -> str:
    return f"{round(weather.temp_c)}°C"


def notes(pieces, weather) -> tuple[list[tuple[float, str]], list[str]]:
    """(reasons, cautions) about how an outfit suits today's weather."""
    if weather is None:
        return [], []
    reasons: list[tuple[float, str]] = []
    cautions: list[str] = []
    clothes = [p for p in pieces if p.item["category"] in ("Clothing", "Footwear")]
    warm = [p for p in clothes if is_warm(p)]
    if weather.temp_c >= HOT_C:
        if warm:
            cautions.append(f"Might feel warm at {_degrees(weather)}: your {', '.join(p.name for p in warm)}")
        elif any(is_light(p) for p in clothes):
            reasons.append((1.5, f"Light, breezy pieces for a {_degrees(weather)} day"))
    elif weather.temp_c <= COLD_C:
        if warm:
            reasons.append((1.5, f"Your {warm[0].name} keeps you warm at {_degrees(weather)}"))
        else:
            cautions.append(f"It's {_degrees(weather)} today: add a jacket or a warm layer")
    if weather.rain:
        wet = [p.name for p in pieces if p.type_key in HEELS
               or (p.role == "Bottom" and p.colour and p.colour.name in LIGHT_COLOURS)]
        if wet:
            cautions.append(f"Rain is expected: your {', '.join(wet)} may not love puddles")
        else:
            reasons.append((0.75, "Rain-friendly: no heels or light-coloured bottoms"))
    return reasons, cautions
