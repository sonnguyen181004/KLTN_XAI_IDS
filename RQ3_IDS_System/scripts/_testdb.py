"""Đưa test về DB tạm. Các test cũ từng ghi thẳng vào data/ids_system.db (DB demo thật).
Import module này SỚM: uvicorn con kế thừa IDS_DB_PATH, nên API test không chạm DB thật."""
import atexit
import os
import shutil
import tempfile
from pathlib import Path

_dir = Path(tempfile.mkdtemp(prefix="ids_stage_"))
TEST_DB = _dir / "ids_system.db"
os.environ["IDS_DB_PATH"] = str(TEST_DB)
atexit.register(lambda: shutil.rmtree(_dir, ignore_errors=True))
