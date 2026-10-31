"""Trang đối chiếu M0 và M1 chạy riêng (không cần dashboard chính):

    streamlit run app/compare_dashboard.py --server.port 8502   (chạy từ thư mục RQ3_IDS_System/)

Cùng nội dung với tab «Đối chiếu M0 / M1» của dashboard chính (app/compare_ui.py)."""
import os
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model_compare as mc  # noqa: E402
from compare_ui import render_compare  # noqa: E402

st.set_page_config(page_title="Đối chiếu M0 và M1", layout="wide")
cfg = mc.load_config()
st.title("Đối chiếu song song M0 và M1")
with st.sidebar:
    db_path = st.text_input("Đường dẫn DB", os.environ.get("IDS_DB_PATH", str(mc.REPO_ROOT / cfg["paths"]["sqlite_db"])))
    source = st.selectbox("Nguồn flow", [""] + mc.list_sources(Path(db_path)), format_func=lambda s: s or "Tất cả")
    runs = mc.list_runs(Path(db_path))
    run_id = st.selectbox("Lượt dữ liệu", [""] + [r[0] for r in runs],
                          format_func=lambda x: "Tất cả" if not x else next(f"{r[1] or 'Dữ liệu cũ'} · {r[2][:19]} · {r[0][:8]}" for r in runs if r[0] == x))
    paused = st.checkbox("Tạm dừng tự làm mới")
render_compare(db_path, source, run_id, paused, key="standalone")
