# Kiến trúc, tiến độ và kế hoạch RQ3

Tài liệu hợp nhất ngày 16/10/2026. Chỉ còn 5 tài liệu RQ3 chính: [kiến trúc và kế hoạch](plan.md), [chạy và đọc UI](dashboard_usage.md), [vận hành](operations.md), [kiểm chứng XAI](xai_validation.md), [tương thích đặc trưng](feature_compatibility.md).

> Trạng thái hiện hành: capture project v2; feeder checkpoint/chống gửi trùng; SHAP queue 200 và phục hồi sau restart. Giữ XGBoost/78 đặc trưng, cấu hình LIME RQ2 và nhánh A/B. Các mục audit/nhật ký bên dưới giữ số liệu của phiên bản được ghi tại thời điểm kiểm thử, không phải mọi nhận định đều mô tả bản hiện tại. Chưa chứng nhận tương thích đầy đủ train–PCAP; nhãn live chưa phải ground truth.

## Trạng thái hiện tại và thứ tự làm tiếp

Đây là mục đọc trước; các nhật ký phía dưới giữ lại để truy vết, không phải danh sách việc chưa làm hôm nay.

**Quyết định mới nhất (18/10/2026):** ưu tiên hoàn chỉnh logic, UI và realtime ổn định, chưa ưu tiên demo tấn công. Làm từng bước; mỗi bước ghi mục đích, thay đổi, kiểm tra, giới hạn và commit riêng, rồi dừng báo cáo trước bước kế tiếp. Không tự push. Hướng dẫn chạy terminal vẫn có hiệu lực; nút Start/Stop được đưa vào lộ trình sau bộ quản lý tiến trình, chưa triển khai. Không tự mở capture, reset DB hoặc đổi model để phục vụ cập nhật tài liệu.

### Lộ trình hoàn thiện hiện hành — thực hiện tuần tự

Các mã HT dưới đây là bước hoàn thiện mới, không thay số Bước 1–16 hoặc E1–E5 trong nhật ký nghiên cứu cũ. Bảng ưu tiên ngày 16/10 phía dưới được giữ làm lịch sử; nếu khác nhau, dùng bảng này.

| Bước | Mục đích và phạm vi | Nghiệm thu / tài liệu tương ứng | Tiến độ |
|---|---|---|---|
| HT1 | Chốt hợp đồng dữ liệu, thời gian và trạng thái; phân biệt code đang có với thiết kế cần thêm | Đối chiếu code, ghi hợp đồng trong `operations.md`; không sửa runtime | Hoàn tất đặc tả 18/10/2026; xem nhật ký HT1 bên dưới |
| HT2 | Kiểm chứng đặc trưng và vòng đời flow trước khi tối ưu capture | Điều tra nguồn train, fixture công thức/timeout/đóng flow; mọi thay đổi có version và đối chiếu, không ép cờ để giảm Hulk. Cập nhật `feature_compatibility.md` | Đang làm: HT2.1 xong 18/10; chưa sửa runtime, chưa chứng nhận tương thích |
| HT3 | Hoàn thiện giao nhận, phục hồi và giới hạn tài nguyên | Kiểm thử mất ACK/restart/file lỗi, chống ghi trùng, backlog XAI, lưu trữ; cập nhật `operations.md` | Chưa bắt đầu; kế thừa checkpoint/idempotency v2 |
| HT4 | Quản lý realtime độc lập vòng làm mới UI | Start/Stop, ownership, heartbeat, flush/drain, khôi phục trạng thái; cập nhật `operations.md` | Chưa bắt đầu |
| HT5 | Hoàn thiện logic đánh giá và XAI | Nhãn thật có nguồn, nhận xét analyst, tham chiếu RQ2, chẩn đoán SHAP/LIME; cập nhật `xai_validation.md` | Chưa bắt đầu |
| HT6 | Hoàn thiện UI dựa trên API/trạng thái đã kiểm chứng | Tổng quan, realtime, CSV/PCAP, flow/cảnh báo, đánh giá; test thao tác và dữ liệu; cập nhật `dashboard_usage.md` | Chưa bắt đầu |
| HT7 | Nghiệm thu toàn hệ thống | E5 đầy đủ, E1, kiểm thử sự cố/chạy lâu/tài nguyên; đồng bộ README và Word theo thực tế | Chưa bắt đầu |

Nếu một bước lớn cần chia nhỏ, ghi HT2.1, HT2.2… với phạm vi và commit riêng trước khi làm; không gộp thay đổi phương pháp với sửa UI. Điều tra thiếu nguồn train không ngăn các bước vận hành độc lập, nhưng phải ghi rõ phần bị chặn và được thống nhất trước khi chuyển bước. Không đánh dấu tương thích hoàn toàn hoặc hoàn thành E4 chỉ vì sửa cờ TCP. Mỗi bước sau phải cập nhật lại trạng thái ở bảng này.

### Nhật ký HT2.1 — 18/10/2026

