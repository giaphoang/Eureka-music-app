import os
from pathlib import Path

from platformdirs import user_data_dir

APP_NAME = "EurekaMusic"
APP_AUTHOR = "EurekaCandidate"
DATA_DIR = Path(os.getenv("EUREKA_DATA_DIR", user_data_dir(APP_NAME, APP_AUTHOR))).expanduser()
DOWNLOAD_DIR = DATA_DIR / "downloads"
DB_PATH = DATA_DIR / "client.sqlite3"
API_BASE_URL = os.getenv("EUREKA_API_URL", "http://localhost:8000").rstrip("/")


def ensure_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
