"""API routes for wardrobe items: list, view, add, edit, delete, and photos (your own only)."""
import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import ValidationError

import auth
import config
import database
import storage
from schemas import ItemFields, ItemOut, item_out
from wardrobe_options import (
    CATEGORIES, COLOUR_MOODS, COMFORT_LEVELS, ITEM_TYPE_SUGGESTIONS, OCCASIONS, STYLES,
)

router = APIRouter(prefix="/api", tags=["wardrobe"])

Db = Annotated[sqlite3.Connection, Depends(database.get_db)]


def _parse_fields(**values) -> ItemFields:
    try:
        return ItemFields(**values)
    except ValidationError as exc:
        messages = [
            f"{'.'.join(str(p) for p in err['loc'])}: {err['msg'].removeprefix('Value error, ')}"
            for err in exc.errors()
        ]
        raise HTTPException(status_code=422, detail=messages) from None


def _get_or_404(db, item_id: int, uid: int) -> dict:
    item = database.get_item(db, item_id, uid)   # someone else's piece looks exactly like a missing one
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
        "colour_moods": COLOUR_MOODS,
        "comfort_levels": COMFORT_LEVELS,
    }


@router.get("/items", response_model=list[ItemOut])
def list_items(db: Db, user: auth.User, search: str = "", category: str | None = None):
    return [item_out(item) for item in database.list_items(db, user["id"], search, category)]


@router.get("/items/{item_id}", response_model=ItemOut)
def get_item(item_id: int, db: Db, user: auth.User):
    return item_out(_get_or_404(db, item_id, user["id"]))


@router.get("/items/{item_id}/photo")
def get_item_photo(item_id: int, db: Db, user: auth.User):
    item = _get_or_404(db, item_id, user["id"])
    path = storage.image_path(item["image_filename"])
    if path is None:
        raise HTTPException(status_code=404, detail="Photo file is missing.")
    return FileResponse(path, headers={"Cache-Control": storage.PHOTO_CACHE})


@router.post("/items", response_model=ItemOut, status_code=201)
def create_item(
    db: Db,
    user: auth.User,
    photo: Annotated[UploadFile, File(description="JPEG, PNG or WebP, up to 5 MB")],
    name: Annotated[str, Form()],
    category: Annotated[str, Form()],
    item_type: Annotated[str, Form()],
    colour: Annotated[str, Form()],
    style: Annotated[str, Form()],
    occasions: Annotated[list[str], Form()],
    notes: Annotated[str, Form()] = "",
    price: Annotated[str, Form(max_length=20)] = "",
):
    fields = _parse_fields(
        name=name, category=category, item_type=item_type, colour=colour,
        style=style, occasions=occasions, notes=notes, price=price,
    )
    if database.count_owned(db, "wardrobe_items", user["id"]) >= config.MAX_ITEMS_PER_USER:
        raise HTTPException(status_code=403, detail=f"Your wardrobe is full ({config.MAX_ITEMS_PER_USER} pieces). "
                            "Delete a few pieces you no longer wear to add new ones.")
    try:
        filename = storage.save_image(photo)
    except storage.InvalidImage as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    try:
        item = database.create_item(db, user["id"], fields, filename)
    except Exception:
        storage.delete_image(filename)  # don't leave an orphan photo behind
        raise
    return item_out(item)


@router.put("/items/{item_id}", response_model=ItemOut)
def update_item(
    item_id: int,
    db: Db,
    user: auth.User,
    name: Annotated[str, Form()],
    category: Annotated[str, Form()],
    item_type: Annotated[str, Form()],
    colour: Annotated[str, Form()],
    style: Annotated[str, Form()],
    occasions: Annotated[list[str], Form()],
    notes: Annotated[str, Form()] = "",
    price: Annotated[str, Form(max_length=20)] = "",
    photo: Annotated[UploadFile | None, File(description="Optional new photo")] = None,
):
    """Replace an item's details. Send a new photo only if it should change."""
    existing = _get_or_404(db, item_id, user["id"])
    fields = _parse_fields(
        name=name, category=category, item_type=item_type, colour=colour,
        style=style, occasions=occasions, notes=notes, price=price,
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
        old_cutout = database.set_cutout(db, item_id, None)  # it showed the old photo
        if old_cutout:
            storage.delete_image(old_cutout)
        item = database.get_item(db, item_id)
    return item_out(item)


@router.delete("/items/{item_id}", status_code=204)
def delete_item(item_id: int, db: Db, user: auth.User):
    item = _get_or_404(db, item_id, user["id"])
    database.delete_item(db, item_id)
    storage.delete_image(item["image_filename"])
    if item.get("cutout_filename"):
        storage.delete_image(item["cutout_filename"])


# ---------- background-removal model, used by the browser to make garment cut-outs ----------

@router.get("/cutout-model")
@router.get("/models/{name}")
def cutout_model(user: auth.User, name: str = "isnet"):
    """AI models for garment cut-outs, downloaded once: 'isnet' (background) and 'clothes' (garment parser).
    Signed-in people only, so strangers can't use up the server's bandwidth."""
    import cutout_model as cm
    if name not in cm.MODELS:
        raise HTTPException(status_code=404, detail="Unknown model.")
    try:
        path = cm.ensure_model(name)
    except cm.ModelUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    return FileResponse(path, media_type="application/octet-stream",
                        headers={"Cache-Control": "private, max-age=31536000, immutable"})



# ---------- garment cut-outs (made in the browser, stored here) ----------

@router.put("/items/{item_id}/cutout", response_model=ItemOut)
def save_item_cutout(
    item_id: int,
    db: Db,
    user: auth.User,
    cutout: Annotated[UploadFile, File(description="PNG with a transparent background")],
    version: Annotated[str, Form(max_length=8)] = "1",
):
    _get_or_404(db, item_id, user["id"])
    try:
        filename = storage.save_cutout(cutout)
    except storage.InvalidImage as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    old = database.set_cutout(db, item_id, filename, version)
    if old:
        storage.delete_image(old)
    return item_out(database.get_item(db, item_id))


@router.get("/items/{item_id}/cutout")
def get_item_cutout(item_id: int, db: Db, user: auth.User):
    item = _get_or_404(db, item_id, user["id"])
    path = storage.image_path(item["cutout_filename"]) if item.get("cutout_filename") else None
    if path is None:
        raise HTTPException(status_code=404, detail="No cut-out yet.")
    return FileResponse(path, media_type="image/png", headers={"Cache-Control": storage.PHOTO_CACHE})


@router.delete("/items/{item_id}/cutout", status_code=204)
def delete_item_cutout(item_id: int, db: Db, user: auth.User):
    _get_or_404(db, item_id, user["id"])
    old = database.set_cutout(db, item_id, None)
    if old:
        storage.delete_image(old)
