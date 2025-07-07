from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple
from enum import Enum
from models.road import Road
import json
from datetime import datetime

class SurfaceType(str, Enum):
    ASPHALT = "ASPHALT"
    CONCRETE = "CONCRETE"
    PAVEMENT_STONES = "PAVEMENT_STONES"
    COMPACTED_GRAVEL = "COMPACTED_GRAVEL"
    DIRT = "DIRT"
    GRASS = "GRASS"
    METAL = "METAL"
    SAND = "SAND"
    WOOD = "WOOD"
    UNKNOWN = "UNKNOWN"

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
    temperature: Optional[float] = None    # in °C
    precipitation: Optional[float] = None  # in mm

    @classmethod
    def from_api_response(cls, api_data: Dict) -> 'WeatherData':
        """Create WeatherData from raw API response"""
        return cls(
            weather_factor=api_data.get('weatherFactor', 1.0),  # Default to 1.0 (no impact)
            temperature=api_data.get('temperature'),
            precipitation=api_data.get('precipitation')
        )

@dataclass
class RoadProfile:
    road: Road
    length: float
    surface_type: SurfaceType
    condition: RoadCondition
    elevation: float
    is_toll_road: bool
    is_tunnel: bool
    is_bridge: bool
    has_speed_bumps: bool
    number_of_lanes: int
    shoulder_type: ShoulderType
    traffic_data: Optional[TrafficData] = None
    weather_data: Optional[WeatherData] = None

    @classmethod
    def from_here_api(cls, road: Road, road_traffic_data: Dict, road_terrain_data: Dict, road_weather_data: Dict):
        """Factory method to create RoadProfile from HERE API response"""
        # Convert raw API data to proper data classes
        traffic_data = (
            TrafficData.from_api_response(road_traffic_data) 
            if road_traffic_data else None
        )
        
        weather_data = (
            WeatherData.from_api_response(road_weather_data)
            if road_weather_data else None
        )

        # Extract attributes from traffic data (assuming this contains road attributes)
        attrs = road_traffic_data.get("attributes", {})
        
        return cls(
            road=road,
            length=road_terrain_data.get("length", road.length),  # Fallback to road.length
            surface_type=SurfaceType(attrs.get("surfaceType", "UNKNOWN")),
            condition=RoadCondition(attrs.get("condition", "UNKNOWN")),
            elevation=road_terrain_data.get("elevation", 0.0),
            is_toll_road=attrs.get("isTollRoad", False),
            is_tunnel=attrs.get("isTunnel", False),
            is_bridge=attrs.get("isBridge", False),
            has_speed_bumps=attrs.get("hasSpeedBumps", False),
            number_of_lanes=attrs.get("numberOfLanes", 1),
            shoulder_type=ShoulderType(attrs.get("shoulderType", "UNKNOWN")),
            traffic_data=traffic_data,
            weather_data=weather_data
        )

class RoadType(str, Enum):
    MOTORWAY = "motorway"
    TRUNK = "trunk"
    PRIMARY = "primary"
    SECONDARY = "secondary"
    TERTIARY = "tertiary"
    UNCLASSIFIED = "unclassified"
    RESIDENTIAL = "residential"
    SERVICE = "service"
    UNKNOWN = "unknown"

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