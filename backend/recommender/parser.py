"""Turn a typed request ("Style my black crop top for a party") into styling filters.

Rule-based and local: we look for known words and phrases, and match
"my ..." references against the user's own wardrobe items. Nothing is sent
to an outside service. Hinglish works too: "Aaj college ke liye kuch comfy",
"Shaadi ke liye kuch lal aur bhaari" (Hindi colour words live in colours.py).
"""
import difflib
import re
from datetime import date

from recommender import colours, festivals, garments as g

# Phrases are matched longest-first, so "family function" wins over "function".
OCCASION_WORDS = {
    "Wedding": ["wedding", "shaadi", "shadi", "marriage", "sangeet", "mehendi", "mehndi",
                "haldi", "reception", "engagement", "baraat", "vivah", "byah", "roka", "sagai"],
    "Traditional function": ["traditional function", "family function", "function", "puja",
                             "pooja", "ceremony", "temple", "griha pravesh", "satyanarayan",
                             "mandir", "katha", "havan"],
    "Festive": ["festive", "festival", "diwali", "navratri", "garba", "dandiya", "eid", "holi",
                "ganpati", "ganesh chaturthi", "durga puja", "onam", "pongal", "rakhi",
                "raksha bandhan", "christmas", "lohri", "gudi padwa", "tyohar", "tyohaar",
                "tyauhar", "dussehra", "dussera", "dasara", "bhai dooj", "dhanteras", "karva chauth",
                "karwa chauth", "chhath", "janmashtami", "teej"],
    "Party": ["party", "birthday", "night out", "club", "clubbing", "cocktail", "celebration",
              "farewell", "freshers"],
    "Formal": ["formal", "interview", "conference", "seminar", "presentation", "viva"],
    "Office": ["office", "work", "workplace", "meeting", "internship", "daftar", "naukri"],
    "College": ["college", "class", "classes", "campus", "lecture", "university", "uni", "school"],
    "Date": ["dinner date", "date", "romantic", "anniversary"],
    "Travel": ["travel", "trip", "vacation", "holiday", "flight", "airport", "road trip", "journey",
               "safar", "yatra"],
    "Casual": ["casual", "everyday", "daily", "hangout", "hang out", "shopping", "brunch",
               "outing", "movie", "movies", "mall", "errands", "ghoomne", "ghumne", "bahar",
               "ghar pe", "ghar par", "dosto ke saath", "doston ke saath"],
}

STYLE_WORDS = {
    "Indo-Western": ["indo western", "indowestern", "fusion"],
    "Traditional": ["traditional", "ethnic", "desi", "indian"],
    "Western": ["western"],
}

COMFORT_WORDS = {
    "Comfort first": ["comfortable", "comfy", "comfort", "cozy", "cosy", "relaxed", "easy",
                      "flat", "flats", "no heels", "aaram", "araam", "aaramdayak", "halka", "halki"],
    "A polished look": ["polished", "elegant", "classy", "glam", "glamorous", "dressy", "chic",
                        "sophisticated", "stylish", "fancy", "bhaari", "bhari", "heavy", "grand",
                        "shandaar", "shandar", "jhakaas"],
}

MOOD_WORDS = {
    "Pastels": ["pastel", "pastels", "soft colours", "soft colors"],
    "Bright & playful": ["bright", "colourful", "colorful", "playful", "vibrant", "fun colours",
                         "rangeen", "chamakdaar", "chatak"],
    "Dark & dramatic": ["dark", "dramatic", "moody", "gehra", "gehre"],
    "Neutrals & earth tones": ["neutral", "neutrals", "earthy", "earth tones", "minimal", "subtle"],
}

