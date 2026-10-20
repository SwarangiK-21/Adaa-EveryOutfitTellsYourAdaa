"""API route that turns a styling request into outfits from the user's wardrobe."""
import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

import database
from datetime import date

import auth
from recommender import festivals
from recommender.engine import RecommendationError, recommend
from recommender.parser import parse_request
from schemas import (
    FestivalNow, ParsedRequest, RecommendationRequest, RecommendationResponse, StylistMessage, item_out,
)

router = APIRouter(prefix="/api", tags=["stylist"])


@router.post("/recommendations", response_model=RecommendationResponse)
def get_recommendations(
    request: RecommendationRequest,
    db: Annotated[sqlite3.Connection, Depends(database.get_db)],
    user: auth.User,
):
    """Suggest up to 4 distinct outfits using only items in your wardrobe."""
    items = database.list_items(db, user["id"])
    try:
        result = recommend(items, request)
    except RecommendationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    for outfit in result["outfits"]:
        for piece in outfit["pieces"]:
            piece["item"] = item_out(piece["item"])
    return result


@router.post("/stylist/parse", response_model=ParsedRequest)
def parse_stylist_message(
    message: StylistMessage,
    db: Annotated[sqlite3.Connection, Depends(database.get_db)],
    user: auth.User,
):
    """Read a typed request like 'Style my black crop top for a party' into filters."""
    return parse_request(message.text, database.list_items(db, user["id"]), date.today())


@router.get("/festivals/now", response_model=FestivalNow | None)
def festival_now():
    """Today's festival and its colour (Navratri: today's colour), or the next one within 3 weeks."""
    return festivals.now(date.today())
