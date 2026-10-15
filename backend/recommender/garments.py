"""What part of an outfit each item plays, worked out from its type.

Users type item types freely ("Crop top", "kurti", "bangels"), so we look for
known type words in the type (then the name), with a little typo tolerance.
"""
import difflib
import re

# Roles for clothing
ONE_PIECE = "Outfit"
TOP = "Top"
BOTTOM = "Bottom"
BLOUSE = "Blouse"
DUPATTA = "Dupatta"
LAYER = "Layer"

# Slots for everything else
FOOTWEAR = "Footwear"
EARRINGS = "Earrings"
NECKLACE = "Necklace"
WRIST = "Bangles / bracelet"
JEWELLERY = "Jewellery"
BAG = "Bag"
ACCESSORY = "Accessory"

_CLOTHING = {
    "gown": ONE_PIECE, "dress": ONE_PIECE, "one piece": ONE_PIECE, "saree": ONE_PIECE,
    "sari": ONE_PIECE, "lehenga": ONE_PIECE, "anarkali": ONE_PIECE, "jumpsuit": ONE_PIECE,
    "co ord set": ONE_PIECE, "sharara set": ONE_PIECE, "kaftan": ONE_PIECE,
    "kurta": TOP, "kurti": TOP, "tunic": TOP, "top": TOP, "crop top": TOP, "shirt": TOP,
    "t shirt": TOP, "tshirt": TOP, "tee": TOP, "tank top": TOP, "sweater": TOP,
    "sweatshirt": TOP, "hoodie": TOP, "blouse": BLOUSE,
    "jeans": BOTTOM, "trousers": BOTTOM, "pants": BOTTOM, "skirt": BOTTOM, "shorts": BOTTOM,
    "culottes": BOTTOM, "jeggings": BOTTOM, "salwar": BOTTOM, "churidar": BOTTOM,
    "palazzo": BOTTOM, "leggings": BOTTOM, "sharara": BOTTOM, "dhoti pants": BOTTOM,
    "patiala": BOTTOM,
    "dupatta": DUPATTA, "stole": DUPATTA,
    "jacket": LAYER, "shrug": LAYER, "blazer": LAYER, "cardigan": LAYER, "coat": LAYER,
    "cape": LAYER, "nehru jacket": LAYER,
}

_JEWELLERY = {
    "earrings": EARRINGS, "earring": EARRINGS, "jhumkas": EARRINGS, "jhumka": EARRINGS,
    "studs": EARRINGS, "chandbali": EARRINGS, "ear cuff": EARRINGS, "hoops": EARRINGS,
    "necklace": NECKLACE, "chain": NECKLACE, "choker": NECKLACE, "pendant": NECKLACE,
    "haar": NECKLACE, "bangles": WRIST, "bangle": WRIST, "bracelet": WRIST, "kada": WRIST,
}

ETHNIC_TOPS = {"kurta", "kurti", "tunic"}
ETHNIC_BOTTOMS_STRICT = {"salwar", "churidar", "patiala"}  # only with kurtas
ETHNIC_BOTTOMS_FLEX = {"palazzo", "leggings", "sharara", "dhoti pants"}

FLAT_FOOTWEAR = {"flats", "sandals", "sneakers", "juttis", "jutti", "kolhapuris", "kolhapuri",
                 "mojari", "loafers", "slippers", "ballerinas"}
HEELED_FOOTWEAR = {"heels", "stilettos", "wedges", "pumps", "block heels", "platforms"}
ETHNIC_FOOTWEAR = {"juttis", "jutti", "kolhapuris", "kolhapuri", "mojari"}
_FOOTWEAR_TYPES = FLAT_FOOTWEAR | HEELED_FOOTWEAR | {"boots", "shoes"}

DRESSY_BAGS = {"clutch", "potli"}
EVERYDAY_BAGS = {"tote", "backpack", "sling bag", "handbag", "shoulder bag"}


def _normalise(text: str) -> str:
    return " ".join(re.sub(r"[^a-z ]", " ", (text or "").lower()).split())


def find_type(text: str, known) -> str | None:
    """Find the best known type word inside free text, e.g. 'Black crop top' -> 'crop top'."""
    cleaned = _normalise(text)
    if not cleaned:
        return None
    if cleaned in known:
        return cleaned
    for key in sorted(known, key=len, reverse=True):
        if re.search(rf"\b{key}\b", cleaned):
            return key
    for word in cleaned.split():
        close = difflib.get_close_matches(word, list(known), n=1, cutoff=0.85)
        if close:
            return close[0]
    return None


def classify(item: dict) -> tuple[str | None, str | None]:
    """Return (role or slot, matched type word) for a wardrobe item."""
    category = item["category"]
    if category == "Clothing":
        key = find_type(item["item_type"], _CLOTHING) or find_type(item["name"], _CLOTHING)
        if key is None:
            return None, None
        role = _CLOTHING[key]
        # A "blouse" in a Western wardrobe is a top, not a saree blouse.
        if role == BLOUSE and item["style"] == "Western":
            role = TOP
        return role, key
    if category == "Jewellery":
        key = find_type(item["item_type"], _JEWELLERY) or find_type(item["name"], _JEWELLERY)
        return (_JEWELLERY[key] if key else JEWELLERY), key
    if category == "Footwear":
        return FOOTWEAR, find_type(item["item_type"], _FOOTWEAR_TYPES)
    if category == "Bags":
        return BAG, find_type(item["item_type"], DRESSY_BAGS | EVERYDAY_BAGS)
    return ACCESSORY, _normalise(item["item_type"])


def top_bottom_fit(top: str, bottom: str) -> tuple[float, str] | None:
    """Can this top be worn with this bottom? Returns (points, reason) or None if not."""
    ethnic_top = top in ETHNIC_TOPS
    if bottom in ETHNIC_BOTTOMS_STRICT:
        return (1.0, f"A classic {top} and {bottom} pairing") if ethnic_top else None
    if bottom in ETHNIC_BOTTOMS_FLEX:
        if ethnic_top:
            return 1.0, f"A classic {top} and {bottom} pairing"
        return 0.0, f"An Indo-Western mix: {top} with {bottom}"
    if bottom == "shorts" and ethnic_top:
        return None
    if ethnic_top:
        return 0.25, f"An easy Indo-Western mix: {top} with {bottom}"
    return 0.5, f"A {top} and {bottom} make a neat pair"
