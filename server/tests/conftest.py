import os
from pathlib import Path

TEST_ROOT = Path("/tmp/eureka-music-server-tests")
TEST_ROOT.mkdir(parents=True, exist_ok=True)
DB_PATH = TEST_ROOT / "test.sqlite3"
DB_PATH.unlink(missing_ok=True)
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{DB_PATH}"
os.environ["AUDIO_ROOT"] = str(TEST_ROOT / "audio")
