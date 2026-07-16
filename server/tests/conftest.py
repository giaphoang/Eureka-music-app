import os
import shutil
from pathlib import Path

import pytest

TEST_ROOT = Path("/tmp/eureka-music-server-tests")
TEST_ROOT.mkdir(parents=True, exist_ok=True)
DB_PATH = TEST_ROOT / "test.sqlite3"
DB_PATH.unlink(missing_ok=True)
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{DB_PATH}"
os.environ["AUDIO_ROOT"] = str(TEST_ROOT / "audio")


@pytest.fixture(autouse=True)
def reset_server_state():
    from app.config import settings
    from app.database import Base, engine

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    shutil.rmtree(settings.audio_root, ignore_errors=True)
    settings.audio_root.mkdir(parents=True, exist_ok=True)
    yield
