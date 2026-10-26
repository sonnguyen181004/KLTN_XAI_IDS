// Dựng báo cáo Word RQ4 từ results/report_data.json. Mọi con số trong văn bản đi qua các hàm định dạng ở đây.
const fs = require("fs");
const path = require("path");
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, HeadingLevel, WidthType, ShadingType,
  AlignmentType, LevelFormat, Footer, PageNumber, BorderStyle, ImageRun,
} = require("docx");

const ROOT = path.resolve(__dirname, "..");
const D = JSON.parse(fs.readFileSync(path.join(ROOT, "results", "report_data.json"), "utf8"));
const OUT = process.argv[2];
const TXT = process.argv[3];
const FONT = "Times New Roman";
const plain = [];

// ---------- định dạng số kiểu Việt Nam
function nf(x, d = 0) {
  const s = Math.abs(x).toFixed(d);
  const [i, f] = s.split(".");
  const ip = i.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return (x < 0 ? "-" : "") + ip + (f ? "," + f : "");
}
const pc = (x, d = 2) => nf(x, d) + "%";
const cr = (m, t) => D.cross.find((r) => r.model === m && r.test === t);
const R = D.rq1;
const A = D.audit;
const X = D.xai;
const T3 = D.t3;
const pct = (a, b, d = 2) => pc((100 * a) / b, d);

// ---------- phần tử văn bản
const run = (t, o = {}) => new TextRun({ text: t, font: FONT, size: o.size || 24, bold: o.bold, italics: o.italics });
function P(t, o = {}) {
  plain.push(t);
  return new Paragraph({ spacing: { after: o.after ?? 120, line: 300 }, alignment: o.align || AlignmentType.JUSTIFIED, children: [run(t, o)] });
}
function H1(t) {
  plain.push(t);
  return new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 300, after: 120 }, children: [run(t, { bold: true, size: 28 })] });
}
function H2(t) {
  plain.push(t);
  return new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 200, after: 100 }, children: [run(t, { bold: true, size: 25 })] });
}
function B(t) {
  plain.push(t);
  return new Paragraph({ numbering: { reference: "bul", level: 0 }, spacing: { after: 80, line: 290 }, alignment: AlignmentType.JUSTIFIED, children: [run(t)] });
}
const border = { style: BorderStyle.SINGLE, size: 4, color: "999999" };
const borders = { top: border, bottom: border, left: border, right: border };
function cell(t, w, head) {
  plain.push(String(t));
  return new TableCell({
    width: { size: w, type: WidthType.DXA }, borders,
    shading: head ? { fill: "E3EAF3", type: ShadingType.CLEAR, color: "auto" } : undefined,
    margins: { top: 50, bottom: 50, left: 80, right: 80 },
    children: [new Paragraph({ spacing: { after: 0, line: 250 }, children: [run(String(t), { size: 19, bold: head })] })],
  });
}
function T(widths, header, rows) {
  const total = widths.reduce((a, b) => a + b, 0);
  return new Table({
    width: { size: total, type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, children: header.map((h, i) => cell(h, widths[i], true)) }),
      ...rows.map((r) => new TableRow({ cantSplit: true, children: r.map((c, i) => cell(c, widths[i], false)) }))],
  });
}
const cap = (t) => P(t, { italics: true, size: 21, after: 160 });
const gap = () => new Paragraph({ spacing: { after: 80 }, children: [] });
function IMG(file, w, h) {
  plain.push("HINH " + file);
  return new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 60 },
    children: [new ImageRun({ type: "png", data: fs.readFileSync(path.join(__dirname, file)), transformation: { width: w, height: h },
      altText: { title: file, description: file, name: file } })] });
}

const c = [];
const W = 9638;

// ================= TIÊU ĐỀ =================
plain.push("TITLE");
c.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 80 }, children: [run("BÁO CÁO THỰC NGHIỆM RQ4", { bold: true, size: 32 })] }));
c.push(P("So sánh mô hình XGBoost huấn luyện trên CSE-CIC-IDS2018 bản gốc và bản đã sửa lỗi, kèm giải thích SHAP và LIME", { align: AlignmentType.CENTER, bold: true, size: 26, after: 80 }));
c.push(P("Dự án IDS thời gian thực có giải thích (RQ1, RQ2, RQ3, RQ4). Ngày lập 26/10/2026. Bản nháp gửi thầy xem.", { align: AlignmentType.CENTER, italics: true, size: 22, after: 200 }));

// ================= 1. TÓM TẮT =================
c.push(H1("1. Tóm tắt"));
c.push(P(`Mô hình XGBoost của dự án (M0) đạt Accuracy ${pc(R.M0.acc)} và Macro F1 ${pc(R.M0.f1)} trên tập kiểm thử của bộ dữ liệu cũ, nhưng khi chạy trên lưu lượng thật của máy người dùng thì ${pc(100 * T3.M0_all784_attack_flagged / T3.t3_flows, 1)} số flow Benign bị báo thành tấn công. Cả ${nf(T3.t3_zone_flows)} flow nằm trong một vùng đặc trưng cụ thể đều bị báo là DoS Hulk, và đặt cờ FIN bằng 0 thì cả ${nf(T3.M0_counterfactual_all784["FIN=0"].changed_labels)} flow đó đổi nhãn, chỉ còn ${nf(T3.M0_counterfactual_all784["FIN=0"].attack_flagged)} trên ${nf(T3.t3_flows)} flow bị báo tấn công. Người dùng xác nhận toàn bộ ${nf(T3.t3_flows)} flow này là lưu lượng bình thường.`));
c.push(P(`Nguồn gốc nằm ở dữ liệu huấn luyện. Trong 9 tệp CSV gốc của CSE-CIC-IDS2018, ${nf(A.orig_benign.tcp_flows)} flow Benign TCP chỉ có ${nf(A.orig_benign.fin_data_gt0)} flow vừa mang cờ FIN vừa có dữ liệu, và không có flow nào mang dữ liệu từ 66 byte trở lên. Trong bản đã sửa lỗi (improved), tỷ lệ này là ${pct(A.imp9_benign.fin_data_gt0, A.imp9_benign.tcp_flows)} và ${pct(A.imp9_benign.fin_data_ge_min, A.imp9_benign.tcp_flows)} của ${nf(A.imp9_benign.tcp_flows)} flow Benign TCP cùng chín ngày. Mô hình cũ gán nhãn tấn công cho từ ${pc(cr("M0", "T2a_improved_stratified").fpr_zone_pct, 3)} đến ${pc(cr("M0", "T2b_improved_thoi_gian").fpr_zone_pct, 0)} flow Benign trong vùng này, với ${nf(cr("M0", "T2a_improved_stratified").benign_zone_n)} flow ở riêng bộ test improved.`));
c.push(P(`Nhóm huấn luyện lại hai mô hình theo đúng quy trình của RQ1 và RQ2, giữ nguyên siêu tham số và cấu hình SHAP, LIME. Mô hình M0b dùng dữ liệu cũ giới hạn 13 lớp chung. Mô hình M1 dùng mẫu 3,25 triệu dòng lấy từ bản improved. M1 báo nhầm ${pc(cr("M1", "T3_realtime_benign").fpr_pct, 1)} trên lưu lượng thật, so với ${pc(cr("M0", "T3_realtime_benign").fpr_pct, 1)} của M0. Tuy nhiên M1 chỉ nhận từ ${pc(cr("M1", "T1_test_cu").hulk_recall_pct, 1)} đến ${pc(cr("M1", "T1_test_cu_sach").hulk_recall_pct, 1)} số flow Hulk của bộ test cũ (bản đầy đủ và bản bỏ trùng), và điểm gần như tuyệt đối của M1 trên dữ liệu improved (Macro F1 ${pc(R.M1.f1)}) cho thấy dữ liệu này dễ tách trong chính phòng lab, không cho thấy chất lượng ngoài đời.`));
c.push(P("Kết luận có thể viết là dữ liệu huấn luyện cũ thiếu một loại lưu lượng Benign rất phổ biến, mô hình học vùng đó là Hulk, và đổi sang dữ liệu đã sửa lỗi làm báo nhầm biến mất trên lưu lượng thật. Chưa thể kết luận rằng nguyên nhân duy nhất là thiếu mẫu, vì hai bộ dữ liệu còn khác nhau ở cách định nghĩa đặc trưng, và thí nghiệm tách hai nguyên nhân (M2) đang được hoãn."));

