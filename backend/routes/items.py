"""API routes for wardrobe items: list, view, add, edit, delete, and photos."""
import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import ValidationError

import database
import storage
from schemas import ItemFields, ItemOut
from wardrobe_options import CATEGORIES, ITEM_TYPE_SUGGESTIONS, OCCASIONS, STYLES

router = APIRouter(prefix="/api", tags=["wardrobe"])

Db = Annotated[sqlite3.Connection, Depends(database.get_db)]


def _to_out(item: dict) -> ItemOut:
    # ?v= changes when the photo changes, so the browser never shows an old cached photo.
    version = item["image_filename"][:8]
    return ItemOut(**item, image_url=f"/api/items/{item['id']}/photo?v={version}")


def _parse_fields(**values) -> ItemFields:
    try:
        return ItemFields(**values)
    except ValidationError as exc:
        messages = [
            f"{'.'.join(str(p) for p in err['loc'])}: {err['msg'].removeprefix('Value error, ')}"
            for err in exc.errors()
        ]
        raise HTTPException(status_code=422, detail=messages) from None


def _get_or_404(db, item_id: int) -> dict:
    item = database.get_item(db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Wardrobe item not found.")
    return item


@router.get("/options")
def get_options():
    """Allowed categories, styles and occasions, plus garment type suggestions."""
    return {
        "categories": CATEGORIES,
        "styles": STYLES,
        "occasions": OCCASIONS,
        "item_type_suggestions": ITEM_TYPE_SUGGESTIONS,
    }


@router.get("/items", response_model=list[ItemOut])
def list_items(db: Db, search: str = "", category: str | None = None):
    return [_to_out(item) for item in database.list_items(db, search, category)]


@router.get("/items/{item_id}", response_model=ItemOut)
def get_item(item_id: int, db: Db):
    return _to_out(_get_or_404(db, item_id))


@router.get("/items/{item_id}/photo")
def get_item_photo(item_id: int, db: Db):
    item = _get_or_404(db, item_id)
    path = storage.image_path(item["image_filename"])
    if path is None:
        raise HTTPException(status_code=404, detail="Photo file is missing.")
    return FileResponse(path)


@router.post("/items", response_model=ItemOut, status_code=201)
def create_item(
    db: Db,
    photo: Annotated[UploadFile, File(description="JPEG, PNG or WebP, up to 5 MB")],
    name: Annotated[str, Form()],
    category: Annotated[str, Form()],
    item_type: Annotated[str, Form()],
    colour: Annotated[str, Form()],
    style: Annotated[str, Form()],
    occasions: Annotated[list[str], Form()],
    notes: Annotated[str, Form()] = "",
):
    fields = _parse_fields(
        name=name, category=category, item_type=item_type, colour=colour,
        style=style, occasions=occasions, notes=notes,
    )
    try:
        filename = storage.save_image(photo)
    except storage.InvalidImage as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    try:
        item = database.create_item(db, fields, filename)
    except Exception:
        storage.delete_image(filename)  # don't leave an orphan photo behind
        raise
    return _to_out(item)


@router.put("/items/{item_id}", response_model=ItemOut)
def update_item(
    item_id: int,
    db: Db,
    name: Annotated[str, Form()],
    category: Annotated[str, Form()],
    item_type: Annotated[str, Form()],
    colour: Annotated[str, Form()],
    style: Annotated[str, Form()],
    occasions: Annotated[list[str], Form()],
    notes: Annotated[str, Form()] = "",
    photo: Annotated[UploadFile | None, File(description="Optional new photo")] = None,
):
    """Replace an item's details. Send a new photo only if it should change."""
    existing = _get_or_404(db, item_id)
    fields = _parse_fields(
        name=name, category=category, item_type=item_type, colour=colour,
        style=style, occasions=occasions, notes=notes,
    )

    filename = existing["image_filename"]
    new_photo = photo is not None and photo.filename
    if new_photo:
        try:
            filename = storage.save_image(photo)
        except storage.InvalidImage as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from None

    try:
        item = database.update_item(db, item_id, fields, filename)
    except Exception:
        if new_photo:
            storage.delete_image(filename)
        raise
    if new_photo:
        storage.delete_image(existing["image_filename"])
    return _to_out(item)


@router.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int, db: Db):
    item = _get_or_404(db, item_id)
    database.delete_item(db, item_id)
    storage.delete_image(item["image_filename"])
