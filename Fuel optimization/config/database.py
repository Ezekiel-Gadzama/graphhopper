import psycopg2
import sshtunnel
from typing import Dict, List, Tuple
from datetime import datetime
from dataclasses import dataclass
from config.settings import settings
from config.constants import constants

@dataclass
class DatabaseConfig:
    ssh_host: str
    ssh_username: str
    ssh_pkey: str
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str

class DatabaseConnection:
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.tunnel = None
        self.connection = None

    def __enter__(self):
        self.tunnel = sshtunnel.SSHTunnelForwarder(
            (self.config.ssh_host, 22),
            ssh_username=self.config.ssh_username,
            ssh_pkey=self.config.ssh_pkey,
            remote_bind_address=(self.config.db_host, self.config.db_port)
        )
        self.tunnel.start()
        
        self.connection = psycopg2.connect(
            database=self.config.db_name,
            user=self.config.db_user,
            password=self.config.db_password,
            host='127.0.0.1',
            port=self.tunnel.local_bind_port
        )
        return self.connection

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            self.connection.close()
        if self.tunnel:
            self.tunnel.stop()