// ================= 2. MỤC TIÊU =================
c.push(H1("2. Mục tiêu và câu hỏi nghiên cứu"));
c.push(P("Báo cáo trả lời bốn câu hỏi theo thứ tự phát sinh trong dự án."));
c.push(B("Mô hình XGBoost đạt kết quả nội bộ cao ở RQ1 có còn đúng khi chạy trên lưu lượng thật, và nếu sai thì sai ở đâu."));
c.push(B("SHAP và LIME của RQ2 có chỉ ra được nguyên nhân của cảnh báo sai hay không."));
c.push(B("Bộ dữ liệu cũ thiếu gì so với bản đã sửa lỗi, và các bài báo đã công bố nói gì về lỗi của bộ dữ liệu này."));
c.push(B("Huấn luyện lại bằng dữ liệu đã sửa lỗi, với đúng quy trình cũ, có giải quyết được báo nhầm hay không và giải thích của mô hình mới có khác không."));

// ================= 3. THỰC NGHIỆM CŨ =================
c.push(H1("3. Thực nghiệm đã làm trước đó"));
c.push(H2("3.1 RQ1, huấn luyện và đánh giá XGBoost"));
c.push(P("Dữ liệu là CSE-CIC-IDS2018 gồm 15,59 triệu flow, được rút xuống 3,5 triệu dòng với tỷ lệ 70% Benign và 30% tấn công, giữ nguyên toàn bộ các lớp hiếm, bỏ cột Timestamp để tránh học vẹt, chia 80% train (2,8 triệu dòng) và 20% test (700 nghìn dòng) theo phân tầng. Mô hình có 78 đặc trưng số và 15 lớp. Siêu tham số được chọn bằng cách quét bảy cấu hình độ sâu và learning rate, và cấu hình có Macro F1 cao nhất là độ sâu 8, learning rate 0,08, 100 cây, tree_method hist, random_state 42."));
c.push(T([4300, 2670, 2668], ["Chỉ số trên tập test cũ (700.000 dòng)", "M0, mô hình RQ1", "Ghi chú"], [
  ["Accuracy", pc(R.M0.acc), ""],
  ["Macro Precision", pc(R.M0.prec), ""],
  ["Macro Recall", pc(R.M0.rec), ""],
  ["Macro F1", pc(R.M0.f1), ""],
  ["FPR của Benign", pc(R.M0.fpr, 4) + " (FP " + nf(R.M0.fp) + ", TN " + nf(R.M0.tn) + ")", "Benign bị báo thành bất kỳ lớp tấn công"],
  ["FNR của tấn công", pc(R.M0.fnr, 4) + " (FN " + nf(R.M0.fn) + ", TP " + nf(R.M0.tp) + ")", "Tấn công bị báo thành Benign"],
  ["F1 của lớp DoS Hulk", pc(100 * D.rq1_hulk.M0["f1-score"], 3), "Gần như hoàn hảo"],
  ["Dòng test trùng hệt dòng train", nf(D.leak.old_test_rows_also_in_train) + " (" + pct(D.leak.old_test_rows_also_in_train, D.leak.old_test_rows) + ")", "Số liệu của RQ2"],
]));
c.push(cap("Bảng 1. Kết quả chính thức của RQ1 trên tập test cũ."));
c.push(P(`Hai điểm trong Bảng 1 cần đọc cùng nhau. Hulk được phân loại gần như hoàn hảo, nhưng hơn một phần tư tập test trùng hệt dòng của tập train, nên phép đo này không hoàn toàn độc lập.`));

c.push(H2("3.2 RQ2, giải thích bằng SHAP và LIME"));
c.push(P(`RQ2 chạy 14 giai đoạn (GĐ0 đến GĐ13) trên một nhóm ${nf(X.M0.cohort)} flow dự đoán đúng, tối đa 100 flow mỗi lớp. SHAP dùng TreeExplainer, xác định và cộng dồn chính xác (sai số cộng dồn lớn nhất ${X.M0.additivity_max.toExponential(1).replace(".", ",")}). LIME dùng cấu hình đã khóa ở GĐ5 trên tập dev, gồm kernel_width 3,312, num_samples 1000, discretize_continuous tắt, num_features 78, nền 2000 dòng train lấy với seed 42.`));
c.push(T([4300, 2670, 2668], ["Kết quả RQ2 trên M0", "Giá trị", "Cách hiểu"], [
  ["Local R bình phương trung vị của LIME", nf(X.M0.lime_median_r2, 3), "Mức khớp của mô hình LIME cục bộ"],
  ["Tỷ lệ flow LIME vượt cổng chất lượng 0,3", pc(100 * X.M0.lime_pass, 1), ""],
  ["Jaccard Top-5 giữa SHAP và LIME", nf(X.M0.jacc5, 3) + " (ngẫu nhiên " + nf(X.M0.jacc5_random, 3) + ")", "Hai phương pháp đồng ý ít"],
  ["AUC comprehensiveness của SHAP", nf(X.M0.comp_shap, 3), "Trung thành hơn LIME"],
  ["AUC comprehensiveness của LIME", nf(X.M0.comp_lime, 3), "Đối chứng ngẫu nhiên " + nf(X.M0.comp_rand, 3)],
  ["Tỷ lệ flow SHAP thắng LIME tại k bằng 5", pc(100 * X.M0.win5, 1), "Nền trung vị toàn cục"],
  ["F1 so với bảng tri thức miền, bản chặt", "SHAP " + nf(X.M0.dom_shap_strict, 3) + ", LIME " + nf(X.M0.dom_lime_strict, 3), ""],
]));
c.push(cap("Bảng 2. Kết quả chính của RQ2 trên M0."));
c.push(P("SHAP của M0 cho lớp Hulk đặt đặc trưng Fwd Seg Size Min lên đầu với trọng số trung bình tuyệt đối " + nf(X.M0.top5_hulk[0][1], 2) + ", cao hơn nhiều so với Init Fwd Win Byts ở vị trí kế tiếp, chỉ " + nf(X.M0.top5_hulk[1][1], 2) + ". Cả hai đặc trưng này gắn với môi trường lab, một là kích thước header tối thiểu và một là cửa sổ nhận ban đầu, và không mô tả hành vi tấn công."));

c.push(H2("3.3 RQ3, hệ thống IDS và hiện tượng báo nhầm"));
c.push(P("RQ3 đưa mô hình vào hệ thống thời gian thực nhận CSV, PCAP hoặc lưu lượng bắt trực tiếp, tự trích 78 đặc trưng, dự đoán, giải thích bằng SHAP và cho phép LIME theo yêu cầu. Đặc trưng do bộ trích của hệ thống tính đã được đối chiếu với tshark và khớp về số gói, số cờ FIN, cửa sổ nhận ban đầu và thời lượng, và dự đoán lại ngoại tuyến cho kết quả giống hệt dữ liệu đã lưu, nên lỗi báo nhầm không nằm ở mã trích hay mã dự đoán."));
c.push(P("Khi chạy với lưu lượng ngoài tập huấn luyện, hệ thống báo DoS Hulk cho các kết nối HTTP bình thường. Phân tích cây quyết định cho thấy mô hình gán Hulk khi đồng thời cờ FIN từ 1 trở lên, Fwd Pkt Len Max từ 66 trở lên và Fwd Seg Size Min dưới 32. Trong 2,8 triệu dòng train có 445 dòng thỏa cả ba điều kiện, và cả 445 dòng đều là Hulk, không có dòng Benign nào. Ngưỡng của vùng này được đọc từ cấu hình hệ thống (hulk_fin_hint) và được dùng nhất quán ở các phần sau."));

