"""Your optional style profile: height, body shape, fit, undertone, things to avoid, colours, usual style."""
import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends

import auth
import database
from schemas import StyleProfile, StyleProfileOut

router = APIRouter(prefix="/api/profile", tags=["account"])
Db = Annotated[sqlite3.Connection, Depends(database.get_db)]


@router.get("/style", response_model=StyleProfileOut)
def get_style_profile(user: auth.User, db: Db):
    """Your style profile; all empty if you haven't filled it in (or skipped it)."""
    return database.get_style_profile(db, user["id"]) or StyleProfileOut()


@router.patch("/style", response_model=StyleProfileOut)
def update_style_profile(body: StyleProfile, user: auth.User, db: Db):
    """Change parts of your style profile: only the fields you send change (send null or [] to clear one).
    Nothing is required."""
    current = StyleProfile(**(database.get_style_profile(db, user["id"]) or {})).model_dump()
    return database.save_style_profile(db, user["id"], {**current, **body.model_dump(exclude_unset=True)})
