"""Bảng tri thức miền (domain knowledge) cho GĐ 11 — CHỐT TRƯỚC khi xem Top-5 SHAP/LIME.

Mỗi lớp tấn công có hai phiên bản:
  - "strict": đặc trưng có liên hệ cơ chế tấn công trực tiếp, rõ ràng nhất (ít đặc trưng).
  - "broad": strict + các đặc trưng liên quan gián tiếp / cùng nhóm hành vi (nhiều hơn).
strict luôn là tập con của broad.

Nguồn trích dẫn dùng chung:
  [1] Sharafaldin, I., Lashkari, A.H., Ghorbani, A.A. (2018). "Toward Generating a New
      Intrusion Detection Dataset and Intrusion Traffic Characterization." ICISSP 2018 —
      mô tả kịch bản tấn công gốc của CSE-CIC-IDS2018 (loại tấn công, công cụ, hành vi).
  [2] Lashkari, A.H. et al. — tài liệu đặc trưng CICFlowMeter (định nghĩa 78+ đặc trưng
      flow dùng trong dataset này: IAT, header length, window size, flag counts, …).
  [3] OWASP / tài liệu công cụ gốc (Slowloris, LOIC, HOIC, Hulk, GoldenEye) — mô tả cơ chế
      tấn công tầng ứng dụng/băng thông làm cơ sở gán đặc trưng kỳ vọng.
  [4] Kiến thức an ninh mạng phổ biến về brute-force/port-scan/injection (hành vi kết nối
      lặp lại, payload bất thường) — dùng khi không có mô tả cụ thể trong [1]-[3].

Đây là một bảng được XÂY DỰNG DỰA TRÊN HIỂU BIẾT CHUNG VỀ CƠ CHẾ TẤN CÔNG, không phải một
benchmark chính thức đã công bố cho riêng tập 78 đặc trưng này — ghi rõ để không bị hiểu
nhầm là một ground-truth tuyệt đối. Đây chính là điểm GĐ11 cần nêu rõ khi báo cáo.
"""
from __future__ import annotations

