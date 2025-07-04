import json
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
from config.database import DatabaseConnection
from config.settings import DatabaseConfig
from models.data_class import FuelPoint
from .polyline import Polyline
import logging
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FuelDatabase:
    def __init__(self, db_config: DatabaseConfig):
        self.db_config = db_config
        self.conn = None
        self.db_wrapper = None
        self.connect()
        

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
    
    def _query_overpass(self, query):
        try:
            response = requests.get("https://overpass-api.de/api/interpreter", params={"data": query}, timeout=30)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Overpass query error: {e}")
            return None

    def get_road_type(self, lat, lon):
        query = f"""[out:json];way(around:20,{lat},{lon})[highway];out tags;"""
        data = self._query_overpass(query)
        if data and 'elements' in data and data['elements']:
            tags = data['elements'][0].get('tags', {})
            highway = tags.get('highway', 'unknown')
            print(f"Highway: {highway}")
            return highway
        return 'unknown'

    def get_road_id(self, lat, lon):
        query = f"""[out:json];way(around:20,{lat},{lon})[highway];out ids;"""
        data = self._query_overpass(query)
        if data and 'elements' in data and data['elements']:
            road_id = data['elements'][0]['id']
            print(f"Road ID: {road_id}")
            return road_id
        return None

    def get_fuel_points(self, vehicle: dict, days: int = 7) -> List[FuelPoint]:
        """Get fuel points for a specific vehicle"""
        now = datetime.now()
        start_timestamp = int((now - timedelta(days=days)).timestamp())
        fuel_records = self.get_fuel_data(vehicle['id'], start_timestamp)
        location_data = self.get_vehicle_location_data(vehicle['agentid'], start_timestamp)
        points = []
        
        # Convert location data to a more searchable format
        loc_timestamps = [loc[2] for loc in location_data]
        
        for record in fuel_records[:10]: 
            sensor_data = record['sensor_data'].split(';')
            for data_point in sensor_data[:10]:
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
                        print(f"Skipping - time difference too large: {time_diff}s")
                        continue

                if location and speed > 0:
                    points.append(FuelPoint(
                        timestamp=datetime.fromtimestamp(timestamp),
                        fuel_level=fuel_level,
                        speed=speed,
                        latitude=location[0],
                        longitude=location[1],
                        gps_speed=location[3],
                        road_type=self.get_road_type(location[0], location[1]),
                        osm_roadID=self.get_road_id(location[0], location[1])
                    ))

        return points