"""Shapes of the data going in and out of the API, with validation."""
from pydantic import BaseModel, Field, field_validator

from wardrobe_options import CATEGORIES, OCCASIONS, STYLES


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
