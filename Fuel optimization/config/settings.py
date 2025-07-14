import os
from dotenv import load_dotenv
from dataclasses import dataclass
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
print(BASE_DIR)
load_dotenv()

@dataclass
class DatabaseConfig:
    ssh_host: str = os.getenv("SSH_HOST")
    ssh_username: str = os.getenv("SSH_USERNAME")
    ssh_pkey: str = str(Path(BASE_DIR).parent / os.getenv("SSH_PKEY_PATH"))
    ssh_port: int = int(os.getenv("SSH_PORT"))
    local_port: int = int(os.getenv("LOCAL_PORT"))
    db_host: str = os.getenv("DB_HOST")
    db_port: int = int(os.getenv("DB_PORT"))
    db_name: str = os.getenv("DB_NAME")
    db_user: str = os.getenv("DB_USER")
    db_password: str = os.getenv("DB_PASSWORD")

class Settings:
    verbose = 0
    YANDEX_API_KEY = os.getenv("YANDEX_API_KEY")
    TOMTOM_API_KEY = os.getenv("TOMTOM_API_KEY")
    TOMORROW_API_KEY = os.getenv("TOMORROW_API_KEY")
    OSM_FILE_PATH = str(Path(BASE_DIR).parent / "moscow.osm.pbf")
    CUSTOM_MODEL_PATH = str(Path(BASE_DIR).parent / "custom_model.json")
    GRAPHHOPPER_URL = os.getenv("GRAPHHOPPER_URL", "http://localhost:8989/route")
    DB_CONFIG = DatabaseConfig()

settings = Settings()