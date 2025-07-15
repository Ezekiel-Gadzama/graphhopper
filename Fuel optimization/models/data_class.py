from dataclasses import dataclass
from typing import List, Optional, Dict
from enum import Enum
from models.road import Road
import json
from datetime import datetime

class SurfaceType(str, Enum):
    ACRYLIC = "ACRYLIC"
    ARTIFICIAL_TURF = "ARTIFICIAL_TURF"
    ASPHALT = "ASPHALT"
    BRICKS = "BRICKS"
    CARPET = "CARPET"
    CHIPSEAL = "CHIPSEAL"
    CLAY = "CLAY"
    COBBLESTONE = "COBBLESTONE"
    COMPACTED = "COMPACTED"
    COMPACTED_GRAVEL = "COMPACTED_GRAVEL"
    CONCRETE = "CONCRETE"
    CONCRETE_LANES = "CONCRETE:LANES"
    CONCRETE_PLATES = "CONCRETE:PLATES"
    DIRT = "DIRT"
    EARTH = "EARTH"
    FINE_GRAVEL = "FINE_GRAVEL"
    GRASS = "GRASS"
    GRASS_PAVER = "GRASS_PAVER"
    GRAVEL = "GRAVEL"
    GROUND = "GROUND"
    ICE = "ICE"
    METAL = "METAL"
    METAL_GRID = "METAL_GRID"
    MUD = "MUD"
    PAVED = "PAVED"
    PAVEMENT_STONES = "PAVING_STONES"
    PAVING_STONES_LANES = "PAVING_STONES:LANES"
    PEBBLESTONE = "PEBBLESTONE"
    PLASTIC = "PLASTIC"
    ROCK = "ROCK"
    SALT = "SALT"
    SAND = "SAND"
    SETT = "SETT"
    SNOW = "SNOW"
    TARTAN = "TARTAN"
    UNHEWN_COBBLESTONE = "UNHEWN_COBBLESTONE"
    UNPAVED = "UNPAVED"
    UNKNOWN = "UNKNOWN"
    WOOD = "WOOD"
    WOODCHIPS = "WOODCHIPS"

class RoadCondition(str, Enum):
    EXCELLENT = "EXCELLENT"
    GOOD = "GOOD"
    FAIR = "FAIR"
    POOR = "POOR"
    VERY_POOR = "VERY_POOR"
    UNKNOWN = "UNKNOWN"

class ShoulderType(str, Enum):
    NONE = "NONE"
    HARD = "HARD"
    SOFT = "SOFT"
    UNKNOWN = "UNKNOWN"

@dataclass
class TrafficData:
    jam_factor: float
    speed: Optional[float] = None          # in km/h
    free_flow_speed: Optional[float] = None  # in km/h

    @classmethod
    def from_api_response(cls, api_data: Dict) -> 'TrafficData':
        """Create TrafficData from raw API response"""
        return cls(
            jam_factor=api_data.get('jamFactor', 0.0),
            speed=api_data.get('speed'),
            free_flow_speed=api_data.get('freeFlowSpeed')
        )

@dataclass
class WeatherData:
    weather_factor: float
    temperature: Optional[float] = None    # °C
    precipitation: Optional[float] = None  # mm
    wind_speed: Optional[float] = None     # km/h or m/s
    wind_direction: Optional[float] = None # degrees
    humidity: Optional[float] = None       # %
    visibility: Optional[float] = None     # meters
    cloud_cover: Optional[float] = None    # %
    snow_depth: Optional[float] = None     # mm
    pressure: Optional[float] = None       # hPa

    @classmethod
    def from_api_response(cls, api_data: Dict) -> 'WeatherData':
        """Create WeatherData from raw Tomorrow.io API response"""
        return cls(
            weather_factor=api_data.get('weatherFactor', 1.0),
            temperature=api_data.get('temperature'),
            precipitation=api_data.get('precipitation'),
            wind_speed=api_data.get('windSpeed'),
            wind_direction=api_data.get('windDirection'),
            humidity=api_data.get('humidity'),
            visibility=api_data.get('visibility'),
            cloud_cover=api_data.get('cloudCover'),
            snow_depth=api_data.get('snowDepth'),
            pressure=api_data.get('pressure')
        )

@dataclass
class RoadProfile:
    road: Road
    length: float
    surface_type: SurfaceType
    condition: RoadCondition
    slope: float
    is_toll_road: bool
    is_tunnel: bool
    is_bridge: bool
    has_speed_bumps: bool
    number_of_lanes: int
    shoulder_type: ShoulderType
    traffic_data: Optional[TrafficData] = None
    weather_data: Optional[WeatherData] = None

    @classmethod
    def from_osm_api_combined(cls, 
            road: Road, 
            traffic_data: Dict, 
            slope: list, 
            weather_data: Dict):
        return cls(
            road=road,
            length=road.length,
            surface_type=SurfaceType(road.osm_tags.get("surface", "UNKNOWN").upper()),
            condition=RoadCondition.UNKNOWN,
            slope=slope,
            is_toll_road=road.osm_tags.get("toll") == "yes",
            is_tunnel=road.osm_tags.get("tunnel") == "yes",
            is_bridge=road.osm_tags.get("bridge") == "yes",
            has_speed_bumps="traffic_calming" in road.osm_tags,
            number_of_lanes=int(road.osm_tags.get("lanes", 1)),
            shoulder_type=ShoulderType.UNKNOWN,
            traffic_data=TrafficData.from_api_response(traffic_data),
            weather_data=WeatherData.from_api_response(weather_data),
        )

class RoadType(str, Enum):
    MOTORWAY = "MOTORWAY"
    TRUNK = "TRUNK"
    PRIMARY = "PRIMARY"
    SECONDARY = "SECONDARY"
    TERTIARY = "TERTIARY"
    UNCLASSIFIED = "UNCLASSIFIED"
    RESIDENTIAL = "RESIDENTIAL"
    SERVICE = "SERVICE"
    TRACK = "TRACK"
    REST_AREA = "REST_AREA"
    UNKNOWN = "UNKNOWN"

@dataclass
class FuelPoint:
    timestamp: datetime
    fuel_level: float  # in liters
    speed: float  # km/h
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    gps_speed: Optional[float] = None
    road_type: Optional[RoadType] = None
    osm_roadID: Optional[int] = None

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
    fuel_points: List[FuelPoint]

@dataclass
class FleetFuelProfile:
    vehicles: List[VehicleFuelProfile]
    average_coefficients: Dict[RoadType, float]
    median_coefficients: Dict[RoadType, float]