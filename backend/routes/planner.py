"""Planning routes: what to buy next (wardrobe gaps) and what to pack for a trip."""
import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends

from datetime import date

from fastapi import Query

import auth
import database
import looks_db
from recommender.events import function_list, plan_event
from recommender.planner import find_gaps, plan_trip, wear_stats
from schemas import EventFunction, EventRequest, GapReport, TripPlan, TripRequest, WearStats, item_out

router = APIRouter(prefix="/api", tags=["planning"])
Db = Annotated[sqlite3.Connection, Depends(database.get_db)]


@router.get("/insights/gaps", response_model=GapReport)
def wardrobe_gaps(db: Db, user: auth.User):
    """The few purchases that would unlock the most new outfits from your wardrobe."""
    report = find_gaps(database.list_items(db, user["id"]), profile=database.get_style_profile(db, user["id"]))
    for s in report["suggestions"]:
        s["pairs_with"] = [item_out(i) for i in s["pairs_with"]]
    return report


def _plan_out(plan: dict) -> dict:
    for day in plan["days"]:
        if day["outfit"]:
            for piece in day["outfit"]["pieces"]:
                piece["item"] = item_out(piece["item"])
    for packed in plan["packing"]:
        packed["item"] = item_out(packed["item"])
    return plan


@router.post("/trips/plan", response_model=TripPlan)
def trip_plan(request: TripRequest, db: Db, user: auth.User):
    """An outfit for each day of a trip, no garment worn twice."""
    return _plan_out(plan_trip(database.list_items(db, user["id"]), request.days, request.style))


@router.get("/events/functions", response_model=list[EventFunction])
def event_functions(user: auth.User):
    """Wedding functions Peheraav can plan, with their usual dress codes."""
    return function_list()


@router.post("/events/plan", response_model=TripPlan)
def event_plan(request: EventRequest, db: Db, user: auth.User):
    """A different look for each function (haldi, mehendi, sangeet...), following its dress code."""
    return _plan_out(plan_event(database.list_items(db, user["id"]), request.functions, request.style))


@router.get("/insights/wear", response_model=WearStats)
def wardrobe_wear(db: Db, user: auth.User, days: Annotated[int, Query(ge=7, le=365)] = 30):
    """How much each piece is worn: not worn in N days, most worn, and cost per wear."""
    stats = wear_stats(database.list_items(db, user["id"]), looks_db.item_wear(db, user["id"]), date.today(), days)
    for key in ("not_worn", "most_worn", "cost_per_wear"):   # a piece can appear in several lists
        stats[key] = [{**row, "item": item_out(row["item"])} for row in stats[key]]
    return stats
