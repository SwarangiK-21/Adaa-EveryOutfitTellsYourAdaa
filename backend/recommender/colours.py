"""Colour names, colour families and simple colour-harmony rules.

Users type colours freely ("Sage green", "daimond", "Off-white"), so we match
known colour words, with a little typo tolerance.
"""
import difflib
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Colour:
    name: str        # canonical name, e.g. "sage"
    hue: int | None  # position on the colour wheel (0-359); None for neutrals and metallics
    kind: str        # "neutral", "metallic", "bright", "pastel", "dark", "earthy" or "multi"

    @property
    def label(self) -> str:
        return self.name.capitalize()


# name: (hue, kind)
_COLOURS = {
    # Neutrals go with almost anything.
    "black": (None, "neutral"), "white": (None, "neutral"), "off white": (None, "neutral"),
    "ivory": (None, "neutral"), "cream": (None, "neutral"), "beige": (None, "neutral"),
    "grey": (None, "neutral"), "charcoal": (None, "neutral"), "navy": (None, "neutral"),
    "tan": (None, "neutral"), "brown": (None, "neutral"), "khaki": (None, "neutral"),
    "nude": (None, "neutral"), "camel": (None, "neutral"), "taupe": (None, "neutral"),
    "denim": (None, "neutral"),
    # Metallics (mostly jewellery).
    "gold": (None, "metallic"), "silver": (None, "metallic"), "rose gold": (None, "metallic"),
    "bronze": (None, "metallic"), "copper": (None, "metallic"), "diamond": (None, "metallic"),
    # Colours with a place on the colour wheel.
    "red": (0, "bright"), "crimson": (350, "bright"), "maroon": (350, "dark"),
    "wine": (345, "dark"), "burgundy": (345, "dark"), "coral": (15, "bright"),
    "rust": (20, "earthy"), "peach": (25, "pastel"), "orange": (30, "bright"),
    "mustard": (45, "earthy"), "yellow": (55, "bright"), "lemon": (55, "pastel"),
    "olive": (75, "earthy"), "lime": (80, "bright"), "sage": (110, "earthy"),
    "green": (120, "bright"), "emerald": (140, "dark"), "bottle green": (140, "dark"),
    "mint": (150, "pastel"), "teal": (180, "bright"), "turquoise": (175, "bright"),
    "aqua": (180, "bright"), "sky blue": (200, "pastel"), "powder blue": (205, "pastel"),
    "blue": (220, "bright"), "royal blue": (225, "bright"), "cobalt": (220, "bright"),
    "lavender": (270, "pastel"), "lilac": (280, "pastel"), "purple": (280, "bright"),
    "violet": (275, "bright"), "plum": (300, "dark"), "magenta": (310, "bright"),
    "fuchsia": (315, "bright"), "hot pink": (325, "bright"), "pink": (335, "bright"),
    "baby pink": (340, "pastel"), "rose": (340, "pastel"), "blush": (345, "pastel"),
    "onion pink": (345, "pastel"),
    "multi": (None, "multi"),
}

_ALIASES = {
    "gray": "grey", "golden": "gold", "oxidised": "silver", "oxidized": "silver",
    "kundan": "gold", "pearl": "white", "moti": "white", "offwhite": "off white",
    "multicolour": "multi", "multicolor": "multi", "multicoloured": "multi",
    "printed": "multi", "floral": "multi",
}

# Hindi / Hinglish colour words ("lal", "peela", "hara"...).
HINDI = {
    "lal": "red", "laal": "red", "peela": "yellow", "pila": "yellow", "peeli": "yellow", "pili": "yellow",
    "hara": "green", "hari": "green", "neela": "blue", "nila": "blue", "neeli": "blue", "nili": "blue",
    "kaala": "black", "kala": "black", "kaali": "black", "safed": "white", "safaid": "white",
    "gulabi": "pink", "narangi": "orange", "kesari": "orange", "baingani": "purple", "jamuni": "purple",
    "bhura": "brown", "bhoora": "brown", "sunehra": "gold", "sunehri": "gold", "chandi": "silver",
    "aasmani": "sky blue", "asmani": "sky blue", "mehroon": "maroon",
    "saffron": "orange", "bhagwa": "orange",
}
_ALIASES.update(HINDI)

