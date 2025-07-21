from dataclasses import dataclass
from typing import List, Optional, Dict, Tuple, Any
from enum import Enum
from models.road import Road, RoadType
from datetime import datetime

class RoadFuelAttribute(str, Enum):
    ROAD_TYPE = "road_type"
    SLOPE = "slope"
    SURFACE_TYPE = "surface_type"
    CONDITION = "condition"
    IS_TOLL_ROAD = "is_toll_road"
    IS_TUNNEL = "is_tunnel"
    IS_BRIDGE = "is_bridge"
    HAS_SPEED_BUMPS = "has_speed_bumps"
    SHOULDER_TYPE = "shoulder_type"

from enum import Enum

class SurfaceType(str, Enum):
    # Existing entries
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
    PAVING_STONES = "PAVING_STONES"
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
    RUBBER = "RUBBER"
    BLOCKS = "BLOCKS"
    GRASS_UNPAVED = "GRASS;UNPAVED"
    COBBLESTONE_FLATTENED = "COBBLESTONE:FLATTENED"
    UNPAVED_PAVED = "UNPAVED;PAVED"
    ONE = "1"
    DIRT_GROUND = "DIRT;GROUND"
    ASPHALT_GROUND = "ASPHALT;GROUND"
    UNPAVED_GRAVEL = "UNPAVED;GRAVEL"
    STEPPING_STONES = "STEPPING_STONES"
    GROUND_DIRT = "GROUND;DIRT"
    CEMENT = "CEMENT"
    PAVING_TILE = "PAVING_TILE"
    TILES = "TILES"
    UNPAVED_GRAVEL_COMMA = "UNPAVED,GRAVEL"
    TRACK = "TRACK"
    
    # New entries from your list
    SLAG = "SLAG"
    LIVE = "LIVE"
    STONE = "STONE"
    TAR = "TAR"
    SAND_GRAVEL = "SAND;GRAVEL"
    CONCRETE_AND_GRAVEL = "CONCRETE AND GRAVEL"
    TARMAC = "TARMAC"
    ASPHALT_MAXHEIGHT = "ASPHALTMAXHEIGHT=4.5"
    PRAIRIE = "PRAIRIE"
    CONCRETE_METAL = "CONCRETE/METAL"
    COMPACTED_SAND = "COMPACTED/SAND"
    CONCRETE_300M_AND_GRAVEL = "CONCRETE (300M) AND GRAVEL"
    METAL_GROUND = "METAL,GROUND"
    CONCRETE_GAVEL = "CONCRETE_GAVEL"
    FINE = "FINE"
    RUBBERCRUMB = "RUBBERCRUMB"
    GRASS_SAND = "GRASS,SAND"
    DIRT_GRASS = "DIRT/GRASS"
    WOODEN_CHIPS = "WOODEN_CHIPS"
    MIXED = "MIXED"
    GRASS_AND_SAND = "GRASS_AND_SAND"
    GRASS_CONCRETE_STEPS = "GRASS,CONCRETE_STEPS"
    ASPHALT_CARPETED = "ASPHALT; CARPETED"
    DIRT_SAND = "DIRT/SAND"
    CARPETED_ROAD = "CARPETED_ROAD"
    CONCRETE_SLABS = "CONCRETE:SLABS"
    GROUND_PAVED = "GROUND+PAVED"
    TWO_M_KURUKKU_ROAD = "2M KURUKKU ROAD"
    GRAVEL_CEMENT = "GRAVEL,CEMENT"
    ANURADHAPURA = "ANURADHAPURA"
    MASON = "MASON"
    BOULDERS = "BOULDERS"
    WOOD_GROUND = "WOOD;GROUND"
    SAND_AND_GRASS = "SAND_AND_GRASS"
    ROAD = "ROAD"
    NO = "NO"
    GROUND_GRAVEL = "GROUND;GRAVEL"
    VINUSHA = "VINUSHA"
    PATH = "PATH"
    CONCRETE_GRAVEL = "CONCRETE/GRAVEL"
    STONES = "STONES"
    MACADAM = "MACADAM"
    EARTH_DASH = "EARTH--"
    PAVING_STONES_ASPHALT = "PAVING_STONES; ASPHALT"
    ASPHALT_GRAVEL = "ASPHALT,GRAVEL"
    BRICK = "BRICK"
    ASPHALT_LANES = "ASPHALT:LANES"
    CONCRETE_PLATES = "CONCRETE_PLATES"
    HARD_SOIL = "HARD SOIL"
    CONCRETE_PLATES_ = "CONCRETE:PLATES"
    
    # Cyrillic and special characters (consider normalizing these)
    GRUNT = "ГРУНТ"
    ASFALT_BETON = "АСФАЛЬТ_БЕТОН"
    PES = "ПЁС"
    SREDNIY_HREBET = "СРЕДНИЙ_ХРЕБЕТ"
    HRUNT = "НРУНТ"
    ORANGE_TPMS_HYD9100 = "ORANGE_TPMS_HYD9100_КУПИТЬ"
    AS_PS = "AS, PS"
    TAAR = "TAAR"
    
    @classmethod
    def _missing_(cls, value):
        """Handle case-insensitive lookup and normalization"""
        value = value.upper().replace(' ', '_')
        for member in cls:
            if member.value.upper() == value:
                return member
        return cls.UNKNOWN


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
    speed: Optional[float] = None                # in km/h
    free_flow_speed: Optional[float] = None      # in km/h
    current_travel_time: Optional[float] = None  # in seconds
    free_flow_travel_time: Optional[float] = None
    confidence: Optional[float] = None           # 0.0 to 1.0
    road_closure: Optional[bool] = False
    segment_coordinates: Optional[List[Tuple[float, float]]] = None
    received: Optional[float] = None             # timestamp
    jam_factor: Optional[float] = None           # computed field

    @classmethod
    def from_api_response(cls, api_data: Dict) -> 'TrafficData':
        """Create TrafficData from TomTom traffic API response"""
        speed = api_data.get('currentSpeed')
        free_flow_speed = api_data.get('freeFlowSpeed')

        # Estimate jam factor if both speeds are present
        jam_factor = None
        if speed and free_flow_speed and free_flow_speed > 0:
            jam_factor = max(0.0, min(1.0, 1 - (speed / free_flow_speed)))

        coords_raw = api_data.get('segmentCoordinates', [])
        coords = [(pt['latitude'], pt['longitude']) for pt in coords_raw] if coords_raw else None

        return cls(
            speed=speed,
            free_flow_speed=free_flow_speed,
            current_travel_time=api_data.get('currentTravelTime'),
            free_flow_travel_time=api_data.get('freeFlowTravelTime'),
            confidence=api_data.get('confidence'),
            road_closure=api_data.get('roadClosure'),
            segment_coordinates=coords,
            received=api_data.get('received'),
            jam_factor=jam_factor
        )