# Words that never identify a wardrobe item on their own.
_IGNORE = {
    "style", "styling", "me", "my", "mine", "a", "an", "the", "for", "to", "with", "and", "or",
    "in", "on", "of", "at", "it", "this", "that", "some", "something", "outfit", "outfits",
    "look", "looks", "wear", "wearing", "want", "need", "what", "should", "can", "i", "im",
    "please", "help", "suggest", "give", "show", "make", "go", "going", "get", "dress", "up",
    "dressed", "new", "nice", "pretty", "cute", "good", "best", "today", "tomorrow", "tonight",
    "weekend", "next", "family", "around", "build", "using", "use", "pair", "match", "matching",
    "piece", "pieces", "item", "items", "one", "like", "would", "love", "be", "is", "am", "are",
    # Hinglish filler words
    "aaj", "kal", "ke", "ki", "ka", "ko", "se", "liye", "lie", "kuch", "kuchh", "mera", "meri", "mere",
    "mujhe", "chahiye", "pehen", "pehnu", "pehnoon", "pehenna", "pehnna", "pehne", "kya", "ek", "aur",
    "bhi", "wala", "wali", "waala", "waali", "sa", "si", "koi", "hai", "ho", "karo", "batao", "bata",
    "dikhao", "dena", "accha", "achha", "acha", "sundar", "mast", "saath", "sath", "par", "pe", "main",
    "mein", "jaana", "jana", "jaa", "ja", "rahi", "raha", "hoon", "hu", "tha", "thi", "abhi", "please",
}


