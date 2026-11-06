"""How someone's optional style profile nudges their outfits.

Every answer is optional and chosen by the person (body shape is never guessed from height or
weight). The profile only *adds* small bonuses with a reason ("why it suits you"); it never hides a
piece. The one exception is what the person said they'd rather avoid (sleeveless, short hemlines,
bodycon, crop tops, or colours): those outfits rank lower and say so, but still appear if the
wardrobe has nothing else. Skin undertone only suggests colours that tend to glow; it never rules
any colour out.

A piece's shape is read from its type, name and notes ("palazzo", "bodycon", "high-waist"...),
the same words people already use when adding clothes.
"""
from recommender import colours, garments as g

PETITE_CM, TALL_CM = 155, 172

# Words that describe how a piece is cut. A piece can have several traits.
_TRAITS = {
    "fitted": ("bodycon", "body con", "fitted", "skinny", "skin fit", "slim fit", "pencil", "sheath", "churidar", "legging"),
    "bodycon": ("bodycon", "body con"),
    "relaxed": ("oversized", "over sized", "baggy", "relaxed", "loose", "boyfriend", "boxy", "kaftan"),
    "flowy": ("palazzo", "wide leg", "wide-leg", "flared", "flare", "a-line", "a line", "anarkali", "lehenga",
              "maxi", "kaftan", "gown", "skater", "sharara", "gharara", "culotte", "umbrella", "saree", "sari"),
    "a_line": ("a-line", "a line", "anarkali", "skater", "flared", "flare", "umbrella", "lehenga"),
    "wide_leg": ("palazzo", "wide leg", "wide-leg", "sharara", "gharara", "culotte", "bell bottom", "baggy", "flared pant"),
    "high_waist": ("high waist", "high-waist", "highwaist", "high rise", "high-rise"),
    "cropped": ("crop", "cropped"),
    "wrap": ("wrap", "angrakha"),
    "belted": ("belt",),
    "sleeveless": ("sleeveless", "spaghetti", "strappy", "halter", "tank", "tube top", "off shoulder", "off-shoulder", "cami"),
    "short": ("mini", "short skirt", "shorts", "short frock", "short dress", "hot pant", "skort"),
    "long": ("maxi", "gown", "floor length", "floor-length", "anarkali", "lehenga", "long kurta", "long one piece",
             "long dress", "saree", "sari", "palazzo", "wide leg", "wide-leg", "sharara"),
    "tunic": ("kurta", "kurti", "tunic", "anarkali", "kaftan", "peplum"),
}

AVOID_LABELS = {"sleeveless": "sleeveless styles", "short_hemlines": "short hemlines",
                "bodycon": "bodycon fits", "crop_tops": "crop tops"}
_AVOID_TRAIT = {"sleeveless": "sleeveless", "short_hemlines": "short", "bodycon": "bodycon", "crop_tops": "cropped"}

# Colours that commonly glow on each undertone (a gentle nudge, never a rule).
_WARM = {"mustard", "olive", "rust", "orange", "peach", "coral", "yellow", "camel", "tan", "brown", "cream",
         "ivory", "off white", "red", "maroon", "bottle green", "khaki", "gold", "bronze", "copper", "beige"}
_COOL = {"navy", "royal blue", "cobalt", "blue", "emerald", "purple", "violet", "lavender", "lilac", "pink",
         "hot pink", "fuchsia", "magenta", "baby pink", "grey", "charcoal", "white", "black", "burgundy",
         "wine", "plum", "teal", "turquoise", "powder blue", "sky blue", "silver", "diamond", "mint"}

_NEAR_FACE = {g.TOP, g.BLOUSE, g.ONE_PIECE, g.DUPATTA}

_SHAPE_TIPS = {
    # body shape: (traits that help, which pieces, the reason)
    "hourglass": (("fitted", "wrap", "belted"), "any", "{name}: a cut that follows the waist, a classic choice for an hourglass shape"),
    "pear": (("a_line", "wide_leg", "flowy"), "bottom", "{name}: a flowing cut past the hips balances a pear shape"),
    "apple": (("tunic", "flowy", "a_line", "wrap"), "upper", "{name}: skims the middle, easy and comfortable for an apple shape"),
    "rectangle": (("wrap", "belted", "cropped", "high_waist", "a_line"), "any", "{name}: adds shape at the waist, as rectangle shapes often like"),
    "inverted_triangle": (("wide_leg", "a_line", "flowy"), "bottom", "{name}: adds volume below, balancing broader shoulders"),
}


def traits(item: dict) -> set[str]:
    if item.get("category") != "Clothing":
        return {"belted"} if "belt" in f"{item.get('item_type', '')} {item.get('name', '')}".lower() else set()
    text = f" {item.get('item_type', '')} {item.get('name', '')} {item.get('notes', '')} ".lower()
    return {trait for trait, words in _TRAITS.items() if any(w in text for w in words)}


def _cap(text: str) -> str:
    return text[:1].upper() + text[1:]


def _colour(piece):
    return piece.colour.name if piece.colour else None


def _which(piece, where: str) -> bool:
    if where == "any":
        return piece.item["category"] == "Clothing"
    if where == "bottom":
        return piece.role == g.BOTTOM or piece.role == g.ONE_PIECE
    return piece.role in (g.TOP, g.BLOUSE, g.ONE_PIECE)          # "upper"