_DARK_NEUTRALS = {"black", "charcoal", "navy", "brown"}
_SOFT_NEUTRALS = {"white", "off white", "ivory", "cream", "beige", "nude"}


def parse(text: str, fuzzy: bool = True) -> Colour | None:
    """Turn free text like 'Sage green' into a Colour, or None if unknown.

    fuzzy=True also accepts near-misses ("daimond"); turn it off for
    sentences, where ordinary words like "tank" could look like "tan".
    """
    words = re.sub(r"[^a-z ]", " ", (text or "").lower()).split()
    if not words:
        return None
    words = [_ALIASES.get(w, w) for w in words]
    cleaned = " ".join(words)

    # The first colour word is usually the specific one: "sage green" -> sage,
    # "navy blue" -> navy. On a tie, prefer the longer name: "bottle green" over "bottle".
    found = []
    for name in _COLOURS:
        match = re.search(rf"\b{name}\b", cleaned)
        if match:
            found.append((match.start(), -len(name), name))
    if found:
        return _make(min(found)[2])

    # Typo tolerance: "daimond" -> "diamond", "blak" -> "black".
    for word in words if fuzzy else []:
        close = difflib.get_close_matches(word, list(_COLOURS) + list(_ALIASES), n=1, cutoff=0.8)
        if close:
            return _make(_ALIASES.get(close[0], close[0]))
    return None


def _make(name: str) -> Colour:
    hue, kind = _COLOURS[name]
    return Colour(name, hue, kind)


def _hue_distance(a: int, b: int) -> int:
    d = abs(a - b) % 360
    return min(d, 360 - d)


def same_family(a: Colour | None, b: Colour | None) -> bool:
    """Is colour b close enough to colour a to count as 'the same colour'?"""
    if a is None or b is None:
        return False
    if a.name == b.name:
        return True
    return a.hue is not None and b.hue is not None and _hue_distance(a.hue, b.hue) <= 20


def harmony(a: Colour | None, b: Colour | None) -> tuple[float, str | None]:
    """How well two colours go together: (points, short explanation)."""
    if a is None or b is None or "multi" in (a.kind, b.kind):
        return 0.0, None
    if a.kind == "metallic" or b.kind == "metallic":
        return 0.5, None
    if a.hue is None and b.hue is None:
        if {a.name, b.name} == {"black", "white"}:
            return 1.5, "Black and white is a timeless pairing"
        if a.name == b.name:
            return 1.25, f"A sleek all-{a.name} look"
        return 1.0, f"{a.label} and {b.name} are easy neutrals together"
    if a.hue is None or b.hue is None:
        neutral, colour = (a, b) if a.hue is None else (b, a)
        return 1.0, f"{neutral.label} keeps the {colour.name} grounded"

    if a.name == b.name:
        return 1.25, f"A tonal {a.name} look"
    d = _hue_distance(a.hue, b.hue)
    if d <= 30:
        return 1.0, f"{a.label} and {b.name} are tonal, close shades"
    if d <= 60:
        return 0.75, f"{a.label} and {b.name} sit side by side on the colour wheel"
    if 150 <= d <= 210:
        return 0.5, f"{a.label} and {b.name} make a bold contrast"
    if a.kind == "bright" and b.kind == "bright":
        return -1.5, f"{a.label} and {b.name} may clash"
    return -0.5, f"{a.label} and {b.name} are an unusual mix"


# Colour moods offered on the Preferences page.
def matches_mood(colour: Colour | None, mood: str | None) -> bool:
    if colour is None or not mood:
        return False
    if mood == "Neutrals & earth tones":
        return colour.kind in ("neutral", "earthy")
    if mood == "Bright & playful":
        return colour.kind == "bright"
    if mood == "Pastels":
        return colour.kind == "pastel" or colour.name in _SOFT_NEUTRALS
    if mood == "Dark & dramatic":
        return colour.kind == "dark" or colour.name in _DARK_NEUTRALS
    return False
