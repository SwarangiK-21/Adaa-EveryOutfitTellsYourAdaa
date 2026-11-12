"""API routes for swapping pieces, saved looks and outfit history."""
import sqlite3
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

import auth
import config
import database
import looks_db
import storage
from recommender.engine import RecommendationError, alternatives, evaluate
from schemas import (
    HistoryEntry, LookCreate, LookOut, LookUpdate, OutfitCheck, OutfitEvaluation,
    StylePrefs, SwapOption, SwapRequest, WearIn, WearOutfitIn, item_out,
)

router = APIRouter(prefix="/api", tags=["looks"])
Db = Annotated[sqlite3.Connection, Depends(database.get_db)]


def _with_items(evaluation: dict) -> dict:
    for piece in evaluation["pieces"]:
        piece["item"] = item_out(piece["item"])
    return evaluation


def _check_items(db, uid: int, item_ids: list[int]) -> list[dict]:
    """All your wardrobe items, after making sure every requested id is really yours."""
    items = database.list_items(db, uid)
    known = {i["id"] for i in items}
    missing = [i for i in item_ids if i not in known]
    if missing:
        raise HTTPException(status_code=400, detail="Some of those pieces are no longer in your wardrobe.")
    if len(set(item_ids)) != len(item_ids):
        raise HTTPException(status_code=400, detail="A look can't contain the same piece twice.")
    return items


_UNSET = object()


def _look_out(db, look: dict, items: list[dict] | None = None, profile=_UNSET) -> dict:
    items = items if items is not None else database.list_items(db, look["user_id"])
    if profile is _UNSET:
        profile = database.get_style_profile(db, look["user_id"])
    prefs = StylePrefs(**look["prefs"])
    out = {**look, **_with_items(evaluate(items, look["item_ids"], prefs, profile))}
    out["photo"] = _photo_out(look, items)
    return out


def _photo_out(look: dict, items: list[dict]) -> dict | None:
    """The look's verified photo, and whether it still shows the look's current pieces."""
    photo = look.get("photo")
    if not photo:
        return None
    names = {i["id"]: i["name"] for i in items}
    changed = [names[i] for i in look["item_ids"] if i not in photo["item_ids"] and i in names]
    return {
        "url": f"/api/looks/{look['id']}/photo?v={photo['image_filename'][:8]}",
        "taken_at": photo["created_at"],
        "matches_current": sorted(photo["item_ids"]) == sorted(look["item_ids"]),
        "changed_pieces": changed,
    }


def _get_look_or_404(db, look_id: int, uid: int) -> dict:
    look = looks_db.get_look(db, look_id, uid)
    if look is None:
        raise HTTPException(status_code=404, detail="Saved look not found.")
    return look


# ---------- swaps ----------

@router.post("/outfits/evaluate", response_model=OutfitEvaluation)
def evaluate_outfit(body: OutfitCheck, db: Db, user: auth.User):
    """Reasons and cautions for an outfit, e.g. after swapping a piece."""
    items = _check_items(db, user["id"], body.item_ids)
    return _with_items(evaluate(items, body.item_ids, body.prefs, database.get_style_profile(db, user["id"])))


@router.post("/outfits/alternatives", response_model=list[SwapOption])
def swap_options(body: SwapRequest, db: Db, user: auth.User):
    """Other pieces from the wardrobe that could replace one piece, best first."""
    items = _check_items(db, user["id"], body.item_ids)
    try:
        options = alternatives(items, body.item_ids, body.replace_item_id, body.prefs)
    except RecommendationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    for o in options:
        o["item"] = item_out(o["item"])
    return options


# ---------- saved looks ----------

@router.get("/looks", response_model=list[LookOut])
def list_looks(db: Db, user: auth.User):
    items = database.list_items(db, user["id"])
    profile = database.get_style_profile(db, user["id"])
    return [_look_out(db, look, items, profile) for look in looks_db.list_looks(db, user["id"])]


@router.post("/looks", response_model=LookOut, status_code=201)
def save_look(body: LookCreate, db: Db, user: auth.User):
    items = _check_items(db, user["id"], body.item_ids)
    if database.count_owned(db, "looks", user["id"]) >= config.MAX_LOOKS_PER_USER:
        raise HTTPException(status_code=403, detail=f"You've saved {config.MAX_LOOKS_PER_USER} looks, the most Peheraav keeps. "
                            "Delete a few old ones to save new ones.")
    prefs = body.prefs.model_dump()
    if looks_db.find_same_look(db, user["id"], body.item_ids, prefs["occasion"]):
        raise HTTPException(status_code=409, detail="You've already saved this look.")
    by_id = {i["id"]: i for i in items}
    name = (body.name or "").strip() or " + ".join(
        by_id[i]["name"] for i in body.item_ids if by_id[i]["category"] == "Clothing"
    ) or "My look"
    # Two looks with the same name are confusing: number the new one ("Crop top + Skirt 2").
    taken = {l["name"].lower() for l in looks_db.list_looks(db, user["id"])}
    base, n = name[:76], 2
    while name.lower() in taken:
        name, n = f"{base} {n}", n + 1
    look = looks_db.create_look(db, user["id"], name[:80], prefs, body.item_ids)
    return _look_out(db, look, items)


