"""Wardrobe planning on top of the outfit engine: what to buy next, and what to pack for a trip
(an outfit per day, no garment worn twice).

Both only use the rules the stylist already uses (roles, top/bottom fit, colour harmony,
occasion tags), so their advice matches the outfits Adaa actually suggests.
"""
from collections import Counter
from datetime import date
from dataclasses import dataclass

from recommender import colours, engine, garments as g
from wardrobe_options import OCCASIONS


@dataclass
class _Req:
    """The minimum the engine's scoring needs to know about a request."""
    occasion: str
    style: str | None = None
    colour: str | None = None
    colour_mood: str | None = None
    comfort: str | None = None


def _harmonious(pieces) -> bool:
    return all(colours.harmony(a.colour, b.colour)[0] >= 0
               for i, a in enumerate(pieces) for b in pieces[i + 1:])


def _bases(wardrobe_items: list[dict], occasion: str, strict: bool = True) -> list[engine.Outfit]:
    """Wearable outfit bases (one-piece, or top + bottom) for an occasion, without colour clashes."""
    req = _Req(occasion)
    clothes = [engine._prepare(i, occasion) for i in wardrobe_items if i["category"] == "Clothing"]
    return [b for b in engine._base_outfits(clothes, req, None, strict=strict) if _harmonious(b.pieces)]


# ---------- What to buy next ----------

# Versatile pieces worth suggesting, with the occasions they are usually worn for.
# (name, category, type, colour, style, occasions)
CATALOGUE = [
    ("White sneakers", "Footwear", "Sneakers", "White", "Western", ["Casual", "College", "Travel"]),
    ("Black block heels", "Footwear", "Heels", "Black", "Western", ["Party", "Date", "Formal", "Office"]),
    ("Nude flats", "Footwear", "Flats", "Nude", "Indo-Western", ["Office", "College", "Casual", "Travel"]),
    ("Gold juttis", "Footwear", "Juttis", "Gold", "Traditional", ["Festive", "Wedding", "Traditional function"]),
    ("Blue jeans", "Clothing", "Jeans", "Denim", "Western", ["Casual", "College", "Travel", "Date"]),
    ("Black trousers", "Clothing", "Trousers", "Black", "Western", ["Office", "Formal", "College"]),
    ("Beige trousers", "Clothing", "Trousers", "Beige", "Western", ["Office", "Formal", "Casual"]),
    ("Black skirt", "Clothing", "Skirt", "Black", "Western", ["Party", "Date", "College"]),
    ("White shirt", "Clothing", "Shirt", "White", "Western", ["Office", "Formal", "College", "Casual"]),
    ("Black top", "Clothing", "Top", "Black", "Western", ["Party", "Date", "Casual", "College"]),
    ("White kurta", "Clothing", "Kurta", "White", "Traditional",
     ["Festive", "Traditional function", "Office", "Casual"]),
    ("White palazzo", "Clothing", "Palazzo", "White", "Indo-Western",
     ["Casual", "Office", "Festive", "Traditional function"]),
    ("Gold jhumkas", "Jewellery", "Jhumkas", "Gold", "Traditional", ["Festive", "Wedding", "Traditional function"]),
    ("Silver studs", "Jewellery", "Earrings", "Silver", "Western", ["Office", "College", "Casual", "Date", "Party"]),
    ("Black clutch", "Bags", "Clutch", "Black", "Western", ["Party", "Date", "Wedding", "Formal"]),
    ("Tan tote", "Bags", "Tote", "Tan", "Western", ["Office", "College", "Casual", "Travel"]),
    ("Gold potli", "Bags", "Potli", "Gold", "Traditional", ["Festive", "Wedding", "Traditional function"]),
]
_LABELS = {g.FOOTWEAR: "shoes", g.BAG: "bag", g.EARRINGS: "earrings"}


def _candidate(entry, index: int) -> dict:
    name, category, item_type, colour, style, occasions = entry
    return {"id": -(index + 1), "name": name, "category": category, "item_type": item_type,
            "colour": colour, "style": style, "occasions": occasions, "notes": ""}


