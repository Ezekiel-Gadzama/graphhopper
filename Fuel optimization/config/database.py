import psycopg2
import sshtunnel
from typing import Optional
from config.settings import DatabaseConfig
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class DatabaseConnection:
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.tunnel: Optional[sshtunnel.SSHTunnelForwarder] = None
        self.connection: Optional[psycopg2.extensions.connection] = None
        self._verify_ssh_key()
        self._start_tunnel()
        self._connect_db()

    def _verify_ssh_key(self):
        """Verify SSH key exists and is properly formatted"""
        key_path = Path(self.config.ssh_pkey)
        if not key_path.exists():
            raise FileNotFoundError(f"SSH key not found at {key_path}")
        
        with key_path.open('r') as f:
            content = f.read().strip()
            if not content.startswith('-----BEGIN OPENSSH PRIVATE KEY-----'):
                logger.error("SSH key format is invalid - expected OpenSSH format")
                raise ValueError("Invalid SSH key format")

    def _start_tunnel(self):
        """Start SSH tunnel"""
        self.tunnel = sshtunnel.SSHTunnelForwarder(
            (self.config.ssh_host, self.config.ssh_port),
            ssh_username=self.config.ssh_username,
            ssh_pkey=self.config.ssh_pkey,
            remote_bind_address=(self.config.db_host, self.config.db_port),
            local_bind_address=('127.0.0.1', self.config.local_port)
        )
        self.tunnel.start()

    def _connect_db(self):
        """Establish DB connection through SSH tunnel"""
        self.connection = psycopg2.connect(
            database=self.config.db_name,
            user=self.config.db_user,
            password=self.config.db_password,
            host='127.0.0.1',
            port=self.tunnel.local_bind_port  # Don't hardcode
        )

    def close(self):
        """Close DB connection and SSH tunnel"""
        if self.connection:
            self.connection.close()
        if self.tunnel:
            self.tunnel.stop()
