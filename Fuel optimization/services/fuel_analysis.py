from typing import List, Dict, Any
from services.api.fuel_database import FuelDatabase
from enum import Enum
from models.data_class import (
    RoadType,
    SurfaceType,
    RoadCondition,
    ShoulderType,
    FuelPoint, 
    RoadSegment,
    RoadFuelAttribute,
    VehicleFuelProfile,
    FleetFuelProfile
)
from utils.geo import calculate_distance
from config.settings import settings

class FuelAnalyzer:
    def __init__(self, road_extractor, verbose: int = settings.verbose):
        self.verbose = verbose
        self.road_extractor = road_extractor
        self.road_attributes = list(RoadFuelAttribute)

        # Define base attribute values per attribute
        self.base_attribute_values = {
            RoadFuelAttribute.ROAD_TYPE: RoadType.PRIMARY,
            RoadFuelAttribute.SURFACE_TYPE: SurfaceType.ASPHALT,
            RoadFuelAttribute.CONDITION: RoadCondition.GOOD,
            RoadFuelAttribute.SLOPE: "0.0",  # Flat slope
            RoadFuelAttribute.IS_TOLL_ROAD: False,
            RoadFuelAttribute.IS_TUNNEL: False,
            RoadFuelAttribute.IS_BRIDGE: False,
            RoadFuelAttribute.HAS_SPEED_BUMPS: False,
            RoadFuelAttribute.SHOULDER_TYPE: ShoulderType.HARD
        }

    def _log(self, *args):
        if self.verbose > 0:
            print(*args)

    def process_fuel_data(self, points: List[FuelPoint]) -> List[FuelPoint]:
        """Process and sort fuel data points by timestamp"""
        # Filter out invalid points and stops
        valid_points = [
            p for p in points 
            if p.latitude and p.longitude and p.speed > 0
        ]
        
        # Sort by timestamp in ascending order
        valid_points = sorted(valid_points, key=lambda x: x.timestamp)
        
        return valid_points

    def create_segments(self, points: List[FuelPoint], attribute: str) -> List[RoadSegment]:
        """
        Create segments of fuel points where the specified road attribute remains constant,
        and where fuel level decreases continuously with reasonable time and distance gaps.

        :param points: A list of FuelPoints in chronological order.
        :param attribute: The name of the road attribute to segment by (e.g., 'road_type', 'surface_type').
        :return: A list of RoadSegment objects.
        """
        if not points:
            return []

        segments = []
        current_segment = [points[0]]

        for i in range(1, len(points)):
            prev = current_segment[-1]
            curr = points[i]

            # Check that both points have road profiles
            if not prev.road_profile or not curr.road_profile:
                continue

            # Extract the attribute value from each point
            prev_val = self._get_nested_attr(prev.road_profile, attribute)
            curr_val = self._get_nested_attr(curr.road_profile, attribute)
            if prev_val is None or curr_val is None:
                continue

            # Enforce all segmentation conditions
            time_diff = (curr.timestamp - prev.timestamp).total_seconds()
            distance = calculate_distance(prev.latitude, prev.longitude, curr.latitude, curr.longitude)
            fuel_drop_ok = curr.fuel_level <= prev.fuel_level
            distance_ok = not (distance > 0.01 and curr.fuel_level == prev.fuel_level)

            if (
                curr_val == prev_val and
                time_diff < 360 and
                fuel_drop_ok and
                distance_ok
            ):
                current_segment.append(curr)
            else:
                if len(current_segment) >= 2:
                    segments.append(self._create_segment(current_segment))
                current_segment = [curr]

        if len(current_segment) >= 2:
            segments.append(self._create_segment(current_segment))

        return segments


    def _create_segment(self, points: List[FuelPoint]) -> RoadSegment:
        """Create a RoadSegment from a list of continuous points"""
        assert all(points[i].fuel_level >= points[i+1].fuel_level for i in range(len(points)-1)), "Fuel must not increase in segment"
        start = points[0]
        end = points[-1]
        
        distance = sum(
            calculate_distance(
                points[i].latitude, points[i].longitude,
                points[i+1].latitude, points[i+1].longitude
            )
            for i in range(len(points)-1)
        )
        
        return RoadSegment(
            start_point=start,
            end_point=end,
            distance=distance,
            fuel_consumption=start.fuel_level - end.fuel_level,
            road_type=start.road_profile.road.road_type,
            duration=(end.timestamp - start.timestamp).total_seconds()
        )
    
    def _get_nested_attr(self, obj, attr_name: str):
        """
        Get attribute from a RoadProfile or its nested Road object.
        For 'slope', return a simplified average (rounded to 1 decimal place).
        Preserve Enums and simple types; stringify only unhashable or complex objects.
        """
        val = None
        if hasattr(obj, attr_name):
            val = getattr(obj, attr_name)
        elif hasattr(obj.road, attr_name):
            val = getattr(obj.road, attr_name)

        if attr_name == "slope" and isinstance(val, list) and val:
            # Compute average slope rounded to 1 decimal place
            return round(sum(val) / len(val), 1)

        # Return enums and primitives as-is
        if isinstance(val, (Enum, str, int, float, bool)) or val is None:
            return val

        # Convert unhashable or complex types (like dicts, lists, objects) to string
        if isinstance(val, (dict, list)):
            return str(val)
        if hasattr(val, '__dict__'):  # likely a dataclass or custom object
            return str(val)

        return val


    def calculate_coefficients(self, segments: List[RoadSegment], attribute: str = "road_type") -> Dict[Any, float]:
        """
        Calculate relative fuel efficiency coefficients for each value of the given road attribute.

        :param segments: List of valid RoadSegment objects.
        :param attribute: Road attribute to group by (e.g., 'surface_type', 'condition').
        :return: Dictionary of attribute_value -> relative fuel efficiency coefficient.
        """
        if not segments:
            return {}

        # Group segments by the attribute value
        segments_by_attr_value = {}
        for segment in segments:
            value = self._get_nested_attr(segment.start_point.road_profile, attribute)
            if value is None:
                continue
            key = value.name if isinstance(value, Enum) else str(value)
            segments_by_attr_value.setdefault(key, []).append(segment)

        # Compute average fuel consumption per km for each attribute value
        consumption_by_value = {}
        for attr_value, segs in segments_by_attr_value.items():
            total_distance = sum(s.distance for s in segs) / 1000  # in km
            total_fuel = sum(s.fuel_consumption for s in segs)
            if total_distance > 0:
                self._log(f"Calculating for {attribute}={attr_value}: Total fuel: {total_fuel}, Total distance: {total_distance} km")
                consumption_by_value[attr_value] = total_fuel / total_distance
            else:
                consumption_by_value[attr_value] = 0.0

        # Get base value for normalization from attribute enum
        try:
            attr_enum = RoadFuelAttribute(attribute)
            base_value = self.base_attribute_values.get(attr_enum)
            if base_value not in consumption_by_value:
                base_value = next(iter(consumption_by_value), None)

            self._log(f"Base value for {attribute}: {base_value}")
        except ValueError:
            base_value = next(iter(consumption_by_value), None)
            self._log(f"Base value for {attribute}: ValueError")

        base_consumption = consumption_by_value.get(base_value, 2.0)
        self._log(f"Base consumption for {attribute}: {base_consumption}")

        # Compute relative coefficients
        coefficients = {
            value: (base_consumption / cons if cons > 0 else 1.0)
            for value, cons in consumption_by_value.items()
        }

        self._log(f"coefficients: {coefficients}")

        return coefficients

    
    def filter_invalid_segments(self, segments: List[RoadSegment], vehicle: Dict[str, Any]) -> List[RoadSegment]:
        """
        Enhanced segment filtering with:
        - L/100km validation for moving vehicles
        - L/hour validation for idle/slow speeds
        - Short-distance special handling
        """
        vehicle_type = vehicle.get('name', 'car').lower()
        is_truck = 'truck' in vehicle_type

        thresholds = {
            'car': {
                # Speed thresholds (km/h)
                'min_speed': 5,
                'max_speed': 120,
                'idle_speed_threshold': 3,  # Below this = considered idle
                
                # Moving consumption (L/100km)
                'min_fuel_l_100km': 3,    # Theoretical minimum (hybrid downhill)
                'max_fuel_l_100km': 25,   # Heavy SUV in traffic
                
                # Stationary/slow consumption (L/hour)
                'min_fuel_l_h': 0.3,      # Minimum possible idling
                'max_fuel_l_h': 1.5,      # Max idling with AC/heavy accessories
                'max_slow_fuel_l_h': 4    # Max for speeds 3-15 km/h
            },
            'truck': {
                'min_speed': 3,
                'max_speed': 90,
                'idle_speed_threshold': 2,
                'min_fuel_l_100km': 15,
                'max_fuel_l_100km': 60,
                'min_fuel_l_h': 0.8,
                'max_fuel_l_h': 3.5,
                'max_slow_fuel_l_h': 15
            }
        }

        t = thresholds['truck'] if is_truck else thresholds['car']
        valid_segments = []

        for segment in segments:
            # Skip invalid segments
            if segment.duration <= 0 or segment.distance <= 0:
                continue

            # Calculate metrics
            distance_km = segment.distance / 1000
            duration_h = segment.duration / 3600
            speed_kmh = distance_km / duration_h
            fuel_l_100km = (segment.fuel_consumption / distance_km) * 100
            fuel_l_h = segment.fuel_consumption / duration_h

            # Idle/slow speed validation
            if speed_kmh < t['idle_speed_threshold'] and not (t['min_fuel_l_h'] <= fuel_l_h <= t['max_fuel_l_h']):
                continue

            # Slow moving validation (3-15 km/h for cars)
            if speed_kmh < 15 and fuel_l_h > t['max_slow_fuel_l_h']:
                continue

            # Validate speed range
            if not (t['min_speed'] <= speed_kmh <= t['max_speed']):
                continue
            
            # Validate consumption per 100km
            if not (t['min_fuel_l_100km'] <= fuel_l_100km <= t['max_fuel_l_100km']):
                continue

            valid_segments.append(segment)

        return valid_segments
    
    def analyze_vehicle(self, vehicle: Dict[str, Any], db: FuelDatabase, days: int = 7) -> VehicleFuelProfile:
        """
        Analyze fuel consumption for a single vehicle across multiple road attributes.

        :param vehicle: A dictionary representing a vehicle (must contain at least an 'id').
        :param db: An instance of FuelDatabase to retrieve fuel data.
        :param days: Number of past days to consider for analysis.
        :return: A VehicleFuelProfile containing segment and coefficient mappings per road attribute.
        """
        points = db.get_fuel_points(vehicle, days)
        processed_points = self.process_fuel_data(points)

        attr_coefficients = {}
        attr_segments = {}

        for attribute in self.road_attributes:
            segments = self.create_segments(processed_points, attribute.value)

            # Filter out segments that are too short, invalid, or inconsistent
            filtered_segments = self.filter_invalid_segments(segments, vehicle)
            attr_segments[attribute] = filtered_segments

            if not filtered_segments:
                attr_coefficients[attribute] = None
                continue

            # Perform linear regression or coefficient estimation
            coefficients = self.calculate_coefficients(filtered_segments, attribute.value)
            attr_coefficients[attribute] = coefficients
            self._log(f"finished attribute: {attribute}")

        return VehicleFuelProfile(
            vehicle_id=str(vehicle['agentid']),
            vehicle_type=vehicle['name'],
            attr_coefficients=attr_coefficients,
            attr_segments=attr_segments,
            fuel_points=processed_points
        )


    def analyze_fleet(self, days: int = 7) -> FleetFuelProfile:
        """
        Analyze fuel consumption for multiple vehicles across multiple road attributes.

        :param days: Number of past days to consider for all vehicles.
        :return: FleetFuelProfile with per-attribute average and median coefficients.
        """
        db = FuelDatabase(settings.DB_CONFIG, self.road_extractor)
        vehicles = db.get_vehicles_with_fuel_sensors()

        # Filter specific vehicles if needed
        vehicles = [v for v in vehicles if v['agentid'] in (900, 917)]

        vehicles_profile = []
        all_attr_coefficients: Dict[str, List[Dict[Any, float]]] = {}

        for vehicle in vehicles:
            self._log(f"Analyzing vehicle {vehicle['agentid']} ({vehicle['name']})")
            profile = self.analyze_vehicle(vehicle, db, days)
            vehicles_profile.append(profile)

            # Collect coefficients by attribute
            for attr, coeff_dict in profile.attr_coefficients.items():
                if coeff_dict is None:
                    continue
                all_attr_coefficients.setdefault(attr, []).append(coeff_dict)

        # Calculate average and median per attribute
        average_attr_coefficients = {}
        median_attr_coefficients = {}

        for attr, coeff_list in all_attr_coefficients.items():
            # Get all possible values for this attribute (e.g., 'HIGHWAY', 'ASPHALT')
            all_keys = set().union(*[c.keys() for c in coeff_list])

            avg = {}
            med = {}
            for key in all_keys:
                values = [c.get(key, 1.0) for c in coeff_list]
                avg[key] = sum(values) / len(values)
                med[key] = sorted(values)[len(values) // 2]
            average_attr_coefficients[attr] = avg
            median_attr_coefficients[attr] = med

        return FleetFuelProfile(
            vehicles=vehicles_profile,
            average_attr_coefficients=average_attr_coefficients,
            median_attr_coefficients=median_attr_coefficients
        )
