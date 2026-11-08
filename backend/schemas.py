"""Shapes of the data going in and out of the API, with validation."""
from datetime import date
from typing import Literal

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
    price: float | None = Field(default=None, ge=0, le=10_000_000)   # optional, for cost per wear

    @field_validator("name", "item_type", "colour", "notes", mode="before")
    @classmethod
    def strip_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("price", mode="before")
    @classmethod
    def blank_price(cls, value):
        if isinstance(value, str):
            value = value.strip().replace(",", "")
            return None if not value else value
        return value

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
    cutout_url: str | None = None   # the garment with its background removed (for outfit boards)
    cutout_version: str | None = None  # which cut-out method made it (newer methods redo older ones)
    created_at: str
    updated_at: str


def item_out(item: dict) -> ItemOut:
    """Database row -> API item, with a photo URL that changes when the photo changes."""
    version = item["image_filename"][:8]
    cutout = item.get("cutout_filename")
    fields = {k: v for k, v in item.items() if k not in ("cutout_filename",)}
    return ItemOut(
        **fields,
        image_url=f"/api/items/{item['id']}/photo?v={version}",
        cutout_url=f"/api/items/{item['id']}/cutout?v={cutout[:8]}" if cutout else None,
    )


# ---------- Outfit recommendations ----------

class WeatherNow(BaseModel):
    """Today's forecast (from Open-Meteo, fetched by the browser), used as a gentle styling nudge."""

    temp_c: float = Field(ge=-60, le=60)      # today's high
    rain: bool = False
    label: str | None = Field(default=None, max_length=80)   # e.g. "33°C, sunny in Pune"


class StylePrefs(BaseModel):
    """The occasion and preferences an outfit is styled for. Only occasion is required."""

    occasion: str
    style: str | None = None
    colour: str | None = Field(default=None, max_length=40)
    colour_mood: str | None = None
    comfort: str | None = None
    weather: WeatherNow | None = None
    festival: str | None = None   # e.g. "republic_day": its usual colours are preferred

    @field_validator("festival", mode="before")
    @classmethod
    def check_festival(cls, value):
        from recommender.festivals import FESTIVALS
        if value in ("", None):
            return None
        if value not in FESTIVALS:
            raise ValueError("unknown festival")
        return value

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
    personal: list[str] = []   # why it suits *you*, from your style profile


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
    festival: str | None = None   # e.g. "republic_day"
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
    personal: list[str] = []


class LookCreate(OutfitCheck):
    name: str | None = Field(default=None, max_length=80)


class LookUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    item_ids: ItemIds | None = Field(default=None, min_length=1, max_length=12)


class LookPhoto(BaseModel):
    """The user's own photo wearing a saved look (a verified preview)."""

    url: str
    taken_at: str
    matches_current: bool          # False once pieces were swapped/deleted after the photo
    changed_pieces: list[str]      # current pieces that weren't in the photo


class LookOut(OutfitEvaluation):
    id: int
    name: str
    prefs: StylePrefs
    missing_pieces: int       # pieces deleted from the wardrobe since saving
    wear_count: int
    last_worn_on: str | None
    created_at: str
    photo: LookPhoto | None = None


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
    look_id: int | None       # None if the saved look was deleted later, or it was never saved
    look_name: str
    occasion: str
    worn_on: str
    pieces: list[OutfitPiece]  # the pieces actually worn that day (still in the wardrobe)


class WearOutfitIn(WearIn):
    """Record wearing an outfit that isn't a saved look (e.g. straight from the stylist)."""

    item_ids: ItemIds = Field(min_length=1, max_length=12)
    occasion: str
    name: str | None = Field(default=None, max_length=80)

    @field_validator("occasion")
    @classmethod
    def check_occasion(cls, value):
        if value not in OCCASIONS:
            raise ValueError(f"occasion must be one of: {', '.join(OCCASIONS)}")
        return value


class ItemWear(BaseModel):
    item: ItemOut
    wears: int                      # times worn (from outfit history)
    last_worn_on: str | None
    days_since: int | None          # days since last worn (None = never)
    cost_per_wear: float | None     # price / wears (price if never worn); None without a price