// ================= 4. BÀI BÁO =================
c.push(H1("4. Các bài báo đã công bố nói gì về lỗi của bộ dữ liệu"));
c.push(P("Mục này lấy nguồn từ hai trang tài liệu của nhóm tác giả tại KU Leuven, gồm trang tài liệu mở rộng của bài WTMC 2021 và trang bổ trợ của bài CNS 2022. Tệp PDF của bài WTMC 2021 không trích được văn bản, nên các chi tiết sau đây là nội dung các trang tóm tắt đó, và cần đối chiếu với bản đầy đủ trước khi trích dẫn từng ý."));
c.push(P("Engelen, Rimmer và Joosen (WTMC 2021) khảo sát bộ CIC-IDS-2017 và mô tả các lỗi sau, trong đó ba lỗi đầu liên quan trực tiếp đến kết quả của nhóm."));
c.push(B("Lỗi TCP appendices. CICFlowMeter kết thúc flow ở gói FIN đầu tiên, trái với đặc tả TCP. Các gói còn lại của kết nối tạo thành những flow nhỏ phụ, có thể bị gán nhãn sai, và sau một lần timeout flow kế tiếp có thể bị đảo chiều."));
c.push(B("Lỗi đếm cờ TCP. Số cờ chỉ nhận giá trị 0 hoặc 1 vì công cụ chỉ ghi nhận cờ ở gói đầu của flow. Tác giả công cụ đã sửa lỗi này vào tháng 10 năm 2019."));
c.push(B("Lỗi cài đặt DoS Hulk. Công cụ gửi tiêu đề Connection: close thay vì Keep-Alive, nên máy chủ đóng kết nối ngay sau mỗi yêu cầu. Các tác giả khuyên không dùng Hulk làm lớp tấn công trong IDS dựa trên flow, vì mô hình có thể học thói quen của công cụ thay vì hành vi DoS."));
c.push(B("Cấu hình máy chủ nạn nhân, ví dụ KeepAliveTimeout 5 giây, làm yếu một số tấn công và tạo nguy cơ học đường tắt theo cấu hình."));
c.push(B("Cửa sổ thời gian gán nhãn trên trang web của bộ dữ liệu không đủ để tái tạo chính xác việc gán nhãn, và các tác giả đã chỉnh tay để khớp số lượng flow gốc."));
c.push(P("Liu, Engelen, Lynar, Essam và Joosen (CNS 2022) mở rộng việc khảo sát sang CSE-CIC-IDS-2018, mô tả nhiều lỗi chưa từng được ghi nhận trong khâu dàn dựng tấn công, tạo đặc trưng, tài liệu và gán nhãn, và công bố các bản dữ liệu đã sửa lỗi cùng công cụ CICFlowMeter đã sửa. Trang bổ trợ của bài này không nêu chi tiết lỗi FIN, mà dẫn sang các trang riêng. Vì vậy việc lỗi TCP appendices có tồn tại trong bản CSV gốc của CSE-CIC-IDS-2018 hay không là điều nhóm chưa kiểm chứng trực tiếp, và chỉ được suy ra từ việc hai bộ dữ liệu cùng dùng CICFlowMeter-V3."));
c.push(P("Tệp CSE-CIC-IDS2018 improved trong thư mục dataset có cột Attempted Category và các nhãn Attempted, khớp với mô tả bản sửa lỗi của nhóm tác giả. Nguồn tải chính xác của tệp này chưa được ghi lại trong dự án và cần được xác nhận trước khi nộp bài."));

// ================= 5. KIỂM TOÁN =================
c.push(H1("5. Kiểm toán dữ liệu: bản gốc và bản improved"));
c.push(P(`Nhóm đếm lại cờ FIN bằng một chương trình đọc toàn bộ chín ngày có mặt ở cả hai bản, chỉ xét flow giao thức TCP và dùng đúng các ngưỡng của mô hình. Ngày Tuesday-20-02 không có trong thư mục CSV gốc nên bị loại khỏi phép so sánh. Bản gốc có ${nf(A.flags.flows_all)} flow, trong đó ${nf(A.flags.flows_tcp)} flow TCP. Bản improved có ${nf(A.imp9_benign.tcp_flows)} flow Benign TCP trong cùng chín ngày, hơn bảy lần bản gốc, và chưa có lời giải thích cho chênh lệch này.`));
c.push(T([4400, 2700, 2538], ["Chỉ tiêu trên flow Benign TCP (9 ngày chung)", "CSV gốc", "Bản improved"], [
  ["Số flow", nf(A.orig_benign.tcp_flows), nf(A.imp9_benign.tcp_flows)],
  ["Mang cờ FIN", nf(A.orig_benign.fin) + " (" + pct(A.orig_benign.fin, A.orig_benign.tcp_flows) + ")", nf(A.imp9_benign.fin) + " (" + pct(A.imp9_benign.fin, A.imp9_benign.tcp_flows) + ")"],
  ["FIN và có dữ liệu", nf(A.orig_benign.fin_data_gt0) + " (" + pct(A.orig_benign.fin_data_gt0, A.orig_benign.tcp_flows, 4) + ")", nf(A.imp9_benign.fin_data_gt0) + " (" + pct(A.imp9_benign.fin_data_gt0, A.imp9_benign.tcp_flows) + ")"],
  ["FIN và dữ liệu từ 66 byte", nf(A.orig_benign.fin_data_ge_min), nf(A.imp9_benign.fin_data_ge_min) + " (" + pct(A.imp9_benign.fin_data_ge_min, A.imp9_benign.tcp_flows) + ")"],
  ["Nằm trong vùng ba điều kiện của Hulk", nf(A.orig_benign.zone), nf(A.imp9_benign.zone) + " (" + pct(A.imp9_benign.zone, A.imp9_benign.tcp_flows) + ")"],
  ["Hulk mang cờ FIN", nf(A.orig_hulk.fin) + " trên " + nf(A.orig_hulk.tcp_flows) + " (" + pct(A.orig_hulk.fin, A.orig_hulk.tcp_flows) + ")", nf(A.imp9_hulk.fin) + " trên " + nf(A.imp9_hulk.tcp_flows) + " (" + pct(A.imp9_hulk.fin, A.imp9_hulk.tcp_flows) + ")"],
  ["Hulk nằm trong vùng ba điều kiện", nf(A.orig_hulk.zone) + " trên " + nf(A.orig_hulk.tcp_flows), nf(A.imp9_hulk.zone) + " trên " + nf(A.imp9_hulk.tcp_flows)],
  ["Giá trị cờ FIN quan sát được", "Chỉ 0 hoặc 1", "Nhận cả 2, 3, 4 và lớn hơn"],
]));
c.push(cap("Bảng 3. Kiểm toán cờ FIN trên flow Benign TCP. Mã và kết quả từng ngày nằm trong RQ4_Retrain_Compare/results."));
c.push(IMG("hinh2_fin_benign.png", 560, 253));
c.push(cap("Hình 1. Tỷ lệ flow Benign TCP mang cờ FIN trong CSV gốc và bản improved."));
c.push(P(`Trong CSV gốc, cờ FIN bằng 0 ở ${pct(A.flags.flows_tcp - A.flags.tcp_fin_ge1, A.flags.flows_tcp)} flow TCP, và chỉ ${pct(A.flags.tcp_ge4pkts_each_way_fin, A.flags.tcp_ge4pkts_each_way)} trong ${nf(A.flags.tcp_ge4pkts_each_way)} flow có từ 4 gói trở lên ở mỗi chiều, tức những kết nối trông khá đầy đủ, mang cờ FIN. Theo giao thức TCP, một kết nối hoàn chỉnh thường kết thúc bằng FIN, nên tỷ lệ này rất thấp. Cờ ACK cũng chỉ có ở ${pct(A.flags.tcp_ack_ge1, A.flags.flows_tcp)} flow TCP dù hầu như mọi kết nối đều có gói ACK. Cả năm cột cờ trong CSV gốc chỉ nhận 0 hoặc 1. Các dấu hiệu này phù hợp với mô tả lỗi đếm cờ và lỗi cắt flow của CICFlowMeter-V3, nhưng chưa phải bằng chứng trực tiếp vì thiếu PCAP gốc.`));
c.push(P("Cách giải thích phù hợp với số liệu như sau. Vì flow bị cắt ở gói FIN đầu tiên và cờ chỉ được ghi nhận ở gói đầu, phần lớn flow mang FIN trong bản gốc là những phần đuôi rỗng của kết nối. Kết nối Benign có dữ liệu bị ghi nhận không có FIN. Riêng Hulk dùng Connection: close nên FIN đi cùng dữ liệu. Giải thích này khớp các con số nhưng là giả thuyết."));

