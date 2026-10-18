"""API routes for the user's own photo and virtual try-on."""
import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

import database
import storage
import tryon
from schemas import ProfileOut, TryOnOut, TryOnRequest, TryOnSettings, TryOnStatus

router = APIRouter(prefix="/api", tags=["try-on"])
Db = Annotated[sqlite3.Connection, Depends(database.get_db)]


def _profile(db) -> dict:
    photo = database.get_profile_photo(db)
    settings = tryon.load_settings()
    return {
        "photo_url": f"/api/profile/photo?v={photo['photo_filename'][:8]}" if photo else None,
        "photo_updated_at": photo["updated_at"] if photo else None,
        "tryon_configured": bool(settings["url"] and settings["token"]),
        "tryon_url": settings["url"] or None,
        "tryon_quality": settings["quality"],
        "tryon_shoes": settings["shoes"],
    }


# ---------- your photo ----------

@router.get("/profile", response_model=ProfileOut)
def get_profile(db: Db):
    return _profile(db)


@router.post("/profile/photo", response_model=ProfileOut, status_code=201)
def upload_profile_photo(
    db: Db,
    photo: Annotated[UploadFile, File(description="A full-length, front-facing photo of you: JPEG, PNG or WebP, up to 5 MB")],
):
    try:
        filename = storage.save_image(photo)
    except storage.InvalidImage as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    old = database.set_profile_photo(db, filename)
    if old:
        storage.delete_image(old)
    tryon.clear_cache()  # old try-on images showed the old photo
    return _profile(db)


@router.get("/profile/photo")
def get_profile_photo(db: Db):
    photo = database.get_profile_photo(db)
    path = storage.image_path(photo["photo_filename"]) if photo else None
    if path is None:
        raise HTTPException(status_code=404, detail="You haven't added your photo yet.")
    return FileResponse(path)


@router.delete("/profile/photo", status_code=204)
def delete_profile_photo(db: Db):
    old = database.set_profile_photo(db, None)
    if old is None:
        raise HTTPException(status_code=404, detail="You haven't added your photo yet.")
    storage.delete_image(old)
    tryon.clear_cache()


# ---------- try-on server settings ----------

@router.put("/tryon/settings", response_model=ProfileOut)
def save_tryon_settings(body: TryOnSettings, db: Db):
    """Save the link and token printed by the Colab notebook (empty values switch try-on off)."""
    token = body.token
    if body.url and not token:
        token = tryon.load_settings()["token"]  # only the link changed: keep the saved token
    tryon.save_settings(body.url, token if body.url else "", body.quality, body.try_shoes)
    return _profile(db)


@router.get("/tryon/status", response_model=TryOnStatus)
def tryon_status():
    settings = tryon.load_settings()
    if not (settings["url"] and settings["token"]):
        return {"configured": False, "online": False, "message": "No try-on server set up yet."}
    try:
        about = tryon.check_server(settings["url"], settings["token"])
    except tryon.TryOnError as exc:
        return {"configured": True, "online": False, "message": str(exc)}
    return {"configured": True, "online": True, "message": f"Connected: {about}."}


# ---------- try-on ----------

@router.post("/tryon", response_model=TryOnOut)
def try_on(body: TryOnRequest, db: Db):
    """An image of you wearing these pieces (made by your try-on server, or reused from the cache)."""
    photo = database.get_profile_photo(db)
    if photo is None:
        raise HTTPException(status_code=409, detail="Add your full-length photo first (Preferences → Your photo).")
    by_id = {i["id"]: i for i in database.list_items(db)}
    missing = [i for i in body.item_ids if i not in by_id]
    if missing:
        raise HTTPException(status_code=400, detail="Some of those pieces are no longer in your wardrobe.")
    try:
        return tryon.generate(photo["photo_filename"], [by_id[i] for i in body.item_ids], body.cached_only)
    except tryon.TryOnError as exc:
        raise HTTPException(status_code=exc.status, detail=str(exc)) from None


@router.get("/tryon/images/{name}")
def tryon_image(name: str):
    path = tryon.cached_image(name)
    if path is None:
        raise HTTPException(status_code=404, detail="Try-on image not found.")
    return FileResponse(path, media_type="image/png")