def apply(outfit, profile: dict | None) -> None:
    """Add 'why it suits you' points and notes to an outfit (its clothes and any accessories)."""
    if not profile:
        return
    personal: list[tuple[float, str]] = []

    def add(points: float, reason: str) -> None:
        outfit.score += points
        personal.append((points, reason))

    clothes = [p for p in outfit.pieces if p.item["category"] == "Clothing"]
    found = {p.id: traits(p.item) for p in outfit.pieces}

    # Things they'd rather not wear: rank lower and say so (still shown if nothing else fits).
    for choice in profile.get("avoid") or []:
        hit = next((p for p in clothes if _AVOID_TRAIT[choice] in found[p.id]), None)
        if hit:
            outfit.score -= 2.0
            outfit.cautions.append(f"Your {hit.name} is one of the {AVOID_LABELS[choice]} you said you usually skip")

    # Colours they love or avoid.
    loves, dislikes = set(profile.get("love_colours") or []), set(profile.get("avoid_colours") or [])
    loved = next((p for p in clothes if _colour(p) in loves), None)
    if loved:
        add(1.0, f"Features {_colour(loved)}, a colour you love")
    disliked = next((p for p in clothes if _colour(p) in dislikes), None)
    if disliked:
        outfit.score -= 1.5
        outfit.cautions.append(f"Your {disliked.name} is {_colour(disliked)}, a colour you'd rather avoid")

    # Preferred fit.
    fit = profile.get("fit")
    if fit == "fitted":
        piece = next((p for p in clothes if "fitted" in found[p.id]), None)
        if piece:
            add(0.6, f"{_cap(piece.name)}: the fitted look you prefer")
    elif fit == "relaxed":
        piece = next((p for p in clothes if found[p.id] & {"relaxed", "flowy"}), None)
        if piece:
            add(0.6, f"{_cap(piece.name)}: the relaxed, easy fit you prefer")
        if any("bodycon" in found[p.id] for p in clothes):
            outfit.score -= 0.4

    # Body shape the person chose.
    tip = _SHAPE_TIPS.get(profile.get("body_shape") or "")
    if tip:
        helpful, where, text = tip
        piece = next((p for p in clothes if _which(p, where) and found[p.id] & set(helpful)), None)
        if not piece and profile["body_shape"] in ("hourglass", "rectangle"):
            piece = next((p for p in outfit.pieces if "belted" in found[p.id]), None)
        if piece:
            add(0.8, text.format(name=_cap(piece.name)))
        if profile["body_shape"] == "pear":
            upper = next((p for p in clothes if p.role in (g.TOP, g.BLOUSE)), None)
            lower = next((p for p in clothes if p.role == g.BOTTOM), None)
            if upper and lower and upper.colour and lower.colour and upper.colour.kind in ("bright", "pastel") \
                    and lower.colour.name in ("black", "navy", "charcoal", "denim", "brown"):
                add(0.4, "A brighter top over a darker bottom draws the eye up")

    # Height.
    height = profile.get("height_cm")
    if height and height < PETITE_CM:
        piece = next((p for p in clothes if "high_waist" in found[p.id]), None)
        if piece:
            add(0.6, f"{_cap(piece.name)}: a high waist adds length to the legs")
        elif len(clothes) >= 2 and len({_colour(p) for p in clothes}) == 1 and _colour(clothes[0]):
            add(0.4, f"One colour head to toe ({_colour(clothes[0])}) adds height")
    elif height and height >= TALL_CM:
        piece = next((p for p in clothes if found[p.id] & {"long", "wide_leg"}), None)
        if piece:
            add(0.5, f"{_cap(piece.name)}: a long line that suits your height")

    # Skin undertone: colours that tend to glow near the face.
    tone = profile.get("undertone")
    if tone in ("warm", "cool"):
        palette = _WARM if tone == "warm" else _COOL
        near = next((p for p in clothes if p.role in _NEAR_FACE and _colour(p) in palette), None)
        if near:
            add(0.5, f"{_colour(near).capitalize()} near your face tends to glow on {tone} undertones")

    _keep(outfit, personal)


def apply_jewellery(outfit, profile: dict | None) -> None:
    """Note matching jewellery metal (gold for warm undertones, silver for cool), once jewellery is chosen."""
    tone = (profile or {}).get("undertone")
    if tone not in ("warm", "cool"):
        return
    metals = ("gold", "bronze", "copper", "rose gold") if tone == "warm" else ("silver", "diamond")
    jewel = next((p for p in outfit.pieces if p.item["category"] == "Jewellery" and _colour(p) in metals), None)
    if jewel:
        metal = "Gold" if tone == "warm" else "Silver"
        _keep(outfit, [(0.3, f"{metal} jewellery like your {jewel.name} suits {tone} undertones")])


def _keep(outfit, notes: list[tuple[float, str]]) -> None:
    existing = {r for _, r in outfit.personal}
    outfit.personal = list(outfit.personal) + [(p, r) for p, r in notes if r not in existing]


def personal_notes(outfit, limit: int = 3) -> list[str]:
    seen, notes = set(), []
    for _, reason in sorted(getattr(outfit, "personal", []), key=lambda r: -r[0]):
        if reason not in seen:
            seen.add(reason)
            notes.append(reason)
    return notes[:limit]


# Shop Smart ideas that are usually only worn by women (hidden if someone says they're a man).
WOMENSWEAR = ("skirt", "heels", "palazzo", "jhumka", "potli", "kurti", "saree", "lehenga", "clutch")


def shop_idea_fits(candidate_name: str, profile: dict | None) -> bool:
    if not profile or profile.get("gender") != "man":
        return True
    return not any(w in candidate_name.lower() for w in WOMENSWEAR)