c.push(H2("5.1 Hulk của hai bản là hai kiểu lưu lượng khác nhau"));
const HP = fs.readFileSync(path.join(ROOT, "results", "hulk_profile_friday16.csv"), "utf8").replace(/^﻿/, "").trim().split("\n").map((l) => l.split(","));
const hh = HP[0];
const col = (n) => hh.indexOf(n);
const rowsHP = HP.slice(1).map((r) => [r[0] + ", " + r[1], nf(+r[col("so_flow_tcp")]), nf(+r[col("Tot Fwd Pkts")]), nf(+r[col("Fwd Pkt Len Max")]), nf(+r[col("Init Fwd Win Byts")]), nf(+r[col("Fwd Seg Size Min")]), nf(+r[col("FIN Flag Cnt")])]);
c.push(T([2338, 1300, 1100, 1300, 1300, 1200, 1100], ["Nhóm (ngày Friday-16, TCP)", "Số flow", "Tot Fwd Pkts", "Fwd Pkt Len Max", "Init Fwd Win Byts", "Fwd Seg Size Min", "FIN Flag Cnt"], rowsHP));
c.push(cap("Bảng 4. Trung vị đặc trưng của flow Hulk và Benign. Mã nằm ở scripts/12_hulk_profile.py."));
c.push(P("Hulk trong CSV gốc có trung vị 2 gói chiều đi, Fwd Pkt Len Max bằng 0 và không có FIN, tức phần lớn là những flow rất ngắn không mang dữ liệu. Hulk trong bản improved là kết nối HTTP đầy đủ với 5 gói chiều đi, có dữ liệu và có FIN. Cửa sổ nhận ban đầu chênh nhau cả trăm lần. Hai bản vì vậy mô tả cùng một công cụ tấn công bằng hai kiểu đặc trưng khác nhau, và một mô hình học từ bản này không thể nhận ra Hulk của bản kia."));

c.push(H2("5.2 Đặc trưng và nhãn"));
c.push(P("Cả 78 đặc trưng của mô hình đều có tương ứng trong bản improved, trong đó 48 đặc trưng chỉ khác tên và được ánh xạ bằng bảng results/mapping_features.csv. Bản improved có thêm 5 cột mà mô hình không dùng, gồm Fwd RST Flags, Bwd RST Flags, ICMP Code, ICMP Type và Total TCP Flow Time. Tập nhãn thì không giống nhau. Bản improved không có DoS attacks-SlowHTTPTest, và FTP-BruteForce chỉ có dạng Attempted. Các nhãn Attempted (tấn công thất bại) bị bỏ ra khỏi mọi thí nghiệm. Bốn loại Infiltration được gộp lại thành một lớp. Kết quả là không gian nhãn chung gồm 13 lớp, và bảng ánh xạ đầy đủ nằm ở results/mapping_labels_improved.csv."));

// ================= 6. THIẾT KẾ =================
c.push(H1("6. Thiết kế thực nghiệm mới"));
c.push(H2("6.1 Nguyên tắc làm đúng như mô hình cũ"));
c.push(T([2300, 3669, 3669], ["Hạng mục", "Mô hình cũ (RQ1, RQ2)", "Mô hình mới (RQ4)"], [
  ["Thuật toán và tham số", "XGBClassifier, 100 cây, độ sâu 8, learning rate 0,08, hist, seed 42", "Giống hệt, không quét lại tham số"],
  ["Đặc trưng", "78 đặc trưng float32, không Timestamp, không IP", "Giống hệt, đổi tên theo bảng ánh xạ"],
  ["Lấy mẫu", "3,5 triệu dòng, 70% Benign và 30% tấn công, giữ 100% lớp hiếm", "Cùng công thức, số mẫu mỗi lớp theo bộ cũ và bị chặn bởi số flow sẵn có"],
  ["Chia dữ liệu", "Stratified 80/20", "Stratified 80/20, cộng thêm bộ giữ riêng theo thời gian"],
  ["Chỉ số", "Accuracy, Macro P, R, F1, FPR, FNR bằng ids_detection_metrics", "Giống hệt, cùng hàm"],
  ["Giải thích", "SHAP toàn cục và từng flow, LIME khóa cấu hình, đồng thuận, cổng chất lượng, trung thành, miền tri thức, nhóm lỗi", "Chạy lại cùng mã, LIME dùng đúng cấu hình đã khóa ở RQ2"],
]));
c.push(cap("Bảng 5. So sánh quy trình cũ và mới."));
c.push(P("Hai giai đoạn của RQ2 được xử lý khác. GĐ5 (chọn lại cấu hình LIME trên tập dev) không chạy lại, và cấu hình đã khóa của RQ2 được dùng nguyên vẹn theo yêu cầu giữ nguyên cấu hình. GĐ9 (độ ổn định và chịu nhiễu) được bỏ qua theo yêu cầu của người dùng, và các số liệu GĐ9 của M0 vẫn có trong RQ2."));

c.push(H2("6.2 Các mô hình"));
c.push(T([1100, 3500, 5038], ["Mã", "Dữ liệu huấn luyện", "Vai trò"], [
  ["M0", "Train cũ, 15 lớp, 2.800.000 dòng", "Mô hình RQ1, giữ nguyên"],
  ["M0b", "Train cũ giới hạn 13 lớp chung, " + nf(Object.entries(D.composition).filter(([k]) => !["FTP-BruteForce", "DoS attacks-SlowHTTPTest"].includes(k)).reduce((s, [, r]) => s + r.old_train, 0)) + " dòng", "Dữ liệu cũ nhưng cùng không gian nhãn với M1, để so sánh công bằng"],
  ["M1", "Mẫu từ bản improved, " + nf(Object.values(D.composition).reduce((s, r) => s + r.d2_train, 0)) + " dòng", "Dữ liệu đã sửa lỗi"],
  ["M2", "Train cũ cộng 10.000 flow Benign trong vùng ba điều kiện lấy từ improved", "Tách thiếu mẫu khỏi khác định nghĩa đặc trưng. Hoãn theo yêu cầu người dùng, mã đã sẵn sàng"],
]));
c.push(cap("Bảng 6. Các mô hình trong RQ4. Mỗi mô hình có file .pkl và bộ mã hóa nhãn riêng trong thư mục models, không ghi đè mô hình RQ1."));
c.push(P("M0b tồn tại vì hai lớp SlowHTTPTest và FTP-BruteForce không có ở bản improved. Nếu so M0 15 lớp với M1 13 lớp thì hai bên có số đáp án khác nhau, nên M0b được huấn luyện trên chính dữ liệu cũ, bỏ hai lớp đó (khoảng 21.000 dòng), với cùng tham số."));

c.push(H2("6.3 Dữ liệu và các bộ đánh giá"));
const comp = D.composition;
const classes = Object.keys(comp);
c.push(T([3000, 1560, 1560, 1760, 1758], ["Lớp", "Train cũ", "Train M1", "Test M1", "Giữ riêng theo thời gian"],
  classes.map((k) => [k, nf(comp[k].old_train), nf(comp[k].d2_train), nf(comp[k].d2_test), nf(comp[k].t2_holdout)])));
c.push(cap("Bảng 7. Thành phần các bộ dữ liệu. Hulk có đúng 155.042 dòng train ở cả hai bộ."));
c.push(P(`Bản improved được quét một lần duy nhất (khoảng 35 GB, ${nf(Object.values(D.scan.raw_label_counts).reduce((s, v) => s + v, 0))} flow), giữ toàn bộ flow của 12 lớp tấn công chung và 7% Benign ngẫu nhiên, chỉ một flow Benign bị bỏ vì giá trị NaN. Số mẫu mỗi lớp tấn công lấy theo thành phần bộ cũ, bị chặn bởi số flow có sẵn. Ví dụ SQL Injection chỉ có 39 flow nên mục tiêu là 30 sau khi trừ phần giữ riêng. Benign được lấy sao cho giữ tỷ lệ 70% và 30%.`));
c.push(P("Để tránh lỗi test trùng train, mỗi lớp được sắp theo thời gian. Phần mẫu chỉ lấy từ 78% đầu của lớp, 2% tiếp theo bị bỏ làm khoảng đệm, và 20% cuối được giữ riêng thành bộ giữ riêng theo thời gian, nhờ đó một kết nối không nằm ở cả hai phía."));
c.push(T([1500, 4300, 3838], ["Mã", "Nội dung", "Ghi chú"], [
  ["T1", "Test cũ, giới hạn 13 lớp (694.758 dòng), và bản bỏ dòng trùng với train cũ", "Trong phân phối của M0 và M0b"],
  ["T2a", "Test stratified 20% của bản improved (" + nf(D.leak.d2_test_rows) + " dòng), và bản bỏ trùng", "Trong phân phối của M1"],
  ["T2b", "Bộ giữ riêng theo thời gian (" + nf(D.leak.t2_holdout_rows) + " dòng), và bản bỏ trùng", "Trong phân phối của M1"],
  ["T3", nf(T3.t3_flows) + " flow realtime của máy người dùng, nguồn feeder_live, bỏ multicast và flow PCAP", "Nhãn Benign do người dùng xác nhận bằng lời ngày 26/10/2026, chưa có chi tiết hoạt động từng phiên"],
]));
c.push(cap("Bảng 8. Các bộ đánh giá."));
c.push(P(`Về trùng lặp, ${nf(D.leak.d2_test_rows_also_in_train)} trên ${nf(D.leak.d2_test_rows)} dòng test của M1 (${pct(D.leak.d2_test_rows_also_in_train, D.leak.d2_test_rows, 1)}) và ${nf(D.leak.t2_holdout_rows_also_in_train)} trên ${nf(D.leak.t2_holdout_rows)} dòng giữ riêng (${pct(D.leak.t2_holdout_rows_also_in_train, D.leak.t2_holdout_rows, 1)}) có 78 đặc trưng giống hệt một dòng trong train. Bộ cũ có ${pct(D.leak.old_test_rows_also_in_train, D.leak.old_test_rows, 2)}. Các công cụ tấn công trong lab gửi nhiều gói giống hệt nhau nên flow trùng xuất hiện tự nhiên khi chia ngẫu nhiên. Nhóm giữ nguyên cách chia để so sánh cùng điều kiện với RQ1, và bổ sung mọi bản bỏ trùng để kết luận không phụ thuộc vào dòng trùng.`));

