"""Rule-based outfit recommendations, built only from the user's own wardrobe.

How it works:
1. Classify every wardrobe item (top, bottom, footwear, earrings, ...).
2. Build outfit "bases": one-pieces (gown, saree...) or a top + a bottom that suit each other.
3. Score each base: occasion, style, colours, the user's preferences.
4. Add the best-matching footwear, jewellery, bag and accessory to each base.
5. Pick up to 4 outfits that are genuinely different from each other.
Every outfit only ever contains items that exist in the wardrobe.
"""
from collections import Counter
from dataclasses import dataclass, field
from itertools import combinations

from recommender import colours, garments as g

STYLE_CLASH = {frozenset({"Traditional", "Western"})}
MINIMAL_OCCASIONS = {"Casual", "College", "Office", "Travel"}
DRESSY_OCCASIONS = {"Party", "Festive", "Wedding", "Traditional function", "Date"}
REUSE_PENALTY = 1.5        # discourages repeating an accessory across outfits
BASE_OVERLAP_PENALTY = 1.0  # discourages repeating a garment across outfits
ACCESSORY_THRESHOLD = 1.0   # an accessory must score at least this to be added
SLOT_NAMES = {g.FOOTWEAR: "footwear", g.BAG: "bags"}


class RecommendationError(ValueError):
    """The request can't be served. The message is safe to show the user."""


@dataclass
class Piece:
    item: dict
    role: str | None
    type_key: str | None
    colour: colours.Colour | None
    tagged: bool  # tagged for the requested occasion

    @property
    def id(self) -> int:
        return self.item["id"]

    @property
    def name(self) -> str:
        return self.item["name"]

    @property
    def style(self) -> str:
        return self.item["style"]


@dataclass
class Outfit:
    pieces: list[Piece]
    score: float = 0.0
    reasons: list[tuple[float, str]] = field(default_factory=list)
    cautions: list[str] = field(default_factory=list)

    def add(self, points: float, reason: str | None = None) -> None:
        self.score += points
        if reason and points > 0:
            self.reasons.append((points, reason))
        elif reason and points < 0:
            self.cautions.append(reason)

    def copy(self) -> "Outfit":
        return Outfit(list(self.pieces), self.score, list(self.reasons), list(self.cautions))

    @property
    def ids(self) -> frozenset[int]:
        return frozenset(p.id for p in self.pieces)


# ---------- scoring helpers ----------

def _style_points(a: str, b: str) -> float:
    if a == b:
        return 0.5
    if frozenset({a, b}) in STYLE_CLASH:
        return -1.5
    return 0.0  # Indo-Western bridges both


def _request_points(piece: Piece, req, weight: float = 1.0) -> float:
    """How well a single piece matches what the user asked for."""
    points = 3.0 if piece.tagged else -1.5
    if req.style:
        if piece.style == req.style:
            points += 2.0
        elif frozenset({piece.style, req.style}) in STYLE_CLASH:
            points -= 2.0
        else:
            points += 0.5
    if req.colour and colours.same_family(colours.parse(req.colour), piece.colour):
        points += 2.0
    if colours.matches_mood(piece.colour, req.colour_mood):
        points += 0.75
    return points * weight


def _dominant_style(pieces: list[Piece]) -> str:
    styles = Counter(p.style for p in pieces)
    return styles.most_common(1)[0][0]


def _score_base(pieces: list[Piece], req, pair_fit: tuple[float, str] | None) -> Outfit:
    outfit = Outfit(pieces)
    for p in pieces:
        outfit.add(_request_points(p, req, weight=1.5))
    if pair_fit:
        outfit.add(*pair_fit)

    best_colour = None
    for a, b in combinations(pieces, 2):
        points, reason = colours.harmony(a.colour, b.colour)
        outfit.score += points
        if points < 0:
            outfit.cautions.append(reason)
        elif reason and (best_colour is None or points > best_colour[0]):
            best_colour = (points, reason)
        outfit.add(_style_points(a.style, b.style))
    if best_colour:
        outfit.reasons.append(best_colour)

    styles = {p.style for p in pieces}
    if len(styles) == 1:
        outfit.reasons.append((0.5, f"Consistent {styles.pop()} styling"))
    elif styles == {"Traditional", "Western"}:
        outfit.cautions.append("Mixes Traditional and Western pieces")
    if req.style and req.style not in {p.style for p in pieces}:
        outfit.cautions.append(f"Not {req.style}: you don't have a {req.style} option for this, "
                               "so this is the closest match")

    if all(p.tagged for p in pieces):
        outfit.reasons.append((3.0, f"Your {_join([p.name for p in pieces])} "
                                    f"{'is' if len(pieces) == 1 else 'are'} tagged for {req.occasion}"))
    if req.colour:
        wanted = colours.parse(req.colour)
        if any(colours.same_family(wanted, p.colour) for p in pieces):
            outfit.reasons.append((2.0, f"Features your preferred colour, {req.colour.lower()}"))
    if req.colour_mood and any(colours.matches_mood(p.colour, req.colour_mood) for p in pieces):
        outfit.reasons.append((0.75, f"Fits your '{req.colour_mood}' colour mood"))
    return outfit


