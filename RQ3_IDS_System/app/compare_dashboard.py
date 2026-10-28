"""Trang đối chiếu song song M0 và M1 trên cùng flow đã lưu. Chạy riêng, không đổi dashboard chính:

    streamlit run app/compare_dashboard.py --server.port 8502   (chạy từ thư mục RQ3_IDS_System/)
"""
import os
import sys
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model_compare as mc  # noqa: E402

st.set_page_config(page_title="Đối chiếu M0 và M1", layout="wide")


@st.cache_resource
def get_pair():
    return mc.ModelPair()


@st.cache_data(ttl=30)
def get_table(db_path: str, source: str, limit: int):
    flows = mc.load_flows(Path(db_path), source or None, limit)
    return flows, get_pair().predict_table(flows)


def shap_chart(top_k):
    frame = pd.DataFrame(top_k)
    chart = alt.Chart(frame).mark_bar().encode(
        y=alt.Y("feature:N", sort="-x", title=None), x=alt.X("phi:Q", title="SHAP (đóng góp cho lớp được dự đoán)"),
        color=alt.condition(alt.datum.phi >= 0, alt.value("#ef7070"), alt.value("#69b9ee")), tooltip=["feature", "value", "phi"])
    st.altair_chart(chart.properties(height=max(160, len(frame) * 30)), width="stretch")


try:
    pair = get_pair()
except FileNotFoundError as e:
    st.error(f"{e}. File mô hình M1 nằm ở RQ4_Retrain_Compare/models và không được commit; cần huấn luyện bằng scripts/05_train_models.py m1.")
    st.stop()

cfg = pair.cfg
db_default = os.environ.get("IDS_DB_PATH", str(mc.REPO_ROOT / cfg["paths"]["sqlite_db"]))
st.title("Đối chiếu song song M0 và M1")
st.caption("M0: mô hình RQ1, học từ dữ liệu cũ (15 lớp). M1: mô hình RQ4, học từ dữ liệu improved (13 lớp). Cùng 78 đặc trưng, cùng siêu tham số. "
           "Trang này tự dự đoán lại các flow đã lưu bằng cả hai mô hình và đọc DB ở chế độ chỉ đọc, không đổi gì ở hệ thống chính.")

with st.sidebar:
    db_path = st.text_input("Đường dẫn DB", db_default)
    sources = mc.list_sources(Path(db_path))
    source = st.selectbox("Nguồn flow", [""] + sources, format_func=lambda s: s or "Tất cả")
    limit = st.slider("Số flow mới nhất", 100, 3000, 1000, step=100)
    top_k = st.slider("Số đặc trưng SHAP", 3, 10, 5)
    if st.button("Làm mới"):
        st.cache_data.clear()

flows, tb = get_table(db_path, source, limit)
if tb.empty:
    st.info("Không có flow nào.")
    st.stop()

n = len(tb)
c = st.columns(5)
c[0].metric("Số flow", f"{n:,}")
c[1].metric("M0 báo tấn công", f"{tb.M0_attack.mean() * 100:.1f}%")
c[2].metric("M1 báo tấn công", f"{tb.M1_attack.mean() * 100:.1f}%")
c[3].metric("Hai mô hình khác nhãn", f"{int(tb.disagree.sum()):,}")
c[4].metric("Trong vùng FIN của Hulk", f"{int(tb.in_zone.sum()):,}")
known = tb[tb.label_true.notna()]
if len(known):
    st.caption(f"{len(known):,} flow có nhãn thật trong DB. Với flow feeder_live, nhãn Benign do người dùng xác nhận bằng lời cho 784 flow ngày 26/10/2026, các flow mới hơn chưa xác nhận.")
else:
    st.caption("Các flow này không có nhãn thật trong DB. Nhãn Benign của feeder_live do người dùng xác nhận bằng lời cho 784 flow ngày 26/10/2026, các flow mới hơn chưa xác nhận.")

left, right = st.columns(2)
with left:
    st.subheader("Số flow theo nhãn dự đoán")
    counts = pd.concat([tb.M0_label.value_counts().rename("M0"), tb.M1_label.value_counts().rename("M1")], axis=1).fillna(0).astype(int)
    st.dataframe(counts, width="stretch")
with right:
    st.subheader("M0 (hàng) so với M1 (cột)")
    st.dataframe(pd.crosstab(tb.M0_label, tb.M1_label), width="stretch")

st.subheader("Chọn một flow để xem SHAP của cả hai mô hình")
only_dis = st.checkbox("Chỉ các flow hai mô hình khác nhãn", value=bool(tb.disagree.any()))
pick = tb[tb.disagree] if only_dis else tb
if pick.empty:
    st.info("Không có flow phù hợp.")
    st.stop()
show = pick[["flow_id", "source", "M0_label", "M0_conf", "M1_label", "M1_conf", "in_zone"]].reset_index(drop=True)
sel = st.dataframe(show, width="stretch", height=240, on_select="rerun", selection_mode="single-row", hide_index=True)
rows = sel.selection.rows if sel and sel.selection else []
flow_id = show.flow_id[rows[0]] if rows else show.flow_id[0]
row = flows[flows.flow_id == flow_id]
res = pair.explain_flow(row, top_k=top_k)
st.markdown(f"**Flow:** `{flow_id}`  |  nguồn: {row.source.iloc[0]}  |  nhãn thật: {row.label_true.iloc[0] or 'chưa có'}  |  trong vùng FIN của Hulk: {'có' if bool(pair.in_zone(row).iloc[0]) else 'không'}")
a, b = st.columns(2)
for col, k, title in [(a, "M0", "M0, dữ liệu cũ"), (b, "M1", "M1, dữ liệu improved")]:
    with col:
        r = res[k]
        st.markdown(f"### {title}")
        st.metric("Nhãn dự đoán", r["label"], delta=f"{r['top3'][0][1] * 100:.1f}% tin cậy", delta_color="off")
        st.caption("Xác suất cao nhất: " + ", ".join(f"{c} {p * 100:.1f}%" for c, p in r["top3"]))
        shap_chart(r["shap"]["top_k"])
        st.caption(f"Sai số cộng dồn SHAP: {r['shap']['additivity_error']:.1e}. Phiên bản mô hình: {r['model_version']}")

st.subheader("Giá trị các đặc trưng chính của flow này")
st.dataframe(row[mc.KEY_FEATURES].T.rename(columns={row.index[0]: "Giá trị"}), width="stretch")
st.warning("Cách đọc: M1 báo Benign đúng trên flow Benign thật không chứng minh M1 tốt. M1 chưa được thử trên tấn công độc lập, "
           "vẫn dựa nhiều vào đặc trưng cửa sổ nhận (Init Bwd Win Byts), và chỉ nhận 3,7% đến 11,8% Hulk của bộ test cũ. "
           "Trang này minh họa vì sao hai mô hình khác nhau, không dùng để xếp hạng chúng.")