// ================= 7. KẾT QUẢ =================
c.push(H1("7. Kết quả"));
c.push(H2("7.1 Huấn luyện theo quy trình RQ1"));
c.push(T([3400, 2080, 2080, 2078], ["Chỉ số trên test của chính mô hình", "M0 (cũ, 15 lớp)", "M0b (cũ, 13 lớp)", "M1 (improved)"], [
  ["Accuracy", pc(R.M0.acc), pc(R.M0b.acc), pc(R.M1.acc)],
  ["Macro Precision", pc(R.M0.prec), pc(R.M0b.prec), pc(R.M1.prec)],
  ["Macro Recall", pc(R.M0.rec), pc(R.M0b.rec), pc(R.M1.rec)],
  ["Macro F1", pc(R.M0.f1), pc(R.M0b.f1), pc(R.M1.f1)],
  ["FPR của Benign", pc(R.M0.fpr, 4), pc(R.M0b.fpr, 4), pc(R.M1.fpr, 4)],
  ["FNR của tấn công", pc(R.M0.fnr, 4), pc(R.M0b.fnr, 4), pc(R.M1.fnr, 4)],
]));
c.push(cap("Bảng 9. Chỉ số theo quy trình RQ1. Mỗi mô hình được đo trên test cùng phân phối với nó, nên các cột không so sánh trực tiếp được."));
c.push(P("M0b gần giống M0 và cao hơn một chút, vì bỏ hai lớp khó (SlowHTTPTest và FTP-BruteForce). M1 đạt gần tuyệt đối. Mục 8 giải thích vì sao con số này không nên được hiểu là chất lượng ngoài đời."));

c.push(H2("7.2 Đánh giá chéo"));
c.push(P("Mỗi mô hình được đo trên mọi bộ test, với cùng một bộ chỉ số. Bảng 10 chỉ nêu các bản đã bỏ dòng trùng, và bản đầy đủ nằm ở results/cross_evaluation.csv."));
const sets = [["T1_test_cu_sach", "T1 test cũ"], ["T2a_improved_stratified_sach", "T2a test improved"], ["T2b_improved_thoi_gian_sach", "T2b giữ riêng theo thời gian"], ["T3_realtime_benign", "T3 realtime (Benign)"]];
const rowsX = [];
for (const [k, nm] of sets) {
  for (const m of ["M0", "M0b", "M1"]) {
    const r = cr(m, k);
    const hk = r.hulk_n > 0 ? pc(r.hulk_recall_pct, 2) : "không có";
    const zn = r.benign_zone_n > 0 ? pc(r.fpr_zone_pct, 1) + " (" + nf(r.benign_zone_n) + ")" : "không có";
    rowsX.push([nm, m, nf(r.n), pc(r.fpr_pct, 2), zn, hk, r.macro_f1_13_pct == null ? "không áp dụng" : pc(r.macro_f1_13_pct, 1)]);
  }
}
c.push(T([2050, 700, 1000, 1300, 1700, 1388, 1500], ["Bộ test", "Mô hình", "Số flow", "Benign báo tấn công", "Báo nhầm trong vùng Hulk (số flow)", "Recall Hulk", "Macro F1 13 lớp"], rowsX));
c.push(cap("Bảng 10. Đánh giá chéo trên các bộ test đã bỏ dòng trùng với train."));
c.push(IMG("hinh1_benign_bao_nham.png", 560, 280));
c.push(cap("Hình 2. Tỷ lệ Benign bị báo thành tấn công theo mô hình và bộ test."));
const m0z = cr("M0", "T2a_improved_stratified_sach");
c.push(P(`Trên dữ liệu improved có nhãn thật, M0 báo ${pc(m0z.fpr_pct, 1)} flow Benign thành tấn công, và trong vùng ba điều kiện của Hulk thì ${pc(m0z.fpr_zone_pct, 2)} trong ${nf(m0z.benign_zone_n)} flow bị báo Hulk. Ngoài vùng này tỷ lệ chỉ ${pc(m0z.fpr_outside_zone_pct, 3)}. Đây là bằng chứng ở quy mô gần một trăm nghìn flow có nhãn thật, không phụ thuộc vào việc tự đánh giá lưu lượng. M1 gần như không báo nhầm Benign trên mọi bộ improved và trên lưu lượng thật, nhưng không dùng được cho dữ liệu cũ. Trên test cũ M1 chỉ nhận ${pc(cr("M1", "T1_test_cu_sach").hulk_recall_pct, 2)} số flow Hulk, vì Hulk của hai bản là hai kiểu lưu lượng khác nhau như Bảng 4 cho thấy.`));
c.push(P(`Chiều ngược lại cũng đáng chú ý. M0 nhận ${pc(m0z.hulk_recall_pct, 2)} flow Hulk của bản improved, nhưng nhiều khả năng nhờ dấu hiệu FIN, vì ${pct(A.imp9_hulk.fin, A.imp9_hulk.tcp_flows, 2)} flow Hulk của bản improved mang FIN. Điểm này làm cho độ nhận Hulk cao của M0 không phản ánh khả năng nhận diện hành vi tấn công.`));

