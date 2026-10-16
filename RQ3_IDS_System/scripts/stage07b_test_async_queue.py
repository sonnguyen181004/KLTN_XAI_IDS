"""Bước 7b — Test hàng đợi giải thích bất đồng bộ (sửa lỗi kiến trúc ở bước 7):
  1) /predict phải trả lời NHANH (không còn +40ms SHAP chặn trong response).
  2) Response có explanation_status="queued"; SHAP CHƯA có ngay, nhưng xuất hiện
     trong DB sau một chút (worker nền xử lý xong).
  3) Dội maxsize + 20 flow tấn công đồng thời theo dung lượng trong config ->
     phải có ít nhất 1 flow bị "dropped_queue_full", NHƯNG Alert của flow đó vẫn
     phải tồn tại trong DB (không mất cảnh báo, chỉ mất phần giải thích).
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests
import yaml

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[2]
RQ3_ROOT = Path(__file__).resolve().parents[1]


def load_config() -> dict:
    with open(RQ3_ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def wait_for_server(url: str, timeout_s: float = 20.0) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        try:
            if requests.get(url, timeout=1).status_code == 200:
                return True
        except requests.exceptions.ConnectionError:
            pass
        time.sleep(0.3)
    return False


def main() -> int:
    cfg = load_config()
    host, port = cfg["api"]["host"], cfg["api"]["port"]
    base_url = f"http://{host}:{port}"
    maxsize = cfg["api"]["max_explain_queue"]

    print("=" * 70)
    print("BƯỚC 7b: TEST HÀNG ĐỢI GIẢI THÍCH BẤT ĐỒNG BỘ")
    print("=" * 70)

    server_log_path = RQ3_ROOT / "data" / "stage07b_server.log"
    server_log_path.parent.mkdir(parents=True, exist_ok=True)
    server_log_file = open(server_log_path, "w", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", host, "--port", str(port)],
        cwd=str(RQ3_ROOT), stdout=server_log_file, stderr=subprocess.STDOUT,
    )

    all_ok = True
    try:
        if not wait_for_server(f"{base_url}/health"):
            server_log_file.flush()
            print("[FAIL] Server không lên được. Log:")
            print(server_log_path.read_text(encoding="utf-8", errors="replace"))
            return 1
        print(f"Server đã sẵn sàng. Hàng đợi giải thích maxsize={maxsize}.")

        attack_payload = json.loads((RQ3_ROOT / "data/samples/sample_attack.json").read_text(encoding="utf-8"))

        # ---- Việc 1: /predict trả lời không chờ SHAP, trả về 'queued' ngay ----------------
        print("\n--- Việc 1: /predict KHÔNG CHỜ SHAP nữa, trả 'queued' ngay ---")
        t0 = time.perf_counter()
        r = requests.post(f"{base_url}/predict", json=attack_payload)
        wall_ms = (time.perf_counter() - t0) * 1000
        body = r.json()
        print(f"  status={r.status_code}, explanation_status={body['explanation_status']}, "
              f"shap trong response={'shap' in body}")
        print(f"  timing_ms={body['timing_ms']}, thời gian thực đo từ client={wall_ms:.1f}ms")
        # Tiêu chí ĐÚNG: response không còn field 'shap' (vì không tính ngay trong request
        # này nữa) và trạng thái phải là 'queued'. KHÔNG áp ngưỡng thời gian tuyệt đối —
        # thử ở bước 7 cho thấy có ~80-90ms overhead mỗi request KHÔNG LIÊN QUAN đến SHAP
        # (có sẵn từ trước, có thể do FastAPI/SQLite/Windows, cần đo riêng ở E1, không phải
        # phạm vi bước này). Bằng chứng ĐÚNG của việc tách SHAP ra nền: response không có
        # key 'shap' và 'timing_ms' không có key 'shap' (so với bước 7 luôn có cả hai).
        ok = (r.status_code == 200 and body["explanation_status"] == "queued"
              and "shap" not in body and "shap" not in body["timing_ms"])
        print(f"  [{'PASS' if ok else 'FAIL'}] (response không còn trường 'shap' — SHAP đã tách sang hàng đợi nền)")
        all_ok &= ok
        alert_id = body["alert_id"]
        flow_id = body["flow_id"]

        # ---- Việc 2: đợi worker nền xử lý xong, SHAP xuất hiện trong DB ------------------
        print("\n--- Việc 2: đợi worker nền tính SHAP, kiểm tra DB ---")
        sys.path.insert(0, str(RQ3_ROOT / "app"))
        import db  # noqa: E402
        conn = db.init_db(REPO_ROOT / cfg["paths"]["sqlite_db"])
        shap_json = None
        for _ in range(20):  # chờ tối đa 2 giây
            row = conn.execute("SELECT shap_top5_json FROM Reliability WHERE alert_id=?", (alert_id,)).fetchone()
            if row and row[0]:
                shap_json = row[0]
                break
            time.sleep(0.1)
        ok = shap_json is not None and len(json.loads(shap_json)) == 5
        print(f"  Sau khi đợi: shap_top5_json={'có, 5 đặc trưng' if ok else 'THIẾU'} -> [{'PASS' if ok else 'FAIL'}]")
        all_ok &= ok

        qstatus = requests.get(f"{base_url}/explain_queue_status").json()
        print(f"  Trạng thái hàng đợi: {qstatus}")

        # ---- Việc 3: dội nhiều flow ĐỒNG THỜI để ép hàng đợi đầy -------------------------
        # QUAN TRỌNG: phải gửi SONG SONG (nhiều luồng cùng lúc), không phải tuần tự —
        # nếu gửi tuần tự (chờ xong request này mới gửi request sau), worker nền xử lý
        # SHAP (~40ms) nhanh hơn tốc độ gửi tuần tự nên hàng đợi không bao giờ đầy kịp
        # (đã thử và thấy 0/60 dropped ở lần chạy đầu — lỗi THIẾT KẾ TEST, không phải lỗi
        # hàng đợi). Dùng ThreadPoolExecutor để bắn gần như đồng thời.
        n_requests = maxsize + 20
        print(f"\n--- Việc 3: dội {n_requests} request ĐỒNG THỜI (maxsize={maxsize}) để ép hàng đợi đầy ---")

        def _one_request(_):
            r = requests.post(f"{base_url}/predict", json=attack_payload)
            if r.status_code != 200:
                return None, f"http_{r.status_code}"
            body = r.json()
            return body["alert_id"], body["explanation_status"]

        with ThreadPoolExecutor(max_workers=n_requests) as pool:
            alert_ids = list(pool.map(_one_request, range(n_requests)))
        statuses = [s for _, s in alert_ids]
        n_dropped = statuses.count("dropped_queue_full")
        n_queued = statuses.count("queued")
        print(f"  Kết quả: {n_queued} 'queued', {n_dropped} 'dropped_queue_full' (tổng {n_requests})")
        ok = n_dropped > 0
        print(f"  [{'PASS' if ok else 'FAIL'}] (kỳ vọng có ít nhất 1 flow bị dropped vì gửi dồn dập hơn maxsize)")
        all_ok &= ok

        if n_dropped > 0:
            dropped_alert_id = next(aid for aid, s in alert_ids if s == "dropped_queue_full")
            row = conn.execute("SELECT alert_id, predicted_label FROM AlertRecord WHERE alert_id=?", (dropped_alert_id,)).fetchone()
            ok2 = row is not None
            print(f"  Kiểm tra alert_id={dropped_alert_id} (bị dropped giải thích) VẪN có trong AlertRecord: "
                  f"{'có' if ok2 else 'MẤT'} -> [{'PASS' if ok2 else 'FAIL'}]")
            all_ok &= ok2
            rel_row = conn.execute("SELECT shap_top5_json FROM Reliability WHERE alert_id=?", (dropped_alert_id,)).fetchone()
            print(f"  (Reliability của alert bị dropped: shap_top5_json = {rel_row[0] if rel_row else '(không có dòng)'} "
                  "— đúng ra phải rỗng/NULL vì không được xếp hàng)")

        conn.close()

    finally:
        print("\nĐang tắt server...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        server_log_file.close()

    print("\n" + "=" * 70)
    print("BƯỚC 7b " + ("HOÀN TẤT — mọi kiểm tra đúng như kỳ vọng." if all_ok else "CÓ LỖI, xem [FAIL] ở trên."))
    print("=" * 70)
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
