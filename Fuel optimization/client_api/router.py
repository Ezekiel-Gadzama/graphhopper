from fastapi import APIRouter, HTTPException
from .models import RouteRequest, RouteResponse
from .service import get_routes, compare_and_compute
import json

router = APIRouter()

# Load the custom model once
with open("custom_model.json") as f:
    CUSTOM_MODEL = json.load(f)

@router.post("/route", response_model=RouteResponse)
def route_with_comparison(req: RouteRequest):
    routes = get_routes(req.start, req.end, CUSTOM_MODEL)

    if not routes["default"] or not routes["custom"]:
        raise HTTPException(status_code=500, detail="Failed to fetch routes.")

    result = compare_and_compute(routes["default"], routes["custom"])
    return result