@dataclass
class WeatherData:
    weather_factor: float
    temperature: Optional[float] = None        # °C
    temperature_apparent: Optional[float] = None # °C (feels-like temperature)
    precipitation: Optional[float] = None      # mm/h (sum of all precipitation types)
    wind_speed: Optional[float] = None         # m/s
    wind_gust: Optional[float] = None          # m/s
    wind_direction: Optional[float] = None     # degrees (0-360)
    humidity: Optional[float] = None           # %
    visibility: Optional[float] = None         # meters
    cloud_cover: Optional[float] = None        # %
    snow_intensity: Optional[float] = None     # mm/h (NOT snow depth)
    pressure: Optional[float] = None           # hPa
    uv_index: Optional[int] = None             # 0-11 scale
    weather_code: Optional[int] = None         # categorical weather condition

    @classmethod
    def from_api_response(cls, api_data: Dict) -> 'WeatherData':
        """
        Creates WeatherData from Tomorrow.io API response.
        Note: snowIntensity is rate of snowfall (mm/h), not snow depth.
        For depth, you would need historical accumulation data.
        """
        values = api_data.get("data", {}).get("values", {})
        
        # Calculate weather factor based on multiple parameters
        weather_factor = cls.calculate_weather_factor(values)
        
        return cls(
            weather_factor=weather_factor,
            temperature=values.get("temperature"),
            temperature_apparent=values.get("temperatureApparent"),
            precipitation=sum([
                values.get("rainIntensity", 0),
                values.get("sleetIntensity", 0),
                values.get("snowIntensity", 0)
            ]) or None,
            wind_speed=values.get("windSpeed"),
            wind_gust=values.get("windGust"),
            wind_direction=values.get("windDirection"),
            humidity=values.get("humidity"),
            visibility=values.get("visibility", 0) * 1000 if values.get("visibility") is not None else None,
            cloud_cover=values.get("cloudCover"),
            snow_intensity=values.get("snowIntensity"),
            pressure=values.get("pressureSurfaceLevel"),
            uv_index=values.get("uvIndex"),
            weather_code=values.get("weatherCode")
        )

    @staticmethod
    def calculate_weather_factor(values: Dict) -> float:
        """
        Calculates a composite weather factor (0-1) for fuel optimization.
        Consider extending this with your specific optimization logic.
        """
        base_factor = 1.0
        
        # Example adjustments (customize these weights based on your needs)
        if values.get("rainIntensity", 0) > 0:
            base_factor *= 0.9  # 10% penalty for rain
        if values.get("snowIntensity", 0) > 0:
            base_factor *= 0.8  # 20% penalty for snow
        if values.get("windSpeed", 0) > 10:  # 10 m/s ~ 36 km/h
            base_factor *= 0.85
        if values.get("temperature") < 0:  # Below freezing
            base_factor *= 0.9
            
        return round(base_factor, 2)

