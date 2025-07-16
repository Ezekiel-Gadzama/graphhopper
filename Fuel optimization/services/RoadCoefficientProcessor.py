from typing import Optional
from models.data_class import RoadProfile, TrafficData, WeatherData, RoadType, SurfaceType, RoadCondition

class RoadCoefficientProcessor:
    """
    Processes a road's physical, environmental, and structural properties to compute
    a priority coefficient used in routing or fuel consumption estimation.
    A higher coefficient implies better conditions (e.g., smooth highway in good weather).
    """

    @classmethod
    def process_road_coefficient(cls, road_profile: RoadProfile) -> float:
        """
        Main entry point to calculate a combined road coefficient.
        
        Args:
            road_profile (RoadProfile): Road information and conditions.

        Returns:
            float: A final multiplier indicating road efficiency or priority.
        """
        coefficient = 1.0

        # Multiply effects of each road feature
        coefficient *= cls._process_road_type(road_profile.road.road_type)
        coefficient *= cls._process_surface_type(road_profile.surface_type)
        coefficient *= cls._process_road_condition(road_profile.condition)
        coefficient *= cls._process_traffic(road_profile.traffic_data)
        coefficient *= cls._process_weather(road_profile.weather_data)
        coefficient *= cls._process_slope(road_profile.slope)
        coefficient *= cls._process_road_features(road_profile)

        # Final clamping adjustments
        return round(cls._final_adjustments(coefficient), 6)

    @staticmethod
    def _process_road_type(road_type: RoadType) -> float:
        """
        Assign coefficient based on road classification.
        Higher values indicate higher suitability/efficiency for driving.
        """
        weights = {
            RoadType.MOTORWAY: 1.3,
            RoadType.MOTORWAY_LINK: 1.25,
            RoadType.TRUNK: 1.2,
            RoadType.TRUNK_LINK: 1.15,
            RoadType.PRIMARY: 1.1,
            RoadType.PRIMARY_LINK: 1.05,
            RoadType.SECONDARY: 1.0,
            RoadType.SECONDARY_LINK: 0.95,
            RoadType.TERTIARY: 0.9,
            RoadType.TERTIARY_LINK: 0.85,
            RoadType.UNCLASSIFIED: 0.8,
            RoadType.RESIDENTIAL: 0.8,
            RoadType.LIVING_STREET: 0.75,
            RoadType.SERVICE: 0.7,
            RoadType.SERVICES: 0.7,
            RoadType.ROAD: 0.9,
            RoadType.TRACK: 0.6,
            RoadType.FOOTWAY: 0.5,
            RoadType.PATH: 0.5,
            RoadType.CYCLEWAY: 0.55,
            RoadType.PEDESTRIAN: 0.5,
            RoadType.BRIDLEWAY: 0.4,
            RoadType.STEPS: 0.4,
            RoadType.SIDEWALK: 0.45,
            RoadType.PLATFORM: 0.4,
            RoadType.BUS_STOP: 0.4,
            RoadType.CORRIDOR: 0.3,
            RoadType.ELEVATOR: 0.2,
            RoadType.VIA_FERRATA: 0.2,
            RoadType.STREET_LAMP: 0.2,
            RoadType.RACEWAY: 0.3,
            RoadType.REST_AREA: 1.0,
            RoadType.CONSTRUCTION: 0.3,
            RoadType.PROPOSED: 0.2,
            RoadType.ABANDONED: 0.1,
            RoadType.UNKNOWN: 0.85,
        }

        return weights.get(road_type, 1.0)

    @staticmethod
    def _process_surface_type(surface_type: SurfaceType) -> float:
        """
        Coefficients based on surface material.
        Smooth surfaces are better for driving; rough or slow surfaces reduce efficiency.
        """
        smooth_surfaces = {
            SurfaceType.ASPHALT, SurfaceType.CONCRETE, SurfaceType.CONCRETE_LANES,
            SurfaceType.CONCRETE_PLATES, SurfaceType.PAVED,
            SurfaceType.METAL, SurfaceType.METAL_GRID
        }

        rough_surfaces = {
            SurfaceType.GRAVEL, SurfaceType.DIRT, SurfaceType.SAND, SurfaceType.CLAY,
            SurfaceType.MUD, SurfaceType.WOODCHIPS, SurfaceType.EARTH
        }

        slow_surfaces = {
            SurfaceType.COBBLESTONE, SurfaceType.UNHEWN_COBBLESTONE, SurfaceType.PAVEMENT_STONES,
            SurfaceType.PAVING_STONES_LANES, SurfaceType.SETT, SurfaceType.ROCK, SurfaceType.RUBBER
        }

        if surface_type in smooth_surfaces:
            return 1.0
        elif surface_type in rough_surfaces:
            return 0.6
        elif surface_type in slow_surfaces:
            return 0.75
        elif surface_type == SurfaceType.UNKNOWN:
            return 0.9
        else:
            return 0.85  # Default for uncommon surfaces

    @staticmethod
    def _process_road_condition(condition: RoadCondition) -> float:
        """
        Adjust coefficient based on physical condition of the road surface.
        """
        weights = {
            RoadCondition.EXCELLENT: 1.2,
            RoadCondition.GOOD: 1.1,
            RoadCondition.FAIR: 1.0,
            RoadCondition.POOR: 0.8,
            RoadCondition.VERY_POOR: 0.6,
            RoadCondition.UNKNOWN: 1.0
        }
        return weights.get(condition, 1.0)

    @staticmethod
    def _process_traffic(traffic_data: Optional[TrafficData]) -> float:
        """
        Adjust coefficient based on real-time traffic conditions.

        Factors considered:
        - jam_factor (if available or estimated)
        - speed / free_flow_speed ratio
        - confidence level
        - road closures (heavily penalized)
        """
        if not traffic_data:
            return 1.0

        coeff = 1.0

        # Heavily penalize closed roads
        if traffic_data.road_closure:
            return 0.3

        # Penalize based on jam factor if available
        if traffic_data.jam_factor is not None:
            coeff *= (1.0 - traffic_data.jam_factor * 0.5)  # reduces from 1.0 to 0.5

        # Consider speed vs free-flow speed ratio
        if traffic_data.speed and traffic_data.free_flow_speed and traffic_data.free_flow_speed > 0:
            speed_ratio = traffic_data.speed / traffic_data.free_flow_speed
            coeff *= 0.8 + (speed_ratio * 0.4)  # favors higher ratio, range ~[0.8, 1.2]

        # Penalize low confidence
        if traffic_data.confidence is not None and traffic_data.confidence < 0.5:
            coeff *= 0.9  # reduce by 10%

        return max(0.3, min(1.5, coeff))  # Clamp to avoid extreme values

    @staticmethod
    def _process_weather(weather_data: Optional[WeatherData]) -> float:
        """
        Adjust coefficient based on weather conditions.
        Cold, wet, or poor visibility lowers the coefficient.
        """
        if not weather_data:
            return 1.0

        coeff = weather_data.weather_factor

        # Penalize temperatures far from 20°C
        if weather_data.temperature is not None:
            temp_diff = abs(20 - weather_data.temperature)
            coeff *= 1.0 - (temp_diff * 0.01)

        # Reduce for high precipitation
        if weather_data.precipitation is not None:
            coeff *= 1.0 - (min(weather_data.precipitation, 50) * 0.01)

        # Additional penalties
        if weather_data.snow_depth and weather_data.snow_depth > 0:
            coeff *= 0.9
        if weather_data.visibility is not None and weather_data.visibility < 500:
            coeff *= 0.85
        if weather_data.wind_speed is not None and weather_data.wind_speed > 50:
            coeff *= 0.95

        return max(0.3, min(1.2, coeff))  # Clamp range

    @staticmethod
    def _process_slope(slope_percent_list: Optional[list[float]]) -> float:
        """
        Combine slope segments into a coefficient.
        Uphill reduces efficiency, downhill may increase slightly.
        """
        if not slope_percent_list:
            return 1.0

        total_coeff = 0.0
        for slope in slope_percent_list:
            if -2 <= slope <= 2:
                total_coeff += 1.0  # Neutral
            elif slope > 2:
                total_coeff += 0.95 if slope < 5 else 0.9 if slope < 8 else 0.85 if slope < 12 else 0.8
            else:
                total_coeff += 1.05 if slope > -5 else 1.1 if slope > -8 else 1.15

        return total_coeff / len(slope_percent_list)

    @staticmethod
    def _process_road_features(road_profile: RoadProfile) -> float:
        """
        Adjust based on features like tolls, tunnels, bridges, bumps, and lanes.
        """
        coeff = 1.0

        if road_profile.is_toll_road:
            coeff *= 1.1  # Often better maintained
        if road_profile.is_tunnel:
            coeff *= 0.9
        if road_profile.is_bridge:
            coeff *= 0.95
        if road_profile.has_speed_bumps:
            coeff *= 0.85

        # Lane-based adjustment
        if road_profile.number_of_lanes >= 4:
            coeff *= 1.1
        elif road_profile.number_of_lanes <= 1:
            coeff *= 0.9

        return coeff

    @staticmethod
    def _final_adjustments(coefficient: float) -> float:
        """
        Final clamping to ensure reasonable bounds.
        """
        return max(0.1, min(2.0, coefficient))  # Clamp result to [0.1, 2.0]
