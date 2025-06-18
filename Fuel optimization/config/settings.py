import os
from dotenv import load_dotenv
from dataclasses import dataclass

load_dotenv()

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

@dataclass
class DatabaseConfig:
    ssh_host: str = os.getenv("SSH_HOST")
    ssh_username: str = os.getenv("SSH_USERNAME")
    ssh_pkey: str = os.getenv("SSH_PKEY_PATH")
    db_host: str = os.getenv("DB_HOST")
    db_port: int = int(os.getenv("DB_PORT", 5432))
    db_name: str = os.getenv("DB_NAME")
    db_user: str = os.getenv("DB_USER")
    db_password: str = os.getenv("DB_PASSWORD")

class Settings:
    HERE_API_KEY = os.getenv("HERE_API_KEY")
    TOMORROW_API_KEY = os.getenv("TOMORROW_API_KEY")
    OSM_FILE_PATH = os.path.join(BASE_DIR, "moscow_tagged.osm.pbf")
    CUSTOM_MODEL_PATH = os.path.join(BASE_DIR, "custom_model.json")
    GRAPHHOPPER_URL = os.getenv("GRAPHHOPPER_URL", "http://localhost:8989/route")
    DB_CONFIG = DatabaseConfig()

settings = Settings()