_DENIM = {"denim", "blue", "sky blue", "powder blue", "navy", "royal blue", "cobalt"}


def _same_colour(a: colours.Colour | None, b: colours.Colour | None) -> bool:
    if a and b and a.name in _DENIM and b.name in _DENIM and "denim" in (a.name, b.name):
        return True   # "Denim" jeans and "Blue" jeans are the same thing
    return colours.same_family(a, b)


def _already_owned(candidate: dict, items: list[dict]) -> bool:
    role, key = g.classify(candidate)
    colour = colours.parse(candidate["colour"])
    for item in items:
        if item["category"] != candidate["category"]:
            continue
        r, k = g.classify(item)
        if r == role and (k == key or role in (g.BAG, g.EARRINGS)) and _same_colour(colours.parse(item["colour"]), colour):
            return True
    return False


def _join(words: list[str]) -> str:
    return words[0] if len(words) == 1 else ", ".join(words[:-1]) + " and " + words[-1]


def find_gaps(items: list[dict], limit: int = 6) -> dict:
    """Suggest the few purchases that would unlock the most new outfits from this wardrobe."""
    now = {o: _bases(items, o) for o in OCCASIONS}
    outfits_now = len({b.ids for bases in now.values() for b in bases})
    by_id = {i["id"]: i for i in items}
    suggestions = []

    for index, entry in enumerate(CATALOGUE):
        cand = _candidate(entry, index)
        if _already_owned(cand, items):
            continue
        role, _ = g.classify(cand)
        new_bases: dict[frozenset, set[str]] = {}
        if cand["category"] == "Clothing":
            for occasion in cand["occasions"]:
                before = {b.ids for b in now[occasion]}
                for b in _bases(items + [cand], occasion):
                    if b.ids not in before:
                        new_bases.setdefault(b.ids, set()).add(occasion)
            reason = "Pairs with {pieces} to make {n} new outfit{s} for {occ}"
        else:
            # Shoes, a bag or earrings complete outfits for occasions that have none tagged yet.
            colour = colours.parse(cand["colour"])
            for occasion in cand["occasions"]:
                has_one = any(occasion in i["occasions"] and g.classify(i)[0] == role for i in items)
                if has_one:
                    continue
                for b in now[occasion]:
                    if all(colours.harmony(colour, p.colour)[0] >= 0 for p in b.pieces):
                        new_bases.setdefault(b.ids, set()).add(occasion)
            if role == g.FOOTWEAR:
                reason = "Completes {n} outfit{s} that {have} no shoes tagged for {occ} yet"
            else:
                reason = "Adds a matching " + _LABELS.get(role, "piece") + " to {n} outfit{s} for {occ} (none of yours are tagged for it yet)"
        if not new_bases:
            continue
        occasions = [o for o in OCCASIONS if any(o in occ for occ in new_bases.values())]
        partners = sorted({i for ids in new_bases for i in ids if i > 0},
                          key=lambda i: -sum(i in ids for ids in new_bases))
        n = len(new_bases)
        partner_names = [by_id[i]["name"] for i in partners[:3]]
        suggestions.append({
            "name": cand["name"], "category": cand["category"], "item_type": cand["item_type"],
            "colour": cand["colour"], "new_outfits": n, "occasions": occasions,
            "reason": reason.format(n=n, s="" if n == 1 else "s", have="has" if n == 1 else "have", occ=_join(occasions),
                                    pieces="your " + _join(partner_names) + (" and more" if len(partners) > 3 else "")),
            "pairs_with": [by_id[i] for i in partners[:6]],
        })

    # Clothes and shoes make outfits possible; a bag or earrings only finish them off, so they come after.
    suggestions.sort(key=lambda s: (s["category"] not in ("Clothing", "Footwear"), -s["new_outfits"], s["name"]))
    picks = suggestions[:limit]
    # Outfits without shoes aren't really complete, so the best shoe idea always makes the list.
    shoes = next((s for s in suggestions if s["category"] == "Footwear"), None)
    if shoes and shoes not in picks and len(picks) == limit:
        picks[-1] = shoes

    counts = Counter()
    for item in items:
        role, _ = g.classify(item)
        counts[role or "Other"] += 1
    notes = []
    empty = [o for o in OCCASIONS if not now[o]]
    if items and empty:
        notes.append(f"No complete outfit is tagged for {_join(empty)} yet.")
    tops = counts[g.TOP] + counts[g.BLOUSE]
    bottoms = counts[g.BOTTOM]
    if tops >= 3 and bottoms and tops >= 3 * bottoms:
        notes.append(f"You have {tops} tops but only {bottoms} bottom{'s' if bottoms != 1 else ''}: "
                     "one more bottom multiplies your outfits.")
    elif bottoms >= 3 and tops and bottoms >= 3 * tops:
        notes.append(f"You have {bottoms} bottoms but only {tops} top{'s' if tops != 1 else ''}: "
                     "one more top multiplies your outfits.")

    return {
        "suggestions": picks,
        "outfits_now": outfits_now,
        "counts": {k: v for k, v in counts.items() if v},
        "notes": notes,
    }