# class -> {"strict": [...], "broad": [...], "rationale": str, "source": str}
DOMAIN_KNOWLEDGE: dict[str, dict] = {
    "DDOS attack-HOIC": {
        "strict": ["Flow Byts/s", "Flow Pkts/s", "Fwd Pkts/s", "Flow Duration"],
        "broad": ["Flow Byts/s", "Flow Pkts/s", "Fwd Pkts/s", "Flow Duration",
                  "Tot Fwd Pkts", "TotLen Fwd Pkts", "Flow IAT Mean", "Flow IAT Std"],
        "rationale": "HOIC là công cụ DDoS băng thông cao, gửi số lượng lớn request HTTP "
                     "đồng thời -> tốc độ gói/byte và mật độ gói tăng vọt, flow ngắn.",
        "source": "[1][3]",
    },
    "DDOS attack-LOIC-UDP": {
        "strict": ["Flow Byts/s", "Flow Pkts/s", "Tot Fwd Pkts", "Fwd Pkts/s"],
        "broad": ["Flow Byts/s", "Flow Pkts/s", "Tot Fwd Pkts", "Fwd Pkts/s",
                  "TotLen Fwd Pkts", "Flow Duration", "Protocol"],
        "rationale": "LOIC bản UDP flood: gửi gói UDP liên tục tốc độ cao, không cần bắt "
                     "tay TCP -> đặc trưng liên quan giao thức và tốc độ gói nổi bật.",
        "source": "[1][3]",
    },
    "DDoS attacks-LOIC-HTTP": {
        "strict": ["Flow Byts/s", "Flow Pkts/s", "Fwd Pkts/s", "Flow IAT Mean"],
        "broad": ["Flow Byts/s", "Flow Pkts/s", "Fwd Pkts/s", "Flow IAT Mean",
                  "Flow Duration", "Tot Fwd Pkts", "Fwd Header Len", "Dst Port"],
        "rationale": "LOIC bản HTTP flood gửi liên tục request GET/POST tới một cổng dịch "
                     "vụ web cố định -> tốc độ gói cao, IAT rất nhỏ và đều.",
        "source": "[1][3]",
    },
    "DoS attacks-GoldenEye": {
        "strict": ["Flow Byts/s", "Flow Pkts/s", "Flow Duration", "Fwd Pkts/s"],
        "broad": ["Flow Byts/s", "Flow Pkts/s", "Flow Duration", "Fwd Pkts/s",
                  "Fwd Header Len", "Tot Fwd Pkts", "Dst Port"],
        "rationale": "GoldenEye là công cụ HTTP flood tốc độ cao (nhiều header/request mỗi "
                     "kết nối) nhằm làm cạn tài nguyên server web.",
        "source": "[1][3]",
    },
    "DoS attacks-Hulk": {
        "strict": ["Flow Byts/s", "Flow Pkts/s", "Flow Duration", "TotLen Fwd Pkts"],
        "broad": ["Flow Byts/s", "Flow Pkts/s", "Flow Duration", "TotLen Fwd Pkts",
                  "Fwd Pkts/s", "Fwd Seg Size Min", "Dst Port"],
        "rationale": "Hulk sinh request HTTP ngẫu nhiên hoá tiêu đề/URL với tải trọng lớn, "
                     "tốc độ cao nhằm làm quá tải web server.",
        "source": "[1][3]",
    },
    "DoS attacks-SlowHTTPTest": {
        "strict": ["Flow Duration", "Flow IAT Mean", "Flow IAT Max", "Fwd Pkts/s"],
        "broad": ["Flow Duration", "Flow IAT Mean", "Flow IAT Max", "Fwd Pkts/s",
                  "Active Mean", "Idle Mean", "Fwd Header Len"],
        "rationale": "SlowHTTPTest là tấn công 'low-and-slow' (gửi header/body cực chậm) "
                     "-> flow kéo dài bất thường, IAT lớn, tốc độ gói rất thấp.",
        "source": "[1][3]",
    },
    "DoS attacks-Slowloris": {
        "strict": ["Flow Duration", "Flow IAT Mean", "Flow IAT Max", "Active Mean"],
        "broad": ["Flow Duration", "Flow IAT Mean", "Flow IAT Max", "Active Mean",
                  "Idle Mean", "Idle Max", "Fwd Pkts/s", "Dst Port"],
        "rationale": "Slowloris giữ nhiều kết nối HTTP mở bằng cách gửi header một phần, "
                     "rất chậm -> thời gian flow dài, nhiều giai đoạn Active/Idle xen kẽ.",
        "source": "[1][3]",
    },
    "Bot": {
        "strict": ["Dst Port", "Flow IAT Mean", "Flow IAT Std", "Idle Mean"],
        "broad": ["Dst Port", "Flow IAT Mean", "Flow IAT Std", "Idle Mean",
                  "Flow Duration", "Fwd Pkts/s", "Init Fwd Win Byts"],
        "rationale": "Lưu lượng botnet C2 (Ares) thường có nhịp beacon định kỳ tới cổng cố "
                     "định -> IAT đều/ổn định, xen kẽ thời gian Idle giữa các lần liên lạc.",
        "source": "[1][4]",
    },
    "FTP-BruteForce": {
        "strict": ["Dst Port", "Flow Duration", "Tot Fwd Pkts", "Init Fwd Win Byts"],
        "broad": ["Dst Port", "Flow Duration", "Tot Fwd Pkts", "Init Fwd Win Byts",
                  "SYN Flag Cnt", "ACK Flag Cnt", "Fwd Pkts/s"],
        "rationale": "Brute-force FTP thử nhiều mật khẩu liên tiếp tới cổng 21 -> nhiều flow "
                     "ngắn, lặp lại, cùng cổng đích, số gói bắt tay ít.",
        "source": "[1][4]",
    },
    "SSH-Bruteforce": {
        "strict": ["Dst Port", "Flow Duration", "Tot Fwd Pkts", "Init Fwd Win Byts"],
        "broad": ["Dst Port", "Flow Duration", "Tot Fwd Pkts", "Init Fwd Win Byts",
                  "SYN Flag Cnt", "ACK Flag Cnt", "Fwd Pkts/s"],
        "rationale": "Tương tự FTP-BruteForce nhưng tới cổng 22 — thử đăng nhập lặp lại, "
                     "flow ngắn và nhiều, cùng cổng đích cố định.",
        "source": "[1][4]",
    },
    "Brute Force -Web": {
        "strict": ["Dst Port", "Fwd Pkt Len Mean", "Flow Duration", "Tot Fwd Pkts"],
        "broad": ["Dst Port", "Fwd Pkt Len Mean", "Flow Duration", "Tot Fwd Pkts",
                  "Fwd Header Len", "ACK Flag Cnt", "PSH Flag Cnt"],
        "rationale": "Brute-force form đăng nhập web (cổng 80/443) qua nhiều request "
                     "POST lặp lại -> cổng đích cố định, độ dài payload khá đều.",
        "source": "[1][4]",
    },
    "Brute Force -XSS": {
        "strict": ["Dst Port", "Fwd Pkt Len Mean", "Fwd Pkt Len Max", "Flow Duration"],
        "broad": ["Dst Port", "Fwd Pkt Len Mean", "Fwd Pkt Len Max", "Flow Duration",
                  "Fwd Header Len", "PSH Flag Cnt", "Tot Fwd Pkts"],
        "rationale": "Tiêm XSS qua tham số web -> payload request (độ dài gói) khác biệt "
                     "so với truy cập thường, cùng cổng dịch vụ web.",
        "source": "[1][4]",
    },
    "SQL Injection": {
        "strict": ["Dst Port", "Fwd Pkt Len Mean", "Fwd Pkt Len Max", "Flow Duration"],
        "broad": ["Dst Port", "Fwd Pkt Len Mean", "Fwd Pkt Len Max", "Flow Duration",
                  "Fwd Header Len", "PSH Flag Cnt", "Tot Fwd Pkts"],
        "rationale": "Tiêm SQL qua tham số web, cơ chế tương tự Brute Force -XSS ở tầng "
                     "mạng (payload bất thường trong request HTTP tới cổng dịch vụ web).",
        "source": "[1][4]",
    },
    "Infilteration": {
        "strict": ["Dst Port", "Protocol", "Init Fwd Win Byts", "Flow Duration"],
        "broad": ["Dst Port", "Protocol", "Init Fwd Win Byts", "Flow Duration",
                  "Fwd Pkt Len Mean", "Tot Fwd Pkts", "Fwd Seg Size Min"],
        "rationale": "Infiltration mô phỏng khai thác lỗ hổng nội bộ + dò quét sau khi "
                     "chiếm được máy -> đa dạng cổng/giao thức đích, hành vi khác lưu "
                     "lượng bình thường ở cấu hình kết nối ban đầu (window size, duration).",
        "source": "[1][4]",
    },
}

# Các đặc trưng được coi là "dấu vân tay môi trường" (environment fingerprint) — cầu nối
# sang RQ3: nếu các đặc trưng này chiếm tỷ lệ cao trong Top-5, có khả năng model đang dựa
# vào đặc điểm riêng của môi trường thu thập dữ liệu (ví dụ cấu hình mạng khi capture) hơn
# là bản chất cơ chế tấn công.
ENVIRONMENT_FINGERPRINT_FEATURES = ["Fwd Seg Size Min", "Dst Port", "Init Fwd Win Byts"]
