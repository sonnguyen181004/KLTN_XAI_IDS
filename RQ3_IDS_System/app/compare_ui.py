"""Phần giao diện đối chiếu M0 và M1, dùng chung cho tab trong dashboard chính (app/dashboard.py) và trang riêng (app/compare_dashboard.py)."""
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

import model_compare as mc


@st.cache_resource
def get_pair():
    return mc.ModelPair()


@st.cache_data(ttl=3)
def _table(db_path: str, source: str, limit: int, run_id: str):
    flows = mc.load_flows(Path(db_path), source or None, limit, run_id or None)
    if flows.empty:
        return flows, flows
    return flows, get_pair().predict_table(flows)


@st.cache_data(ttl=3)
def _search(db_path: str, text: str):
    flows = mc.search_flows(Path(db_path), text)
    if flows.empty:
        return flows, flows
    return flows, get_pair().predict_table(flows)


def _shap_chart(top_k):
    frame = pd.DataFrame(top_k)
    chart = alt.Chart(frame).mark_bar().encode(
        y=alt.Y("feature:N", sort="-x", title=None), x=alt.X("phi:Q", title="SHAP (đóng góp cho lớp được dự đoán)"),
        color=alt.condition(alt.datum.phi >= 0, alt.value("#ef7070"), alt.value("#69b9ee")), tooltip=["feature", "value", "phi"])
    st.altair_chart(chart.properties(height=max(160, len(frame) * 30)), width="stretch")


def render_compare(db_path: str, source: str = "", run_id="", paused: bool = False, key: str = "cmp") -> None:
    """Vẽ nội dung đối chiếu. source, run_id rỗng nghĩa là không lọc; run_id có thể là hàm trả về mã lượt, được gọi lại mỗi lần làm mới. Tự làm mới mỗi 5 giây trừ khi paused."""
    try:
        pair = get_pair()
    except FileNotFoundError as e:
        st.error(f"{e}. File mô hình M1 nằm ở RQ4_Retrain_Compare/models và không được commit; huấn luyện bằng "
                 "python RQ4_Retrain_Compare/scripts/05_train_models.py m1.")
        return

    @st.fragment(run_every=None if paused else "5s")
    def body():
        c0, c1 = st.columns(2)
        limit = c0.slider("Số flow mới nhất", 100, 3000, 1000, step=100, key=key + "_limit")
        top_k = c1.slider("Số đặc trưng SHAP", 3, 10, 5, key=key + "_topk")
        query = st.text_input("Tìm flow theo flow ID (gõ một phần cũng được)", key=key + "_q", placeholder="dán flow ID vào đây").strip()
        try:
            if query:
                flows, tb = _search(db_path, query)
            else:
                flows, tb = _table(db_path, source, limit, run_id() if callable(run_id) else run_id)
        except Exception as exc:  # DB đang bận hoặc chưa có bảng
            st.error(f"Không đọc được DB: {exc}")
            return
        if tb.empty:
            st.info("Không có flow nào khớp flow ID này." if query else "Chưa có flow nào trong phạm vi đang chọn (lượt dữ liệu và nguồn ở thanh bên).")
            return
        if query:
            st.caption(f"Đang hiển thị {len(tb)} flow khớp «{query}» trên toàn bộ DB, bỏ qua lọc lượt và nguồn ở thanh bên. Xóa ô tìm để quay lại.")
        n = len(tb)
        c = st.columns(5)
        c[0].metric("Số flow", f"{n:,}")
        c[1].metric("M0 báo tấn công", f"{tb.M0_attack.mean() * 100:.1f}%")
        c[2].metric("M1 báo tấn công", f"{tb.M1_attack.mean() * 100:.1f}%")
        c[3].metric("Hai mô hình khác nhãn", f"{int(tb.disagree.sum()):,}")
        c[4].metric("Trong vùng FIN của Hulk", f"{int(tb.in_zone.sum()):,}")
        st.caption("Flow chưa có nhãn thật trong DB, nên tab này không kết luận mô hình nào đúng. "
                   "Nếu lúc bắt bạn chỉ lướt web bình thường thì flow nên là Benign.")
        left, right = st.columns(2)
        with left:
            st.markdown("**Số flow theo nhãn dự đoán**")
            st.dataframe(pd.concat([tb.M0_label.value_counts().rename("M0"), tb.M1_label.value_counts().rename("M1")], axis=1).fillna(0).astype(int), width="stretch")
        with right:
            st.markdown("**M0 (hàng) so với M1 (cột)**")
            st.dataframe(pd.crosstab(tb.M0_label, tb.M1_label), width="stretch")

        st.markdown("**Chọn một flow để xem SHAP của cả hai mô hình**")
        only_dis = st.checkbox("Chỉ các flow hai mô hình khác nhãn", value=bool(tb.disagree.any()) and not query, key=key + "_dis")
        pick = tb[tb.disagree] if only_dis else tb
        if pick.empty:
            st.info("Không có flow phù hợp.")
            return
        show = pick[["flow_id", "source", "M0_label", "M0_conf", "M1_label", "M1_conf", "in_zone"]].reset_index(drop=True)
        sel = st.dataframe(show, width="stretch", height=240, on_select="rerun", selection_mode="single-row", hide_index=True, key=key + "_tbl")
        rows = sel.selection.rows if sel and sel.selection else []
        flow_id = show.flow_id[rows[0]] if rows and rows[0] < len(show) else show.flow_id[0]
        row = flows[flows.flow_id == flow_id]
        res = pair.explain_flow(row, top_k=top_k)
        st.markdown(f"**Flow:** `{flow_id}` · nguồn: {row.source.iloc[0]} · nhãn thật: {row.label_true.iloc[0] or 'chưa có'} · "
                    f"trong vùng FIN của Hulk: {'có' if bool(pair.in_zone(row).iloc[0]) else 'không'}")
        a, b = st.columns(2)
        for col, k, title in [(a, "M0", "M0, dữ liệu cũ"), (b, "M1", "M1, dữ liệu improved")]:
            with col:
                r = res[k]
                st.markdown(f"##### {title}")
                st.metric("Nhãn dự đoán", r["label"], delta=f"{r['top3'][0][1] * 100:.1f}% tin cậy", delta_color="off")
                st.caption("Xác suất cao nhất: " + ", ".join(f"{cl} {p * 100:.1f}%" for cl, p in r["top3"]))
                _shap_chart(r["shap"]["top_k"])
                st.caption(f"Sai số cộng dồn SHAP: {r['shap']['additivity_error']:.1e}. Phiên bản mô hình: {r['model_version']}")
        st.markdown("**Giá trị các đặc trưng chính của flow này**")
        st.dataframe(row[mc.KEY_FEATURES].T.rename(columns={row.index[0]: "Giá trị"}), width="stretch")
        st.warning("Cách đọc: M1 báo Benign đúng trên flow Benign thật không chứng minh M1 tốt. M1 chưa được thử trên tấn công độc lập, "
                   "vẫn dựa nhiều vào đặc trưng cửa sổ nhận (Init Bwd Win Byts), và chỉ nhận 3,7% đến 11,8% Hulk của bộ test cũ. "
                   "Tab này minh họa vì sao hai mô hình khác nhau, không dùng để xếp hạng chúng.")

    st.caption("M0: mô hình RQ1, học từ dữ liệu cũ (15 lớp). M1: mô hình RQ4, học từ dữ liệu improved (13 lớp). Cùng 78 đặc trưng, cùng siêu tham số. "
               "Tab tự dự đoán lại các flow đã lưu bằng cả hai mô hình và đọc DB ở chế độ chỉ đọc, không đổi gì ở API hay DB.")
    body()
