from typing import List, Tuple, Optional
from pydantic import BaseModel


class Coordinate(BaseModel):
    lat: float
    lon: float


class RouteRequest(BaseModel):
    start: Coordinate
    end: Coordinate


class Segment(BaseModel):
    osm_ids: List[List[int]]
    distance: float
    time: float


class RouteResponse(BaseModel):
    default: Segment
    custom: Segment
    fuel_saving_liters: Optional[float] = None
    fuel_saving_percent: Optional[float] = None
    distance_diff: Optional[float] = None
    time_diff: Optional[float] = None