# ---------- Trip packing (and event planning, which uses the same search) ----------

UNTAGGED_COST = 6.0    # using clothes not tagged for that day's occasion (only if nothing else fits)
REUSE_BONUS = 2.0      # shoes / bag / jewellery already in the suitcase are preferred
OPTIONS_PER_DAY = 12   # best outfits considered for each day
SEARCH_LIMIT = 60000   # steps of the search before settling for the best plan found
DRESS_CODE_BONUS = 3.0  # per garment in one of the day's dress-code colours
AVOID_COST = 4.0        # per garment in a colour the dress code avoids
_TRIP_SLOTS = (g.FOOTWEAR, g.EARRINGS, g.NECKLACE, g.BAG)


@dataclass(frozen=True)
class DaySpec:
    """What one day (or one wedding function) asks for."""
    occasions: tuple[str, ...]            # tagged for any of these counts as "tagged"
    label: str                            # "Day 3" or "Haldi"
    style: str | None = None
    comfort: str | None = None
    colours: tuple[str, ...] = ()         # dress-code colours, e.g. ("yellow", "mustard")
    avoid: tuple[str, ...] = ()           # colours to avoid, e.g. ("white", "black") at a wedding
    too_casual: tuple[str, ...] = ()      # kinds of piece that don't suit it, e.g. ("jeans",)
    dress_code: str | None = None         # shown to the user
    slots: tuple[str, ...] = _TRIP_SLOTS


def _colour_hits(pieces, names: tuple[str, ...]) -> list:
    wanted = [colours.parse(n) for n in names]
    return [p for p in pieces if p.item["category"] == "Clothing"
            and any(colours.same_family(w, p.colour) for w in wanted if w)]


def _req(spec: DaySpec, occasion: str | None = None) -> _Req:
    return _Req(occasion or spec.occasions[0], style=spec.style, comfort=spec.comfort)


def _day_options(items: list[dict], spec: DaySpec) -> list[tuple[float, engine.Outfit, bool]]:
    """(score, outfit base, uses untagged clothes) for one day, best first."""
    tagged: dict[frozenset, engine.Outfit] = {}
    for occasion in spec.occasions:
        clothes = [engine._prepare(i, occasion) for i in items if i["category"] == "Clothing"]
        for b in engine._base_outfits(clothes, _req(spec, occasion), None, strict=True):
            if b.ids not in tagged or b.score > tagged[b.ids].score:
                tagged[b.ids] = b
    clothes = [engine._prepare(i, spec.occasions[0]) for i in items if i["category"] == "Clothing"]
    untagged = [b for b in engine._base_outfits(clothes, _req(spec), None, strict=False) if b.ids not in tagged]

    def points(b: engine.Outfit) -> float:
        return (b.score + DRESS_CODE_BONUS * len(_colour_hits(b.pieces, spec.colours))
                - AVOID_COST * len(_colour_hits(b.pieces, spec.avoid))
                - AVOID_COST * sum(1 for p in b.pieces if p.type_key in spec.too_casual))

    best_tagged = sorted(tagged.values(), key=lambda b: (-points(b), sorted(b.ids)))[:OPTIONS_PER_DAY]
    best_untagged = sorted(untagged, key=lambda b: (-points(b), sorted(b.ids)))[:OPTIONS_PER_DAY]
    return ([(points(b), b, False) for b in best_tagged]
            + [(points(b) - UNTAGGED_COST, b, True) for b in best_untagged])


