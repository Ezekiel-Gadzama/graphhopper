from typing import Optional
from models.data_class import RoadProfile, TrafficData, WeatherData
from models.data_class import RoadProfile, RoadType, SurfaceType, RoadCondition

class RoadCoefficientProcessor:
    """
    Processes road profile features to calculate a combined priority coefficient
    that can be used as a multiplier in custom routing models.
    """
    
    @classmethod
    def process_road_coefficient(cls, road_profile: RoadProfile) -> float:
        """
        Calculate a combined priority coefficient based on road features.
        Returns a multiplier value where:
        - >1.0 means higher priority (better conditions)
        - 1.0 means neutral
        - <1.0 means lower priority (worse conditions)
        """
        # Initialize with baseline coefficient
        coefficient = 1.0
        
        # Process each feature category
        coefficient *= cls._process_road_type(road_profile.road.road_type)
        coefficient *= cls._process_surface_type(road_profile.surface_type)
        coefficient *= cls._process_road_condition(road_profile.condition)
        coefficient *= cls._process_traffic(road_profile.traffic_data)
        coefficient *= cls._process_weather(road_profile.weather_data)
        coefficient *= cls._process_slope(road_profile.slope)
        coefficient *= cls._process_road_features(road_profile)
        
        # Apply any final adjustments
        coefficient = cls._final_adjustments(coefficient)
        
        return coefficient
    
    @staticmethod
    def _process_road_type(road_type: RoadType) -> float:
        """Calculate coefficient based on road type"""
        road_type_weights = {
            RoadType.MOTORWAY: 1.3,
            RoadType.TRUNK: 1.2,
            RoadType.PRIMARY: 1.1,
            RoadType.SECONDARY: 1.0,
            RoadType.TERTIARY: 0.9,
            RoadType.UNCLASSIFIED: 0.8,
            RoadType.RESIDENTIAL: 0.7,
            RoadType.SERVICE: 0.6,
            RoadType.UNKNOWN: 0.8
        }
        return road_type_weights.get(road_type, 1.0)
    
    @staticmethod
    def _process_surface_type(surface_type: SurfaceType) -> float:
        """Calculate coefficient based on surface type"""
        surface_weights = {
            SurfaceType.ASPHALT: 1.0,
            SurfaceType.CONCRETE: 0.95,
            SurfaceType.PAVEMENT_STONES: 0.85,
            SurfaceType.COMPACTED_GRAVEL: 0.8,
            SurfaceType.DIRT: 0.7,
            SurfaceType.GRASS: 0.6,
            SurfaceType.METAL: 0.9,
            SurfaceType.SAND: 0.5,
            SurfaceType.WOOD: 0.8,
            SurfaceType.UNKNOWN: 0.9
        }
        return surface_weights.get(surface_type, 1.0)
    
    @staticmethod
    def _process_road_condition(condition: RoadCondition) -> float:
        """Calculate coefficient based on road condition"""
        condition_weights = {
            RoadCondition.EXCELLENT: 1.2,
            RoadCondition.GOOD: 1.1,
            RoadCondition.FAIR: 1.0,
            RoadCondition.POOR: 0.8,
            RoadCondition.VERY_POOR: 0.6,
            RoadCondition.UNKNOWN: 1.0
        }
        return condition_weights.get(condition, 1.0)
    
    @staticmethod
    def _process_traffic(traffic_data: Optional[TrafficData]) -> float:
        """Calculate coefficient based on traffic conditions"""
        if not traffic_data:
            return 1.0
            
        # Base traffic coefficient
        traffic_coeff = 1.0 - (traffic_data.jam_factor * 0.5)  # Jam factor 0-1
        
        # Speed ratio adjustment
        if traffic_data.speed and traffic_data.free_flow_speed:
            speed_ratio = traffic_data.speed / traffic_data.free_flow_speed
            traffic_coeff *= 0.8 + (speed_ratio * 0.4)  # Maps 0-1 to 0.8-1.2
            
        return max(0.5, min(1.5, traffic_coeff))  # Clamp between 0.5-1.5
    
    @staticmethod
    def _process_weather(weather_data: Optional[WeatherData]) -> float:
        """Calculate coefficient based on weather conditions"""
        if not weather_data:
            return 1.0
            
        # Start with weather factor if provided
        weather_coeff = weather_data.weather_factor
        
        # Temperature adjustment (optimal around 20°C)
        if weather_data.temperature is not None:
            temp_diff = abs(20 - weather_data.temperature)
            weather_coeff *= 1.0 - (temp_diff * 0.01)  # 1% reduction per °C from ideal
            
        # Precipitation adjustment
        if weather_data.precipitation is not None:
            weather_coeff *= 1.0 - (min(weather_data.precipitation, 50) * 0.01)  # 1% reduction per mm up to 50mm
            
        return max(0.3, min(1.2, weather_coeff))  # Clamp between 0.3-1.2
    
    @staticmethod
    def _process_slope(slope_percent: float) -> float:
        """
        Calculate fuel efficiency coefficient based on road slope.
        Uphill reduces efficiency, downhill might improve it slightly or keep it neutral.
        """
        slope = slope_percent

        if -2 <= slope <= 2:
            return 1.0  # Flat or very gentle slope
        elif slope > 2:
            # Uphill — more fuel
            if slope < 5:
                return 0.95
            elif slope < 8:
                return 0.9
            elif slope < 12:
                return 0.85
            else:
                return 0.8
        elif slope < -2:
            # Downhill — less fuel
            if slope > -5:
                return 1.05
            elif slope > -8:
                return 1.1
            else:
                return 1.15

    
    @staticmethod
    def _process_road_features(road_profile: RoadProfile) -> float:
        """Calculate coefficient based on special road features"""
        feature_coeff = 1.0
        
        if road_profile.is_toll_road:
            feature_coeff *= 1.1  # Toll roads often better maintained
            
        if road_profile.is_tunnel:
            feature_coeff *= 0.9  # Slightly penalize tunnels
            
        if road_profile.is_bridge:
            feature_coeff *= 0.95  # Slightly penalize bridges
            
        if road_profile.has_speed_bumps:
            feature_coeff *= 0.85  # Speed bumps reduce efficiency
            
        # Adjust for number of lanes
        if road_profile.number_of_lanes >= 4:
            feature_coeff *= 1.1
        elif road_profile.number_of_lanes <= 1:
            feature_coeff *= 0.9
            
        return feature_coeff
    
    @staticmethod
    def _final_adjustments(coefficient: float) -> float:
        """Apply any final adjustments to the coefficient"""
        # Round to 2 decimal places
        return round(coefficient, 2)