def _addition_points(piece: Piece, outfit: Outfit, req, usage: Counter) -> float:
    """How well an accessory (or dupatta/layer) fits a given outfit."""
    points = _request_points(piece, req)
    base = [p for p in outfit.pieces if p.item["category"] == "Clothing"]
    if base:
        points += sum(colours.harmony(piece.colour, p.colour)[0] for p in base) / len(base)
        points += min(0.0, _style_points(piece.style, _dominant_style(base)))
    points -= REUSE_PENALTY * usage[piece.id]

    if piece.role == g.FOOTWEAR:
        if req.comfort == "Comfort first":
            points += 1.0 if piece.type_key in g.FLAT_FOOTWEAR else (-2.0 if piece.type_key in g.HEELED_FOOTWEAR else 0)
        elif req.comfort == "A polished look" and piece.type_key in g.HEELED_FOOTWEAR:
            points += 0.75
        if piece.type_key in g.ETHNIC_FOOTWEAR and base and _dominant_style(base) == "Traditional":
            points += 0.75
    if piece.role == g.BAG:
        if piece.type_key in g.DRESSY_BAGS:
            points += 0.5 if req.occasion in DRESSY_OCCASIONS else -0.5
        elif piece.type_key in g.EVERYDAY_BAGS:
            points += 0.5 if req.occasion in MINIMAL_OCCASIONS else -0.5
    return points


def _metal(piece: Piece) -> str | None:
    if piece.colour and piece.colour.kind == "metallic":
        return "silver" if piece.colour.name in ("silver", "diamond") else piece.colour.name
    return None


# ---------- building outfits ----------

