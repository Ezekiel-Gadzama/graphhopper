import json
from typing import List, Dict, Tuple
from datetime import datetime
from dataclasses import dataclass
from config.database import DatabaseConnection, DatabaseConfig
from models.data_class import FuelPoint
from utils.polyline import Polyline
from datetime import timedelta

class FuelDatabase:
    def __init__(self, db_config: DatabaseConfig):
        self.db_config = db_config

    def get_vehicles_with_fuel_sensors(self) -> List[Dict]:
        """Retrieve vehicles equipped with fuel sensors"""
        query = """
        SELECT sensor.id, veh.agentid, sensor.info, veh.typeid, veh_type.name
        FROM sensor, veh, veh_type
        WHERE sensor.semanticid = 2
          AND sensor.typeid = 1
          AND veh.agentid = sensor.agent_id
          AND veh.typeid = veh_type.id;
        """
        
        with DatabaseConnection(self.db_config) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query)
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_fuel_data(self, sensor_id: int, start_timestamp: int) -> List[Dict]:
        """Retrieve raw fuel data for a specific sensor"""
        query = """
        SELECT * FROM agr_fuel_data
        WHERE sensor_id = %s AND unixstarttimestamp > %s;
        """
        
        with DatabaseConnection(self.db_config) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (sensor_id, start_timestamp))
                columns = [desc[0] for desc in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_vehicle_location_data(self, agent_id: int, start_timestamp: int) -> List[Tuple[float, float, int, float]]:
        """Retrieve and decode vehicle location data"""
        query = """
        SELECT polyline FROM agr_odo_polyline
        WHERE agent_id = %s AND ts >= %s;
        """
        
        with DatabaseConnection(self.db_config) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (agent_id, start_timestamp))
                result = cursor.fetchone()
                if result and result[0]:
                    return Polyline.decode(result[0], 'ffii', 6)
                return []

    def get_fuel_points(self, vehicle_id: int, days: int = 7) -> List[FuelPoint]:
        """Get combined fuel and location data as FuelPoint objects"""
        now = datetime.now()
        start_timestamp = int((now - timedelta(days=days)).timestamp())
        
        # Get vehicle info
        vehicles = self.get_vehicles_with_fuel_sensors()
        vehicle = next((v for v in vehicles if v['agentid'] == vehicle_id), None)
        if not vehicle:
            return []
        
        # Get fuel data
        fuel_records = self.get_fuel_data(vehicle['id'], start_timestamp)
        location_data = self.get_vehicle_location_data(vehicle_id, start_timestamp)
        
        # Process and combine data
        points = []
        for record in fuel_records:
            # Parse sensor data format: [seconds_from_midnight]:[fuel_level]:[speed];[next_record];...
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
                
                # Find matching location by timestamp
                timestamp = record['unixstarttimestamp'] + seconds
                location = next(
                    (loc for loc in location_data 
                     if abs(loc[2] - timestamp) <= 5),  # 5-second tolerance
                    None
                )
                
                if location:
                    points.append(FuelPoint(
                        timestamp=datetime.fromtimestamp(timestamp),
                        fuel_level=fuel_level,
                        speed=speed,
                        latitude=location[0],
                        longitude=location[1],
                        gps_speed=location[3]
                    ))
        
        return points