- **Mục đích:** kiểm chứng giả thuyết cờ TCP và các giới hạn vòng đời capture để chọn việc sửa có bằng chứng. Phạm vi điều tra nhỏ thuộc HT2, không phải hoàn thành toàn bộ HT2.
- **Đã làm:** rà nguồn code/lịch sử preprocessing, kiểm tra đường đếm cờ Java tham khảo; thêm Stage25 đọc model và trích hai PCAP offline để so nhị phân hóa cờ trong bộ nhớ; thêm sáu fixture vòng đời v2 vào Stage20. Chi tiết và giới hạn nằm trong [báo cáo HT2.1](feature_compatibility.md#ht21).
- **Kết quả quan trọng:** 74/92 vector đổi cờ nhưng 92/92 nhãn, xác suất và lá cây không đổi. Model dùng ngưỡng 1 tại các split cờ, nên không lấy count>1 làm nguyên nhân trực tiếp đã chứng minh cho Hulk. Tái hiện idle đúng 240s phụ thuộc thứ tự GC, FIN/RST chưa đóng flow, tuple tái sử dụng bị gộp và IAT âm khi packet lệch thứ tự.
- **Kiểm tra mới:** Stage20 21/21 PASS; Stage23 self-test 3/3 PASS; Stage25 92 flow, 0 nhãn đổi. Test baseline PASS xác nhận cả hành vi chưa tốt, không chứng minh đã sửa. Có cảnh báo phiên bản pickle/encoder; không ghi đè model. Không chạy API/UI/capture live, không sửa DB hoặc dữ liệu đầu vào.
- **Tài liệu:** cập nhật mục này, `feature_compatibility.md`, ghi chú `operations.md`; thêm một JSON tổng hợp có checksum, không thêm Markdown mới. Chỉ thêm diagnostic/test, giữ nguyên runtime và cấu hình.
- **Commit của bước:** `git log --oneline --grep="test(rq3): audit flag sensitivity and capture lifecycle"`.
- **Chưa giải quyết:** nguồn tạo Parquet còn thiếu; chưa đọc nội dung hai báo cáo Word trong thư mục processed ở bước này; chưa hoàn tất độ đúng đầu vào hay giảm báo nhầm. Không đánh dấu E4 hoàn tất.
- **Tiếp theo:** HT2.2, ưu tiên sửa ranh giới idle nhất quán bằng adapter có version và đối chiếu PCAP; chốt riêng chính sách packet lệch thứ tự/TCP close trước khi triển khai các thay đổi tiếp theo. Dừng sau commit HT2.1 để báo cáo.

### Nhật ký HT1 — 18/10/2026

- **Mục đích:** có một hợp đồng chung để API, capture, feeder và UI không diễn giải khác nhau về dữ liệu/trạng thái; tránh biến thiết kế tương lai thành lời khẳng định hệ thống đã có.
- **Đã làm:** đối chiếu `normalize.py`, `flow_metadata.py`, `main.py`, `db.py`, `feeder.py`, `explain_queue.py`, `explain_lime.py`, `monitoring.py`, `dashboard.py` và capture v2; ghi [hợp đồng dữ liệu và trạng thái](operations.md#contract-ht1).
- **Phạm vi thay đổi:** chỉ `plan.md` và `operations.md`; không thêm Markdown mới, không sửa Word gốc, model, code, config, DB hoặc PCAP. Word và README sẽ được đồng bộ khi các phần triển khai tương ứng được chốt, không ghi trước là đã có chức năng.
- **Kiểm tra:** đối chiếu tên trường/trạng thái với code; kiểm tra `git diff --check`, liên kết nội bộ của phần mới và phạm vi diff trước commit. Đây là nghiệm thu đặc tả, không phải kiểm thử runtime mới hoặc chứng nhận tương thích 78 công thức.
- **Commit của bước:** tra bằng `git log --oneline --grep="docs(rq3): define HT1 data and lifecycle contract"`; không ghi hash của chính commit vào nội dung commit đó.
- **Tiếp theo:** HT2, bắt đầu bằng điều tra và chốt nhóm đặc trưng/vòng đời flow cần kiểm chứng; chưa tự nhị phân hóa cờ hoặc giảm timeout.

| Ưu tiên | Công việc | Điều kiện hoàn tất |
|---|---|---|
| Đã làm | Gom 11 Markdown RQ3 thành 5 tài liệu; sửa liên kết, giữ JSON bằng chứng | Không còn liên kết tới file đã gộp; bản cũ phục hồi được bằng Git |
| Đang hoàn thiện | UI: Giám sát flow / Hướng dẫn live / Nạp CSV–PCAP; đọc từng flow, biểu đồ, trạng thái SHAP/LIME | Regression API/UI PASS và mở bản chạy trên máy; chưa coi hướng dẫn terminal là nút điều khiển capture |
| Đang ưu tiên | Hướng dẫn tự chạy/test, xác nhận đúng lượt/nguồn và ghi nhận lỗi khi người dùng test | Có bước CSV, PCAP, live liên tục, dừng/tiếp tục và chẩn đoán rõ; không gán trạng thái “đang bắt” chỉ từ API khỏe |
| Hoãn | Nút Bắt đầu/Dừng capture và telemetry trực tiếp trên UI | Chỉ triển khai khi tiếp tục hạng mục này; cần quản lý process, chống chạy trùng và dừng/flush/drain an toàn |
| Tiếp theo 2 | Đo chạy lâu/tải và phục hồi, E1 độ trễ | Ghi số flow CSV/API, thời gian HTTP/end-to-end, queue/SHAP dropped và tài nguyên; phân biệt packet sniff với flow đã xuất |
| Tiếp theo 3 | Xác minh train–PCAP và E5 đối chiếu RQ2 | Có nguồn preprocessing/cặp PCAP–CSV để chốt quy ước; E5 chạy nguyên cohort A và cấu hình khóa, không tự sửa kết quả để khớp |
| Tiếp theo 4 | Traffic có nhãn xác minh; FPR/FNR và lab được phép | Tách dự đoán với ground truth; chưa có nhãn thì không báo FPR live; chỉ quyết định train lại sau kiểm tra đầu vào |
| Sau đó | Đóng gói Docker và hoàn tất báo cáo | Cấu hình/dependency tái lập và giới hạn được ghi đúng; Npcap Windows cần phương án riêng |

Các bất biến: cùng `/predict` cho ba nguồn; XGBoost RQ1/78 đặc trưng; cảnh báo trước SHAP nền; LIME thủ công theo RQ2; A/B chỉ trình bày; sáu bảng DB. Không đổi model hay cấu hình giải thích trong đợt gom tài liệu/UI này.

Ngày 16/10/2026: gộp tài liệu, thêm tab hướng dẫn live và đặt tên tab rõ nguồn. Không xóa DB, PCAP, Word hoặc JSON bằng chứng. Hướng dẫn bắt đầu: [chạy và xem UI](dashboard_usage.md).

- [Kiến trúc và nhật ký triển khai](#architecture-history)
- [Thiết kế và nhật ký UI](#ui-history)

---

<a id="architecture-history"></a>

# Kế hoạch xây dựng hệ thống IDS có giải thích (RQ3)

> Dự án **mới hoàn toàn**, không tái sử dụng `cicflowmeter_capture_demo/` cũ. Đặc tả gốc: `Kiến trúc hệ thống IDS.docx` (kiến trúc 7 khối / 6 tầng, mô hình logic 3 làn, mô hình vật lý, API, thực thể dữ liệu, 5 thí nghiệm E1–E5) — tài liệu đó là nguồn sự thật, kế hoạch này là cách triển khai nó thành code.

## 0. Bức tranh tổng thể

**Ổn định vận hành v2 (16/10/2026):** [capture v2, feeder checkpoint/idempotency và khôi phục SHAP](operations.md#stability-v2). Giữ sáu bảng và các tầng kiến trúc; `/predict` lưu giao dịch nguyên khối rồi dispatch SHAP, LIME theo yêu cầu. CLI mặc định sửa window=0; bản quy ước train thử nghiệm tách riêng, chưa thay model/RQ2. Hướng dẫn cũ nói feeder restart luôn gửi lại từ đầu hoặc queue không phục hồi là lịch sử trước bản này; hành vi hiện tại xem tài liệu mới.

**Hợp đồng ngữ nghĩa đặc trưng (16/10/2026):** [audit quan hệ từng dòng train/test](feature_compatibility.md#semantics) đã kiểm tra toàn bộ 3,5 triệu dòng. Xác minh sample SD độ dài trong trường hợp hai packet phân biệt được, floor Down/Up và window thiếu=-1; phát hiện thêm quan hệ hai mean dùng n/n+1. Capture v1 còn khác các quy ước này và ghi đè initial window=0. Subflow packet lại khớp tổng trên toàn bộ tập đủ điều kiện, không được mặc định coi sai. Đã có script/JSON tái lập, chưa đổi runtime/model/LIME; còn thiếu nguồn preprocessing/cặp original PCAP–CSV để chứng nhận tương thích.

**Bản sửa capture v1 (16/10/2026):** [triển khai và kết quả kiểm tra](feature_compatibility.md#adapter-v1). Đã sửa 5 lỗi được audit tái hiện trong adapter thuộc mã dự án; CLI/UI PCAP dùng bản mới mặc định. Có version metadata qua CSV→API→DB→UI, giữ đúng 78 đặc trưng lưu. Test fixture/API/UI PASS; hai PCAP đối chiếu chưa đổi nhãn, LIME còn suy biến. Thử Wi-Fi thật trên DB tạm được ghi riêng trong tài liệu. Phần audit và ma trận dưới đây mô tả baseline trước sửa, không thay chứng cứ lịch sử.

**Audit đặc trưng 16/10/2026:** đã đối chiếu đủ 78 tên/thứ tự cột, quét train 2,8 triệu dòng và nhóm cờ/bulk/active/idle trên daily cleaned 15.589.784 dòng; 8 fixture xác nhận lỗi extractor (lặp gói đầu, CWR, IAT, active/idle, protocol trong khóa flow). Xem [báo cáo tương thích](feature_compatibility.md#baseline-audit) và [ma trận 78 cột](feature_compatibility.md#matrix-78). Chưa sửa extractor hoặc train model. Các nhận định lịch sử dưới đây quy cảnh báo Hulk hoàn toàn cho model/dịch chuyển môi trường cần đọc theo kết luận audit mới; chưa xác minh quan hệ nhân quả đó.

**Cập nhật hàng đợi 16/10/2026:** tăng `api.max_explain_queue` từ 50 lên **200 tác vụ SHAP chờ**, ngoài tác vụ đang chạy. Cần restart API để áp dụng. Giữ chính sách đầy queue thì bỏ SHAP mới, giữ dự đoán/cảnh báo; dashboard lấy dung lượng từ API. Các con số maxsize=50 ở nhật ký Bước 7b dưới đây là bằng chứng của cấu hình lịch sử, không phải giới hạn hiện hành. Chưa có benchmark kết luận 200 tối ưu hoặc cơ chế phục hồi queue sau restart.

**Khối hiển thị dễ hiểu:** [Hướng dẫn đọc đặc trưng, SHAP và LIME](dashboard_usage.md#read-xai). Tên/giá trị/đơn vị được giải nghĩa bằng tiếng Việt; đây là tầng trình bày, không thay logic dự đoán hoặc số liệu nghiên cứu.

**Cập nhật runtime/UI 16/10/2026:** [Dashboard mới và hướng dẫn](dashboard_usage.md), [checklist triển khai](plan.md#ui-history), [LIME suy biến và đối chứng đặc trưng](xai_validation.md#lime-validity). Đã thêm kiểm tra tính hợp lệ lân cận LIME; không đổi cấu hình RQ2, model hoặc luật nhánh A/B. Kết quả giải thích không hợp lệ không được trình bày như R²/Jaccard đáng tin cậy.

```
Tầng 1        Tầng 2              Tầng 3       Tầng 4                Tầng 5         Tầng 6
Traffic  →  Bắt gói & gom   →   Model đoán  →  Giải thích +      →  Quyết định   →  API +
vào          thành flow          (XGBoost)      chấm tin cậy          hiển thị       Dashboard
```

Nguyên tắc cứng (lấy từ tài liệu kiến trúc, không được vi phạm):
- Cảnh báo tạo ngay từ Prediction, **không chờ** giải thích xong.
- SHAP (TreeSHAP) là giải thích **mặc định, tự động**. LIME **chỉ chạy khi analyst bấm xin** (dùng đúng cấu hình đã khóa ở RQ2: `kernel_width=3,312`, `num_samples=1000`, `discretize_continuous=False`, nền 2.000 dòng, seed 42).
- Tầng 5 (nhánh A/B) chỉ đổi **cách hiển thị**, không đổi nhãn, không ẩn cảnh báo.
- Mọi bước ghi lại mốc thời gian (phục vụ thí nghiệm E1).
- Model, 78 cột và thứ tự cột phải **giống hệt** RQ1/RQ2 để so sánh được.

### 0.1. BA nguồn flow hợp lệ ở Tầng 1 — ghi rõ để khỏi quên

Tài liệu kiến trúc (Khối 1 + mô hình logic Làn A) nói **Tầng 1 có đúng 3 nguồn**, KHÔNG chỉ traffic thật:

| # | Nguồn | Cách lấy | Dùng để | Trạng thái code |
|---|---|---|---|---|
| 1 | **Mạng lab thật** (Victim + Attacker) | Npcap/tcpdump bắt gói sống + CICFlowMeter gom flow trực tiếp | Demo thật, thí nghiệm E2/E3/E4 | ❌ Chưa làm — cần máy ảo (M4) + bộ feeder (bước 8b) |
| 2 | **File PCAP đã ghi sẵn** (phát lại bằng `tcpreplay`) | Vẫn qua Npcap + CICFlowMeter (chỉ khác nguồn gói là "phát lại" thay vì "sống") | Demo không cần máy Attacker, hoặc test lại 1 tình huống cố định nhiều lần | ❌ Chưa làm — **dùng CHUNG bộ feeder với nguồn 1** (CICFlowMeter vẫn ghi ra cùng 1 file CSV, feeder không cần biết gói đến từ đâu) |
| 3 | **CSV/Parquet đã có đặc trưng sẵn** (Tập A = cohort RQ2, Tập B = dữ liệu sạch) | Đọc file trực tiếp, không cần bắt gói gì cả | Test hệ thống, E5 (so khớp RQ2) | ✅ Đang dùng từ bước 3 tới giờ |

**Điểm quan trọng nhất (đã làm ĐÚNG từ đầu, xác nhận lại):** tài liệu nói *"Cả hai nguồn đổ vào CÙNG MỘT hộp tiếp theo, nên phần còn lại không cần biết flow đến từ đâu."* — và đúng là vậy: `POST /predict` của hệ thống (từ bước 6) chỉ nhận 1 dòng 78 đặc trưng, **không quan tâm nó từ CICFlowMeter hay từ file CSV có sẵn**. Vậy nguồn 1 và 2 chỉ còn thiếu đúng 1 việc: **bộ feeder** (bước 8b, mục 5.1) đứng giữa CICFlowMeter và `/predict` — **dùng chung cho cả nguồn 1 và nguồn 2**, không cần code riêng cho từng nguồn.

## 1. Hai câu đã chốt trước khi code

### 1.1. Dữ liệu dùng để test — không phải "model học thuộc"
- Khi gọi `/predict`, hệ thống **chỉ gửi 78 con số đặc trưng**, không gửi nhãn thật → model luôn đoán thật, không "tra bảng đáp án". Nhãn thật chỉ giữ riêng để tự so sánh sau.
- Dùng **2 tập dữ liệu**, mục đích khác nhau:
  - **Tập A — cohort 1.339 flow của RQ2** (giữ nguyên, không đổi): bắt buộc dùng để **E5** (so khớp kết quả hệ thống mới với kết quả RQ2 đã có).
  - **Tập B — tập mới, "sạch"**: lấy từ `test_set.parquet`, **loại bỏ hẳn** các dòng trùng với `train_set.parquet` (train/test của CSE-CIC-IDS2018 trùng ~27,7% dòng — vấn đề đã ghi nhận ở RQ2 GĐ1), rồi lấy mẫu ngẫu nhiên phân tầng theo lớp (~200–300 flow). Tập này **chắc chắn model chưa từng thấy dưới bất kỳ hình thức nào** — dùng để demo và test hệ thống nói chung, tránh mọi tranh cãi "có phải học thuộc không".

### 1.2. Test tầng 2 (bắt gói) độc lập, trước khi có lab tấn công
- Việc cài Npcap + CICFlowMeter và thử bắt traffic bình thường của chính máy bạn (mở vài trang web, bắt gói 1–2 phút) là một bước kiểm tra **tách biệt hoàn toàn** khỏi việc dựng máy attacker/victim.
- Mục đích: xác nhận cơ chế "bắt gói → gom flow → ra đúng 78 cột" chạy đúng kỹ thuật, trước khi lo tới việc tấn công thật.
- Việc này bạn tự làm trên máy mình (cài phần mềm), song song với lúc tôi viết code tầng 3–6.

## 2. Các mốc thực hiện (M1 → M5)

| Mốc | Nội dung | Cần máy ảo? | Ai làm |
|---|---|---|---|
| **M0** | Khung dự án: `RQ3_IDS_System/`, `config.yaml`, schema SQLite (6 bảng) | Không | Tôi |
| **M1** | Tầng 2 (chuẩn hóa) + Tầng 3 (dự đoán) + Tầng 4 (SHAP/LIME/độ tin cậy) + Tầng 5 (nhánh A/B) + Tầng 6 (API + Dashboard + Docker), chạy bằng Tập A + Tập B | Không | Tôi |
| **M2** | Thí nghiệm **E1** (đo độ trễ thật qua API) và **E5** (so khớp Tập A với RQ2) | Không | Tôi |
| **M3** | Bạn tự cài Npcap + CICFlowMeter, test bắt gói trên máy mình (mục 1.2) — song song làm với M1 | 1 máy (máy bạn) | Bạn (tôi hướng dẫn) |
| **M4** | Dựng 3 máy ảo VirtualBox (Victim, Attacker, Monitor) trên mạng host-only cô lập, nối hệ thống vào traffic thật | 3 máy ảo | Bạn dựng, tôi hướng dẫn từng lệnh |
| **M5** | Thí nghiệm **E2** (lệch phân bố), **E3** (báo động giả trên traffic thật), **E4** (kiểm chứng cờ môi trường) trên traffic thật từ M4 | 3 máy ảo | Cùng làm |

M0–M2 làm được trọn vẹn ngay bây giờ, không cần chờ gì. M3 làm song song, không phụ thuộc M1/M2. M4–M5 cần bạn chuẩn bị máy ảo trước.

## 3. Chi tiết M1 — xây 6 tầng

### Tầng 2 — Chuẩn hóa flow
- Input: 1 dòng 78+ cột (từ Tập A/B, hoặc sau này từ CICFlowMeter thật).
- Kiểm tra: đủ 78 cột không, có NaN không → thiếu thì trả lỗi `422`, lưu vào bảng `DataError`, **không đoán bừa**.
- Chuẩn hóa: đổi cột thời gian ×1.000.000 (giây → micro giây), xếp đúng thứ tự cột như lúc huấn luyện model.

### Tầng 3 — Dự đoán
- Nạp lại `best_xgboost_model.pkl` + `label_encoder.pkl` từ RQ1 (dùng lại nguyên file, không huấn luyện lại).
- `POST /predict`: trả nhãn + xác suất 15 lớp. Nhãn ≠ Benign → tạo `AlertRecord` ngay.

### Tầng 4 — Giải thích + độ tin cậy
- **TreeSHAP tự động**: mọi Alert đều chạy, lấy Top-5 có dấu, ghi kèm additivity check.
- **LIME theo yêu cầu**: `POST /explain` với `method=lime`, dùng đúng cấu hình khóa ở RQ2.
- **Tính tại chỗ (rẻ)**: faithfulness nhanh + đếm cờ môi trường — **xem lưu ý quan trọng ngay dưới đây, hai thứ này KHÔNG phải bằng chứng kết luận**.
- **Tra bảng có sẵn (đắt)**: độ ổn định + độ chịu nhiễu theo từng lớp — lấy thẳng từ `rq2_master_summary.json` của RQ2, nạp 1 lần lúc khởi động, không tính lại mỗi flow.
- Cờ lớp hiếm: nhãn dự đoán có dưới 100 mẫu huấn luyện thì bật cờ (hiện chỉ SQL Injection).

**⚠️ Lưu ý quan trọng — tránh overclaim:**

- **Cờ môi trường chỉ là cờ cảnh báo, không phải bằng chứng.** Đếm xem Top-5 có bao nhiêu trong 3 đặc trưng (Dst Port, Fwd Seg Size Min, Init Fwd Win Byts) chỉ nói "lời giải thích CÓ KHẢ NĂNG dựa vào đặc điểm môi trường lab, nên xem kỹ hơn" — đây là **giả thuyết tự đặt** (RQ2 mục L3.5), **chưa được kiểm chứng**; việc kiểm chứng thật sự là thí nghiệm **E4** (huấn luyện lại không dùng 3 đặc trưng, so độ chính xác trong/chéo miền). Cờ không chứng minh model sai, không đổi nhãn, không ẩn cảnh báo.
- **Faithfulness tính tại chỗ là PROXY nhanh, không phải phép đo faithfulness đầy đủ của RQ2.** RQ2 đo bài bản: xóa k=1→10, **3 giá trị nền** (median toàn tập, mean toàn tập, median lớp Benign), tính AUC trên cả deletion lẫn insertion, có đối chứng ngẫu nhiên, kiểm định Wilcoxon, chạy hàng nghìn flow. Bản runtime chỉ kịp làm **một bước xóa, một giá trị nền (median toàn tập), một con số duy nhất** — không AUC, không đối chứng ngẫu nhiên đi kèm mỗi lần. Chỉ dùng để so với một **ngưỡng đơn giản tính sẵn từ RQ2** (phục vụ quyết định nhánh A/B ở tầng 5), **không được trích dẫn như một phép đo faithfulness chuẩn** trong báo cáo.

### Tầng 5 — Nhánh A/B
- Ngưỡng tính từ **cohort 1.339 flow theo từng lớp** (ví dụ phân vị thấp của faithfulness) — **không dùng** tập dev 250 flow của RQ2 (184/250 là Benign, không đại diện).
- Nhánh A: mọi chỉ số ổn → hiện SHAP bình thường.
- Nhánh B: 1 chỉ số dưới ngưỡng, hoặc ≥2 cờ môi trường, hoặc lớp hiếm → hiện SHAP kèm dòng "cần xem lại" + nút xem LIME.

### Tầng 6 — API + Dashboard
- **FastAPI**: `POST /predict`, `POST /explain`, `GET /alerts`, `GET /health`.
- **Streamlit**: 1 trang — bảng cảnh báo, biểu đồ SHAP/LIME có dấu, bảng độ tin cậy, nhãn nhánh A/B.
- **Docker Compose**: gói 2 service, chạy bằng `docker compose up`.
- **Lưu trữ**: SQLite (6 bảng: `FlowRecord`, `DataError`, `Prediction`, `AlertRecord`, `Reliability`, `Timing`).

## 4. Chi tiết M2 — E1 và E5

- **E1 (độ trễ)**: bơm Tập A qua `/predict` rồi `/explain` **qua API thật** (HTTP, không gọi hàm Python trực tiếp), đo median và p95 từng khâu (chuẩn hóa, dự đoán, SHAP, LIME, đánh giá tin cậy) — so với số đo "thô" ở RQ2 (SHAP ~19ms, LIME ~148ms) để biết chạy qua API có chậm thêm không.
- **E5 (nhất quán offline)**: Tập A qua API → so nhãn dự đoán và Top-5 SHAP với kết quả gốc đã có từ RQ2. Khớp 100% thì xác nhận code hệ thống không có lỗi (sai cột, sai đơn vị, sai model) so với pipeline RQ2 gốc.

## 5. Chi tiết M4 — dựng traffic thật (để khi tới lúc)

- VirtualBox, 3 máy ảo trên 1 mạng **host-only** (cô lập, không nối internet):
  - **Victim**: Linux, chạy sẵn 1 dịch vụ (nginx hoặc SSH) để có cái tấn công vào.
  - **Attacker**: Linux/Kali, công cụ `hydra` (brute-force), `nmap` (quét cổng), `hping3` (DDoS giả lập).
  - **Monitor**: chạy Npcap/tcpdump + CICFlowMeter + hệ thống (API + Dashboard) của M1.
- Cách đơn giản nhất để bắt đầu: Monitor và Victim **là cùng một máy** (bắt traffic đến/đi chính nó) — không cần cấu hình mạng phức tạp.
- Cách đúng kiến trúc (làm sau): Monitor là máy riêng, bật **promiscuous mode** trên card mạng host-only để "nghe" được cả traffic giữa Victim và Attacker.
- Phương án dự phòng không cần máy Attacker: dùng `tcpreplay` phát lại 1 file pcap mẫu có sẵn, Npcap/CICFlowMeter trên Monitor vẫn bắt được như traffic thật.

### 5.1. Bộ "feeder" — nối CICFlowMeter với hệ thống TỰ ĐỘNG (không qua tay người)

Dùng CHUNG cho cả nguồn 1 (mạng lab thật) và nguồn 2 (phát lại PCAP) ở mục 0.1 — CICFlowMeter ghi ra CSV giống nhau bất kể gói tin là "sống" hay "phát lại", nên feeder không cần phân biệt.

CICFlowMeter tự nó chỉ làm việc "bắt gói + tính đặc trưng + ghi ra CSV" — đây là phần mềm có sẵn, không cần code. Nhưng CICFlowMeter **không tự gửi** dữ liệu sang hệ thống của mình. Cần 1 mảnh code riêng — gọi là **feeder** — đứng giữa 2 bên:

```
CICFlowMeter (bắt gói, ghi CSV)  →  [FEEDER theo dõi file, phát hiện dòng mới]  →  POST /predict  →  Dashboard
```

- **Việc của bạn** (không cần code): cài Npcap + CICFlowMeter, chạy ở chế độ **bắt trực tiếp (live capture)** trỏ vào 1 card mạng — CICFlowMeter sẽ tự ghi thêm dòng mới vào 1 file CSV mỗi khi có flow mới kết thúc.
- **Việc tôi code**: script `feeder.py` chạy nền liên tục, theo dõi file CSV đó, phát hiện dòng MỚI xuất hiện → tự đối chiếu/đổi tên cột, đổi đơn vị μs (tham số đã có sẵn ở bước 4) → tự `POST /predict` → không cần ai copy/paste tay.
- **Test được NGAY BÂY GIỜ, không cần CICFlowMeter thật**: giả lập bằng cách tự ghi từng dòng của Tập B vào 1 file CSV cách nhau vài giây (như CICFlowMeter đang chạy thật), xem feeder có tự phát hiện + tự gửi đúng không. Khi có CICFlowMeter thật, chỉ cần đổi đường dẫn file theo dõi, không sửa code.
- Xếp vào **Bước 8b** trong tiến độ bên dưới — làm độc lập, không phụ thuộc thứ tự bước 9-16.

## 6. Việc tôi làm ngay bây giờ

1. `RQ3_IDS_System/scripts/stage00_build_clean_dataset.py` — tạo Tập B (loại trùng train/test, lấy mẫu phân tầng).
2. `RQ3_IDS_System/app/` — code tầng 2–6 (FastAPI + Streamlit + SQLite schema).
3. `RQ3_IDS_System/scripts/stageE1_latency.py`, `stageE5_consistency.py` — 2 thí nghiệm M2.
4. Test toàn bộ bằng Tập A + Tập B, không cần máy ảo.

## 6.1. Các bước còn lại (Bước 9 → 16) — danh sách để không quên

Viết ra hết TRƯỚC khi làm, để không quên việc gì giữa các lần làm việc. Đánh dấu ✅ và
dời xuống mục 7 (có chi tiết đầy đủ) ngay khi xong, y như các bước 1–8 đã làm.

| Bước | Nội dung | Tầng/Khối liên quan | Input cần có |
|---|---|---|---|
| **10** | "Tra bảng có sẵn (đắt)": nạp `rq2_master_summary.json` 1 lần lúc khởi động, tra `stability_lookup` + `robustness_lookup_json` theo **lớp dự đoán** (không tính lại mỗi flow — xem `gd9_stability`, `gd9_noise` trong file đó). Ghi vào 2 cột đã có sẵn trong `Reliability` nhưng chưa ai điền. | Tầng 4 | `rq2_master_summary.json` (đã có sẵn, đường dẫn trong `config.yaml: paths.rq2_master_summary`) |
| **11** | Tầng 5 — luật quyết định nhánh A/B: không có cờ nào (env_fingerprint_flag=0 và rare_class_flag=0) → nhánh A; có ít nhất 1 cờ → nhánh B. Ghi `branch` + `branch_reason` vào `Reliability`. **Lưu ý đã chốt ở tài liệu kiến trúc (mục "Đồng bộ với phần cũ")**: CHỈ dựa vào 2 cờ lưu ý này, KHÔNG dùng ngưỡng từ tập dev 250 flow của RQ2 (184/250 là Benign, không đại diện), KHÔNG dùng Agreement làm ngưỡng chính (Jaccard\@5 trung bình RQ2 chỉ 0,141). | Tầng 5 (Khối 6) | Cần Bước 8 (cờ) đã xong — ✅ |
| **12** | `GET /alerts` — danh sách Alert kèm trạng thái giải thích, lọc theo thời gian/nhãn/nhánh (theo đúng bảng API trong tài liệu kiến trúc). | Tầng 6 | Cần Bước 11 (branch) để lọc theo nhánh |
| **13** | Streamlit Dashboard — 1 trang: bảng cảnh báo, biểu đồ SHAP/LIME có dấu (2 tab), bảng độ tin cậy, nhãn nhánh A/B, `GET /health`. | Tầng 6 (Khối 7) | Cần `/alerts`, `/explain` đã có |
| **14** | Docker Compose — gói API + Dashboard thành 2 service, chạy bằng `docker compose up` (đúng mô hình vật lý: Monitor chạy Docker Compose, bắt gói chạy NGOÀI container). | Tầng 6 | Cần 13 xong |
| **15** | `scripts/stageE1_latency.py` — M2: bơm Tập A qua `/predict` + `/explain` **qua API thật**, đo median/p95 từng khâu (normalize, predict, SHAP, LIME, reliability), so với RQ2 (SHAP~19ms, LIME~148ms). | M2 (E1) | Cần `/explain` (Bước 9) xong để đo được khâu LIME |
| **16** | `scripts/stageE5_consistency.py` — M2: Tập A qua API → so nhãn + Top-5 SHAP với kết quả gốc RQ2 (khớp 100% thì xác nhận hệ thống không lỗi). | M2 (E5) | Không phụ thuộc bước nào ở trên, có thể làm sớm hơn nếu muốn |

Sau Bước 16 mới tới **M4** (dựng 3 máy ảo Victim/Attacker/Monitor trên VirtualBox host-only) và **M5** (E2 lệch phân bố, E3 báo động giả, E4 cờ môi trường — đo trên traffic thật từ M4).

## 7. Tiến độ (cập nhật sau mỗi bước)

### Bước 1 — `config.yaml` ✅
- **Mục đích**: gom mọi tham số dự án vào 1 file, không ghi cứng đường dẫn/số liệu rải rác trong code.
- Tạo `RQ3_IDS_System/config.yaml`: đường dẫn model/dữ liệu RQ1/RQ2, cấu hình LIME khóa y hệt RQ2 (kernel_width=3,312, num_samples=1000, discretize_continuous=false), 3 đặc trưng cờ môi trường, ngưỡng lớp hiếm (<100 mẫu train), tham số Tập B.
- Kiểm tra: đọc file thành công, xác nhận cả 7 đường dẫn tới dữ liệu/model có sẵn đều tồn tại trên đĩa.
- Sửa 1 lần: bỏ đường dẫn `rq2_domain_knowledge` (trỏ sang file `.py` của RQ2) vì dư thừa — 3 tên đặc trưng môi trường đã có sẵn ngay trong `config.yaml`, không script nào cần đọc thêm file đó.
- Commit: `8218ec3`, `99f3c53`.

### Bước 2 — Schema SQLite (6 bảng) ✅
- **Mục đích**: tạo "nơi chứa" cho mọi dữ liệu hệ thống sẽ ghi ra khi chạy thật (flow, lỗi, dự đoán, cảnh báo, độ tin cậy, thời gian từng bước) — chuẩn bị trước khi có logic xử lý.
- Tạo `app/db.py`: định nghĩa 6 bảng `FlowRecord`, `DataError`, `Prediction`, `AlertRecord`, `Reliability`, `Timing` (có khóa ngoại nối nhau). 78 đặc trưng gộp vào 1 cột JSON (`features_json`) thay vì 78 cột SQL riêng, vì tên đặc trưng có khoảng trắng/dấu `/`.
- Tạo `scripts/stage02_init_db.py`: chạy tạo DB thật + tự kiểm tra 3 việc — (1) đủ 6/6 bảng, (2) đúng cột từng bảng, (3) chèn 1 flow giả (78 "đặc trưng") rồi đọc lại khớp 100%, sau đó tự xóa dòng test.
- Thêm `*.db`, `*.csv` của `RQ3_IDS_System/data/` vào `.gitignore` (dữ liệu sinh ra, không commit).
- Commit: `e5b3f06`.

### Bước 3 — Tập B (dữ liệu sạch, loại trùng train/test) ✅
- **Mục đích**: có một tập flow để demo/test mà chắc chắn model chưa từng thấy dưới bất kỳ hình thức nào (kể cả trùng lặp ẩn với train), tránh mọi tranh cãi "model học thuộc".
- Tạo `scripts/stage03_build_clean_dataset.py`: băm 78 cột của train_set và test_set, loại khỏi test_set mọi dòng trùng hash với train_set, rồi lấy mẫu phân tầng (seed 42, tối đa 30 dòng/lớp) từ phần còn lại.
- **Kết quả chạy thật**: 194.149/700.000 dòng test (27,74%) trùng train — khớp đúng con số RQ2 đã ghi nhận trước đó. Sau khi loại trùng còn 505.851 dòng "sạch". Lấy mẫu được **241 flow, 13/15 lớp**.
- **Phát hiện cần ghi nhận trung thực**: 2 lớp `DoS attacks-SlowHTTPTest` và `FTP-BruteForce` **100% dòng test trùng với train** (1.735/1.735 và 3.507/3.507) → **0 dòng sạch còn lại**, nên **không có mặt trong Tập B**. Đây là đặc điểm thật của cách lấy mẫu gốc của CSE-CIC-IDS2018, không phải lỗi code — khi demo/báo cáo cần nói rõ Tập B chỉ phủ được 13/15 lớp, 2 lớp này phải dùng Tập A (cohort RQ2) hoặc traffic thật để minh họa.
- Tự kiểm tra lại: băm 241 dòng của Tập B, xác nhận 0 dòng trùng train_set — [PASS].
- File ra: `RQ3_IDS_System/data/clean_holdout_set.csv` (không commit git, đã gitignore).
- Commit: `6ba128a`.

### Bước 4 — Tầng 2: hàm chuẩn hóa flow ✅
- **Mục đích**: đứng giữa "dữ liệu thô nhận được" và "model" — đảm bảo chỉ dữ liệu đủ điều kiện (đủ 78 cột, không NaN, đúng thứ tự cột) mới được đưa vào model dự đoán; dữ liệu thiếu/lỗi bị từ chối có lý do rõ ràng (422) thay vì để model đoán bừa và sai âm thầm.
- Tạo `app/normalize.py`: hàm `normalize_flow()` kiểm tra đủ cột, kiểm tra NaN/Inf, tự sắp lại đúng thứ tự cột theo model; tham số `convert_seconds_to_microseconds` (mặc định tắt) chuẩn bị sẵn cho traffic thật ở M4, chưa dùng tới lúc này vì Tập A/B đã đúng đơn vị micro giây từ gốc.
- Tạo `scripts/stage04_test_normalize.py`, chạy 4 tình huống trên dữ liệu thật (Tập B):
  1. 3 dòng thật từ Tập B → PASS, đúng thứ tự cột.
  2. Cố ý xóa cột `Fwd Pkt Len Std` → bị từ chối đúng lý do, đúng tên cột liệt kê.
  3. Cố ý đặt `Flow IAT Min = NaN` → bị từ chối đúng lý do, đúng tên cột liệt kê.
  4. Đảo ngược toàn bộ thứ tự 78 cột ở input → hàm tự sắp lại đúng thứ tự model mong đợi, không từ chối oan.
- Kết quả chạy thật: cả 4 tình huống đều đúng như kỳ vọng — xem log chạy, không có [FAIL] nào.
- Commit: `cf8cff4`.

### Bước 5 — Tầng 3: nạp model, hàm dự đoán ✅
- **Mục đích**: nối ngay sau hàm chuẩn hóa — nhận 1 dòng đã chuẩn hóa, trả về nhãn + xác suất 15 lớp, kèm "phiên bản model" (hash SHA-256 file .pkl) để truy vết sau này.
- Tạo `app/predict.py` (class `Detector`): nạp model/encoder RQ1 (không huấn luyện lại), `model_version` = 16 ký tự đầu SHA-256 của file model (`52eb5a671ee82109`), hàm `predict_flow()`.
- Tạo `scripts/stage05_test_predict.py`, 3 việc kiểm tra bằng dữ liệu thật:
  1. **Tự nhất quán**: tổng xác suất 15 lớp = 0,99999994 (≈1.0), lớp xác suất cao nhất khớp `predicted_label` — [PASS].
  2. **So với Tập B** (241 flow, đã biết đáp án): độ chính xác tổng 212/241 = **88,0%**. Theo lớp: hầu hết 94,7–100%, nhưng **Infilteration chỉ 15,8%** (3/19), Brute Force-Web 63,2%, SQL Injection 69,2% — ba con số này **khớp đúng** với 3 lớp "khó" đã ghi nhận sẵn trong tài liệu kiến trúc (Infilteration Recall ~16% trên toàn test set) → một dấu hiệu nhất quán tốt, không phải trùng hợp.
  3. **So với `pred_label` có sẵn trong cohort_ids.csv của RQ2** (50 flow lấy ngẫu nhiên từ Tập A, seed 42): **khớp y hệt 50/50 = 100%** — xác nhận hàm dự đoán mới không có lỗi nạp model/sai thứ tự cột so với pipeline RQ2 gốc (kiểm tra sớm, thu nhỏ của thí nghiệm E5).
- Commit: `2cae3b1`.

### Bước 6 — FastAPI: `POST /predict`, `GET /health` ✅
- **Mục đích**: ghép tầng 2 (chuẩn hóa) + tầng 3 (dự đoán) + ghi DB thành 1 dịch vụ web thật, gọi được qua HTTP thay vì chỉ gọi hàm Python trực tiếp — lần đầu hệ thống "chạy được" theo đúng nghĩa.
- Cài `fastapi`, `uvicorn`, `requests`. Tạo `app/main.py` (`POST /predict`, `GET /health`) và `scripts/stage06_test_api.py`.
- **3 lỗi thật gặp phải khi test — ghi lại để không lặp lại:**
  1. **Deadlock subprocess**: ban đầu bắt log server qua `subprocess.PIPE` nhưng không đọc liên tục → ống dẫn đầy làm uvicorn bị treo khi ghi log, server "giả treo" không trả lời request nào. **Sửa**: ghi log server ra file trên đĩa (`data/stage06_server.log`) thay vì PIPE.
  2. **`sqlite3.ProgrammingError: SQLite objects created in a thread can only be used in that same thread`**: dùng 1 connection SQLite chung mở lúc khởi động, nhưng FastAPI chạy mỗi request sync trong 1 thread riêng của thread pool → SQLite (mặc định `check_same_thread=True`) chặn. **Sửa**: thêm `db.get_connection()`, mở 1 connection MỚI cho MỖI request, đóng lại sau khi xong.
  3. **`sqlite3.IntegrityError: FOREIGN KEY constraint failed`**: ghi `Timing` (có khóa ngoại tới `FlowRecord.flow_id`) TRƯỚC KHI ghi `FlowRecord` → vi phạm khóa ngoại. **Sửa**: đổi thứ tự, ghi `FlowRecord` trước, `Timing` sau.
- **Kết quả chạy thật (sau khi sửa cả 3 lỗi) — log đầy đủ, mọi [PASS]:**
  - `GET /health` → 200, `model_loaded=True`.
  - 3 flow thật từ Tập B qua `POST /predict` → cả 3 trả 200, nhãn đúng, `timing_ms` ví dụ dòng 0: normalize=4,5ms, predict=13,3ms, total=75,6ms.
  - Flow thiếu cột `Idle Min` → 422, đúng lý do, đúng tên cột.
  - Mở lại file DB: cả 3 flow có đủ `FlowRecord`, `Prediction`, 3 dòng `Timing`; bảng `DataError` có 2 dòng (đúng số lỗi đã tạo ra trong lúc test).
- **Bạn (người dùng) tự test lại thủ công, độc lập với script tự động** — xác nhận kết quả trùng khớp:
  - Chạy `python -m uvicorn app.main:app --port 8000` để tự bật server, mở `http://127.0.0.1:8000/docs` (giao diện Swagger UI do FastAPI tự sinh) để gọi `/predict` bằng tay, không qua script.
  - **Sự cố gặp phải**: terminal có `(.venv)` ở đầu dòng nhắc, nhưng là venv của **`cicflowmeter_capture_demo/`** (thư mục demo cũ) tự kích hoạt, không phải môi trường đã cài `fastapi`/`uvicorn` (cài vào Python hệ thống) → báo lỗi `No module named uvicorn`. **Sửa**: chạy `deactivate` để thoát venv cũ trước khi gọi `python -m uvicorn...`. Đây là một lời nhắc tốt: venv cũ vẫn có thể tự kích hoạt trong terminal nếu không cẩn thận, dù code không hề đụng tới thư mục đó.
  - Để tiện bấm thử qua Swagger UI, đã xuất sẵn 2 file mẫu (lấy từ Tập B, flow model chưa từng thấy): `data/samples/sample_benign.json` (đáp án đúng = Benign) và `data/samples/sample_attack.json` (đáp án đúng = Bot).
  - Bạn dán `sample_attack.json` vào `/predict` qua Swagger UI và chạy thành công.
- Commit: `41949ed`.

### Bước 7 — Tầng 4a: TreeSHAP tự động, nối vào `/predict` ✅
- **Mục đích**: mỗi cảnh báo có kèm "vì sao mô hình nghĩ vậy" — SHAP chạy TỰ ĐỘNG cho mọi Alert (khác LIME ở bước 9, chỉ chạy khi analyst bấm xin, đúng nguyên tắc kiến trúc Khối 3).
- Tạo `app/explain_shap.py` (class `ShapExplainer`), `db.upsert_reliability()` (ghi từng phần, không đè dữ liệu bước khác), nối vào `app/main.py`, `scripts/stage07_test_shap.py`.
- **Kết quả chạy thật — PASS ngay lần đầu, không gặp lỗi:**
  - Flow Bot (sample_attack.json) → `is_alert=True`, có Top-5 SHAP. **`Dst Port` φ=+7,512 — gần như một mình quyết định cả quyết định** (4 đặc trưng còn lại φ chỉ 0,01–0,05) — khớp ĐÚNG với phát hiện ở RQ2 (Bot gần như hoàn toàn dựa vào Dst Port, mean|φ|≈7,4/97,1% trọng số) → xác nhận code SHAP mới hoạt động nhất quán với phân tích RQ2 gốc.
  - Additivity: sai số = **9,537e-07** — cùng bậc với RQ2 (1e-5 đến 1e-6), xác nhận TreeSHAP tính đúng.
  - Flow Benign → `shap=None`, `is_alert=False` — đúng nguyên tắc "chỉ tính SHAP khi có cảnh báo".
  - Mở DB: bảng `Reliability` có dòng ứng với `alert_id`, `shap_top5_json` đủ 5 phần tử.
  - **Thời gian SHAP qua API: 40,79 ms** — chậm hơn ~2 lần so với con số RQ2 đo khi chạy hàng loạt theo lô (~19 ms/flow). Hợp lý: RQ2 dùng `TreeExplainer` trên nhiều flow cùng lúc (tận dụng batch), còn ở đây mỗi request API chỉ giải thích 1 flow riêng lẻ + có thêm chi phí HTTP/threadpool của FastAPI. Số liệu chính xác hơn sẽ có ở thí nghiệm **E1** (đo trên nhiều flow, lấy median/p95).
- **Bạn tự test lại thủ công qua Swagger UI** (`/docs`), độc lập với script tự động:
  - Dán `sample_attack.json` (Bot) vào `POST /predict` → xác nhận response có trường `"shap"` đầy đủ (`class_explained`, `base_value`, `top_k` 5 đặc trưng, `additivity_error`), khác hẳn lần test bước 6 lúc trường này còn chưa tồn tại.
  - Dán `sample_benign.json` vào `POST /predict` → xác nhận trường `"shap"` là `null` (đúng nguyên tắc: Benign không tạo cảnh báo nên không chạy SHAP).
- Commit: `5e39a85`.

### Bước 7b — Sửa lỗi kiến trúc: hàng đợi giải thích BẤT ĐỒNG BỘ ✅
- **Vì sao có bước này**: trước khi làm bước 8, kiểm lại 8 bước "Luồng xử lý một flow" trong tài liệu kiến trúc so với code đã viết (bước 1-7). Phát hiện: tài liệu yêu cầu *"Cảnh báo hiện lên dashboard NGAY, phần giải thích được NỐI THÊM VÀO khi tính xong"* + *"giải thích được ghi thành một tác vụ CHỜ (tối đa 50)... nếu hàng đợi đầy thì cảnh báo vẫn hiện, chỉ thiếu phần giải thích"* — nhưng code bước 7 lại tính SHAP ĐỒNG BỘ ngay trong `/predict`, không có hàng đợi, không có giới hạn 50. Đây là 1 **lỗi kiến trúc thật**, không chỉ là thiếu sót nhỏ — nếu không sửa, traffic thật dồn dập (demo DDoS) sẽ làm API chậm dây chuyền.
- **Mục đích**: tách việc tính SHAP ra khỏi request `/predict` — API tạo Alert và trả lời ngay, SHAP chạy trong 1 **thread nền riêng**, đọc việc từ 1 **hàng đợi có giới hạn** (`queue.Queue(maxsize=50)`, lấy từ `config.yaml: api.max_explain_queue`). Hàng đợi đầy → bỏ phần giải thích, GIỮ nguyên cảnh báo.
- Tạo `app/explain_queue.py` (class `ExplainQueue`: `submit()` không chặn, worker thread riêng xử lý tuần tự); sửa `app/main.py` (`/predict` gọi `explain_queue.submit()` thay vì gọi SHAP trực tiếp, trả thêm field `explanation_status`: `"queued"` / `"dropped_queue_full"` / `None`); thêm `GET /explain_queue_status` để quan sát hàng đợi; tạo `scripts/stage07b_test_async_queue.py`.
- **2 lỗi thật gặp phải khi test, đã sửa:**
  1. **Test sai thiết kế**: lần đầu gửi 60 request TUẦN TỰ để ép hàng đợi đầy — nhưng worker xử lý SHAP (~40ms) nhanh hơn tốc độ gửi tuần tự (~96ms/request) nên hàng đợi không bao giờ đầy kịp (0/60 dropped). **Sửa**: dùng `ThreadPoolExecutor` gửi 70 request ĐỒNG THỜI.
  2. **`sqlite3.OperationalError: database is locked`** (lỗi thật, quan trọng): 70 connection SQLite ghi đồng thời bị khóa lẫn nhau, nhiều request lỗi 500. **Sửa**: bật `PRAGMA journal_mode = WAL` (cho phép đọc/ghi đồng thời tốt hơn) + `timeout=10.0` khi mở connection (chờ thay vì báo lỗi ngay khi bị khóa tạm thời) trong `app/db.py`.
- **Kết quả chạy thật (sau khi sửa cả 2 lỗi) — mọi [PASS]:**
  - `/predict` không còn field `"shap"` trong response, `explanation_status="queued"` — xác nhận đã tách SHAP ra khỏi đường đồng bộ.
  - Phát hiện thêm: tổng thời gian request vẫn ~40-108ms dù đã bỏ SHAP (~40ms) ra khỏi đường đồng bộ — có ~overhead khác (có thể từ FastAPI/SQLite/Windows) **đã tồn tại từ trước bước 7b**, không phải do thay đổi này gây ra; để lại cho **E1** đo chính xác, không thuộc phạm vi bước này.
  - Đợi worker xử lý xong: `Reliability.shap_top5_json` xuất hiện đúng 5 phần tử.
  - Dội 70 request đồng thời (maxsize=50): **60 'queued', 10 'dropped_queue_full'** — đúng kỳ vọng. Alert bị dropped **vẫn tồn tại** trong `AlertRecord` (không mất cảnh báo), chỉ `Reliability` không có dòng (đúng — không được xếp hàng giải thích).
- Commit: `cf83fb6`.

### Bước 8b — Bộ "feeder" tự động (chuẩn bị cho bắt traffic thật) ✅
- **Mục đích**: trả lời câu hỏi "hệ thống có tự động bắt rồi đưa flow vào model không, hay phải làm tay?" — xem chi tiết mục 5.1. Dùng CHUNG cho cả nguồn 1 (mạng lab thật) và nguồn 2 (PCAP phát lại) ở mục 0.1 — CICFlowMeter ghi CSV giống nhau bất kể gói tin "sống" hay "phát lại".
- Tạo `app/feeder.py`: theo dõi 1 file CSV, phát hiện dòng MỚI (so độ dài file mỗi vòng lặp) → đọc, đổi đơn vị μs nếu cần (tham số `--convert-units`, dùng lại `TIME_COLUMNS` từ `app/normalize.py`) → tự `POST /predict` → log kết quả. Thêm `feeder` section vào `config.yaml` (đường dẫn theo dõi mặc định, chu kỳ kiểm tra, cờ đổi đơn vị).
- Tạo `scripts/stage08b_test_feeder.py`: GIẢ LẬP CICFlowMeter thật bằng cách tự ghi 8 dòng của Tập B vào 1 file CSV, cách nhau 1,5 giây (không cần CICFlowMeter/máy ảo gì cả).
- **2 lỗi gặp khi test (cả 2 đều ở SCRIPT TEST, không phải ở feeder) — đã sửa:**
  1. Quên bật **unbuffered** (`-u`) cho tiến trình con `feeder.py` → log chưa kịp ghi ra file khi script test đọc, tưởng feeder gửi 0 dòng (thực ra DB đã nhận đủ 8 — kiểm tra DB trực tiếp phát hiện ra feeder vẫn đúng, chỉ log đọc sai).
  2. Regex kiểm tra log dùng `\S+` (không khoảng trắng) để bắt `predicted_label` — SAI vì nhãn như "Brute Force -XSS" có khoảng trắng, chỉ khớp nhãn 1 từ (SSH-Bruteforce, Infilteration, Benign) → **sửa thành** `(.+?), is_alert=` để bắt đủ cả nhãn có khoảng trắng.
- **Kết quả chạy thật — mọi [PASS]:**
  - Feeder gửi đủ **8/8 dòng**, đúng thứ tự #1→#8, không thiếu không trùng.
  - **Nhãn dự đoán đúng 7/8** — chỉ sai đúng 1 ca: SQL Injection (lớp cực hiếm, 9-13 mẫu toàn tập) bị đoán Benign, khớp với hạn chế đã biết từ RQ1, không phải lỗi feeder.
  - Mở DB: `FlowRecord` tăng đúng 8 dòng sau khi feeder chạy.
  - Toàn bộ luồng **CSV → feeder → /predict → DB** chạy tự động hoàn toàn, không cần tay người ở giữa — đúng mục tiêu ban đầu của bước này.
- Khi có CICFlowMeter thật (M4): chỉ cần đổi `--watch` sang đường dẫn CICFlowMeter ghi ra và bật `--convert-units` (nếu CICFlowMeter xuất giây) — không cần sửa code.
- Commit: `f0f21b4`.

### M3 — Test bằng traffic thật trên chính máy bạn (KHÔNG cần máy ảo) ✅
- **Vì sao làm ngay, không đợi M4**: M3 (mục 1.2, mục 2) không phụ thuộc M4 — chỉ cần Npcap + CICFlowMeter chạy trên máy hiện tại, bắt traffic bình thường (lướt web), không cần máy Victim/Attacker. Làm ngay để xác nhận "cầu nối" CSV→feeder→hệ thống hoạt động với dữ liệu CICFlowMeter THẬT (không phải giả lập từ Tập B như bước 8b).
- **Môi trường mới riêng**: `RQ3_IDS_System/.venv_capture/` (Python 3.13, KHÔNG dùng lại venv của `cicflowmeter_capture_demo/`), cài `cicflowmeter==0.5.0` (ghi lại ở `requirements-capture.txt`). Lý do cần bản 0.5.0: bản 0.2.0 đi kèm Python 3.11 có lỗi ghi flow trên Windows (đã biết từ trước).
- **⚠️ Chỉ `scripts/run_live_capture.py` cần chạy bằng `.venv_capture`** (vì nó import trực tiếp thư viện `cicflowmeter`). `app/feeder.py` và `app/main.py` (API) vẫn chạy bằng **Python hệ thống** như mọi bước trước (cần `yaml`, `pandas`, `fastapi`... mà `.venv_capture` không có, chỉ có `cicflowmeter`/`scapy`). Dùng nhầm venv cho feeder sẽ báo `ModuleNotFoundError: No module named 'yaml'` — đã gặp thật khi hướng dẫn test, đã sửa lại hướng dẫn.
- **3 lỗi/vấn đề thật gặp phải, đã tìm ra và sửa (không phải vấn đề ở hệ thống RQ3, mà ở việc dùng CICFlowMeter đúng cách):**
  1. **Lỗi thật trong chính thư viện `cicflowmeter` 0.5.0**: `sniffer.py::main()` gọi `create_sniffer(...)` bằng tham số VỊ TRÍ nhưng thứ tự không khớp chữ ký hàm — `args.verbose` (bool) bị nhét nhầm vào tham số `fields`, gây `AttributeError: 'bool' object has no attribute 'split'` mỗi khi chạy qua CLI `cicflowmeter` thẳng. **Sửa**: viết `scripts/run_live_capture.py` gọi THẲNG hàm `create_sniffer()` bằng keyword argument (né lỗi thứ tự), không qua CLI gốc.
  2. **File CSV trống dù bắt được hàng nghìn gói tin**: CICFlowMeter chỉ ghi 1 flow ra CSV khi flow đã "đóng" (FIN/RST) hoặc hết hạn (timeout) — dừng sớm (test 15 giây) mà không ép ghi nốt thì mọi flow "đang mở" (đa số traffic HTTPS/keep-alive) bị bỏ qua, file trông như trống dù đã xử lý 4316+ gói tin. **Sửa**: gọi `session.flush_flows()` (có sẵn trong thư viện) ngay sau khi dừng sniffer, ép ghi nốt toàn bộ flow còn dang dở.
  3. **Tên cột hoàn toàn khác** (đúng như đã cảnh báo trước khi làm): CICFlowMeter 0.5.0 xuất tên cột kiểu `snake_case` (`dst_port`, `flow_duration`...) + 4 cột định danh thừa (`src_ip`, `dst_ip`, `src_port`, `timestamp`), khác hẳn 78 tên cột model cần (`Dst Port`, `Flow Duration`...). Thời gian cũng xác nhận ra là **giây** (vd `flow_duration=15.016630`), đúng như tài liệu kiến trúc đã cảnh báo. **Sửa**: thêm `CICFLOWMETER_COLUMN_MAP` (78 cặp ánh xạ 1-1, phát hiện thêm 1 điểm lệch tên: `cwr_flag_count` ↔ `CWE Flag Count`) vào `app/feeder.py`, áp dụng trước khi gửi; 4 cột định danh không có trong bảng ánh xạ cứ để nguyên, `/predict` tự bỏ qua vì không nằm trong 78 cột nó cần.
- **Kết quả chạy thật — luồng đầy đủ không giả lập bất kỳ phần nào:**
  - Bắt traffic Wi-Fi thật 15 giây trong lúc dùng máy bình thường → 4316+ gói tin, 25 flow ghi ra CSV (sau khi ép flush).
  - Chạy `feeder.py --convert-units` trên file CSV thật đó (không phải Tập B giả lập) → gửi đủ **25/25 flow** qua `/predict`.
  - **Kết quả dự đoán: 25/25 = Benign** — đúng 100%, hợp lý vì đây chỉ là traffic bình thường, không có tấn công nào.
  - Xác nhận toàn bộ chuỗi **gói tin thật → CICFlowMeter thật → feeder (đổi tên cột + đơn vị) → API → model → DB** chạy đúng, không có bước nào còn là giả lập.
- Việc còn lại để có M4 đầy đủ: traffic TẤN CÔNG thật (cần máy Attacker + Victim, mạng host-only cô lập) để xem hệ thống có phát hiện và cảnh báo đúng không — quy trình kỹ thuật (feeder, mapping cột, flush) đã kiểm chứng xong ở đây, M4 chỉ còn là việc dựng máy ảo + tạo traffic tấn công, không cần sửa code gì thêm.

### Bước 8 — Tầng 4b: Đánh giá độ tin cậy + gắn cờ ✅
- **Mục đích**: đúng mục "Tầng 4" trong plan (mục 3) — phần "Tính tại chỗ (rẻ)": faithfulness proxy nhanh + đếm cờ môi trường + cờ lớp hiếm, chạy cho MỌI Alert, NGAY SAU TreeSHAP (dùng Top-5 SHAP làm input) — khác với "tra bảng có sẵn từ RQ2" (đắt hơn, để ở bước 10).
- **⚠️ Nhắc lại overclaim** (giữ nguyên trong docstring `app/reliability.py`): faithfulness ở đây chỉ là PROXY một bước/một giá trị nền — KHÔNG phải phép đo faithfulness đầy đủ của RQ2 (xóa k=1..10, 3 giá trị nền, AUC, đối chứng ngẫu nhiên, Wilcoxon). Cờ môi trường chỉ là cờ cảnh báo/bằng chứng hỗ trợ, chưa phải kết luận đã kiểm chứng (kiểm chứng giả thuyết này là **E4**, chưa làm).
- Tạo `scripts/stage08_compute_train_stats.py`: chạy 1 lần, đọc `train_set.parquet` (2,8 triệu dòng), tính trung vị toàn cục (`global_median`) của 78 đặc trưng + số mẫu huấn luyện từng lớp, lưu ra `data/train_stats.json` (không commit, đã thêm vào `.gitignore` — tái tạo được bằng cách chạy lại script). Kết quả: chỉ **SQL Injection = 70 mẫu** dưới ngưỡng 100 (`rare_class_min_train_samples` trong `config.yaml`) — lớp hiếm duy nhất trong Tập B/C.
- Tạo `app/reliability.py` (class `ReliabilityScorer`): nạp `train_stats.json` 1 lần lúc server khởi động, hàm `score()` nhận flow đã chuẩn hóa + nhãn dự đoán + Top-5 SHAP, trả về:
  - `faithfulness_proxy_drop`: đặt Top-k (mặc định k=5, lấy từ `config.yaml: faithfulness_proxy.k`) đặc trưng SHAP về `global_median`, gọi lại `Detector.predict_flow()`, đo xác suất lớp dự đoán tụt bao nhiêu.
  - `env_fingerprint_count`/`env_fingerprint_flag`: đếm trong Top-5 có bao nhiêu đặc trưng thuộc 3 đặc trưng môi trường (`Dst Port`, `Fwd Seg Size Min`, `Init Fwd Win Byts`), bật cờ khi ≥2 (ngưỡng từ `config.yaml`).
  - `rare_class_flag`: bật khi nhãn dự đoán có dưới 100 mẫu huấn luyện (tra từ `train_stats.json`, không tính lại mỗi request).
- Nối vào `app/explain_queue.py`: `ReliabilityScorer.score()` chạy trong CÙNG worker thread, NGAY SAU SHAP (dùng lại `shap_result["top_k"]` vừa tính), ghi 4 cột mới vào `Reliability` qua `upsert_reliability()` (không đè `shap_top5_json` đã ghi trước đó), thêm `Timing(step="reliability")`. Sửa `app/main.py`: khởi tạo `ReliabilityScorer` 1 lần lúc startup (đọc `train_stats.json` + tham số từ `config.yaml`), truyền vào `ExplainQueue`.
- Tạo `scripts/stage08_test_reliability.py`: bật server con, bắn 2 flow THẬT từ Tập B (`clean_holdout_set.csv`) qua `/predict` — SQL Injection (lớp hiếm, kỳ vọng `rare_class_flag=1`) và Bot (lớp thường, kỳ vọng `rare_class_flag=0`) — chờ hàng đợi xử lý xong rồi mới đọc DB (vì SHAP/reliability chạy bất đồng bộ từ Bước 7b).
- **Kết quả chạy thật — cả 2 case [PASS]:**
  - SQL Injection: `predicted_label=SQL Injection` (đoán đúng), `faithfulness_proxy_drop=0,8202`, `env_fingerprint_count=1` → `env_fingerprint_flag=0` (dưới ngưỡng 2), `rare_class_flag=1` — đúng, lớp có 70 mẫu train < 100.
  - Bot: `faithfulness_proxy_drop=0,9957` (xác suất Bot tụt gần hết khi xóa Top-5 SHAP — khớp phát hiện RQ2 là Bot gần như chỉ dựa vào `Dst Port`), `env_fingerprint_count=1` → `env_fingerprint_flag=0`, `rare_class_flag=0` — đúng, lớp có 100.650 mẫu train.
  - Trước khi viết test, đã mở trực tiếp `ids_system.db` kiểm tra: 183 Alert cũ (tạo trước khi bước 8 có code) đúng như dự kiến có `faithfulness_proxy_drop=NULL`, chỉ 1 Alert mới nhất (lúc đang thử feeder, nhãn Bot) có đủ số liệu — xác nhận code không âm thầm ghi đè/sai dữ liệu cũ.
- Commit: `79cbe5f`.

### Bước 9 — Tầng 4b: LIME theo yêu cầu (`POST /explain`) ✅
- **Mục đích**: thêm cách giải thích thứ 2 (LIME) bên cạnh SHAP — nhưng KHÔNG tự động (chậm hơn SHAP ~8 lần: RQ2 đo LIME~148ms so SHAP~19ms), chỉ chạy khi analyst chủ động xin qua `POST /explain`.
- Tra lại đúng cách RQ2 cài đặt LIME (`RQ2/scripts/stage06_lime_per_flow.py`) để dùng chung phương pháp, so sánh được: `LimeTabularExplainer` khởi tạo 1 lần với nền 2.000 dòng (seed khóa), cách seed riêng theo từng flow (`RQ2/scripts/lib/common.py::set_lime_explainer_seed` — lime==0.2.0.1 không có tham số `random_state` ở `explain_instance()`, phải tự gán lại thủ công `explainer.random_state` + `explainer.base.random_state` trước MỖI lần gọi, nếu không kết quả không tái lập được).
- Tạo `scripts/stage09_compute_lime_background.py`: lấy sẵn 2.000 dòng nền từ `train_set.parquet` (seed khóa trong `config.yaml: lime.background_seed`), lưu `data/lime_background.npy` (không commit, gitignore) — tránh đọc lại 2,8 triệu dòng mỗi lần khởi động server.
- Tạo `app/explain_lime.py` (class `LimeExplainer`, hàm `set_lime_explainer_seed` sao chép nguyên vẹn từ RQ2): seed riêng theo từng alert bằng cách băm `alert_id` (chuỗi UUID) ra số nguyên ổn định (`sha256` — không dùng `hash()` built-in vì `PYTHONHASHSEED` ngẫu nhiên giữa các lần chạy).
- Thêm `POST /explain` vào `app/main.py`: nhận `alert_id` + `method` (chỉ nhận `"lime"`, SHAP đã tự động nên không xin lại qua đây). Chạy ĐỒNG BỘ (analyst đang chờ, không qua hàng đợi nền như SHAP), giới hạn số lượt chạy cùng lúc bằng `threading.Semaphore(config.yaml: api.max_concurrent_lime=4)` — vượt ngưỡng trả `429`; không có `alert_id` trả `404`. Ghi `lime_top5_json` + `agreement_jaccard5` vào `Reliability`.
- Thêm `db.get_alert()`, `db.get_flow_features()`, `db.get_shap_top5()` vào `app/db.py` (tra cứu lại dữ liệu đã lưu, vì request `/explain` chỉ gửi `alert_id`, không gửi lại 78 đặc trưng).
- **Agreement (Jaccard\@5) tính ĐÚNG cách RQ2 làm** (`RQ2/scripts/stage07_agreement.py`): so trực tiếp tên đặc trưng SHAP (sạch, vd `"Dst Port"`) với `feature_desc` THÔ của LIME (có thể kèm bất đẳng thức, vd `"Dst Port <= 8080.00"`) — KHÔNG tự "sửa" cho khớp đẹp hơn, vì đây chính là 1 lý do Jaccard\@5 trung bình RQ2 chỉ 0,141.
- Tạo `scripts/stage09_test_lime.py`, test qua API thật, 5 việc:
  1. Flow Bot → `/explain` trả Top-5 LIME hợp lệ, `local_r2` trong [0,1], có `agreement_jaccard5`.
  2. `alert_id` không tồn tại → `404`.
  3. `method="shap"` (không hỗ trợ qua `/explain`) → `400`.
  4. Mở DB xác nhận `lime_top5_json` (5 phần tử) + `agreement_jaccard5` đã ghi vào `Reliability`.
  5. Gọi lại `/explain` LẦN 2 cùng `alert_id` → Top-5 và `local_r2` phải GIỐNG HỆT lần 1 (seed cố định theo flow, đúng nguyên tắc tái lập của RQ2).
- **Kết quả chạy thật — cả 5 việc [PASS]**:
  - Flow Bot: `local_r2=0,4731` (model tuyến tính cục bộ của LIME khớp model gốc ở mức trung bình), Top-5 LIME hoàn toàn khác Top-5 SHAP (LIME không hề chọn `Dst Port`, dù SHAP coi đó gần như quyết định duy nhất) → `agreement_jaccard5=0,111` (chỉ 1 đặc trưng trùng trong hợp 9 đặc trưng).
  - **Phát hiện cần ghi nhận trung thực, không phải lỗi**: con số Agreement rất thấp này khớp đúng hiện tượng RQ2 đã ghi nhận (Jaccard\@5 trung bình chỉ 0,141, SHAP và LIME "ít khi đồng ý") — đây là dấu hiệu code hoạt động nhất quán với phát hiện gốc, KHÔNG phải dấu hiệu lỗi cần sửa.
  - Thời gian gọi `/explain` qua API: 66,6ms — nhanh hơn số RQ2 đo khi chạy hàng loạt (~148ms), hợp lý vì đây chỉ 1 request đơn, chưa tính network stack đầy đủ như batch RQ2; số chính xác hơn để dành cho **E1**.
  - Gọi lại lần 2: `local_r2` và Top-5 giống hệt lần 1 (sai số 0) — xác nhận seed theo flow hoạt động đúng, tái lập được.
- Commit: `4e866ca`.

### Bước 11 — Tầng 5: Luật quyết định nhánh A/B ✅
- **Mục đích**: thêm luật quyết định flow nào hiển thị "bình thường" (nhánh A), flow nào cần hiển thị kèm cảnh báo "cần xem lại" + gợi ý xem thêm LIME (nhánh B) — chỉ đổi CÁCH HIỂN THỊ, không đổi nhãn, không ẩn cảnh báo (đúng nguyên tắc cứng ở mục 0 và mục 3 của plan). Bỏ qua Bước 10 (tra bảng RQ2) theo quyết định của bạn — bước 11 không phụ thuộc bước 10, chỉ dùng 2 cờ đã có từ bước 8.
- Thêm `ReliabilityScorer._decide_branch()` vào `app/reliability.py`, gọi trong `score()`: branch = `'A'` nếu CẢ 2 cờ (`env_fingerprint_flag`, `rare_class_flag`) đều 0; `'B'` nếu có ít nhất 1 cờ được bật — **CHỈ dựa vào 2 cờ này**, đúng như plan đã chốt (không dùng ngưỡng từ tập dev 250 flow của RQ2 vì không đại diện, không dùng Agreement vì Jaccard\@5 trung bình RQ2 chỉ 0,141, không đủ ổn định làm ngưỡng). Ghi kèm `branch_reason` mô tả cờ nào gây ra nhánh B.
- Sửa `app/explain_queue.py`: ghi thêm `branch` + `branch_reason` vào `Reliability` cùng lúc với các cột bước 8 (không cần bước/worker riêng, vì đã có đủ 2 cờ ngay sau khi `score()` chạy).
- Tạo `scripts/stage11_test_branch.py`: test qua API thật với 3 case, cố tình chọn đủ cả 3 tình huống khác nhau:
  1. Bot (cả 2 cờ = 0) → kỳ vọng branch = 'A'.
  2. SQL Injection (rare_class_flag=1) → kỳ vọng branch = 'B'.
  3. DoS attacks-Hulk (dự đoán trước từ SHAP toàn cục RQ2: Top-5 gồm `Fwd Seg Size Min` + `Init Fwd Win Byts`, đủ 2 đặc trưng môi trường → env_fingerprint_flag=1) → kỳ vọng branch = 'B'.
- **Kết quả chạy thật — cả 3 case [PASS]:**
  - Bot: `env_fingerprint_flag=0, rare_class_flag=0` → `branch=A`, `branch_reason="Không có cờ nào được bật — hiển thị SHAP bình thường."`
  - SQL Injection: `rare_class_flag=1` → `branch=B`, `branch_reason` nêu đúng lý do.
  - DoS attacks-Hulk: dự đoán đúng trước khi test — `env_fingerprint_flag=1` thật (không phải giả định) → `branch=B` — xác nhận nhánh B không chỉ lý thuyết, có flow thật rơi vào đúng trường hợp này.
- Commit: `b31fe54`.

### Bước 12 — Tầng 6: `GET /alerts` ✅
- **Mục đích**: thêm API trả danh sách Alert kèm trạng thái giải thích, lọc theo thời gian/nhãn/nhánh — đúng nguyên văn bảng API trong tài liệu kiến trúc (`Kiến trúc hệ thống IDS.docx`, phần "Giao diện (API) giữa tầng 6 và các tầng dưới": *"GET /alerts | Bộ lọc thời gian, nhãn, nhánh | Danh sách Alert kèm trạng thái giải thích"*). Đây là API đầu tiên cung cấp dữ liệu "nhìn thấy được" cho Dashboard (bước 13).
- Thêm `db.get_alerts(conn, since, until, label, branch)` vào `app/db.py`: `LEFT JOIN AlertRecord` với `Reliability` (LEFT vì SHAP có thể chưa xử lý xong — hàng đợi bất đồng bộ từ bước 7b — hoặc đã bị bỏ do hàng đợi đầy, khi đó không có dòng `Reliability`), lọc động theo tham số được truyền, sắp theo `created_at` giảm dần. Tính `explanation_status` theo 3 mức: `"pending_or_dropped"` (chưa có `shap_top5_json`), `"shap_only"`, `"shap_and_lime"`.
- Thêm `GET /alerts` vào `app/main.py`: 4 tham số query tùy chọn `since`/`until` (ISO 8601, so sánh chuỗi vì `created_at` luôn ghi cùng định dạng UTC), `label` (= predicted_label), `branch` (chỉ nhận `'A'`/`'B'`, sai thì `422`).
- Tạo `scripts/stage12_test_alerts.py`, test qua API thật, 5 việc: (1) không lọc gì → thấy đủ 2 alert vừa tạo (Bot + SQL Injection); (2) lọc `label=Bot` → chỉ còn alert Bot; (3) lọc `branch=B` → chỉ còn alert branch B; (4) lọc `since=<mốc trước 2 alert mới>` → loại hết alert cũ, chỉ còn đúng 2 alert mới; (5) `branch=C` (sai) → `422`.
- **Kết quả chạy thật — cả 5 việc [PASS]:**
  - DB lúc test đã có 254 alert tích lũy từ các bước trước — `GET /alerts` không lọc trả đủ `count=254`, có cả 2 alert mới.
  - `label=Bot` → `count=78` (đúng số Alert Bot tích lũy qua nhiều lần test trước đó).
  - `branch=B` → `count=3` (đúng — 1 từ bước 11 (SQL Injection) + 1 từ bước 11 (DoS Hulk) + 1 SQL Injection mới tạo lúc test này).
  - `since=<mốc ngay trước khi tạo 2 alert mới>` → `count=2`, lọc đúng chỉ còn 2 alert mới tạo, loại hết 252 alert cũ.
  - `branch=C` → `422` đúng như kỳ vọng validate input.
- Commit: `1eabece`.

### Việc thêm trước bước 13 — Hỗ trợ đọc lại file `.pcap` (nguồn 2 ở mục 0.1) ✅
- **Mục đích**: trả lời câu hỏi "test CSV/PCAP có trích xuất đưa vào model được chưa" — xác nhận CSV đã test từ lâu (bước 3, 8b, M3); PCAP thì chưa, nhưng khi đọc lại code thư viện `cicflowmeter` phát hiện KHÔNG cần `tcpreplay` như kiến trúc dự tính ban đầu — `create_sniffer(input_file=...)` tự đọc trực tiếp 1 file `.pcap`, xử lý giống hệt bắt sống.
- Sửa `scripts/run_live_capture.py`: thêm `--pcap-input <file>` (nhóm loại trừ lẫn nhau với `--interface`) — đọc xong hết gói trong file thì tự dừng (không cần `--seconds`/Ctrl+C như khi bắt sống).
- **Chưa test được bằng chạy thật** — cần 1 file `.pcap` thật (chưa có sẵn trong máy, cần bạn tự bắt bằng Npcap giống M3 rồi lưu ra `.pcap`, hoặc cung cấp file có sẵn). Việc test thật để sau, không chặn bước 13.
- Commit: `bc9f158`.

### Bước 13 — Tầng 6 (Khối 7): Streamlit Dashboard ✅
- **Mục đích**: trang Dashboard duy nhất — bảng cảnh báo, biểu đồ SHAP/LIME có dấu (2 tab), bảng độ tin cậy, nhãn nhánh A/B, hiển thị trạng thái `/health` — đúng mục 3 "Tầng 6 — API + Dashboard" của plan. Đây là phần đầu tiên xem được trực tiếp trên trình duyệt, không chỉ qua script test.
- Cài `streamlit==1.65.0` (thêm vào `requirements.txt`) — lưu ý thật gặp phải: `pip` trên máy trỏ sang 1 môi trường Anaconda khác (`PRP201c`), khác với `python` dùng cho project này → cài nhầm môi trường, `import streamlit` báo thiếu module dù vừa cài xong. **Sửa**: dùng `python -m pip install` thay vì gọi `pip` trực tiếp, đảm bảo cài đúng vào môi trường `python` đang dùng.
- Tạo `app/dashboard.py`: gọi API qua HTTP (`requests`, giống mọi script test từ bước 6 tới giờ) — **không đọc trực tiếp file DB**, đúng tách bạch Tầng 6 API / Dashboard trong kiến trúc. Gồm: khối trạng thái `/health` + `/explain_queue_status` (model, số lớp, hàng đợi, số bị bỏ); bộ lọc + bảng cảnh báo (gọi `/alerts`, đúng bước 12); chọn 1 alert → 2 tab SHAP/LIME (biểu đồ cột có dấu `st.bar_chart`, dương/âm rõ ràng) + nút "Xin giải thích LIME" (gọi `/explain` ngay trong dashboard nếu chưa có); bảng độ tin cậy kèm đúng các cảnh báo overclaim (faithfulness chỉ là proxy, cờ môi trường chỉ là cờ cảnh báo) lấy nguyên văn từ plan.md.
- Mở rộng `db.get_alerts()` (bước 12) để trả thêm đầy đủ các cột `Reliability` còn thiếu (`shap_top5`, `lime_top5`, `agreement_jaccard5`, `faithfulness_proxy_drop`, cờ, `stability_lookup`, `robustness_lookup`) — cần cho Dashboard hiển thị chi tiết, đúng nghĩa "danh sách Alert KÈM trạng thái giải thích" trong tài liệu kiến trúc (không phải sửa lại API, chỉ bổ sung trường trả về — đã chạy lại `scripts/stage12_test_alerts.py` xác nhận không vỡ bước 12 cũ).
- Tạo `scripts/stage13_test_dashboard.py` — **phát hiện thật khi viết test**: lần đầu test bằng cách gửi HTTP GET thẳng vào trang Dashboard rồi tìm chữ "RQ3"/"IDS" trong HTML trả về — LUÔN THẤT BẠI dù dashboard chạy đúng, vì Streamlit trả về 1 khung HTML tĩnh giống nhau cho mọi app (chỉ load React, nội dung thật chỉ render sau khi có kết nối WebSocket) — cách test đó không phát hiện được lỗi thật bên trong script. **Sửa đúng cách**: dùng `streamlit.testing.v1.AppTest` (có sẵn từ Streamlit 1.65.0) — chạy THẬT script `app/dashboard.py` ở chế độ headless, bắt được exception thật nếu code có lỗi.
- Test 3 việc: (1) chạy `AppTest.from_file()` lần đầu, không được có exception; (2) trang phải có tiêu đề chứa "IDS" + ít nhất 1 bảng; (3) chọn 1 alert ĐÃ CÓ LIME trong selectbox (xin LIME trước qua `/explain`), chạy lại, không lỗi, phải thấy thêm bảng chi tiết.
- **Kết quả chạy thật — cả 3 việc [PASS], 0 exception ở cả 2 lần chạy script** (lần đầu + sau khi chọn alert có LIME):
  - Bắn 3 flow thật (Bot, SQL Injection, DoS attacks-Hulk) qua `/predict`, xin thêm LIME cho 1 alert qua `/explain`, rồi mới chạy AppTest — Dashboard hiển thị đúng dữ liệu thật, không phải dữ liệu giả.
  - Phát hiện phụ (không phải lỗi, chỉ dọn sạch): Streamlit cảnh báo `use_container_width` sẽ bị bỏ sau 2025-12-31 — đã sửa hết 4 chỗ thành `width="stretch"`, chạy lại xác nhận hết cảnh báo.
- Commit: `bc9f158`.

### Bước 13 (bổ sung theo yêu cầu) — Nạp dữ liệu ngay trên Dashboard (CSV + PCAP) ✅
- **Mục đích**: bạn hỏi muốn Dashboard có sẵn các nút gửi CSV/PCAP (và real-time để sau) thay vì phải dùng Swagger UI hay terminal riêng — thêm 1 khối "Nạp dữ liệu vào hệ thống" ngay trên Dashboard, vẫn gọi `/predict` qua HTTP như mọi nguồn khác (không tự ý gọi tắt qua hàm Python nào khác, giữ đúng nguyên tắc Dashboard chỉ là client của API).
- Thêm 2 tab vào `app/dashboard.py`:
  - **"Gửi file CSV"**: `st.file_uploader`, đọc toàn bộ dòng, dùng lại `feeder.row_to_payload()` (bước 8b) để map tên cột/đơn vị, gửi từng dòng vào `/predict`, có thanh tiến trình + bảng kết quả từng dòng (OK/lỗi/predicted_label).
  - **"Phát lại PCAP"**: `st.file_uploader` nhận `.pcap`/`.pcapng`, lưu ra `data/dashboard_uploaded_replay.pcap`, gọi `subprocess` chạy `scripts/run_live_capture.py --pcap-input ... ` bằng Python của `.venv_capture` (đúng việc mới thêm trước bước 13), đọc CSV CICFlowMeter xuất ra, map cột/đơn vị, gửi từng flow vào `/predict`. Có kiểm tra `venv_capture` chưa cài thì báo lỗi rõ ràng, trỏ tới mục M3/5.1 trong plan — không âm thầm crash.
- Mở rộng `scripts/stage13_test_dashboard.py` thêm **Việc 4**: dùng `AppTest.file_uploader[...].upload()` (có sẵn từ Streamlit 1.65.0) để giả lập người dùng thật upload file `data/clean_holdout_set.csv` (241 dòng, Tập B) vào tab CSV, bấm nút gửi, kiểm tra không exception VÀ số alert trong DB tăng lên sau khi gửi (không chỉ kiểm tra UI không lỗi, phải xác nhận dữ liệu thật đã vào hệ thống).
- **Kết quả chạy thật [PASS]:** upload 241 dòng Tập B qua tab CSV của Dashboard (không qua script/terminal nào khác) → 0 exception → số alert trong DB tăng từ 271 lên 469 (đúng — không phải mọi dòng đều là tấn công, nhiều dòng Benign không tạo alert).
- **Tab PCAP chưa test chạy thật được** — vẫn thiếu 1 file `.pcap` mẫu như đã ghi ở mục trước bước 13. Code đã viết xong, đường ống đã rõ, chỉ còn thiếu dữ liệu để kiểm chứng — không được coi là "đã xong" cho tới khi chạy thật ra kết quả.
- **Chưa làm (để sau theo yêu cầu của bạn)**: nút "Bắt real-time" ngay trên Dashboard (cần Streamlit chạy với quyền Administrator để Npcap hoạt động, phức tạp hơn do phải quản lý tiến trình nền + tự làm mới trang trong khi đang bắt) — hiện tại bắt real-time vẫn làm qua terminal như hướng dẫn cũ (`scripts/run_live_capture.py --interface ...`).
- Commit: `84e423f`.

### Bước 13 (sửa lỗi) — Tab PCAP crash thật khi bạn tự test + né tcpdump + tự làm mới bảng ✅
- **Vì sao có mục này**: bạn tự test tab "Phát lại PCAP" với file `.pcap` thật của bạn và gặp crash `TypeError: unsupported operand type(s) for +: 'NoneType' and 'str'` tại `st.code(proc.stdout + proc.stderr)` — đúng kiểu lỗi phải sửa ngay vì bạn gặp khi tự test, không phải tôi đoán ra. Cũng yêu cầu thêm: gửi/bắt xong phải thấy bảng cảnh báo tự cập nhật ngay (trước đó phải tự bấm lọc/F5).
- **3 lỗi thật, tìm ra theo đúng thứ tự khi lần theo lỗi gốc (không phải sửa mò):**
  1. **Lỗi hiển thị (sửa trước, chưa phải gốc rễ)**: `proc.stdout`/`proc.stderr` có thể là `None` trong 1 số tình huống (timeout, tiến trình chết sớm) — code cũ cộng thẳng 2 chuỗi không phòng hờ `None`. **Sửa**: `(proc_stdout or "") + (proc_stderr or "")`, thêm `except subprocess.TimeoutExpired` báo lỗi rõ ràng thay vì để crash.
  2. **Lỗi gốc rễ thật trong thư viện `cicflowmeter`**: `create_sniffer(input_file=...)` gắn CỨNG bộ lọc BPF `filter="ip and (tcp or udp)"` cho cả chế độ đọc file — với file pcap, scapy áp bộ lọc này bằng cách tự shell ra chạy `tcpdump -w -`, nhưng **Windows không có sẵn `tcpdump`** → luôn lỗi `Scapy_Exception: tcpdump is not available` ngay khi chạy, làm tiến trình con chết sớm, góp phần gây ra tình huống (1) ở trên. **Sửa**: `scripts/run_live_capture.py` không gọi `create_sniffer()` cho chế độ pcap nữa — tự dựng `AsyncSniffer(offline=..., prn=session.process, store=False)` thẳng, BỎ HẲN tham số `filter` (không mất gì vì `FlowSession.process()` bên trong thư viện đã tự bỏ qua gói không phải TCP/UDP, đúng việc bộ lọc kia định làm).
  3. **Lỗi thật thứ 2, tái hiện được y hệt lỗi bạn gặp khi viết test đầy đủ**: sau khi sửa (2), chạy test với file pcap thật thì vẫn gặp `UnicodeDecodeError: 'charmap' codec can't decode byte 0x90` trong 1 thread nền của `subprocess.run()` — vì mặc định nó đọc output bằng encoding hệ thống (cp1252 trên Windows), nhưng log DEBUG của CICFlowMeter có byte không giải mã được bằng cp1252. Thread đó CHẾT ÂM THẦM (in traceback ra console, không ném lên luồng chính) và để `proc.stdout = None` — **đây mới là nguyên nhân sâu xa thật sự** của lỗi (1) bạn gặp ban đầu. **Sửa**: thêm `encoding="utf-8", errors="replace"` vào `subprocess.run()` trong `app/dashboard.py`, khớp với `sys.stdout.reconfigure(encoding="utf-8")` ở các script con.
- **Theo yêu cầu "gửi/bắt xong phải thấy bảng cảnh báo tự cập nhật"**: cả 2 tab (CSV + PCAP) đổi từ `st.info("...bấm lọc/F5...")` sang `st.toast(...) ; st.rerun()` — gửi xong tự chạy lại toàn trang, bảng cảnh báo bên dưới tự lấy dữ liệu mới, không cần bạn tự bấm gì thêm.
- Tạo `scripts/make_synthetic_pcap.py`: dựng 6 gói tin TCP giả (SYN/SYN-ACK/ACK/PSH+data/FIN/FIN) bằng `scapy`, lưu ra `.pcap` — **không cần Npcap/quyền Administrator, không bắt gói thật nào** — dùng để test tab PCAP lặp lại được bất cứ lúc nào, không phải chờ có file pcap thật.
- Mở rộng `scripts/stage13_test_dashboard.py` thêm **Việc 5**: tạo pcap giả lập bằng script trên, dùng `AppTest.file_uploader.upload()` giả lập upload qua đúng tab PCAP của Dashboard, bấm nút, kiểm tra không exception.
- **Kết quả chạy thật — cả 5 việc [PASS], 0 exception**: test Việc 5 **tái hiện lại chính xác lỗi `UnicodeDecodeError`** bạn gặp (xác nhận đây đúng là lỗi thật, không phải ngẫu nhiên riêng máy bạn) trước khi sửa (3); sau khi sửa cả 3 lỗi, chạy lại thì sạch hoàn toàn, trích đúng 1 flow từ pcap giả lập, gửi vào `/predict` thành công.
- **Dọn dữ liệu test tích lũy** (theo yêu cầu "xóa mấy cái đang ở tạm/mẫu để tôi test"): xóa `data/ids_system.db` (tích lũy 1471 alert từ các lần tôi test — không commit vào git, xóa an toàn, khởi động lại server sẽ tự tạo lại 6 bảng rỗng) + dọn hết các file `.csv`/`.log` tạm còn sót lại trong `data/` từ các bước test trước, chỉ giữ lại file thật cần dùng (`clean_holdout_set.csv`, `train_stats.json`, `lime_background.npy`, `samples/`).
- Commit: `201801b`.

### Bước 13 (bổ sung 2) — `GET /flows` (xem cả Benign) + phát hiện thật: model sai lệch vì cờ FIN ✅

**Phần 1 — `GET /flows` (theo yêu cầu "tôi cũng cần các flow bình thường hiện ra màn hình nữa"):**
- **Vì sao cần**: `GET /alerts` (bước 12) chỉ trả Alert — mà Alert CHỈ được tạo khi nhãn dự đoán khác Benign (đúng nguyên tắc kiến trúc). Flow Benign (traffic bình thường, không tấn công) không bao giờ tạo Alert nên không bao giờ xuất hiện trên Dashboard trước đây — bạn test xong không thấy traffic bình thường đâu cả, chỉ thấy toàn cảnh báo.
- Thêm `db.get_flows()`: `LEFT JOIN FlowRecord` với `Prediction`, lọc theo thời gian/nhãn, trả cả flow Benign lẫn flow tạo cảnh báo, kèm cờ `is_alert` tính sẵn. Thêm `GET /flows` vào `app/main.py` — **đây là điểm gọi API thứ 5, NGOÀI 4 điểm gọi gốc trong tài liệu kiến trúc** (`POST /predict`, `POST /explain`, `GET /alerts`, `GET /health`) — ghi rõ trong code là bổ sung theo nhu cầu thực tế khi test, không phải một phần đặc tả gốc.
- Thêm bảng "Tất cả flow đã xử lý (kể cả Benign)" vào `app/dashboard.py`, đặt TRƯỚC bảng cảnh báo (không phải sau) — vì bảng cảnh báo có `st.stop()` khi rỗng, đặt sau sẽ bị chặn không hiện ra lúc DB chưa có cảnh báo nào.
- **Lỗi thật khi viết test cho phần này**: `scripts/stage13_test_dashboard.py` Việc 3 (chọn alert có LIME) dùng `max(select_boxes, key=lambda sb: len(sb.options))` để đoán ô nào là ô "chọn cảnh báo" — hoạt động được bao lâu nay vì DB luôn có hàng trăm alert tích lũy (ô chọn alert luôn có nhiều lựa chọn nhất). Sau khi dọn sạch DB (chỉ còn 3 alert) để test sạch, ô lọc nhánh (3 lựa chọn: tất cả/A/B) bị TRÙNG số lượng với ô chọn alert → chọn nhầm ô → test FAIL dù `dashboard.py` hoàn toàn không có lỗi. **Sửa**: nhận diện theo `label` ("Chọn cảnh báo để xem chi tiết") thay vì đếm số lựa chọn.
- **Kết quả chạy thật — lại 5/5 việc [PASS]** sau khi sửa.

**Phần 2 — Phát hiện thật khi bạn tự test bằng file `.pcap` của chính bạn (traffic duyệt web bình thường):**
- Bạn báo model đoán sai nhiều — 5/33 flow bị đoán nhầm "DoS attacks-Hulk" dù chỉ là traffic duyệt web HTTPS bình thường. Tôi mở lại đúng file CSV CICFlowMeter đã trích ra từ pcap của bạn (`172.20.10.8` nói chuyện HTTPS với nhiều server — rõ ràng là traffic bình thường) để tìm nguyên nhân, không đoán mò.
- **Tìm ra nguyên nhân rõ ràng bằng cách so sánh trực tiếp**: cả 5 flow bị đoán nhầm đều có `fin_flag_cnt ≥ 1` (1 hoặc 2); cả 28 flow còn lại (đoán đúng Benign) **đều có `fin_flag_cnt = 0`**, không ngoại lệ. Tra thêm SHAP của 1 ca: `FIN Flag Cnt` là đặc trưng đóng góp mạnh nhất (phi=+5,87), áp đảo các đặc trưng khác.
- **Đây KHÔNG phải lỗi code** (đã xác nhận CICFlowMeter trích xuất đúng, feeder map cột đúng, API hoạt động đúng) — mà là **một giới hạn thật của chính model** (huấn luyện trên CICIDS2018, 2018): rất có thể trong bộ dữ liệu gốc, các phiên "Benign" (bắt gói nhiều giờ liên tục) hiếm khi được chụp đủ để thấy gói FIN đóng kết nối (bị cắt giữa chừng do hết thời gian bắt), còn traffic tấn công (công cụ tự động, mở/đóng kết nối nhanh) lại hay có FIN rõ ràng — khiến model học nhầm "có FIN = khả nghi" thay vì học đúng bản chất tấn công Hulk. Khi bạn bắt 1 đoạn traffic NGẮN của chính mình, nhiều phiên HTTPS kịp đóng hẳn trong lúc bắt → có FIN → rơi đúng vào điểm mù này.
- **Không sửa model** (ngoài phạm vi RQ3 — RQ3 dùng lại nguyên model đã huấn luyện từ RQ1, không huấn luyện lại) — ghi nhận đây là **bằng chứng thật, giá trị**, đúng loại phát hiện RQ3 được thiết kế để phơi bày (model có thể dựa vào đặc điểm "môi trường bắt gói" thay vì bản chất tấn công — cùng tinh thần với cờ môi trường ở bước 8, dù `FIN Flag Cnt` không nằm trong 3 đặc trưng cờ môi trường đã định nghĩa sẵn). Nên đưa vào báo cáo cuối như 1 ví dụ thật, cụ thể, có số liệu, về giới hạn tổng quát hoá của model khi gặp traffic thật ngoài phòng lab — việc kiểm chứng bài bản giả thuyết này (không chỉ riêng FIN flag) vẫn để dành cho **E2/E4** ở M5.
- Dọn sạch `data/ids_system.db` (đã tích lũy >1400 alert do tôi gửi lại nhiều lần cùng 33 flow để chẩn đoán) bằng `DELETE` qua SQL (không xóa file, vì server bạn có thể đang chạy — an toàn hơn nhờ chế độ WAL), giữ nguyên schema — Dashboard giờ về trạng thái sạch, sẵn sàng để bạn test lại từ đầu.
- Commit: `62c1a6f`.

### Bước 13 (bổ sung 3) — Phân biệt "lúc gói tin thật xảy ra" với "lúc hệ thống xử lý" ✅
- **Vì sao có mục này**: bạn phản ánh sau mỗi lần gửi CSV/PCAP, bảng cảnh báo hiện thời gian "loạn", không theo thứ tự nào, không biết cảnh báo nào ứng với thời điểm nào. Nguyên nhân thật: `received_at`/`created_at` trước giờ luôn là **lúc hệ thống xử lý request** (giờ thật lúc bạn bấm gửi) — khi phát lại 1 file cũ, hàng chục flow được xử lý dồn dập trong vài giây, nên mọi thời gian hiện ra gần như giống hệt nhau, không phản ánh đúng thứ tự traffic THẬT đã xảy ra trong file gốc. Thêm vào đó, mọi flow (dù từ CSV, PCAP hay gõ tay) đều ghi `source="api"` giống hệt nhau — không phân biệt được đợt gửi nào.
- Thêm cột `FlowRecord.flow_timestamp` (có migrate an toàn `ALTER TABLE ... ADD COLUMN` cho DB cũ đã tồn tại, không yêu cầu xóa DB) — lưu đúng lúc gói tin THẬT xảy ra, lấy từ cột `timestamp` CICFlowMeter ghi sẵn trong CSV (chỉ có khi nguồn là CICFlowMeter thật — CSV Tập A/B không có cột này nên sẽ là `NULL`, hiển thị rõ "(không rõ — nguồn không kèm mốc thời gian gốc)" thay vì giả vờ có).
- `POST /predict` thêm 2 tham số query TÙY CHỌN (không phải đặc trưng, không phá vỡ hợp đồng cũ): `source` (mặc định `"api"`, Dashboard gửi đúng `"csv_upload"`/`"pcap_replay"`, `app/feeder.py` gửi `"feeder_live"`) và `flow_timestamp`.
- `db.get_alerts()`/`db.get_flows()`: `LEFT JOIN` thêm `FlowRecord` để lấy `source`/`flow_timestamp`, **sắp theo `COALESCE(flow_timestamp, received_at) DESC`** — flow có mốc thời gian gốc được ưu tiên sắp theo đúng thứ tự traffic thật xảy ra, không theo thứ tự upload.
- Cả 2 bảng trên Dashboard (`Tất cả flow`, `Danh sách cảnh báo`) hiện tách rõ **2 cột thời gian riêng**: "thời điểm gói tin thật" và "lúc hệ thống xử lý", kèm cột "nguồn" — không còn gộp chung gây nhầm lẫn nữa.
- **Xác nhận chạy thật**: gửi lại 1 flow qua tab PCAP, mở DB kiểm tra trực tiếp — `flow_timestamp='2026-10-14T23:46:02'` (giờ máy lúc gói tin được ghi trong pcap) khác hẳn `received_at='2026-10-14T16:46:05 UTC'` (= 23:46:05 giờ VN, lúc hệ thống xử lý) — đúng như kỳ vọng, 2 mốc thời gian tách biệt rõ ràng. `source` phân biệt đúng 3 giá trị `api`/`csv_upload`/`pcap_replay` sau khi test cả 3 đường.
- Chạy lại `scripts/stage12_test_alerts.py` (5/5 PASS) và `scripts/stage13_test_dashboard.py` (5/5 PASS) xác nhận không vỡ gì.
- Commit: `872289e`.

---

<a id="ui-history"></a>

# Kế hoạch cải thiện Dashboard IDS RQ3

Trạng thái: **đã triển khai dashboard mới và PASS test cô lập; chờ nghiệm thu một lượt Wi-Fi live trên máy người dùng**. Cập nhật: 16/10/2026 (Asia/Bangkok).

Mục tiêu: khi bắt traffic thật, người xem nhận ra ngay flow nào thuộc lượt bắt hiện tại, thấy kết quả dự đoán mới mà không phải bấm F5, và chọn **bất kỳ flow nào** để xem đủ thông tin phù hợp với kiến trúc IDS có giải thích.

## 1. Nguồn thiết kế và nguyên tắc không được đổi

- Nguồn: `Kiến trúc hệ thống IDS.docx`, đặc biệt **Khối 7 — Bảng điều khiển cho analyst** và **Mô hình logic hợp nhất** (mục này được tài liệu chỉ định ưu tiên khi các phần cũ khác nhau); `RQ3_IDS_System/docs/plan.md`; code hiện tại trong `app/`.
- Một flow hợp lệ được chuẩn hóa thành đúng 78 đặc trưng rồi XGBoost trả xác suất 15 lớp. Metadata như IP, cổng, nguồn và lượt bắt **không** được đưa thêm vào 78 đặc trưng hoặc thay model RQ1.
- Nhãn khác Benign tạo cảnh báo ngay. SHAP tự động chạy nền cho cảnh báo; LIME chỉ chạy khi analyst bấm yêu cầu. Flow Benign vẫn xem được dự đoán nhưng không có SHAP/LIME mặc định.
- Nhánh A/B chỉ thay cách hiển thị và lời nhắc; không sửa nhãn, không xóa/ẩn cảnh báo. Theo mô hình logic hợp nhất, luật A/B hiện chỉ dựa vào cờ môi trường và cờ lớp hiếm. Agreement/faithfulness không tự trở thành ngưỡng quyết định.
- Dashboard chỉ truy cập dữ liệu qua API. Không đọc SQLite trực tiếp từ Streamlit.
- Đồ thị SHAP và LIME giữ dấu, nhưng phải tách tab/trục vì SHAP hiện giải thích raw margin, LIME giải thích xác suất. Không diễn giải hai độ lớn là cùng đơn vị.
- `faithfulness_proxy_drop` chỉ là proxy nhanh; cờ môi trường chỉ là dấu hiệu cần xem xét. Nhãn dự đoán và xác suất không phải nhãn thật hay bằng chứng tấn công đã xác nhận.

## 2. Vấn đề đã thấy khi test ngày 16/10/2026

| Hiện tượng | Nguyên nhân trong code hiện tại | Hướng xử lý |
|---|---|---|
| Flow mới khó thấy, phải bấm F5 | Dashboard chỉ gọi `/flows` và `/alerts` khi Streamlit chạy lại; feeder cập nhật DB nhưng không kích hoạt trang | Làm mới vùng giám sát theo chu kỳ, có nút tạm dừng |
| Dữ liệu nhiều lần test trộn lẫn | `FlowRecord` có `source` nhưng chưa có mã lượt bắt; DB giữ dữ liệu cũ | Gắn `capture_run_id` cho flow mới, mặc định xem lượt hiện tại; có lựa chọn xem lịch sử |
| Bảng dài, muốn xem flow phải tìm cảnh báo trong dropdown | Chi tiết hiện chỉ chọn `AlertRecord`; Benign không có trang chi tiết | Chọn trực tiếp một dòng ở bảng mọi flow và mở panel chi tiết qua `flow_id` |
| Giờ `07:21` đứng cạnh `00:23+00:00` gây nhầm | Thời gian gốc CICFlowMeter không có múi giờ, còn `received_at` là UTC; UI in ISO thô | Chuẩn hóa mốc giờ, hiển thị giờ Việt Nam và giải thích từng mốc |
| Thứ tự mới/cũ có thể khó hiểu | SQL `ORDER BY COALESCE(flow_timestamp, received_at)` đang so chuỗi local không múi giờ với UTC | Danh sách live xếp theo lúc hệ thống nhận; thời gian gốc là cột riêng và có chế độ xem theo mốc gốc |
| Không thấy IP nguồn/đích trong chi tiết | Feeder bỏ cột chuỗi `src_ip`/`dst_ip` khi tạo payload số; DB chưa lưu metadata này | Truyền/lưu metadata riêng, giữ nguyên đầu vào model |
| Nhiều cảnh báo Hulk giống nhau làm ngập bảng | Dashboard hiện từng Alert; `group_key` hiện chỉ dùng nhãn dự đoán | Gom **cách hiển thị** theo lượt bắt + cặp IP/cổng + lớp và khoảng thời gian; luôn mở ra được từng cảnh báo |
| Có packet nhưng chưa có dự đoán | CICFlowMeter chỉ xuất flow khi đóng/hết hạn hoặc lúc dừng bắt để `flush_flows()` | Hiển thị trạng thái “đang bắt, chưa có flow hoàn tất”; không hứa dự đoán theo từng packet |

Ảnh test cho thấy flow có `source=feeder_live`, `flow_timestamp` khoảng **07:21**, còn lúc hệ thống xử lý `00:23+00:00` tương ứng khoảng **07:23 GMT+7**. Sự khác biệt định dạng này dễ làm dữ liệu mới trông như dữ liệu cũ. Cần kiểm tra thêm liệu `timestamp` của CICFlowMeter là thời điểm bắt đầu flow hay mốc nào trước khi đổi nhãn cột trong UI.

## 3. Màn hình đề xuất

### 3.1. Tổng quan live

1. Thanh đầu trang: trạng thái API/model; thời điểm **flow cuối được API nhận**; hàng đợi SHAP, số tác vụ bị bỏ; tên lượt bắt đang xem. Nếu không có flow mới, hiển thị “chưa có flow hoàn tất” thay vì suy đoán bộ bắt đã dừng.
2. Bộ lọc gọn: `Lượt hiện tại / Lịch sử`, nguồn (`feeder_live`, CSV, PCAP), thời gian, Benign/cảnh báo, lớp dự đoán, nhánh A/B. Mặc định lượt hiện tại và mới nhất trước.
3. Thẻ chỉ số cho lượt/bộ lọc đang chọn: số flow, Benign, cảnh báo, SHAP chờ/xong/bị bỏ. Mọi số phải ghi rõ mẫu số và phạm vi.
4. Biểu đồ tổng quan: số flow theo phút; Benign so với cảnh báo theo thời gian; số cảnh báo theo lớp. Đây là **số dự đoán**, không phải số vụ tấn công đã được kiểm chứng.
5. Bảng flow chính: giờ Việt Nam, nguồn/lượt bắt, IP/cổng nếu có, nhãn, xác suất lớp thắng, trạng thái cảnh báo/XAI. Cột dài/ít dùng nằm trong chi tiết. Một cú chọn dòng mở chi tiết bên cạnh hoặc ngay dưới bảng.
6. Khu nạp CSV/PCAP chuyển vào tab riêng để không chiếm phần đầu màn hình giám sát live.
7. Vùng bảng và chỉ số tự làm mới khoảng 3–5 giây/lần. Có `Tạm dừng làm mới` khi analyst đang đọc chi tiết; bộ lọc và flow đang chọn không bị nhảy. Không tự gửi lại file hoặc tự gọi LIME khi trang làm mới.

### 3.2. Chi tiết một flow được chọn

| Khu vực | Nội dung |
|---|---|
| Nhận diện | Flow ID đầy đủ, lượt bắt, nguồn, IP nguồn/đích, cổng, protocol, thời lượng nếu có; thiếu dữ liệu thì ghi “nguồn không cung cấp” |
| Thời gian | Mốc traffic gốc, lúc API nhận, lúc dự đoán, lúc SHAP hoàn tất nếu có; một định dạng `dd/MM/yyyy HH:mm:ss` GMT+7, có thể mở mốc UTC/raw |
| Dự đoán | Nhãn thắng và xác suất; biểu đồ xác suất 15 lớp (hoặc Top-5 và nút mở đủ 15); phiên bản model; nhãn thật chỉ hiện khi nguồn có cung cấp |
| Benign | Ghi “Đã lưu dự đoán bình thường; không tạo cảnh báo/SHAP theo thiết kế” |
| Cảnh báo | Alert ID, trạng thái SHAP `chờ / xong / bị bỏ`, nhánh A/B và lý do; cảnh báo vẫn thấy khi XAI chưa xong |
| SHAP | Top-5 thanh ngang hai phía trục 0, màu/legend nhất quán; tên đặc trưng, giá trị gốc và φ; chú thích dấu nghĩa là đẩy về/ra khỏi **lớp đang giải thích** |
| LIME | Nút yêu cầu thủ công, trạng thái đang chạy, Top-5 ở tab riêng, Local R² nếu API trả, Jaccard@5 chỉ khi đủ cả SHAP và LIME |
| Độ tin cậy | Faithfulness proxy, cờ môi trường `n/3`, cờ lớp hiếm, số tham chiếu RQ2 theo lớp khi bước 10 triển khai; thiếu thì ghi “chưa có”, không hiển thị `None` hoặc một “điểm tin cậy” tổng hợp giả tạo |
| Độ trễ | Các bước đã ghi trong `Timing`; không gọi các số live là kết quả median/p95 E1 chính thức khi thí nghiệm E1 chưa làm |

### 3.3. Cảnh báo liên quan

Cho phép nhóm để dễ đọc khi có nhiều flow giống nhau, nhưng không xóa bản ghi con. Chỉ nhóm bằng IP/cổng khi metadata thực sự có; nguồn Tập A/B thiếu IP thì dùng nhóm theo lớp và ghi rõ giới hạn. Người xem mở nhóm vẫn tới được từng `flow_id`/`alert_id`.

## 4. Việc cần thay trong dữ liệu và API

- [x] `app/feeder.py`: tạo mã lượt bắt một lần khi khởi động; gửi `capture_run_id` và metadata IP/cổng/protocol của dòng CICFlowMeter qua tham số/đối tượng metadata tách khỏi 78 đặc trưng. Không mặc định lọc IP máy chủ trong đợt cải thiện UI này.
- [x] `app/main.py`: chấp nhận metadata **tùy chọn** để lời gọi `/predict` cũ còn hoạt động; không đưa metadata vào `Detector.predict_flow()`.
- [x] `app/db.py`: migration không mất dữ liệu cho `capture_run_id`, IP/cổng và thời gian gốc được chuẩn hóa; bản ghi cũ không có metadata vẫn đọc được.
- [x] API danh sách: lọc theo lượt bắt, nguồn và thời gian; phân trang tại DB cho `/flows` và `/alerts` thay vì kéo toàn bộ cảnh báo rồi cắt 100 dòng trong UI. Phạm vi/tổng số trả về phải rõ.
- [x] API chi tiết theo `flow_id`: ghép FlowRecord + Prediction + AlertRecord nếu có + Reliability + Timing. Có kết quả chi tiết cho cả Benign.
- [x] API số liệu tổng quan: trả số đếm và các bucket thời gian từ **toàn bộ phạm vi lọc**, không tính biểu đồ trên 200 dòng gần nhất rồi gọi đó là tổng hệ thống.
- [x] Trạng thái SHAP: phân biệt `queued`, `processed`, `dropped_queue_full`; hiện tại `get_alerts()` gộp chưa xử lý và bị bỏ thành `pending_or_dropped`.
- [ ] Timezone: lưu/so sánh bằng mốc UTC có múi giờ khi nguồn xác định được múi giờ; giữ raw timestamp để truy vết. Với dữ liệu cũ không rõ múi giờ, không âm thầm suy ra chính xác giả. Danh sách live xếp theo `received_at`, chế độ phát lại có thể xếp theo thời gian gốc đã chuẩn hóa.

## 5. Thứ tự triển khai dự kiến

1. **Pha A — sửa quan sát live:** phân biệt lượt bắt, thời gian, thứ tự mới nhất, tự làm mới, bảng flow gọn. Đây là phần giải quyết trực tiếp vấn đề trong ảnh.
2. **Pha B — chi tiết một flow:** API chi tiết và chọn dòng; xác suất 15 lớp, metadata, trạng thái Benign/cảnh báo; SHAP/LIME/độ tin cậy/Timing.
3. **Pha C — biểu đồ và cảnh báo liên quan:** số liệu tổng quan tính từ API, nhóm cảnh báo chỉ ở lớp hiển thị, cải thiện cách đọc cờ và giới hạn mô hình.
4. **Pha D — kiểm thử và cập nhật tài liệu:** test API, Streamlit AppTest, CSV/PCAP và một lượt live mới; cập nhật `README.md` và `docs/plan.md` sau khi code thực sự xong.

## 6. Tiêu chí nghiệm thu

- [ ] Feeder gửi một flow mới thì nó xuất hiện ở màn hình live trong một chu kỳ làm mới sau khi API ghi xong; lần test cũ không trộn vào chế độ “lượt hiện tại”. Nếu CICFlowMeter chưa xuất flow, UI nói rõ chưa có flow hoàn tất.
- [x] Chọn được cả flow Benign và flow tạo cảnh báo; một flow có một màn chi tiết nhất quán qua `flow_id`.
- [x] Cảnh báo xuất hiện trước SHAP; khi SHAP xong cùng cảnh báo được cập nhật. LIME chỉ chạy khi bấm.
- [x] Xác suất 15 lớp khớp dữ liệu Prediction; Top-5 SHAP/LIME và dấu khớp bản ghi API; nhánh B giữ nguyên nhãn/cảnh báo và hiển thị lý do.
- [x] Thời gian ở bảng là GMT+7 dễ đọc; UTC/raw nằm trong chi tiết; sắp xếp theo lúc API nhận trong live; PCAP cũ gửi lại vẫn được nhận biết là lượt xử lý mới với thời gian traffic gốc riêng.
- [x] Biểu đồ/tổng số tôn trọng cùng bộ lọc và không chỉ dựa vào giới hạn 200 flow/100 alert của UI.
- [ ] Metadata không làm thay đổi thứ tự, đơn vị hay số lượng 78 đặc trưng model; các API cũ và test bước 6–13 vẫn chạy.
- [x] Không xóa `data/ids_system.db`, CSV/PCAP hay dữ liệu thử hiện có để triển khai UI. Migration và dữ liệu mới được kiểm tra bằng bản sao/test riêng trước khi dùng DB hiện tại.

## 7. Ngoài phạm vi lượt cải thiện UI

- Huấn luyện lại model hoặc coi cảnh báo Hulk trên traffic web bình thường là tấn công đã xác thực.
- Chạy SHAP mặc định cho Benign hoặc LIME tự động cho mọi flow.
- Thay đổi luật nhánh A/B, tự đặt ngưỡng faithfulness/agreement, hoặc trình bày hai cột stability/robustness là đã có dữ liệu trước khi bước 10 được triển khai.
- Giải quyết độ trễ nội tại của CICFlowMeter bằng cách ép ghi các flow đang mở theo chu kỳ tùy ý. Việc đó có thể làm thay đổi đặc trưng flow và cần một thiết kế/kiểm chứng riêng.

## 8. Nhật ký tiến độ

### Adapter capture có phiên bản và kiểm tra realtime (16/10/2026)

- [x] `app/capture_adapter.py`: sửa đếm đầu flow/CWR/IAT/Active-Idle/protocol key; session đồng bộ GC, replay theo clock PCAP; không sửa site-packages.
- [x] CLI mặc định project v1, hỗ trợ baseline `--extractor legacy`; lịch sử audit dùng legacy để tái lập.
- [x] Metadata extractor version từ CSV qua feeder/upload tới API/DB/UI; migration cộng cột, vector mới lưu đúng 78 đặc trưng.
- [x] 10 bài fixture và regression API/UI/CSV/PCAP PASS; đối chiếu hai PCAP trên lượt tạm: 92 vector đổi, 0 nhãn đổi; 8 LIME vẫn thiếu neighborhood.
- [x] Wi-Fi thật 20 giây: 2.704 gói →178 flow →178 dự đoán; không lỗi feeder trong mẫu; SHAP 14/14, không dropped. UI AppTest PASS. Phiên ngắn nhận 0 flow trước khi dừng; chưa coi là chứng minh streaming tức thì.
- [x] Wi-Fi thật 100 giây: 42.027 packet →159 flow →159 dự đoán; 88 flow lên API trước khi capture dừng. SHAP 29/29, không dropped/lỗi feeder trong mẫu; version/IP/78 cột/15 lớp/đơn vị/UI AppTest PASS. CSV packet total khớp callback count; chưa đo mất packet trước callback hoặc tải dài.
- [ ] Chốt quy ước length/header/std/subflow/window/cờ với nguồn train; sửa retry feeder, thiết kế timeout/TCP close cho mục tiêu độ trễ, đo tải dài.

Chi tiết và JSON đo thực: [capture_adapter_v1.md](feature_compatibility.md#adapter-v1). Ngưỡng hiện tại duration 90 giây/idle 240 giây; cần restart API/UI và capture/feeder với tên file mới để áp dụng đầy đủ.

### Kiểm tra tương thích 78 đặc trưng (16/10/2026)

- [x] Quét đủ train 2,8 triệu dòng, các cột trọng tâm trên 10 daily cleaned (15.589.784 dòng), đọc DB PCAP ở mode=ro.
- [x] 8 fixture TCP/UDP tái hiện lỗi đếm đầu flow, CWR, IAT một khoảng, active/idle và thiếu protocol trong khóa flow; một fixture đối chiếu đường `run_live_capture.py` thực tế.
- [x] Xuất [báo cáo](feature_compatibility.md#baseline-audit), [ma trận đủ 78 cột](feature_compatibility.md#matrix-78) và JSON bằng chứng; đính chính nhận định quy toàn bộ cảnh báo nhầm cho model trong README/kế hoạch.
- [ ] Sửa extractor có phiên bản trong mã dự án, kiểm chứng chuẩn length/header/std/subflow/window và nguồn preprocessing; chưa tự sửa site-packages, clip cờ hoặc zero bulk.

### Mở rộng hàng đợi SHAP theo yêu cầu (16/10/2026)

- [x] Tăng cấu hình từ 50 lên 200 tác vụ chờ; không đổi worker hoặc luật khi queue đầy.
- [x] UI tiếp tục đọc `maxsize` qua API, không gán cứng mẫu số; bảng vẫn 50 flow/trang.
- [x] Cập nhật README, hướng dẫn chạy và kế hoạch RQ3; giữ số liệu test queue 50 trong nhật ký lịch sử.
- [x] Kiểm tra `submit()` khi worker dừng trong bộ nhớ: nhận đủ 200 tác vụ, tác vụ 201 trả `dropped_queue_full`, queue vẫn 200; không ghi DB. Chạy lại `stage14_test_dashboard_redesign.py`: toàn bộ regression API/UI/CSV/PCAP PASS trên DB tạm với cấu hình mới. Đây không phải benchmark tải.
- [ ] Đo tải để chọn dung lượng phù hợp; chưa cải thiện tốc độ xử lý, retry feeder hoặc khôi phục queue RAM.

Áp dụng bằng khởi động lại API. Đây là thay đổi cấu hình dung lượng, không phải kết quả benchmark hoặc sửa độ tin cậy giao nhận dữ liệu.

### Audit hai PCAP theo yêu cầu người dùng (16/10/2026)

- [x] Đọc 92 flow, tính lại model: 92/92 khớp nhãn/xác suất; trích lại PCAP: 59/59 và 33/33 khớp 78 đặc trưng.
- [x] 8/8 SHAP khớp và additivity sai số tối đa ≈2,861e-6; 8/8 LIME ESS≈1.
- [x] Phân biệt 2 flow có weight underflow về 0 và 6 flow có weight khác 0 nhưng cực nhỏ; không kết luận đồng loạt 999 weight bằng 0.
- [x] Kiểm tra cờ/bulk trên toàn bộ 2,8 triệu dòng train và 13 mẫu LIME đối chứng.
- [ ] Chưa thay adapter đặc trưng/cấu hình LIME; cần một bước sửa phương pháp có đánh giá riêng. Sửa UI trước đó chỉ làm rõ tính không hợp lệ.

Chi tiết: [pcap_xai_audit_20261016.md](xai_validation.md#pcap-audit). Lệnh kiểm tra chỉ đọc: `scripts/stage17_audit_pcap_xai.py`.

### Điều chỉnh theo phản hồi: cần hiểu tên đặc trưng (16/10/2026)

- [x] Định nghĩa tiếng Việt + đơn vị + lưu ý cho đủ 78 tên đầu vào, dùng chung API/UI; không còn placeholder trong danh mục.
- [x] SHAP/LIME có phần đọc từng đặc trưng bằng lời ngay dưới biểu đồ, phân biệt giá trị đầu vào và hệ số giải thích.
- [x] Tra cứu một đặc trưng là giao diện chính; bảng rộng 78 cột số liệu tham chiếu chuyển vào phần mở rộng gọn hơn.
- [x] LIME lỗi giải thích quy trình, số mẫu mất trọng số và ý nghĩa kết quả bằng ngôn ngữ phổ thông; kỹ thuật/JSON thu gọn.
- [x] Giữ nguyên mô hình, đầu vào, cấu hình LIME và luật A/B; không biến diễn giải thành quy tắc phát hiện mới.

Hướng dẫn: [reading_shap_lime.md](dashboard_usage.md#read-xai). Test `stage16_test_feature_help.py` kiểm tra đủ 78 tên, đơn vị, dấu và định dạng số.

### Bổ sung theo test PCAP: LIME và đối chứng (16/10/2026)

- [x] Xác định LIME toàn trọng số 0: 999/1000 mẫu lân cận có kernel weight bằng 0; cỡ mẫu hiệu dụng bằng 1.
- [x] Lưu chẩn đoán; không công bố R²/Jaccard/Top-5 có ý nghĩa khi LIME suy biến; nhận diện kết quả cũ toàn 0 mà không sửa lịch sử DB.
- [x] Khóa RNG LIME khi có nhiều request đồng thời để giữ tái lập theo flow.
- [x] Tab đối chứng đủ 78 đặc trưng, nền LIME và P05/median/P95 tập B theo nhãn; số mẫu/nguồn/giới hạn ghi rõ.
- [x] Test số học bình thường/suy biến/hằng, đa luồng và kết quả legacy; test API/UI/CSV/PCAP bằng DB tạm.
- [x] Audit baseline và adapter v1: tái hiện/sửa 5 lỗi extractor; giữ cấu hình RQ2, không ép LIME có thanh.
- [x] Audit quan hệ từng dòng: toàn bộ train/test và 10 daily cleaned; [hợp đồng ngữ nghĩa](feature_compatibility.md#semantics) kèm JSON/checksum và fixture.
- [ ] Nghiệm thu tương thích ngữ nghĩa train/PCAP: chưa xong; còn khác SD, ratio, sentinel window, length/header, mean, cờ/bulk và nguồn preprocessing lịch sử.

Xem [báo cáo kỹ thuật và cách sử dụng](xai_validation.md#lime-validity). Đây là sửa tính trung thực của kết quả/UI, không phải tuyên bố đã khắc phục dịch chuyển phân bố traffic thật.

| Ngày | Mục | Trạng thái | Bằng chứng/ghi chú |
|---|---|---|---|
| 16/10/2026 | Lập kế hoạch theo ảnh test live và tài liệu kiến trúc | Xong | Chưa sửa code |

Khi bắt đầu triển khai, cập nhật checkbox và nhật ký này sau từng pha để không bỏ sót việc.

### Cập nhật triển khai 16/10/2026

- Pha A/B/C: đã có metadata riêng, migration cộng thêm cột/index, API chi tiết/số liệu/lượt và phân trang; UI tự cập nhật 5 giây, bộ lọc lượt, chọn mọi flow, biểu đồ tổng quan/xác suất/SHAP/LIME/timing, nhóm cảnh báo 5 phút.
- Pha D: PASS `scripts/stage14_test_dashboard_redesign.py` trên DB tạm, API cổng riêng, model thật và Streamlit AppTest. Có kiểm tra CSV và PCAP qua CICFlowMeter thật, không chỉ kiểm tra HTTP server khởi động. Test bước 13 đã chuyển tiếp sang bộ test mới để không ghi vào DB demo.
- Kiểm tra metadata không làm thay đổi xác suất model với cùng 78 đặc trưng; không thay luật dự đoán, SHAP/LIME hay nhánh A/B.
- Test bước 4 (chuẩn hóa) và bước 5 (dự đoán) PASS; 50/50 mẫu đối chiếu khớp RQ2. Có cảnh báo phiên bản thư viện model cũ, được ghi trong hướng dẫn.
- Feeder sửa lỗi dòng trống có thể làm lệch con trỏ và gửi lặp. Dòng cuối chưa đủ cột được chờ ở lượt đọc sau.
- Không xóa dữ liệu demo; chưa tự restart API/feeder đang chạy của người dùng.
- Hướng dẫn chạy lại: [dashboard_usage.md](dashboard_usage.md).

### Phần chưa nghiệm thu / giới hạn được giữ rõ

- Đã chạy Wi-Fi live 20s/100s trên DB tạm sau adapter v1 (xem báo cáo capture); chưa xác nhận tự-refresh/click bằng trình duyệt thật, AppTest đã chạy các nhánh UI.
- Chưa chạy lại toàn bộ test bước 6–12; không đánh dấu tương thích toàn bộ chỉ dựa trên bộ smoke/regression mới.
- UI hiện xếp theo lúc API nhận. Chế độ sắp xếp riêng theo timestamp gốc cho replay chưa thêm; vẫn xem được timestamp gốc trong chi tiết, không trộn với UTC.
- Bộ lọc UI cung cấp toàn bộ lượt/5 phút/15 phút/1 giờ/hôm nay; khoảng tùy ý dùng API since/until, chưa có date-picker.
- Nhóm chỉ hiển thị 100 nhóm mới nhất trong phạm vi, từng nhóm có phân trang; bảng flow chính vẫn cho xem mọi flow.
- API chỉ biết flow đã được gửi đến, không có heartbeat của capture. Bản v2 đã phục hồi SHAP bị ngắt từ DB, hiển thị backlog riêng; chỉ chạy một API process/DB. Xem [cập nhật ổn định](operations.md#stability-v2).

### Ổn định vận hành sau audit

- [x] Capture v2 bảo toàn initial window=0; candidate quy ước train tách phiên bản và đối chiếu hai PCAP.
- [x] Feeder đọc tăng dần, checkpoint sau ACK, backoff, khóa, xử lý dòng dở dang và phát hiện truncate.
- [x] `/predict` chống gửi trùng bằng khóa, hash và giao dịch nguyên khối trên sáu bảng hiện có.
- [x] SHAP phục hồi tác vụ bị ngắt từ DB, giữ giới hạn queue 200 và chính sách dropped.
- [ ] Tương thích đầy đủ train/V3, ground truth đánh giá live, benchmark dài/tải cao và tab điều khiển capture.
