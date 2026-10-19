"""Planning routes: what to buy next (wardrobe gaps) and what to pack for a trip."""
import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends

import database
from recommender.planner import find_gaps, plan_trip
from schemas import GapReport, TripPlan, TripRequest, item_out

router = APIRouter(prefix="/api", tags=["planning"])
Db = Annotated[sqlite3.Connection, Depends(database.get_db)]


@router.get("/insights/gaps", response_model=GapReport)
def wardrobe_gaps(db: Db):
    """The few purchases that would unlock the most new outfits from your wardrobe."""
    report = find_gaps(database.list_items(db))
    for s in report["suggestions"]:
        s["pairs_with"] = [item_out(i) for i in s["pairs_with"]]
    return report


@router.post("/trips/plan", response_model=TripPlan)
def trip_plan(request: TripRequest, db: Db):
    """An outfit for each day of a trip, packing as few pieces as possible."""
    plan = plan_trip(database.list_items(db), request.days, request.style)
    for day in plan["days"]:
        if day["outfit"]:
            for piece in day["outfit"]["pieces"]:
                piece["item"] = item_out(piece["item"])
    for packed in plan["packing"]:
        packed["item"] = item_out(packed["item"])
    return plan