c.push(H2("7.3 Trên lưu lượng thật của máy người dùng"));
const t3m0 = cr("M0", "T3_realtime_benign"), t3m0b = cr("M0b", "T3_realtime_benign"), t3m1 = cr("M1", "T3_realtime_benign");
c.push(T([3200, 2146, 2146, 2146], ["Trên " + nf(T3.t3_flows) + " flow Benign realtime", "M0", "M0b", "M1"], [
  ["Báo thành tấn công", pc(t3m0.fpr_pct, 1), pc(t3m0b.fpr_pct, 1), pc(t3m1.fpr_pct, 1)],
  ["Báo thành Hulk", pc(t3m0.benign_called_hulk_pct, 1), pc(t3m0b.benign_called_hulk_pct, 1), pc(t3m1.benign_called_hulk_pct, 1)],
  ["Trong vùng ba điều kiện (" + nf(T3.t3_zone_flows) + " flow), báo tấn công", pc(t3m0.fpr_zone_pct, 0), pc(t3m0b.fpr_zone_pct, 0), pc(t3m1.fpr_zone_pct, 0)],
  ["Ngoài vùng, báo tấn công", pc(t3m0.fpr_outside_zone_pct, 2), pc(t3m0b.fpr_outside_zone_pct, 2), pc(t3m1.fpr_outside_zone_pct, 2)],
]));
c.push(cap("Bảng 11. Kết quả trên flow realtime, nhãn Benign do người dùng xác nhận."));
const cf = T3.M0_counterfactual_all784;
c.push(P(`Với M0, SHAP của lớp Hulk trên ${nf(T3.t3_zone_flows)} flow trong vùng cho FIN Flag Cnt trung bình ${nf(T3.M0.mean_shap_of_predicted_class_top8["FIN Flag Cnt"], 2)} và Fwd Pkt Len Max ${nf(T3.M0.mean_shap_of_predicted_class_top8["Fwd Pkt Len Max"], 2)}, hai đóng góp dương lớn nhất. Giá trị của FIN trùng với con số đã đo ở các PCAP trước đó. Thử phản thực trên ${nf(T3.t3_flows)} flow cho kết quả ở Bảng 12.`));
c.push(T([4200, 2719, 2719], ["Thay đổi đặc trưng (M0)", "Flow còn bị báo tấn công", "Số nhãn bị đổi"], [
  ["Không đổi", nf(T3.M0_all784_attack_flagged), "0"],
  ["FIN Flag Cnt bằng 0", nf(cf["FIN=0"].attack_flagged), nf(cf["FIN=0"].changed_labels)],
  ["Fwd Pkt Len Max bằng 0", nf(cf["Fwd Pkt Len Max=0"].attack_flagged), nf(cf["Fwd Pkt Len Max=0"].changed_labels)],
  ["Fwd Seg Size Min bằng 32", nf(cf["Fwd Seg Size Min=32"].attack_flagged), nf(cf["Fwd Seg Size Min=32"].changed_labels)],
  ["Init Fwd Win Byts bằng 64240", nf(cf["Init Fwd Win Byts=64240"].attack_flagged), nf(cf["Init Fwd Win Byts=64240"].changed_labels)],
  ["Dst Port bằng 80", nf(cf["Dst Port=80"].attack_flagged), nf(cf["Dst Port=80"].changed_labels)],
]));
c.push(cap("Bảng 12. Thử phản thực của M0 trên flow realtime."));
c.push(P("Đặt FIN bằng 0 hoặc Fwd Pkt Len Max bằng 0 làm 148 flow trong vùng đổi nhãn và chỉ còn 3 đến 4 trên 784 flow bị báo tấn công, còn đổi cửa sổ nhận hoặc cổng đích gần như không đổi nhãn nào. Tức là cảnh báo sai của M0 do một tổ hợp cụ thể gồm FIN, độ dài dữ liệu và kích thước header, đúng như phân tích cây quyết định. Phép thử này đo cách M0 quyết định, không chứng minh M0 sai nếu bỏ đặc trưng, vì các flow này được xác nhận là Benign độc lập."));
c.push(P("M1 gán Benign cho cả 148 flow này. Đặc trưng đóng góp lớn nhất cho quyết định của M1 trên các flow này là Init Bwd Win Byts, với SHAP trung bình " + nf(T3.M1.mean_shap_of_predicted_class_top8["Init Bwd Win Byts"], 2) + ". Đây lại là một đặc trưng cửa sổ nhận, tức gắn với môi trường, nên M1 đúng trên lưu lượng thật nhưng chưa chắc vì lý do hành vi. Điều này cần được ghi rõ trong bài báo."));

c.push(H2("7.4 SHAP và LIME của M1 so với M0"));
c.push(P("Chuỗi giải thích của RQ2 được chạy lại nguyên vẹn cho M1, trừ GĐ5 và GĐ9 như đã nêu. Bảng 13 so sánh với M0."));
c.push(T([3638, 3000, 3000], ["Chỉ số", "M0 (RQ2)", "M1 (RQ4)"], [
  ["Số flow trong nhóm đánh giá", nf(X.M0.cohort), nf(X.M1.cohort)],
  ["Số flow dự đoán sai trong nhóm lỗi", nf(X.M0.errors), nf(X.M1.errors)],
  ["Sai số cộng dồn SHAP lớn nhất", X.M0.additivity_max.toExponential(1).replace(".", ","), X.M1.additivity_max.toExponential(1).replace(".", ",")],
  ["Local R bình phương trung vị của LIME", nf(X.M0.lime_median_r2, 3), nf(X.M1.lime_median_r2, 3)],
  ["Flow LIME vượt cổng chất lượng 0,3", pc(100 * X.M0.lime_pass, 1), pc(100 * X.M1.lime_pass, 1)],
  ["Jaccard Top-5 giữa SHAP và LIME", nf(X.M0.jacc5, 3), nf(X.M1.jacc5, 3)],
  ["AUC comprehensiveness, SHAP", nf(X.M0.comp_shap, 3), nf(X.M1.comp_shap, 3)],
  ["AUC comprehensiveness, LIME", nf(X.M0.comp_lime, 3), nf(X.M1.comp_lime, 3)],
  ["SHAP thắng LIME tại k bằng 5", pc(100 * X.M0.win5, 1), pc(100 * X.M1.win5, 1)],
  ["F1 miền tri thức bản chặt, SHAP và LIME", nf(X.M0.dom_shap_strict, 3) + " và " + nf(X.M0.dom_lime_strict, 3), nf(X.M1.dom_shap_strict, 3) + " và " + nf(X.M1.dom_lime_strict, 3)],
  ["Tỷ lệ đặc trưng môi trường trong Top-5 của flow sai", pc(100 * X.M0.err_env, 1), pc(100 * X.M1.err_env, 1)],
]));
c.push(cap("Bảng 13. Kết quả giải thích của M0 và M1 theo cùng một quy trình."));
c.push(P(`Kết luận về phương pháp giữ nguyên. SHAP trung thành hơn LIME ở cả hai mô hình với AUC comprehensiveness ${nf(X.M1.comp_shap, 2)} so với ${nf(X.M1.comp_lime, 2)} ở M1, và SHAP thắng ở ${pc(100 * X.M1.win5, 0)} số flow. Hai phương pháp đồng ý với nhau nhiều hơn mức ngẫu nhiên nhưng vẫn thấp. LIME của M1 đạt cổng chất lượng ở ít flow hơn M0 (${pc(100 * X.M1.lime_pass, 1)} so với ${pc(100 * X.M0.lime_pass, 1)}). Nhóm lỗi của M1 chỉ có ${nf(X.M1.errors)} flow nên các so sánh trên nhóm lỗi chỉ mang tính tham khảo.`));
c.push(P(`SHAP toàn cục của M1 cho lớp Hulk vẫn đặt ${X.M1.top5_hulk[0][0]} (${nf(X.M1.top5_hulk[0][1], 2)}) và ${X.M1.top5_hulk[1][0]} (${nf(X.M1.top5_hulk[1][1], 2)}) lên đầu, tức M1 vẫn nhận Hulk chủ yếu qua đặc trưng môi trường, dù không còn dùng cờ FIN. Với lớp Benign, đặc trưng đứng đầu của M1 là ${X.M1.top5_benign[0][0]} (${nf(X.M1.top5_benign[0][1], 2)}). Dữ liệu sửa lỗi bỏ được đường tắt FIN nhưng không bỏ được đường tắt môi trường.`));

