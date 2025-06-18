from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
from enum import Enum
import json
from datetime import datetime

@dataclass
class TrafficData:
    jam_factor: float
    speed: Optional[float] = None
    free_flow_speed: Optional[float] = None

@dataclass
class WeatherData:
    weather_factor: float
    temperature: Optional[float] = None
    precipitation: Optional[float] = None

class RoadType(str, Enum):
    MOTORWAY = "motorway"
    TRUNK = "trunk"
    PRIMARY = "primary"
    SECONDARY = "secondary"
    TERTIARY = "tertiary"
    UNCLASSIFIED = "unclassified"
    RESIDENTIAL = "residential"
    SERVICE = "service"

@dataclass
class FuelPoint:
    timestamp: datetime
    fuel_level: float  # in liters
    speed: float  # km/h
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    gps_speed: Optional[float] = None
    road_type: Optional[RoadType] = None

@dataclass
class RoadSegment:
    start_point: FuelPoint
    end_point: FuelPoint
    distance: float  # in meters
    fuel_consumption: float  # in liters
    road_type: RoadType
    duration: float  # in seconds

@dataclass
class VehicleFuelProfile:
    vehicle_id: str
    vehicle_type: str
    segments: List[RoadSegment]
    coefficients: Dict[RoadType, float]

@dataclass
class FleetFuelProfile:
    vehicles: List[VehicleFuelProfile]
    average_coefficients: Dict[RoadType, float]
    median_coefficients: Dict[RoadType, float]