def _choose(options: list[list[tuple[float, engine.Outfit, bool]]]) -> list[int | None]:
    """Pick one option per day so that no garment is worn twice, filling as many days as possible
    with the best total score. Returns the chosen option index per day (None = no outfit)."""
    order = sorted(range(len(options)), key=lambda d: len(options[d]))   # hardest days first
    best = {"filled": -1, "score": float("-inf"), "pick": [None] * len(options)}
    pick: list[int | None] = [None] * len(options)
    steps = 0

    def search(k: int, used: set[int], filled: int, score: float) -> None:
        nonlocal steps
        steps += 1
        if steps > SEARCH_LIMIT:
            return
        remaining = len(order) - k
        if filled + remaining < best["filled"]:
            return  # can't beat the best plan even if every remaining day gets an outfit
        if k == len(order):
            if (filled, score) > (best["filled"], best["score"]):
                best.update(filled=filled, score=score, pick=list(pick))
            return
        day = order[k]
        for index, (points, base, _) in enumerate(options[day]):
            if base.ids & used:
                continue
            pick[day] = index
            search(k + 1, used | base.ids, filled + 1, score + points)
            pick[day] = None
        search(k + 1, used, filled, score)   # leave this day without an outfit

    search(0, set(), 0, 0.0)
    return best["pick"]


def plan_days(items: list[dict], specs: list[DaySpec], unit: str = "day") -> dict:
    """An outfit for each day (or function). No garment is worn twice; shoes, bags and jewellery
    are reused where they suit."""
    cache: dict[DaySpec, list] = {}
    options = [cache.setdefault(s, _day_options(items, s)) for s in specs]
    chosen = _choose(options)

    notes: list[str] = []
    packed: Counter = Counter()          # item id -> times worn
    worn_on: dict[int, list[int]] = {}
    plan = []
    short: list[DaySpec] = []            # left empty because every suitable piece is already used
    for day, spec in enumerate(specs, start=1):
        entry = {"day": day, "occasion": spec.occasions[0], "label": spec.label,
                 "dress_code": spec.dress_code, "outfit": None}
        plan.append(entry)
        index = chosen[day - 1]
        if index is None:
            if not options[day - 1]:
                notes.append(f"{spec.label}: no outfit possible from your wardrobe.")
            else:
                short.append(spec)
            continue
        _, base, untagged = options[day - 1][index]
        if untagged:
            notes.append(f"{spec.label}: nothing new is tagged for {_join(list(spec.occasions))}, "
                         "so it uses the closest match.")

        req = _req(spec)
        tags = set(spec.occasions)
        wardrobe = [engine._prepare(i, spec.occasions[0]) for i in items]
        for p in wardrobe:
            p.tagged = bool(tags & set(p.item["occasions"]))
        outfit = base.copy()
        if spec.colours:
            hits = _colour_hits(outfit.pieces, spec.colours)
            if hits:
                outfit.reasons.append((9.0, f"Fits the dress code: your {_join([p.name for p in hits])}"))
            else:
                outfit.cautions.append(f"Nothing in {_join(list(spec.colours))} fits here, so this is the closest match")
        for p in _colour_hits(outfit.pieces, spec.avoid):
            outfit.cautions.append(f"{p.colour.label} is usually avoided at a {spec.label.lower()}: your {p.name}")
        casual = [p.name for p in outfit.pieces if p.type_key in spec.too_casual]
        if casual:
            outfit.cautions.append(f"A bit casual for a {spec.label.lower()}: your {_join(casual)}. "
                                   "Add a dressier piece to your wardrobe for this one")
        for slot in spec.slots:
            slot_options = [(engine._addition_points(p, outfit, req, Counter())
                             + (REUSE_BONUS if p.id in packed else 0), p)
                            for p in wardrobe if p.role == slot and p.tagged and p.id not in outfit.ids]
            slot_options = [o for o in slot_options if o[0] >= engine.ACCESSORY_THRESHOLD]
            if slot_options:
                outfit.pieces.append(max(slot_options, key=lambda o: (o[0], -o[1].id))[1])

        for p in outfit.pieces:
            packed[p.id] += 1
            worn_on.setdefault(p.id, []).append(day)
        entry["outfit"] = {
            "rank": day, "score": round(outfit.score, 1),
            "pieces": [{"role": p.role, "item": p.item} for p in outfit.pieces],
            "reasons": [r for _, r in sorted(outfit.reasons, key=lambda r: -r[0])][:3],
            "cautions": list(dict.fromkeys(outfit.cautions)),
        }

    if short:
        filled = sum(1 for d in plan if d["outfit"])
        occasions = list(dict.fromkeys(o for s in short for o in s.occasions))
        notes.insert(0, f"{_join([s.label for s in short])}: not enough different clothes to dress "
                        f"{len(specs)} {unit}s without repeating any (your wardrobe covers {filled}). "
                        f"Add or tag more clothes for {_join(occasions)}.")

    by_id = {i["id"]: i for i in items}
    order = {c: n for n, c in enumerate(["Clothing", "Footwear", "Jewellery", "Bags", "Accessories"])}
    packing = sorted(
        ({"item": by_id[i], "uses": n, "days": worn_on[i]} for i, n in packed.items()),
        key=lambda p: (order.get(p["item"]["category"], 9), -p["uses"], p["item"]["name"]),
    )
    outfits = sum(1 for d in plan if d["outfit"])
    return {"days": plan, "packing": packing, "pieces": len(packing), "outfits": outfits,
            "notes": list(dict.fromkeys(notes))}