// ================= 8. CHẨN ĐOÁN =================
c.push(H1("8. Vì sao M1 đạt gần 100%"));
const dg = D.diag;
c.push(P("Điểm của M1 trên dữ liệu improved cao đến mức cần kiểm tra trước khi tin. Nhóm kiểm tra ba khả năng."));
c.push(T([2400, 3800, 3438], ["Giả thuyết", "Kiểm tra", "Kết quả"], [
  ["Test có dòng giống hệt train", "Bỏ " + nf(dg.M1_test_stratified_khong_trung.removed) + " dòng trùng rồi đo lại", "Macro F1 " + pc(dg.M1_test_stratified_khong_trung.macro_f1) + ", không đổi so với " + pc(R.M1.f1)],
  ["Chia ngẫu nhiên làm lộ dữ liệu", "Đo trên bộ giữ riêng theo thời gian đã bỏ " + nf(dg.M1_holdout_thoi_gian_khong_trung.removed) + " dòng trùng", "Macro F1 " + pc(dg.M1_holdout_thoi_gian_khong_trung.macro_f1) + ", vẫn rất cao"],
  ["Mô hình chỉ dựa vài đặc trưng môi trường", "Huấn luyện lại không có Dst Port, Protocol, hai cửa sổ nhận ban đầu và Fwd Seg Size Min", "Macro F1 " + pc(dg.M1_bo_dac_trung_moi_truong_test_stratified.macro_f1) + ", Hulk recall " + pc(dg.M1_bo_dac_trung_moi_truong_test_stratified.hulk_recall, 1)],
]));
c.push(cap("Bảng 14. Kiểm tra nguyên nhân điểm cao của M1 (scripts/09_diagnose_m1.py)."));
const imp = dg.importance_M1;
c.push(P(`Tổng gain của XGBoost cho thấy M1 dựa nhiều nhất vào Init Fwd Win Byts (${nf(imp["Init Fwd Win Byts"], 1)}%), Init Bwd Win Byts (${nf(imp["Init Bwd Win Byts"], 1)}%), Dst Port (${nf(imp["Dst Port"], 1)}%) và Fwd Seg Size Min (${nf(imp["Fwd Seg Size Min"], 1)}%), tổng khoảng ${nf(imp["Init Fwd Win Byts"] + imp["Init Bwd Win Byts"] + imp["Dst Port"] + imp["Fwd Seg Size Min"], 0)}%. Nhưng bỏ cả các đặc trưng này, mô hình vẫn đạt Macro F1 gần như cũ. Điều đó nghĩa là điểm cao không phụ thuộc vào vài đặc trưng cụ thể mà đến từ việc các lớp vốn rất dễ tách trong dữ liệu improved.`));
c.push(P(`Giải thích phù hợp nhất với số liệu là mỗi loại tấn công trong lab do một công cụ chạy từ vài máy, nên dấu vết rất nhất quán, và bộ giữ riêng theo thời gian vẫn thuộc cùng chiến dịch tấn công trong cùng phòng lab. Bản improved cũng đã sửa nhãn và cách tách flow, nên có thể ít flow mơ hồ hơn bản gốc, nơi mô hình cũ chỉ đạt Macro F1 ${pc(R.M0.f1, 1)}. Vì vậy điểm trên bộ test cùng nguồn đo khả năng nhận ra chiến dịch trong lab, không đo khả năng phát hiện tấn công ngoài đời. Bằng chứng rõ nhất là M1 gần như không nhận ra Hulk của bộ cũ.`));

// ================= 9. THẢO LUẬN =================
c.push(H1("9. Thảo luận"));
c.push(P("Câu hỏi bộ dữ liệu cũ thiếu gì có câu trả lời cụ thể hơn sau thực nghiệm này. Bản CSV gốc gần như không có Benign nào vừa đóng bằng FIN vừa mang dữ liệu, trong khi đó là hơn một phần ba flow Benign TCP ở bản đã sửa lỗi. Mô hình học từ bản gốc đã gán nhãn Hulk cho toàn bộ vùng này, và điều đó được kiểm chứng ở ba cấp độ độc lập gồm " + nf(cr("M0", "T2a_improved_stratified_sach").benign_zone_n) + " flow Benign trong vùng ở bộ test improved, " + nf(cr("M0", "T2b_improved_thoi_gian_sach").benign_zone_n) + " flow ở bộ giữ riêng theo thời gian, và " + nf(T3.t3_zone_flows) + " flow realtime do người dùng xác nhận."));
c.push(P("Thực nghiệm cũng cho thấy việc sửa dữ liệu không giải quyết hết vấn đề. Mô hình M1 loại bỏ được báo nhầm FIN nhưng vẫn dựa nhiều vào đặc trưng môi trường như cửa sổ nhận ban đầu và kích thước header tối thiểu. Những đặc trưng này khác nhau giữa các mạng, nên M1 có thể thất bại ở một môi trường khác dù đúng ở máy của người dùng. Đây cũng là điều Engelen và cộng sự cảnh báo khi nói về nguy cơ học đường tắt theo cấu hình lab."));
c.push(P("Với giải thích, SHAP đóng vai trò công cụ chẩn đoán trong cả hai mô hình. Nó chỉ ra FIN và Fwd Pkt Len Max ở M0, và chỉ ra các đặc trưng cửa sổ nhận ở M1, và kết quả của nó được kiểm chứng bằng cấu trúc cây và thử phản thực. LIME kém tin cậy hơn, đạt cổng chất lượng ở " + pc(100 * X.M1.lime_pass, 0) + " flow của M1 trong nhóm đánh giá, và theo kết quả RQ3 trước đó bị loại gần hết trên flow thật vì các flow này nằm quá xa dữ liệu nền mà LIME lấy mẫu quanh đó."));
c.push(H2("9.1 Những điều có thể và chưa thể kết luận"));
c.push(B("Có thể kết luận rằng dữ liệu train cũ không có Benign trong vùng ba điều kiện, rằng vùng này khớp các báo nhầm quan sát được, và rằng đặt FIN bằng 0 loại bỏ các báo nhầm đó ở M0."));
c.push(B("Có thể kết luận rằng bản CSV gốc gần như không có Benign mang FIN và dữ liệu, trong khi bản improved có hơn một phần ba."));
c.push(B("Có thể kết luận rằng huấn luyện lại trên bản improved theo đúng quy trình cũ làm báo nhầm trên lưu lượng thật của máy người dùng từ " + pc(t3m0.fpr_pct, 1) + " xuống " + pc(t3m1.fpr_pct, 1) + "."));
c.push(B("Chưa thể kết luận rằng nguyên nhân duy nhất là thiếu mẫu Benign. Thí nghiệm M2 để tách thiếu mẫu khỏi khác định nghĩa đặc trưng đang được hoãn."));
c.push(B("Chưa thể kết luận rằng lỗi bắt nguồn từ công cụ trích xuất CICFlowMeter-V3, vì thiếu cặp PCAP và CSV gốc để kiểm chứng trực tiếp."));
c.push(B("Chưa thể kết luận gì về khả năng M1 phát hiện tấn công thật ngoài lab, vì chưa có dữ liệu tấn công độc lập."));