@router.put("/looks/{look_id}", response_model=LookOut)
def update_look(look_id: int, body: LookUpdate, db: Db, user: auth.User):
    """Rename a look and/or change its pieces (e.g. after a swap)."""
    _get_look_or_404(db, look_id, user["id"])
    if body.item_ids is not None:
        _check_items(db, user["id"], body.item_ids)
    name = body.name.strip() if body.name else None
    return _look_out(db, looks_db.update_look(db, look_id, name, body.item_ids))


@router.delete("/looks/{look_id}", status_code=204)
def delete_look(look_id: int, db: Db, user: auth.User):
    _get_look_or_404(db, look_id, user["id"])
    old_photo = looks_db.delete_look(db, look_id)
    if old_photo:
        storage.delete_image(old_photo)


# ---------- outfit history ----------

@router.post("/looks/{look_id}/wear", response_model=HistoryEntry, status_code=201)
def wear_look(look_id: int, db: Db, user: auth.User, body: WearIn | None = None):
    """Record that a saved look was worn (today, unless a date is given)."""
    look = _get_look_or_404(db, look_id, user["id"])
    if not look["item_ids"]:
        raise HTTPException(status_code=400, detail="This look has no pieces left to wear.")
    worn_on = (body.worn_on if body else None) or date.today()
    entry = looks_db.log_wear(db, user["id"], look, worn_on)
    return _history_out(db, entry, database.list_items(db, user["id"]))


def _history_out(db, entry: dict, items: list[dict]) -> dict:
    # The pieces worn that day (a later swap in the saved look doesn't rewrite history).
    by_id = {i["id"]: i for i in items}
    worn = [by_id[i] for i in looks_db.worn_item_ids(db, entry["id"]) if i in by_id]
    if worn:
        prefs = {"occasion": entry["occasion"]}
        pieces = evaluate(worn, [i["id"] for i in worn], StylePrefs(**prefs))["pieces"]
        pieces = [{"role": p["role"], "item": item_out(p["item"])} for p in pieces]
    else:
        look = looks_db.get_look(db, entry["look_id"]) if entry["look_id"] else None
        pieces = _look_out(db, look, items)["pieces"] if look else []
    return {**entry, "pieces": pieces}


@router.post("/history", response_model=HistoryEntry, status_code=201)
def wear_outfit(body: WearOutfitIn, db: Db, user: auth.User):
    """Record wearing an outfit that isn't saved (e.g. straight from the stylist)."""
    items = database.list_items(db, user["id"])
    known = {i["id"]: i for i in items}
    missing = [i for i in body.item_ids if i not in known]
    if missing:
        raise HTTPException(status_code=400, detail="Some of these pieces are no longer in your wardrobe.")
    ids = list(dict.fromkeys(body.item_ids))
    name = body.name or " + ".join(known[i]["name"] for i in ids
                                   if known[i]["category"] == "Clothing") or "Outfit"
    entry = looks_db.log_outfit_wear(db, user["id"], ids, name[:80], body.occasion, body.worn_on or date.today())
    return _history_out(db, entry, items)


@router.get("/history", response_model=list[HistoryEntry])
def outfit_history(db: Db, user: auth.User):
    items = database.list_items(db, user["id"])
    return [_history_out(db, entry, items) for entry in looks_db.list_history(db, user["id"])]


@router.delete("/history/{wear_id}", status_code=204)
def delete_history_entry(wear_id: int, db: Db, user: auth.User):
    if looks_db.get_wear(db, wear_id, user["id"]) is None:
        raise HTTPException(status_code=404, detail="History entry not found.")
    looks_db.delete_wear(db, wear_id)


# ---------- verified photos (you wearing a saved look) ----------

@router.post("/looks/{look_id}/photo", response_model=LookOut, status_code=201)
def upload_look_photo(
    look_id: int,
    db: Db,
    user: auth.User,
    photo: Annotated[UploadFile, File(description="Your photo wearing this look: JPEG, PNG or WebP, up to 5 MB")],
):
    """Attach your own photo of this look. It's shown as a verified preview while the look is unchanged."""
    look = _get_look_or_404(db, look_id, user["id"])
    if not look["item_ids"]:
        raise HTTPException(status_code=400, detail="This look has no pieces left.")
    try:
        filename = storage.save_image(photo)
    except storage.InvalidImage as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    try:
        old = looks_db.set_photo(db, look_id, filename, look["item_ids"])
    except Exception:
        storage.delete_image(filename)
        raise
    if old:
        storage.delete_image(old)
    return _look_out(db, looks_db.get_look(db, look_id))


@router.get("/looks/{look_id}/photo")
def get_look_photo(look_id: int, db: Db, user: auth.User):
    _get_look_or_404(db, look_id, user["id"])
    photo = looks_db.get_photo(db, look_id)
    path = storage.image_path(photo["image_filename"]) if photo else None
    if path is None:
        raise HTTPException(status_code=404, detail="This look has no photo.")
    return FileResponse(path, headers={"Cache-Control": storage.PHOTO_CACHE})


@router.delete("/looks/{look_id}/photo", status_code=204)
def delete_look_photo(look_id: int, db: Db, user: auth.User):
    _get_look_or_404(db, look_id, user["id"])
    old = looks_db.delete_photo(db, look_id)
    if old is None:
        raise HTTPException(status_code=404, detail="This look has no photo.")
    storage.delete_image(old)
