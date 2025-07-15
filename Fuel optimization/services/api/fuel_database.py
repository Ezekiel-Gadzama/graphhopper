import json, os, time
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
from config.database import DatabaseConnection
from config.settings import DatabaseConfig
from models.data_class import FuelPoint, RoadType, Road
from .polyline import Polyline
import logging
import requests
from utils.geo import calculate_distance
from models.road import RoadExtractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FuelDatabase:
    def __init__(self, db_config: DatabaseConfig, extractor: RoadExtractor):
        self.db_config = db_config
        self.conn = None
        self.db_wrapper = None
        self.connect()
        self.road_cache = {}  # Format: {(lat, lon): (road_type, road_id)}
        self.road_cache_file = "road_cache.json"
        self.preloaded_roads: List[Road] = []
        self._load_preloaded_roads(center_lat=47.546642, center_lon=38.874741, radius=50000)
        self._load_road_cache()


    def connect(self):
        """Establish and store a reusable database connection"""
        if self.conn is None:
            self.db_wrapper = DatabaseConnection(self.db_config)
            self.conn = self.db_wrapper.connection


    def close(self):
        """Close the persistent connection"""
        if self.db_wrapper:
            self.db_wrapper.close()
            self.conn = None


    def get_vehicles_with_fuel_sensors(self) -> List[Dict]:
        query = """
        SELECT sensor.id, veh.agentid, sensor.info, veh.typeid, veh_type.name
        FROM sensor, veh, veh_type
        WHERE sensor.semanticid = 2
          AND sensor.typeid = 1
          AND veh.agentid = sensor.agent_id
          AND veh.typeid = veh_type.id;
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query)
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Database query failed: {str(e)}")
            return []

    def get_fuel_data(self, sensor_id: int, start_timestamp: int) -> List[Dict]:
        query = """
        SELECT * FROM agr_fuel_data
        WHERE sensor_id = %s AND unixstarttimestamp > %s;
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query, (sensor_id, start_timestamp))
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Fuel data query failed: {str(e)}")
            return []

    def get_vehicle_location_data(self, agent_id: int, start_timestamp: int) -> List[Tuple[float, float, int]]:
        """Returns list of (latitude, longitude, timestamp) tuples"""
        query = """
        SELECT * FROM ag_polylines
        WHERE agent_id = %s AND ts >= %s;
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query, (agent_id, start_timestamp))
                results = cursor.fetchall()
                location_data = []
                for result in results:
                    if result and result[2]:
                        try:
                            coords = Polyline.decode(result[2], format='ffii', precision=6)
                        except Exception as decode_err:
                            logger.warning(f"Decoding failed for: {result[2][:10]}... Error: {decode_err}")
                            continue
                        location_data.extend([(lat, lon, i1, i2) for lat, lon, i1, i2 in coords])
                return location_data
        except Exception as e:
            logger.error(f"Location data query failed: {str(e)}")
        return []
    
    def _load_preloaded_roads(self, center_lat: float, center_lon: float, radius: int):
        """Preload roads from Overpass API within a given radius"""
        print("Preloading roads from Overpass API...")
        
        # Initialize set if not already
        if not hasattr(self, 'preloaded_road_ids'):
            self.preloaded_road_ids = set()
        
        query = f"""
        [out:json];
        way(around:{radius},{center_lat},{center_lon})[highway];
        out body geom;
        """
        data = self._query_overpass(query)
        if not data or 'elements' not in data:
            print("No roads found in Overpass preload.")
            return

        new_road_count = 0
        for el in data['elements']:
            if 'geometry' in el and 'tags' in el and 'highway' in el['tags']:
                road_id = el['id']
                if road_id in self.preloaded_road_ids:
                    continue  # Skip duplicates

                coords = [(pt['lat'], pt['lon']) for pt in el['geometry']]
                road_type = el['tags']['highway']
                self.preloaded_roads.append(Road(
                    osm_id=road_id,
                    coordinates=coords,
                    road_type=road_type,
                    osm_tags=el['tags']
                ))
                self.preloaded_road_ids.add(road_id)
                new_road_count += 1

        print(f"Loaded {new_road_count} new roads from Overpass (Total: {len(self.preloaded_road_ids)})")

    def _load_road_cache(self):
        if os.path.exists(self.road_cache_file):
            try:
                with open(self.road_cache_file, "r") as f:
                    raw_cache = json.load(f)
                    self.road_cache = {
                        tuple(map(float, k.split(','))): tuple(v) for k, v in raw_cache.items()
                    }
                    print(f"Loaded cached road ID and Type with {len(self.road_cache)} points.")
            except Exception as e:
                logger.warning(f"Failed to load road cache: {e}")

    def _save_road_cache(self):
        try:
            with open(self.road_cache_file, "w") as f:
                json.dump({
                    f"{lat:.6f},{lon:.6f}": [road_id, road_type]
                    for (lat, lon), (road_id, road_type) in self.road_cache.items()
                }, f)
        except Exception as e:
            logger.error(f"Failed to save road cache: {e}")

    
    def _query_overpass(self, query):
        try:
            response = requests.get("https://overpass-api.de/api/interpreter", params={"data": query}, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Overpass query error: {e}")
            return None

    def get_road_info(self, lat: float, lon: float, retry: Optional[bool] = True) -> Tuple[Optional[int], str]:
        key = (round(lat, 6), round(lon, 6))
        cached = self.road_cache.get(key)
        
        if cached:
            print("Using cache")
            return cached

        nearest_road = None
        min_distance = float('inf')
        for road in self.preloaded_roads:
            for point in road.coordinates:
                dist = calculate_distance(lat, lon, point[0], point[1]) #road.coordinates[0][0], road.coordinates[0][1]
                if dist < min_distance:
                    min_distance = dist
                    nearest_road = road
        
        if nearest_road and min_distance <= 100:
            road_id = nearest_road.osm_id
            road_type = nearest_road.road_type
            print(f"Now minumum distance is {int(min_distance)}m")
        else:
            road_id = None
            road_type = "unknown"
            print(f"mini distance is {int(min_distance/1000)}km")
            if min_distance > 2000 and retry:
                self._load_preloaded_roads(center_lat=key[0], center_lon=key[1], radius=50000)
                return self.get_road_info(lat=lat, lon=lon, retry=False)

        self.road_cache[key] = (road_id, road_type)
        self._save_road_cache()
        return road_id, road_type

    def get_fuel_points(self, vehicle: dict, days: int = 7) -> List[FuelPoint]:
        """Get fuel points for a specific vehicle"""
        import time
        start_time = time.time()
        now = datetime.now()
        start_timestamp = int((now - timedelta(days=days)).timestamp())
        fuel_records = self.get_fuel_data(vehicle['id'], start_timestamp)
        location_data = self.get_vehicle_location_data(vehicle['agentid'], start_timestamp)
        print(f"length of location: {len(location_data)} and cache: {len(self.road_cache)}")
        for index, location in enumerate(location_data, start=1):
            print(f"Processing location index: {index}")
            self.get_road_info(location[0], location[1])

        return []
        
        points = []
        
        # Convert location data to a more searchable format
        loc_timestamps = [loc[2] for loc in location_data]

        print(f"Found {len(fuel_records)} fuel records for vehicle {vehicle['agentid']}")
        print(f"Found {len(location_data)} location records for vehicle {vehicle['agentid']}")

        for index, record in enumerate(fuel_records, start=1):  # start=1 makes it 1-based
            sensor_data = record['sensor_data'].split(';')
            print(f"Processing fuel record #{index}: size of sensor data: {len(sensor_data)}")
            for index, data_point in enumerate(sensor_data, start=1): 
                if not data_point:
                    continue
                parts = data_point.split(':')
                if len(parts) < 3:
                    continue

                seconds = int(parts[0])
                fuel_level = float(parts[1])
                speed = float(parts[2])
                timestamp = record['unixstarttimestamp'] + seconds  
                
                # Find the closest location by timestamp
                location = None
                time_diff = float('inf')
                if location_data and loc_timestamps:
                    # Verify the timestamp exists in location data
                    if timestamp in loc_timestamps:
                        closest_idx = loc_timestamps.index(timestamp)
                        time_diff = 0
                    else:
                        # Find nearest timestamp
                        closest_idx, time_diff = min(
                            ((i, abs(ts - timestamp)) for i, ts in enumerate(loc_timestamps)))
                    
                    if time_diff <= 300:
                        location = location_data[closest_idx]
                    else:
                        continue

                if location and speed > 0:
                    osm_roadID, road_type = self.get_road_info(location[0], location[1])
                    if osm_roadID == None:
                        continue
                    points.append(FuelPoint(
                        timestamp=datetime.fromtimestamp(timestamp),
                        fuel_level=fuel_level,
                        speed=speed,
                        latitude=location[0],
                        longitude=location[1],
                        gps_speed=location[3],
                        road_type=RoadType(road_type.upper()),
                        osm_roadID=osm_roadID
                    ))

        print(f"Execution completed in {time.time() - start_time:.2f}s")
        return points
    
    def get_all_agent_ids(self):
        query = """
        SELECT DISTINCT agentid FROM veh ORDER BY agentid;
        """
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query)
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Failed to fetch agent IDs: {str(e)}")
            return []