def _clean(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", text.lower().replace("-", " ")).split())


def _find_phrase(text: str, table: dict[str, list[str]]) -> tuple[str | None, str | None]:
    """Return (value, matched phrase) for the earliest, then longest, phrase found."""
    best = None
    for value, phrases in table.items():
        for phrase in phrases:
            m = re.search(rf"\b{re.escape(phrase)}\b", text)
            if m:
                key = (m.start(), -len(phrase))
                if best is None or key < best[0]:
                    best = (key, value, phrase)
    return (best[1], best[2]) if best else (None, None)


def _find_festival(text: str) -> tuple[festivals.Festival | None, str | None]:
    """The festival named in the text, if any, and the words that named it. Small typos are fine
    ("ganesh chaturti", "sankranthi"); short names (holi, eid, teej) must be exact."""
    words = text.split()
    best = None
    for f in festivals.FESTIVALS.values():
        for alias in f.aliases:
            n = len(alias.split())
            for i in range(len(words) - n + 1):
                window = " ".join(words[i:i + n])
                exact = window == alias
                if not exact and (len(alias) < 6
                                  or difflib.SequenceMatcher(None, window, alias).ratio() < 0.86):
                    continue
                key = (not exact, i, -len(alias))
                if best is None or key < best[0]:
                    best = (key, f, window)
    return (best[1], best[2]) if best else (None, None)


def _remove(text: str, phrase: str | None) -> str:
    return re.sub(rf"\b{re.escape(phrase)}\b", " ", text, count=1) if phrase else text


def _words_match(word: str, target: str) -> bool:
    if word == target:
        return True
    # Small typo tolerance for longer words ("sandels" -> "sandals"), plus plurals.
    if word.rstrip("s") == target.rstrip("s"):
        return True
    return len(word) >= 4 and difflib.SequenceMatcher(None, word, target).ratio() >= 0.85


def _match_items(words: list[str], items: list[dict]) -> tuple[list[dict], set[str]]:
    """Find the wardrobe item(s) the user is talking about. Returns (best items, used words)."""
    scored = []
    for item in items:
        # Words that name the item, minus colours: "black" alone shouldn't pick "black sandals".
        def nouns(text):
            return {w for w in _clean(text).split()
                    if w not in _IGNORE and colours.parse(w, fuzzy=False) is None}
        name_words, type_words = nouns(item["name"]), nouns(item["item_type"])
        colour_words = set(_clean(item["colour"]).split())
        used, points = set(), 0.0
        for w in words:
            # A word from the item's own name counts more than one from its type:
            # "my gown" means the piece named "gown" over another piece of type Gown.
            if any(_words_match(w, n) for n in name_words):
                used.add(w)
                points += 2
            elif any(_words_match(w, n) for n in type_words):
                used.add(w)
                points += 1
        if not used:
            continue  # a colour alone ("something black") doesn't point at one item
        for w in words:
            if w not in used and any(_words_match(w, c) for c in colour_words):
                used.add(w)
                points += 1
        scored.append((points, item, used))
    if not scored:
        return [], set()
    top = max(s[0] for s in scored)
    best = [s for s in scored if s[0] == top]
    return [s[1] for s in best], set().union(*(s[2] for s in best))


def parse_request(text: str, items: list[dict], today: date | None = None) -> dict:
    """Read a typed request. Returns filters plus what was understood and what's missing."""
    cleaned = _clean(text)
    result = {"occasion": None, "style": None, "colour": None, "colour_mood": None,
              "comfort": None, "anchor_item_id": None, "festival": None,
              "understood": [], "missing": [], "ambiguous": [], "not_found": []}

    # A festival or national day ("Republic Day", "ganesh chaturti") brings its own colours.
    festival, phrase = _find_festival(cleaned)
    rest = _remove(cleaned, phrase)
    if festival:
        result["festival"] = festival.key
        result["understood"].append(f"Festival: {festival.name} ({festival.colour_text})")

    occasion, phrase = _find_phrase(rest, OCCASION_WORDS)
    rest = _remove(rest, phrase)
    # "Diwali puja" is still Diwali; "Diwali party" is a party with Diwali colours.
    if festival and occasion in (None, "Traditional function", "Festive"):
        occasion = festival.occasion
    if occasion:
        result["occasion"] = occasion
        result["understood"].append(f"Occasion: {occasion}")

    for key, table, label in (("style", STYLE_WORDS, "Style"),
                              ("comfort", COMFORT_WORDS, "Comfort"),
                              ("colour_mood", MOOD_WORDS, "Colour mood")):
        value, phrase = _find_phrase(rest, table)
        if value:
            result[key] = value
            result["understood"].append(f"{label}: {value}")
            rest = _remove(rest, phrase)

    # Hindi colour words become English ones, so "hari kurti" finds your green kurti.
    rest = " ".join(colours.HINDI.get(w, w) for w in rest.split())
    words = [w for w in rest.split() if w not in _IGNORE]
    matches, used = _match_items(words, items)
    if len(matches) == 1:
        anchor = matches[0]
        result["anchor_item_id"] = anchor["id"]
        result["understood"].append(f"Building around your {anchor['name']}")
    elif len(matches) > 1:
        result["ambiguous"] = [{"id": m["id"], "name": m["name"]} for m in matches]
    else:
        # They named a kind of piece ("my green kurta") that isn't in the wardrobe: say so.
        named = [w for w in words if w in g.KNOWN_TYPE_WORDS]
        if named:
            colour_word = next((w for w in words if colours.parse(w, fuzzy=False)), None)
            piece = " ".join(([colour_word] if colour_word else []) + named)
            result["not_found"].append(piece)

    # A colour that wasn't part of naming an item is a colour preference.
    for i, w in enumerate(words):
        if w in used:
            continue
        # Two-word colours first ("sky blue", "bottle green"), then single words.
        pair = f"{w} {words[i + 1]}" if i + 1 < len(words) else ""
        colour = (colours.parse(pair, fuzzy=False) if pair else None)
        if not colour or colour.name != pair:
            colour = colours.parse(w, fuzzy=False)
        if colour and colour.kind != "multi":
            result["colour"] = colour.name
            result["understood"].append(f"Colour: {colour.name}")
            break

    if festival:
        # The festival's usual style, unless you asked for another; Navratri: today's colour.
        if not result["style"] and festival.style:
            result["style"] = festival.style
            result["understood"].append(f"Style: {festival.style} (usual for {festival.name})")
        todays = festivals.day_colour(festival.key, today or date.today())
        if todays and not result["colour"]:
            result["colour"] = todays[0]
            result["understood"].append(f"Today's {festival.name} colour: {todays[0]}")

    if not occasion:
        result["missing"].append("occasion")
    return result
