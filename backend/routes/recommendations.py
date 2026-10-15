"""API route that turns a styling request into outfits from the user's wardrobe."""
import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

import database
from recommender.engine import RecommendationError, recommend
from schemas import RecommendationRequest, RecommendationResponse, item_out

router = APIRouter(prefix="/api", tags=["stylist"])


@router.post("/recommendations", response_model=RecommendationResponse)
def get_recommendations(
    request: RecommendationRequest,
    db: Annotated[sqlite3.Connection, Depends(database.get_db)],
):
    """Suggest up to 4 distinct outfits using only items in the wardrobe."""
    items = database.list_items(db)
    try:
        result = recommend(items, request)
    except RecommendationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None

    for outfit in result["outfits"]:
        for piece in outfit["pieces"]:
            piece["item"] = item_out(piece["item"])
    return result
