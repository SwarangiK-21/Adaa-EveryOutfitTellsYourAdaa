"""Wedding week (and other multi-function events): a different look for every function, following
the usual dress codes, from the user's own wardrobe. Uses the trip planner's no-repeat search.

Dress codes are common North/West Indian customs, used as gentle preferences: pieces in the
function's colours score higher, and colours usually avoided (all-white or all-black at the
ceremony) score lower. Nothing is ruled out, and every choice is explained.
"""
from recommender import garments as g
from recommender.planner import DaySpec, plan_days

_JEWELLERY_SLOTS = (g.FOOTWEAR, g.EARRINGS, g.NECKLACE, g.WRIST, g.BAG)
_CASUAL = ("jeans", "shorts", "t shirt", "tshirt", "tee", "hoodie", "sweatshirt")
DRESSY = {"wedding", "reception", "engagement", "cocktail"}   # casual pieces are a poor fit here

# key: (label, occasions (tagged for any counts), style, comfort, colours, avoid, dress code)
FUNCTIONS = {
    "haldi": ("Haldi", ("Traditional function", "Wedding", "Festive"), "Traditional", "Comfort first",
              ("yellow", "mustard", "lemon", "orange"), (),
              "Yellow, mustard or orange; light and comfy (haldi gets messy!)"),
    "mehendi": ("Mehendi", ("Traditional function", "Wedding", "Festive"), None, "Comfort first",
                ("green", "bottle green", "olive", "sage", "mint", "emerald", "teal"), (),
                "Greens and bright florals; comfy enough to sit in for hours"),
    "sangeet": ("Sangeet", ("Wedding", "Party", "Festive"), "Indo-Western", None,
                ("pink", "magenta", "fuchsia", "purple", "royal blue", "gold", "silver"), (),
                "Bright, sparkly and easy to dance in"),
    "cocktail": ("Cocktail", ("Party", "Wedding"), "Western", "A polished look",
                 ("black", "navy", "wine", "emerald", "silver", "gold"), (),
                 "Evening glam: dark tones or metallics"),
    "engagement": ("Engagement / Roka", ("Wedding", "Traditional function", "Party"), None, "A polished look",
                   ("pink", "peach", "lavender", "rose", "gold", "blush"), (),
                   "Soft pastels or rosy tones"),
    "wedding": ("Wedding ceremony", ("Wedding", "Traditional function"), "Traditional", "A polished look",
                ("red", "maroon", "pink", "magenta", "gold", "orange", "wine"), ("white", "black"),
                "Rich traditional wear in red, pink or gold; avoid all-white and all-black"),
    "reception": ("Reception", ("Wedding", "Party", "Formal"), None, "A polished look",
                  ("wine", "navy", "emerald", "gold", "silver", "black", "pastel"), (),
                  "An elegant evening look: a gown, saree or something dressy"),
    "puja": ("Puja / Griha pravesh", ("Traditional function", "Festive"), "Traditional", None,
             ("yellow", "red", "orange", "cream", "white", "green"), (),
             "Simple, graceful traditional wear"),
}
FULL_WEDDING = ["haldi", "mehendi", "sangeet", "wedding", "reception"]


def function_list() -> list[dict]:
    return [{"key": k, "label": f[0], "dress_code": f[6], "colours": list(f[4])} for k, f in FUNCTIONS.items()]


def plan_event(items: list[dict], functions: list[str], style: str | None = None) -> dict:
    """A different look for each function, in the order given. style (optional) overrides each
    function's usual style."""
    specs = []
    for key in functions:
        label, occasions, usual_style, comfort, wanted, avoid, code = FUNCTIONS[key]
        specs.append(DaySpec(occasions, label, style=style or usual_style, comfort=comfort,
                             colours=wanted, avoid=avoid, too_casual=_CASUAL if key in DRESSY else (),
                             dress_code=code, slots=_JEWELLERY_SLOTS))
    return plan_days(items, specs, unit="function")
