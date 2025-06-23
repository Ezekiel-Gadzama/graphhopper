import json
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
from config.database import DatabaseConnection
from config.settings import DatabaseConfig
from models.data_class import FuelPoint
import polyline
import logging

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
        SELECT polyline, ts FROM agr_odo_polyline
        WHERE agent_id = %s AND ts >= %s;
        """
        
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query, (agent_id, start_timestamp))
                results = cursor.fetchall()
                location_data = []
                for result in results:
                    if result and result[0]:
                        coords = polyline.decode(result[0], 6)
                        ts = result[1]
                        location_data.extend([(lat, lon, ts) for lat, lon in coords])
                return location_data
        except Exception as e:
            logger.error(f"Location data query failed: {str(e)}")
        return []
    
    
    def get_fuel_points(self, vehicle_id: int, days: int = 7) -> List[FuelPoint]:
        now = datetime.now()
        start_timestamp = int((now - timedelta(days=days)).timestamp())

        vehicles = self.get_vehicles_with_fuel_sensors()
        vehicle = next((v for v in vehicles if v['agentid'] == vehicle_id), None)
        if not vehicle:
            return []

        fuel_records = self.get_fuel_data(vehicle['id'], start_timestamp)
        location_data = self.get_vehicle_location_data(vehicle_id, start_timestamp)
        points = []
        for record in fuel_records:
            sensor_data = record['sensor_data'].split(';')
            for data_point in sensor_data:
                if not data_point:
                    continue

                parts = data_point.split(':')
                if len(parts) < 3:
                    continue

                seconds = int(parts[0])
                fuel_level = float(parts[1])
                speed = float(parts[2])

                timestamp = record['unixstarttimestamp'] + seconds
                location = next(
                    (loc for loc in location_data if abs(loc[2] - timestamp) <= 5),
                    None
                )

                if location and speed > 0:
                    points.append(FuelPoint(
                        timestamp=datetime.fromtimestamp(timestamp),
                        fuel_level=fuel_level,
                        speed=speed,
                        latitude=location[0],
                        longitude=location[1],
                        gps_speed=speed  # Using the same speed value since we don't have GPS speed
                    ))

        return points