def _join(names: list[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def _prepare(item: dict, occasion: str) -> Piece:
    role, key = g.classify(item)
    return Piece(item, role, key, colours.parse(item["colour"]), occasion in item["occasions"])


def _base_outfits(clothes: list[Piece], req, anchor: Piece | None, strict: bool) -> list[Outfit]:
    def usable(p: Piece) -> bool:
        return p.tagged or not strict or (anchor is not None and p.id == anchor.id)

    by_role: dict[str, list[Piece]] = {}
    for p in clothes:
        if usable(p):
            by_role.setdefault(p.role, []).append(p)

    bases = [_score_base([p], req, None) for p in by_role.get(g.ONE_PIECE, [])]
    for top in by_role.get(g.TOP, []):
        for bottom in by_role.get(g.BOTTOM, []):
            fit = g.top_bottom_fit(top.type_key, bottom.type_key)
            if fit is not None:
                bases.append(_score_base([top, bottom], req, fit))
    # A blouse can also be the top half with a skirt (lehenga-style).
    for blouse in by_role.get(g.BLOUSE, []):
        for bottom in by_role.get(g.BOTTOM, []):
            if bottom.type_key == "skirt":
                bases.append(_score_base([blouse, bottom], req, (0.5, "A blouse and skirt in lehenga style")))

    if anchor and anchor.item["category"] == "Clothing" and anchor.role in (g.ONE_PIECE, g.TOP, g.BOTTOM, g.BLOUSE):
        bases = [b for b in bases if anchor.id in b.ids]
    return bases


def _complete(base: Outfit, wardrobe: list[Piece], req, usage: Counter, anchor: Piece | None) -> Outfit:
    """Add matching blouse/dupatta/layer, footwear, jewellery, bag and accessory to a base."""
    outfit = base.copy()
    main = {p.type_key for p in base.pieces}

    def best(role: str, threshold: float, require_tag: bool = True) -> Piece | None:
        if anchor and anchor.role == role and anchor.id not in outfit.ids:
            return anchor  # the user asked for this piece: always include it
        # Only add pieces the user tagged for this occasion (the user's own judgement wins).
        options = [(_addition_points(p, outfit, req, usage), p) for p in wardrobe
                   if p.role == role and (p.tagged or not require_tag) and p.id not in outfit.ids]
        options = [o for o in options if o[0] >= threshold]
        return max(options, key=lambda o: (o[0], -o[1].id))[1] if options else None

    def include(piece: Piece | None, reason: str | None = None) -> None:
        if piece is None:
            return
        points = _addition_points(piece, outfit, req, usage) * 0.5
        outfit.score += points
        if reason:
            outfit.reasons.append((max(points, 0.5), reason))
        outfit.pieces.append(piece)

    # Pieces that complete a garment.
    if main & {"saree", "sari", "lehenga"}:
        blouse = best(g.BLOUSE, -99, require_tag=False)  # a saree needs a blouse, tagged or not
        include(blouse, f"Paired with your {blouse.name}" if blouse else None)
        if blouse is None:
            outfit.cautions.append("Add a saree/lehenga blouse to your wardrobe to complete this look")
    if main & (g.ETHNIC_TOPS | {"lehenga", "anarkali"}):
        dupatta = best(g.DUPATTA, ACCESSORY_THRESHOLD)
        include(dupatta, f"Your {dupatta.name} adds a traditional finish" if dupatta else None)
    if not main & {"saree", "sari", "lehenga"}:
        include(best(g.LAYER, ACCESSORY_THRESHOLD + 1.5))

    # Footwear, jewellery, bag, accessory.
    include(best(g.FOOTWEAR, ACCESSORY_THRESHOLD))
    max_jewellery = 2 if (req.occasion in MINIMAL_OCCASIONS or req.comfort == "Comfort first") else 3
    metals = []
    for slot in (g.EARRINGS, g.NECKLACE, g.WRIST, g.JEWELLERY):
        if sum(p.item["category"] == "Jewellery" for p in outfit.pieces) >= max_jewellery:
            break
        piece = best(slot, ACCESSORY_THRESHOLD)
        if piece and metals and _metal(piece) and _metal(piece) not in metals and piece is not anchor:
            continue  # keep metals consistent (gold with gold, silver with silver)
        if piece and _metal(piece):
            metals.append(_metal(piece))
        include(piece)
    if len(set(metals)) == 1 and len(metals) >= 2:
        outfit.reasons.append((0.5, f"{metals[0].capitalize()} jewellery keeps the metals consistent"))
    include(best(g.BAG, ACCESSORY_THRESHOLD))
    include(best(g.ACCESSORY, ACCESSORY_THRESHOLD + 0.5))
    if anchor and anchor.id not in outfit.ids:
        include(anchor)  # e.g. a dupatta or jewellery the user asked for that no rule above added

    shoes = next((p for p in outfit.pieces if p.role == g.FOOTWEAR), None)
    if shoes and req.comfort == "Comfort first" and shoes.type_key in g.FLAT_FOOTWEAR:
        outfit.reasons.append((1.0, f"Your {shoes.name} keep it comfortable"))
    if anchor and anchor.id in outfit.ids:
        outfit.reasons.append((10.0, f"Built around your {anchor.name}"))
    return outfit


def recommend(items: list[dict], req) -> dict:
    """Return up to req.count distinct outfits using only these wardrobe items."""
    wardrobe = [_prepare(item, req.occasion) for item in items]
    notes: list[str] = []

    anchor = None
    if req.anchor_item_id is not None:
        anchor = next((p for p in wardrobe if p.id == req.anchor_item_id), None)
        if anchor is None:
            raise RecommendationError("That piece is no longer in your wardrobe.")
        if anchor.role is None:
            raise RecommendationError(
                f"Adaa doesn't know how to style a '{anchor.item['item_type']}' yet. "
                "Try editing its type (e.g. Kurta, Top, Jeans, Saree).")
        if not anchor.tagged:
            notes.append(f"Your {anchor.name} isn't tagged for {req.occasion}, "
                         "but it's included because you asked for it.")

    clothes = [p for p in wardrobe if p.item["category"] == "Clothing"]
    unknown = [p for p in clothes if p.role is None]
    if unknown:
        notes.append("Adaa couldn't tell how to wear: "
                     + _join([f"{p.name} (type '{p.item['item_type']}')" for p in unknown])
                     + ". Edit their type to include them.")

    relaxed = False
    bases = _base_outfits(clothes, req, anchor, strict=True)
    if not bases:
        bases = _base_outfits(clothes, req, anchor, strict=False)
        relaxed = bool(bases)
        if relaxed:
            notes.insert(0, f"None of your clothes make a complete outfit tagged for {req.occasion}, "
                            "so these are the closest matches from your wardrobe.")
    if not bases:
        notes.insert(0, _why_no_outfits(clothes, anchor))
        return {"outfits": [], "notes": notes, "relaxed": False}

    # Pick outfits one at a time, preferring ones that differ from those already chosen.
    chosen: list[Outfit] = []
    usage: Counter = Counter()
    remaining = sorted(bases, key=lambda b: (-b.score, sorted(b.ids)))
    while remaining and len(chosen) < req.count:
        best_pick = None
        for base in remaining:
            outfit = _complete(base, wardrobe, req, usage, anchor)
            overlap = sum(1 for i in base.ids if usage[i])
            total = outfit.score - BASE_OVERLAP_PENALTY * overlap
            if best_pick is None or total > best_pick[0]:
                best_pick = (total, base, outfit)
        _, base, outfit = best_pick
        remaining.remove(base)
        chosen.append(outfit)
        usage.update(outfit.ids)

    if len(chosen) < req.count:
        notes.append(f"Only {len(chosen)} distinct outfit{'s' if len(chosen) != 1 else ''} "
                     f"{'is' if len(chosen) == 1 else 'are'} possible from your wardrobe for this request. "
                     f"Add more clothes tagged for {req.occasion} for more variety.")
    notes.extend(_missing_slot_notes(wardrobe, chosen, req.occasion))

    return {
        "outfits": [
            {
                "rank": rank,
                "score": round(o.score, 1),
                "pieces": [{"role": p.role, "item": p.item} for p in o.pieces],
                "reasons": [r for _, r in sorted(o.reasons, key=lambda r: -r[0])][:4],
                "cautions": list(dict.fromkeys(o.cautions)),
            }
            for rank, o in enumerate(chosen, start=1)
        ],
        "notes": notes,
        "relaxed": relaxed,
    }


def _why_no_outfits(clothes: list[Piece], anchor: Piece | None) -> str:
    if not clothes:
        return "Add some clothes to your wardrobe first (a kurta, a top and jeans, a saree...)."
    if anchor and anchor.item["category"] == "Clothing":
        return (f"Adaa couldn't find anything in your wardrobe to complete your {anchor.name}. "
                "Try adding a matching top or bottom.")
    roles = {p.role for p in clothes}
    if g.TOP in roles and g.BOTTOM not in roles:
        return "Your wardrobe has tops but no bottoms yet. Add jeans, a skirt, a salwar or palazzos."
    if g.BOTTOM in roles and g.TOP not in roles:
        return "Your wardrobe has bottoms but no tops yet. Add a top, shirt or kurta."
    return "Adaa couldn't build a complete outfit from your clothes yet. Add a top and bottom, or a dress/saree."


def _missing_slot_notes(wardrobe: list[Piece], chosen: list[Outfit], occasion: str) -> list[str]:
    notes = []
    used_roles = {p.role for o in chosen for p in o.pieces}
    for role, label in SLOT_NAMES.items():
        owned = [p for p in wardrobe if p.role == role]
        if not owned:
            notes.append(f"You haven't added any {label} yet. Outfits will be more complete with some.")
        elif role not in used_roles:
            notes.append(f"None of your {label} are tagged for {occasion}, so outfits don't include any.")
    jewellery = [p for p in wardrobe if p.item["category"] == "Jewellery"]
    if jewellery and not any(p.item["category"] == "Jewellery" for o in chosen for p in o.pieces):
        notes.append(f"None of your jewellery is tagged for {occasion}, so outfits don't include any.")
    return notes


# ---------- checking a given outfit, and suggesting swaps (Phase 5) ----------

_CORE_ROLES = (g.ONE_PIECE, g.TOP, g.BOTTOM, g.BLOUSE)


def evaluate(items: list[dict], item_ids: list[int], req) -> dict:
    """Score and explain an outfit made of these wardrobe items (e.g. after a swap)."""
    by_id = {i["id"]: i for i in items}
    pieces = [_prepare(by_id[i], req.occasion) for i in item_ids if i in by_id]
    core = [p for p in pieces if p.item["category"] == "Clothing" and p.role in _CORE_ROLES]
    others = [p for p in pieces if p not in core]

    fit = None
    tops = [p for p in core if p.role in (g.TOP, g.BLOUSE)]
    bottoms = [p for p in core if p.role == g.BOTTOM]
    clash = None
    if len(tops) == 1 and len(bottoms) == 1:
        fit = g.top_bottom_fit(tops[0].type_key, bottoms[0].type_key)
        if fit is None:
            clash = f"{tops[0].name} and {bottoms[0].name} don't usually go together"

    outfit = _score_base(core, req, fit) if core else Outfit([])
    for p in others:
        outfit.score += _addition_points(p, outfit, req, Counter()) * 0.5
        outfit.pieces.append(p)

    cautions = list(outfit.cautions)
    if clash:
        cautions.insert(0, clash)
    roles = {p.role for p in core}
    if not core:
        cautions.insert(0, "This look has no clothing in it")
    elif g.ONE_PIECE not in roles and not ({g.TOP, g.BLOUSE} & roles and g.BOTTOM in roles):
        cautions.insert(0, "This look needs a top and a bottom, or a one-piece")
    untagged = [p.name for p in pieces if not p.tagged]
    if untagged:
        cautions.append(f"Not tagged for {req.occasion}: {_join(untagged)}")

    return {
        "score": round(outfit.score, 1),
        "pieces": [{"role": p.role or "Piece", "item": p.item} for p in outfit.pieces],
        "reasons": [r for _, r in sorted(outfit.reasons, key=lambda r: -r[0])][:4],
        "cautions": list(dict.fromkeys(cautions)),
    }


def alternatives(items: list[dict], item_ids: list[int], replace_id: int, req, limit: int = 6) -> list[dict]:
    """Other wardrobe pieces that could replace one piece of an outfit, best first."""
    by_id = {i["id"]: i for i in items}
    if replace_id not in item_ids or replace_id not in by_id:
        raise RecommendationError("That piece isn't part of this outfit any more.")
    current = [_prepare(by_id[i], req.occasion) for i in item_ids if i in by_id]
    target = next(p for p in current if p.id == replace_id)
    if target.role is None:
        raise RecommendationError(f"Adaa doesn't know what kind of piece '{target.name}' is, "
                                  "so it can't suggest swaps. Try editing its type.")
    rest = [p for p in current if p.id != replace_id]
    bottom = next((p for p in rest if p.role == g.BOTTOM), None)
    top = next((p for p in rest if p.role == g.TOP), None)
    main_colour = next((p.colour for p in rest if p.item["category"] == "Clothing"), None)

    options = []
    for item in items:
        if item["id"] in item_ids:
            continue
        cand = _prepare(item, req.occasion)
        if cand.role != target.role:
            continue
        # Keep the outfit wearable: a new top must still go with the bottom, and vice versa.
        if cand.role == g.TOP and bottom and g.top_bottom_fit(cand.type_key, bottom.type_key) is None:
            continue
        if cand.role == g.BOTTOM and top and g.top_bottom_fit(top.type_key, cand.type_key) is None:
            continue
        swapped = [cand.id if i == replace_id else i for i in item_ids]
        score = evaluate(items, swapped, req)["score"]
        reason = f"Tagged for {req.occasion}" if cand.tagged else f"Not tagged for {req.occasion}"
        colour_points, colour_reason = colours.harmony(cand.colour, main_colour)
        if colour_reason and colour_points > 0:
            reason += f" · {colour_reason}"
        options.append({"item": item, "role": cand.role, "tagged": cand.tagged,
                        "reason": reason, "score": score})

    options.sort(key=lambda o: (not o["tagged"], -o["score"], o["item"]["id"]))
    return options[:limit]
