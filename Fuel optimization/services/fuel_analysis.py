from typing import List, Dict, Any
from services.api.fuel_database import FuelDatabase
from models.data_class import (
    RoadType, 
    FuelPoint, 
    RoadSegment, 
    VehicleFuelProfile,
    FleetFuelProfile
)
from utils.geo import calculate_distance
from config.settings import settings

class FuelAnalyzer:
    def __init__(self, road_extractor):
        self.base_road_type = RoadType.PRIMARY
        self.invalid_agents = set()
        self.all_agents = set()
        self.road_extractor = road_extractor

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

    def create_segments(self, points: List[FuelPoint]) -> List[RoadSegment]:
        """Group points into continuous road segments"""
        if not points:
            return []
            
        segments = []
        current_segment = [points[0]]
        print(f"starting point Road type: {points[0].road_type} with timestamp: {points[0].timestamp}")
        for point in points[1:]:
            if not point.road_type:
                continue
            # Continue segment if same road type and time difference < threshold
            print(f"Road type: {point.road_type} with timestamp: {point.timestamp}")
            distance_ok = not (calculate_distance(point.latitude, point.longitude,
                                current_segment[-1].latitude,
                                current_segment[-1].longitude) > 0.01
                            and point.fuel_level == current_segment[-1].fuel_level)

            if (point.road_type == current_segment[-1].road_type and 
                (point.timestamp - current_segment[-1].timestamp).total_seconds() < 360 and
                point.fuel_level <= current_segment[-1].fuel_level and
                distance_ok):
                
                current_segment.append(point)
            else:
                if len(current_segment) > 1:
                    segments.append(self._create_segment(current_segment))
                current_segment = [point]

        
        if len(current_segment) > 1:
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
            road_type=start.road_type,
            duration=(end.timestamp - start.timestamp).total_seconds()
        )

    def calculate_coefficients(self, segments: List[RoadSegment]) -> Dict[RoadType, float]:
        """Calculate fuel coefficients for each road type"""
        if not segments:
            return {}
            
        # Group segments by road type
        segments_by_type = {}
        for segment in segments:
            if segment.road_type not in segments_by_type:
                segments_by_type[segment.road_type] = []
            segments_by_type[segment.road_type].append(segment)
        # Calculate average consumption per km for each road type
        consumption = {}
        for road_type, type_segments in segments_by_type.items():

            # Print each segment's details
            for i, segment in enumerate(type_segments, start=1):
                print(f"Segment {i}:")
                print(f"  Distance: {segment.distance / 1000:.4f} km")  # Convert meters to km
                print(f"  Fuel Used: {segment.fuel_consumption:.4f} liters")
                print(f"  Duration: {segment.duration / 60:.2f} minutes")  # Convert seconds to minutes
            
            total_distance = sum(s.distance for s in type_segments) / 1000  # to km
            total_fuel = sum(s.fuel_consumption for s in type_segments)
            consumption[road_type] = total_fuel / total_distance if total_distance > 0 else 0
            print(f"Road type: {road_type} total distance : {total_distance} and total fuel: {total_fuel} with consumption[road_type]: {consumption[road_type]}")
        
        # Calculate coefficients relative to primary roads
        base_consumption = consumption.get(self.base_road_type, 1.0)
        print(f"consumption is : {consumption}")
        coefficients = {
            road_type: base_consumption / cons if cons > 0 else 1.0
            for road_type, cons in consumption.items()
        }
        
        print(f"consumption coefficients: {coefficients}")
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
        agent_id = str(vehicle['agentid'])
        self.all_agents.add(agent_id)

        for segment in segments:
            # Skip invalid segments
            if segment.duration <= 0 or segment.distance <= 0:
                self.invalid_agents.add(agent_id)
                continue

            # Calculate metrics
            distance_km = segment.distance / 1000
            duration_h = segment.duration / 3600
            speed_kmh = distance_km / duration_h
            fuel_l_100km = (segment.fuel_consumption / distance_km) * 100
            fuel_l_h = segment.fuel_consumption / duration_h

            # Idle/slow speed validation
            if speed_kmh < t['idle_speed_threshold'] and not (t['min_fuel_l_h'] <= fuel_l_h <= t['max_fuel_l_h']):
                self.invalid_agents.add(agent_id)
                continue

            # Slow moving validation (3-15 km/h for cars)
            if speed_kmh < 15 and fuel_l_h > t['max_slow_fuel_l_h']:
                self.invalid_agents.add(agent_id)
                continue

            # Validate speed range
            if not (t['min_speed'] <= speed_kmh <= t['max_speed']):
                self.invalid_agents.add(agent_id)
                continue
            
            # Validate consumption per 100km
            if not (t['min_fuel_l_100km'] <= fuel_l_100km <= t['max_fuel_l_100km']):
                self.invalid_agents.add(agent_id)
                continue

            valid_segments.append(segment)

        return valid_segments
    
    def analyze_vehicle(self, vehicle: Dict[str, Any], db: FuelDatabase, days: int = 7) -> VehicleFuelProfile:
        """Analyze fuel consumption for a single vehicle"""
        points = db.get_fuel_points(vehicle, days)
        if not points:
            print(f"No fuel points found for vehicle {vehicle['agentid']}")
            self.invalid_agents.add(str(vehicle['agentid']))

        processed_points = self.process_fuel_data(points)
        segments = self.create_segments(processed_points)
        # Filter invalid segments and print agents with bad data
        segments = self.filter_invalid_segments(segments, vehicle)
        coefficients = self.calculate_coefficients(segments)
        
        return VehicleFuelProfile(
            vehicle_id=str(vehicle['agentid']),
            vehicle_type=vehicle['name'],
            segments=segments,
            coefficients=coefficients,
            fuel_points=processed_points
        )

    def analyze_fleet(self, days: int = 7) -> FleetFuelProfile:
        """Analyze fuel consumption for multiple vehicles"""
        db = FuelDatabase(settings.DB_CONFIG, self.road_extractor)
        vehicles = db.get_vehicles_with_fuel_sensors()
        vehicles = [v for v in vehicles if v['agentid'] in (900, 917)]
        print(f"Filtered vehicles: {vehicles}")
        vehicles_profile = []
        all_coefficients = []
        # for vehicle in vehicles:
        profile = self.analyze_vehicle(vehicles[0], db, days)
        vehicles_profile.append(profile)
        all_coefficients.append(profile.coefficients)
        
        # Calculate average and median coefficients across fleet
        road_types = set().union(*[c.keys() for c in all_coefficients])
        
        average_coefficients = {
            rt: sum(c.get(rt, 1.0) for c in all_coefficients) / len(all_coefficients)
            for rt in road_types
        }
        
        median_coefficients = {
            rt: sorted(c.get(rt, 1.0) for c in all_coefficients)[len(all_coefficients) // 2]
            for rt in road_types
        }
        
        return FleetFuelProfile(
            vehicles=vehicles_profile,
            average_coefficients=average_coefficients,
            median_coefficients=median_coefficients
        )