@dataclass
class RoadProfile:
    road: Road
    length: float
    surface_type: SurfaceType
    condition: RoadCondition
    is_toll_road: bool
    is_tunnel: bool
    is_bridge: bool
    has_speed_bumps: bool
    number_of_lanes: int
    shoulder_type: ShoulderType
    traffic_data: Optional[TrafficData] = None
    weather_data: Optional[WeatherData] = None

    @classmethod
    def build_profile(cls, 
            road: Road, 
            traffic_data: Optional[Dict] = None, 
            weather_data: Optional[Dict] = None):
        return cls(
            road=road,
            length=road.length,
            surface_type=SurfaceType(road.osm_tags.get("surface", "UNKNOWN").upper()),
            condition=RoadCondition.UNKNOWN,
            is_toll_road=road.osm_tags.get("toll") == "yes",
            is_tunnel=road.osm_tags.get("tunnel") == "yes",
            is_bridge=road.osm_tags.get("bridge") == "yes",
            has_speed_bumps="traffic_calming" in road.osm_tags,
            number_of_lanes=int(str(road.osm_tags.get("lanes", 1)).strip('`\'" ')),
            shoulder_type=ShoulderType.UNKNOWN,
            traffic_data=TrafficData.from_api_response(traffic_data) if traffic_data else None,
            weather_data=WeatherData.from_api_response(weather_data) if weather_data else None,
        )


@dataclass
class FuelPoint:
    timestamp: datetime
    fuel_level: float  # in liters
    speed: float  # km/h
    road_profile : RoadProfile
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    gps_speed: Optional[float] = None

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
    attr_coefficients: Dict[str, Optional[Dict[Any, float]]]
    attr_segments: Dict[str, List[List['FuelPoint']]]
    fuel_points: List['FuelPoint']

@dataclass
class FleetFuelProfile:
    vehicles: List[VehicleFuelProfile]
    average_attr_coefficients: Dict[str, Dict[Any, float]]
    median_attr_coefficients: Dict[str, Dict[Any, float]]
