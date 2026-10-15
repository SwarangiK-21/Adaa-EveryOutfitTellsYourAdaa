"""Shapes of the data going in and out of the API, with validation."""
from datetime import date

from pydantic import BaseModel, Field, field_validator

from wardrobe_options import CATEGORIES, COLOUR_MOODS, COMFORT_LEVELS, OCCASIONS, STYLES


class ItemFields(BaseModel):
    """Details the user enters for a wardrobe item (everything except the photo)."""

    name: str = Field(min_length=1, max_length=80)
    category: str
    item_type: str = Field(min_length=1, max_length=40)
    colour: str = Field(min_length=1, max_length=40)
    style: str
    occasions: list[str] = Field(min_length=1)
    notes: str = Field(default="", max_length=300)

    @field_validator("name", "item_type", "colour", "notes", mode="before")
    @classmethod
    def strip_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("category")
    @classmethod
    def check_category(cls, value):
        if value not in CATEGORIES:
            raise ValueError(f"category must be one of: {', '.join(CATEGORIES)}")
        return value

    @field_validator("style")
    @classmethod
    def check_style(cls, value):
        if value not in STYLES:
            raise ValueError(f"style must be one of: {', '.join(STYLES)}")
        return value

    @field_validator("occasions")
    @classmethod
    def check_occasions(cls, value):
        unknown = [o for o in value if o not in OCCASIONS]
        if unknown:
            raise ValueError(f"unknown occasion(s): {', '.join(unknown)}")
        # Remove duplicates but keep the user's order.
        return list(dict.fromkeys(value))


class ItemOut(ItemFields):
    """A saved wardrobe item as returned by the API."""

    id: int
    image_url: str
    created_at: str
    updated_at: str


def item_out(item: dict) -> ItemOut:
    """Database row -> API item, with a photo URL that changes when the photo changes."""
    version = item["image_filename"][:8]
    return ItemOut(**item, image_url=f"/api/items/{item['id']}/photo?v={version}")


# ---------- Outfit recommendations ----------

class StylePrefs(BaseModel):
    """The occasion and preferences an outfit is styled for. Only occasion is required."""

    occasion: str
    style: str | None = None
    colour: str | None = Field(default=None, max_length=40)
    colour_mood: str | None = None
    comfort: str | None = None

    @field_validator("style", "colour", "colour_mood", "comfort", mode="before")
    @classmethod
    def blank_to_none(cls, value):
        if isinstance(value, str):
            value = value.strip()
            if not value or value == "No preference":
                return None
        return value

    @field_validator("occasion")
    @classmethod
    def check_occasion(cls, value):
        if value not in OCCASIONS:
            raise ValueError(f"occasion must be one of: {', '.join(OCCASIONS)}")
        return value

    @field_validator("style")
    @classmethod
    def check_style(cls, value):
        if value is not None and value not in STYLES:
            raise ValueError(f"style must be one of: {', '.join(STYLES)}")
        return value

    @field_validator("colour_mood")
    @classmethod
    def check_mood(cls, value):
        if value is not None and value not in COLOUR_MOODS:
            raise ValueError(f"colour_mood must be one of: {', '.join(COLOUR_MOODS)}")
        return value

    @field_validator("comfort")
    @classmethod
    def check_comfort(cls, value):
        if value is not None and value not in COMFORT_LEVELS:
            raise ValueError(f"comfort must be one of: {', '.join(COMFORT_LEVELS)}")
        return value


class RecommendationRequest(StylePrefs):
    """A styling request: preferences plus an optional piece to build around."""

    anchor_item_id: int | None = None
    count: int = Field(default=4, ge=1, le=4)


class OutfitPiece(BaseModel):
    role: str          # e.g. "Top", "Footwear", "Earrings"
    item: ItemOut      # always a real wardrobe item


class OutfitOut(BaseModel):
    rank: int
    score: float
    pieces: list[OutfitPiece]
    reasons: list[str]
    cautions: list[str]


class RecommendationResponse(BaseModel):
    outfits: list[OutfitOut]
    notes: list[str]   # limitations, e.g. "You haven't added any bags yet."
    relaxed: bool      # True if occasion tags had to be ignored to find any outfit


# ---------- Typed requests ("Style my black crop top for a party") ----------

class StylistMessage(BaseModel):
    text: str = Field(min_length=1, max_length=300)


class ItemRef(BaseModel):
    id: int
    name: str


class ParsedRequest(BaseModel):
    """Filters read from a typed request, plus what was understood or is missing."""

    occasion: str | None
    style: str | None
    colour: str | None
    colour_mood: str | None
    comfort: str | None
    anchor_item_id: int | None
    understood: list[str]      # e.g. ["Occasion: Party", "Building around your crop top"]
    missing: list[str]         # e.g. ["occasion"]
    ambiguous: list[ItemRef]   # several pieces matched equally, e.g. two black tops
    not_found: list[str]       # pieces they named that aren't in the wardrobe, e.g. "green kurta"



# ---------- Saved looks, swaps and history (Phase 5) ----------

ItemIds = list[int]


class OutfitCheck(BaseModel):
    """An outfit to score/explain, e.g. after swapping a piece."""

    prefs: StylePrefs
    item_ids: ItemIds = Field(min_length=1, max_length=12)


class SwapRequest(OutfitCheck):
    replace_item_id: int


class SwapOption(BaseModel):
    item: ItemOut
    role: str
    tagged: bool      # tagged for the occasion?
    reason: str


class OutfitEvaluation(BaseModel):
    pieces: list[OutfitPiece]
    reasons: list[str]
    cautions: list[str]


class LookCreate(OutfitCheck):
    name: str | None = Field(default=None, max_length=80)


class LookUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    item_ids: ItemIds | None = Field(default=None, min_length=1, max_length=12)


class LookOut(OutfitEvaluation):
    id: int
    name: str
    prefs: StylePrefs
    missing_pieces: int       # pieces deleted from the wardrobe since saving
    wear_count: int
    last_worn_on: str | None
    created_at: str


class WearIn(BaseModel):
    worn_on: date | None = None   # defaults to today

    @field_validator("worn_on")
    @classmethod
    def not_in_future(cls, value):
        if value is not None and value > date.today():
            raise ValueError("worn_on can't be in the future")
        return value


class HistoryEntry(BaseModel):
    id: int
    look_id: int | None       # None if the saved look was deleted later
    look_name: str
    occasion: str
    worn_on: str
    pieces: list[OutfitPiece]  # the look's current pieces (empty if the look was deleted)