def plan_trip(items: list[dict], days: list[str], style: str | None = None) -> dict:
    """An outfit for each day of a trip. No garment is worn twice; shoes, bags and jewellery are
    reused where they suit, so the suitcase stays light."""
    specs = [DaySpec((occasion,), f"Day {n}", style=style) for n, occasion in enumerate(days, start=1)]
    return plan_days(items, specs)


# ---------- Wear stats ----------

def wear_stats(items: list[dict], wear: dict[int, tuple[int, str]], today: date, days: int = 30) -> dict:
    """How much each piece is worn: not worn lately, most worn, and cost per wear.

    wear: item id -> (times worn, last date worn as "YYYY-MM-DD"), from outfit history.
    """
    rows = []
    for item in items:
        n, last = wear.get(item["id"], (0, None))
        since = (today - date.fromisoformat(last)).days if last else None
        price = item.get("price")
        rows.append({
            "item": item, "wears": n, "last_worn_on": last, "days_since": since,
            "cost_per_wear": round(price / max(n, 1), 2) if price is not None else None,
        })
    not_worn = [r for r in rows if r["days_since"] is None or r["days_since"] > days]
    # Never worn first (oldest additions first), then the longest since last worn.
    not_worn.sort(key=lambda r: (r["days_since"] is not None, -(r["days_since"] or 0), r["item"]["created_at"]))
    most_worn = sorted((r for r in rows if r["wears"]), key=lambda r: (-r["wears"], r["item"]["name"]))[:5]
    priced = [r for r in rows if r["item"].get("price") is not None]
    cost = sorted(priced, key=lambda r: (r["cost_per_wear"], -r["wears"], r["item"]["name"]))
    spent = sum(r["item"]["price"] for r in priced)
    total_wears = sum(max(r["wears"], 1) for r in priced)
    return {
        "days": days,
        "total_items": len(items),
        "worn_recently": sum(1 for r in rows if r["days_since"] is not None and r["days_since"] <= days),
        "total_spent": round(spent, 2) if priced else None,
        "priced_items": len(priced),
        "average_cost_per_wear": round(spent / total_wears, 2) if priced else None,
        "not_worn": not_worn,
        "most_worn": most_worn,
        "cost_per_wear": cost,
    }