// ================= 10. HƯỚNG BÀI BÁO =================
c.push(H1("10. Hướng viết bài báo khoa học"));
c.push(H2("10.1 Câu chuyện"));
c.push(P("Bài báo bắt đầu từ một nghịch lý. Một mô hình phát hiện xâm nhập đạt hiệu năng nội bộ rất cao nhưng báo nhầm hàng loạt khi chạy trên lưu lượng thật. Câu hỏi đặt ra là điều gì che giấu lỗi trong phép đánh giá thông thường và giải thích mô hình có giúp tìm ra lỗi hay không."));
c.push(P("Phần tiếp theo kể quá trình truy tìm. SHAP chỉ vào cờ FIN. Phân tích cây quyết định cho ra một vùng ba điều kiện chỉ có Hulk trong dữ liệu train. Thử phản thực khẳng định vùng đó là thứ làm nhãn đổi. Kiểm toán dữ liệu cho thấy bản CSV gốc gần như không có Benign trong vùng này còn bản đã sửa lỗi có hơn một phần ba, và lỗi khớp với mô tả TCP appendices và cách đếm cờ sai của CICFlowMeter-V3 trong tài liệu của Engelen và cộng sự."));
c.push(P("Phần cuối kiểm chứng và rút bài học. Huấn luyện lại bằng dữ liệu đã sửa lỗi với đúng quy trình cũ làm báo nhầm biến mất, nhưng giải thích của mô hình mới cho thấy đường tắt môi trường vẫn còn, nên điểm cao trên dữ liệu cùng nguồn không đủ để tin. Bài học chung là phải đánh giá IDS bằng dữ liệu ngoài nguồn huấn luyện và dùng giải thích như một công cụ kiểm tra dữ liệu."));
c.push(P("Tên bài đề xuất bằng tiếng Việt là Khi độ chính xác nội bộ đánh lừa, dùng SHAP, LIME và kiểm tra phản thực để phát hiện lỗi cờ FIN trong bộ dữ liệu CSE-CIC-IDS2018. Tên tiếng Anh là When Internal Accuracy Misleads, Using SHAP, LIME and Counterfactual Checks to Expose a FIN-Flag Shortcut in CSE-CIC-IDS2018."));
c.push(H2("10.2 Vấn đề, mục tiêu và câu hỏi"));
c.push(P("Vấn đề là mô hình IDS học đường tắt từ khoảng trống hoặc lỗi của bộ dữ liệu mà các chỉ số nội bộ không phát hiện được. Mục đích là chỉ ra cách dùng giải thích và kiểm thử độc lập để phát hiện, xác nhận và giảm thiểu đường tắt đó. Các câu hỏi nghiên cứu gồm bốn câu."));
c.push(B("RQ1. Hiệu năng của mô hình thay đổi thế nào giữa tập kiểm thử nội bộ và dữ liệu độc lập có nhãn. Trả lời bằng Bảng 10 và 11."));
c.push(B("RQ2. SHAP, đường đi trong cây và phản thực có xác định được đặc trưng gây báo nhầm hay không, và LIME có đủ tin cậy để đối chiếu không. Trả lời bằng mục 7.3 và 7.4."));
c.push(B("RQ3. Bộ dữ liệu cũ khác bản đã sửa lỗi ở điểm nào liên quan đến vùng đặc trưng đó. Trả lời bằng mục 5."));
c.push(B("RQ4. Huấn luyện lại bằng dữ liệu đã sửa lỗi có giảm báo nhầm mà vẫn giữ khả năng nhận Hulk không. Trả lời một phần bằng mục 7.2, phần còn lại cần M2 và dữ liệu tấn công độc lập."));
c.push(H2("10.3 Tính chất nào của lời giải thích quan trọng nhất"));
c.push(P("Số liệu hiện có gợi ý rằng tính hợp lệ của lời giải thích quan trọng hơn mức độ dễ đọc. LIME cho lời giải thích gọn nhưng bị loại gần hết trên lưu lượng thật. Tiếp theo là khả năng kiểm chứng ngược, vì SHAP có giá trị chẩn đoán khi kết quả của nó truy lại được bằng đường đi trong cây, thống kê dữ liệu train và thử phản thực. Mức độ dễ đọc đứng sau hai tính chất trên. Kết luận này cần được củng cố bằng thí nghiệm kiểm tra LIME trực tiếp trên flow realtime của M1."));
c.push(H2("10.4 Đóng góp dự kiến"));
c.push(B("Bằng chứng thực nghiệm về khoảng cách giữa đánh giá nội bộ và hành vi của IDS trên lưu lượng thật."));
c.push(B("Quy trình chẩn đoán gồm SHAP, đường đi trong cây, thống kê dữ liệu train, phản thực và kiểm toán bộ dữ liệu."));
c.push(B("So sánh có kiểm soát giữa mô hình huấn luyện trên dữ liệu cũ và dữ liệu đã sửa lỗi, cùng quy trình và cùng cấu hình giải thích."));
c.push(H2("10.5 Việc còn lại trước khi nộp"));
c.push(T([700, 5700, 3238], ["STT", "Việc", "Mục đích"], [
  ["1", "Chạy M2, thêm 10.000 flow Benign trong vùng ba điều kiện vào train cũ", "Tách thiếu mẫu khỏi khác định nghĩa đặc trưng"],
  ["2", "Thu dữ liệu tấn công độc lập có nhãn, hoặc nêu rõ đây là hạn chế", "Đo khả năng phát hiện ngoài lab"],
  ["3", "Ghi nhật ký hoạt động chi tiết của các phiên realtime", "Củng cố nhãn Benign của T3"],
  ["4", "Xác nhận nguồn tải của bản improved và giải thích chênh lệch số flow", "Đảm bảo tài liệu tham khảo"],
  ["5", "Đọc bản đầy đủ bài WTMC 2021 và CNS 2022, đối chiếu các chi tiết đã trích", "Tránh trích sai"],
  ["6", "Chạy LIME trên flow realtime của M1 và đo tỷ lệ hợp lệ", "Củng cố kết luận về tính hợp lệ"],
]));
c.push(cap("Bảng 15. Các việc còn lại."));

// ================= 11. HẠN CHẾ =================
c.push(H1("11. Hạn chế"));
c.push(B("Nhãn Benign của bộ realtime dựa trên lời xác nhận bằng lời của người dùng, chưa có nhật ký hoạt động chi tiết từng phiên."));
c.push(B("Bộ realtime có 784 flow từ hai mạng (Wi-Fi nhà và điểm phát sóng điện thoại) trong một ngày, nên chưa đại diện cho nhiều môi trường."));
c.push(B("Chưa có dữ liệu tấn công độc lập, nên chưa đo được khả năng phát hiện tấn công của mô hình mới ngoài lab."));
c.push(B("Thí nghiệm M2 bị hoãn, nên chưa tách được hai nguyên nhân là thiếu mẫu và khác định nghĩa đặc trưng."));
c.push(B("Lỗi lịch sử của công cụ trích xuất chưa được kiểm chứng trực tiếp vì thiếu cặp PCAP và CSV gốc."));
c.push(B("Ngày Tuesday-20-02 không có trong CSV gốc nên không nằm trong phép kiểm toán so sánh."));
c.push(B("Hulk của CICFlowMeter-V3 có cài đặt lỗi theo tài liệu của Engelen và cộng sự, nên bài báo nên dùng Hulk như một ca nghiên cứu về học đường tắt, không dùng như bằng chứng khả năng phát hiện DoS nói chung."));
c.push(B("Cách chọn siêu tham số của RQ1 dựa trên điểm test của chính mô hình, và được giữ nguyên theo yêu cầu để so sánh cùng điều kiện."));

// ================= 12. TÁI LẬP =================
c.push(H1("12. Tái lập"));
c.push(P("Mã, kết quả và tài liệu nằm trong thư mục RQ4_Retrain_Compare. Các tập dữ liệu trung gian và file mô hình .pkl không được commit theo cấu hình của repo, nhưng mã và số liệu kết quả đều có trong git."));
c.push(T([2700, 6938], ["Tệp", "Nội dung"], [
  ["scripts/01_mapping_tables.py", "Bảng ánh xạ 78 đặc trưng và các nhãn giữa hai bản"],
  ["scripts/02_audit_orig_csv.py", "Kiểm toán cờ FIN trong CSV gốc"],
  ["scripts/03_build_improved_cache.py", "Quét bản improved một lần, kiểm toán FIN và lấy mẫu"],
  ["scripts/04_build_datasets.py", "Dựng train, test, bộ giữ riêng theo thời gian và dữ liệu thêm cho M2"],
  ["scripts/05_train_models.py", "Huấn luyện M0b, M1 (và M2) với tham số RQ1"],
  ["scripts/06_prepare_t3_realtime.py, 06b_confirm_t3.py", "Dựng bộ realtime T3 từ DB hệ thống"],
  ["scripts/07_evaluate_cross.py", "Đánh giá chéo, có bản bỏ trùng"],
  ["scripts/08_run_xai.py", "Chuỗi SHAP và LIME (GĐ0 đến GĐ13) cho một mô hình"],
  ["scripts/09_diagnose_m1.py", "Chẩn đoán điểm cao của M1"],
  ["scripts/10_t3_explain.py", "SHAP và phản thực trên flow realtime"],
  ["scripts/11_report_data.py, 12_hulk_profile.py", "Gom số liệu cho báo cáo và hồ sơ Hulk"],
  ["results/ và xai_runs/m1/", "Kết quả CSV, JSON và hình của mọi bước"],
]));
c.push(cap("Bảng 16. Các tệp chính."));

// ================= 13. THAM KHẢO =================
c.push(H1("13. Tài liệu tham khảo"));
c.push(P("Engelen, G., Rimmer, V., Joosen, W. (2021). Troubleshooting an Intrusion Detection Dataset, the CICIDS2017 Case Study. WTMC 2021. Trang tài liệu mở rộng tại intrusion-detection.distrinet-research.be/WTMC2021/extended_doc.html."));
c.push(P("Liu, L., Engelen, G., Lynar, T., Essam, D., Joosen, W. (2022). Error Prevalence in NIDS datasets, A Case Study on CIC-IDS-2017 and CSE-CIC-IDS-2018. IEEE Conference on Communications and Network Security (CNS), trang 254 đến 262. Trang bổ trợ tại intrusion-detection.distrinet-research.be/CNS2022/."));
c.push(P("Số liệu nội bộ lấy từ RQ1_Model_Training_xboost/results, RQ2/runs/20261009/gd13_report/rq2_master_summary.json, RQ3_IDS_System/docs/feature_compatibility.md và RQ4_Retrain_Compare/results."));

const doc = new Document({
  styles: { default: { document: { run: { font: FONT, size: 24 } } } },
  numbering: { config: [{ reference: "bul", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] }] },
  sections: [{
    properties: { page: { size: { width: 11906, height: 16838 }, margin: { top: 1134, bottom: 1134, left: 1134, right: 1134 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 20 })] })] }) },
    children: c,
  }],
});
Packer.toBuffer(doc).then((b) => { fs.writeFileSync(OUT, b); fs.writeFileSync(TXT, plain.join("\n"), "utf8"); console.log("ok", b.length); });