class WearStats(BaseModel):
    days: int                       # the "not worn in N days" window
    total_items: int
    worn_recently: int              # pieces worn in the window
    total_spent: float | None       # sum of the prices you entered
    priced_items: int
    average_cost_per_wear: float | None
    not_worn: list[ItemWear]        # not worn in the window (or never), longest first
    most_worn: list[ItemWear]
    cost_per_wear: list[ItemWear]   # priced pieces, best value first



# ---------- Planning: what to buy next, and what to pack ----------

class GapSuggestion(BaseModel):
    name: str                  # e.g. "White sneakers" (a suggestion, not something you own)
    category: str
    item_type: str
    colour: str
    new_outfits: int           # complete outfits it would add
    occasions: list[str]
    reason: str
    pairs_with: list[ItemOut]  # your own pieces it goes with


class GapReport(BaseModel):
    suggestions: list[GapSuggestion]
    outfits_now: int           # distinct complete outfits your wardrobe makes today
    counts: dict[str, int]     # pieces per role, e.g. {"Top": 6, "Bottom": 3}
    notes: list[str]


class TripRequest(BaseModel):
    days: list[str] = Field(min_length=1, max_length=14)   # the occasion for each day
    style: str | None = None

    @field_validator("days")
    @classmethod
    def check_days(cls, value):
        for occasion in value:
            if occasion not in OCCASIONS:
                raise ValueError(f"each day must be one of: {', '.join(OCCASIONS)}")
        return value

    @field_validator("style", mode="before")
    @classmethod
    def check_style(cls, value):
        if value in ("", None):
            return None
        if value not in STYLES:
            raise ValueError(f"style must be one of: {', '.join(STYLES)}")
        return value


class TripDay(BaseModel):
    day: int
    occasion: str
    label: str | None = None        # "Day 3", or a function like "Haldi"
    dress_code: str | None = None   # for wedding functions
    outfit: OutfitOut | None


class EventFunction(BaseModel):
    key: str
    label: str
    dress_code: str
    colours: list[str]


class EventRequest(BaseModel):
    functions: list[str] = Field(min_length=1, max_length=10)   # e.g. ["haldi", "mehendi", "wedding"]
    style: str | None = None

    @field_validator("functions")
    @classmethod
    def check_functions(cls, value):
        from recommender.events import FUNCTIONS
        unknown = [f for f in value if f not in FUNCTIONS]
        if unknown:
            raise ValueError(f"unknown function(s): {', '.join(unknown)}")
        return value

    @field_validator("style", mode="before")
    @classmethod
    def check_style(cls, value):
        if value in ("", None):
            return None
        if value not in STYLES:
            raise ValueError(f"style must be one of: {', '.join(STYLES)}")
        return value


class PackedItem(BaseModel):
    item: ItemOut
    uses: int
    days: list[int]


class TripPlan(BaseModel):
    days: list[TripDay]
    packing: list[PackedItem]
    pieces: int     # how many pieces to pack
    outfits: int    # how many days got an outfit
    notes: list[str]


class FestivalNow(BaseModel):
    """Today's festival (with today's colour for Navratri), or the next one within three weeks."""
    key: str
    name: str
    today: bool
    in_days: int
    date: str
    colour: str
    colours: list[str]
    day_label: str
    title: str
    tip: str
    occasion: str
    style: str | None


# ---------- Accounts ----------

import re as _re

_EMAIL = _re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _clean_phone(value: str) -> str:
    """Keep a leading + and digits only; 10-15 digits (e.g. 9876543210 or +91 98765 43210)."""
    value = (value or "").strip()
    digits = _re.sub(r"\D", "", value)
    if not 10 <= len(digits) <= 15:
        raise ValueError("Please enter a valid phone number (10 to 15 digits).")
    return ("+" if value.startswith("+") else "") + digits


