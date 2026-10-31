"""Bước 7 gốc kiểm tra trường 'shap' trong phản hồi /predict. Từ bước 7b, SHAP chạy nền qua hàng đợi
nên phản hồi không còn trường đó và test cũ luôn lỗi. Hành vi hiện hành được kiểm bởi stage07b."""
import runpy
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
runpy.run_path(str(Path(__file__).with_name("stage07b_test_async_queue.py")), run_name="__main__")