class AccountFields(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    phone: str = Field(max_length=25)

    @field_validator("name", mode="before")
    @classmethod
    def clean_name(cls, value):
        value = " ".join(str(value or "").split())
        if not value:
            raise ValueError("Please tell us your name.")
        return value

    @field_validator("phone", mode="before")
    @classmethod
    def clean_phone(cls, value):
        return _clean_phone(str(value or ""))


class SignupIn(AccountFields):
    email: str = Field(max_length=120)
    password: str = Field(min_length=8, max_length=128)
    accept_privacy: bool = False   # "I'm 18 or older and agree to the privacy note"

    @field_validator("accept_privacy")
    @classmethod
    def must_accept(cls, value):
        if not value:
            raise ValueError("Please confirm you're 18 or older and agree to the terms of use and privacy note.")
        return value

    @field_validator("email", mode="before")
    @classmethod
    def clean_email(cls, value):
        value = str(value or "").strip().lower()
        if not _EMAIL.match(value):
            raise ValueError("Please enter a valid email address.")
        return value


class LoginIn(BaseModel):
    email: str = Field(max_length=120)
    password: str = Field(max_length=128)

    @field_validator("email", mode="before")
    @classmethod
    def clean_email(cls, value):
        return str(value or "").strip().lower()


class ForgotIn(BaseModel):
    email: str = Field(max_length=120)

    @field_validator("email", mode="before")
    @classmethod
    def clean_email(cls, value):
        return str(value or "").strip().lower()


class VerifyIn(BaseModel):
    token: str = Field(min_length=10, max_length=100)


class ResetIn(BaseModel):
    token: str = Field(min_length=10, max_length=100)
    password: str = Field(min_length=8, max_length=128)


class PasswordChange(BaseModel):
    current_password: str = Field(max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class DeleteAccountIn(BaseModel):
    password: str = Field(max_length=128)


class AboutOut(BaseModel):
    """What the sign-up screen and privacy note need to know about this Adaa."""
    contact_email: str      # whom to ask about your data ("" = the person who runs this Adaa)
    max_items: int
    max_looks: int


class UserOut(BaseModel):
    id: int
    name: str
    first_name: str           # what Adaa calls you, e.g. "Ananya"
    email: str
    phone: str
    created_at: str
    moved_items: int = 0      # on sign-up: pieces from before accounts that moved into this account
    email_verified: bool = False


def user_out(user: dict, moved_items: int = 0) -> UserOut:
    return UserOut(id=user["id"], name=user["name"], first_name=user["name"].split()[0], email=user["email"],
                   phone=user["phone"], created_at=user["created_at"], moved_items=moved_items,
                   email_verified=bool(user.get("email_verified_at")))


# ---------- Optional style profile ----------

BodyShape = Literal["hourglass", "pear", "apple", "rectangle", "inverted_triangle"]
Fit = Literal["fitted", "regular", "relaxed"]
Undertone = Literal["warm", "cool", "neutral"]
Gender = Literal["woman", "man", "non_binary"]
AvoidStyle = Literal["sleeveless", "short_hemlines", "bodycon", "crop_tops"]


class StyleProfile(BaseModel):
    """Everything is optional: skip any question and Adaa still works."""
    height_cm: int | None = Field(default=None, ge=120, le=220)
    body_shape: BodyShape | None = None     # chosen by the person, never guessed
    fit: Fit | None = None
    undertone: Undertone | None = None      # only nudges colour suggestions, never limits choices
    gender: Gender | None = None            # only hides shop ideas you'd never wear
    avoid: list[AvoidStyle] = Field(default=[], max_length=4)
    love_colours: list[str] = Field(default=[], max_length=8)
    avoid_colours: list[str] = Field(default=[], max_length=8)
    style: str | None = Field(default=None, max_length=40)
    comfort: str | None = Field(default=None, max_length=40)
    colour_mood: str | None = Field(default=None, max_length=40)
    onboarded: bool = False

    @field_validator("avoid")
    @classmethod
    def no_repeats(cls, value):
        return list(dict.fromkeys(value))

    @field_validator("love_colours", "avoid_colours")
    @classmethod
    def known_colours(cls, value):
        from recommender import colours
        names = []
        for text in value:
            colour = colours.parse(str(text)[:40], fuzzy=False)
            if colour is None:
                raise ValueError(f"Adaa doesn't know the colour '{str(text)[:40]}'.")
            names.append(colour.name)
        return list(dict.fromkeys(names))


class StyleProfileOut(StyleProfile):
    updated_at: str | None = None

