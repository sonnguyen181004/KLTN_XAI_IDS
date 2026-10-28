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
const TC = D.train_cmp;
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
c.push(P(`Nguồn gốc nằm ở dữ liệu huấn luyện. Bộ train cũ của RQ1 có ${nf(TC.cu.benign.tcp_rows)} flow Benign TCP, trong đó ${nf(TC.cu.benign.fin_data_gt0)} flow vừa mang cờ FIN vừa có dữ liệu và không flow nào mang dữ liệu từ 66 byte trở lên. Bộ train improved dựng theo cùng công thức lấy mẫu có ${nf(TC.moi.benign.tcp_rows)} flow Benign TCP, trong đó ${pct(TC.moi.benign.fin_data_gt0, TC.moi.benign.tcp_rows, 1)} vừa mang cờ FIN vừa có dữ liệu và ${pct(TC.moi.benign.fin_data_ge_min, TC.moi.benign.tcp_rows, 1)} mang dữ liệu từ 66 byte trở lên. Trên ${nf(cr("M0", "T2a_improved_stratified").benign_zone_n)} flow Benign có nhãn thật của bộ test improved nằm trong vùng này, mô hình cũ gán nhãn tấn công cho ${pc(cr("M0", "T2a_improved_stratified").fpr_zone_pct, 3)}.`));
c.push(P(`Nhóm huấn luyện lại hai mô hình theo đúng quy trình của RQ1 và RQ2, giữ nguyên siêu tham số và cấu hình SHAP, LIME. M0b dùng dữ liệu cũ giới hạn 13 lớp chung. M1 dùng ${nf(TC.moi.rows)} dòng train lấy từ bản improved, cùng công thức lấy mẫu và cùng cách chia stratified 80/20 của RQ1, không dùng Timestamp hay địa chỉ IP. M1 báo nhầm ${pc(cr("M1", "T3_realtime_benign").fpr_pct, 1)} trên lưu lượng thật, so với ${pc(cr("M0", "T3_realtime_benign").fpr_pct, 1)} của M0. Tuy nhiên M1 chỉ nhận ${pc(cr("M1", "T1_test_cu").hulk_recall_pct, 1)} số flow Hulk của bộ test cũ và báo nhầm ${pc(cr("M1", "T1_test_cu").fpr_pct, 1)} Benign cũ.`));
c.push(P(`M1 đạt Macro F1 ${pc(R.M1.f1)} trên test cùng nguồn. Nhóm kiểm tra riêng M1 và không thấy rò rỉ: nhãn xáo trộn chỉ đạt mức đoán lớp đông nhất, không có nhóm đặc trưng nào trùng mà khác nhãn. Điểm cao đến từ việc bài toán dễ: chỉ ${nf(D.standalone.learning_curve["0.001"].train_rows)} dòng train (0,1%) đã cho Macro F1 ${pc(D.standalone.learning_curve["0.001"].macro_f1, 1)}, và ${pc(D.standalone.nearest_neighbor.frac_below_0_01, 0)} dòng test có một dòng train gần như y hệt. Điểm này đo khả năng nhận ra chiến dịch tấn công trong chính phòng lab, chưa phải chất lượng ngoài đời.`));
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
c.push(H1("5. So sánh hai bộ dữ liệu train"));
c.push(P(`Phần này so sánh đúng hai bộ đã đưa vào huấn luyện: bộ train cũ của RQ1 (${nf(TC.cu.rows)} dòng, giới hạn 13 lớp chung) và bộ train improved dựng cho M1 (${nf(TC.moi.rows)} dòng). Cả hai theo cùng công thức lấy mẫu (70% Benign, 30% tấn công, cùng thành phần các lớp tấn công lớn), nên so sánh trực tiếp được. Nhóm không dùng các tệp dữ liệu gốc nữa vì bộ train chính là mẫu của chúng. Chỉ xét flow giao thức TCP và dùng đúng các ngưỡng của vùng Hulk.`));
c.push(T([4300, 2670, 2668], ["Chỉ tiêu", "Train cũ", "Train improved"], [
  ["Số dòng / số flow TCP", nf(TC.cu.rows) + " / " + nf(TC.cu.tcp_rows), nf(TC.moi.rows) + " / " + nf(TC.moi.tcp_rows)],
  ["Benign TCP mang cờ FIN", nf(TC.cu.benign.fin) + " trên " + nf(TC.cu.benign.tcp_rows) + " (" + pct(TC.cu.benign.fin, TC.cu.benign.tcp_rows) + ")", nf(TC.moi.benign.fin) + " trên " + nf(TC.moi.benign.tcp_rows) + " (" + pct(TC.moi.benign.fin, TC.moi.benign.tcp_rows) + ")"],
  ["Benign TCP có FIN và có dữ liệu", nf(TC.cu.benign.fin_data_gt0) + " (" + pct(TC.cu.benign.fin_data_gt0, TC.cu.benign.tcp_rows, 4) + ")", nf(TC.moi.benign.fin_data_gt0) + " (" + pct(TC.moi.benign.fin_data_gt0, TC.moi.benign.tcp_rows) + ")"],
  ["Benign TCP có FIN và dữ liệu từ 66 byte", nf(TC.cu.benign.fin_data_ge_min), nf(TC.moi.benign.fin_data_ge_min) + " (" + pct(TC.moi.benign.fin_data_ge_min, TC.moi.benign.tcp_rows) + ")"],
  ["Benign nằm trong vùng ba điều kiện của Hulk", nf(TC.cu.benign.zone), nf(TC.moi.benign.zone) + " (" + pct(TC.moi.benign.zone, TC.moi.benign.tcp_rows) + ")"],
  ["Hulk TCP mang cờ FIN", nf(TC.cu.hulk.fin) + " trên " + nf(TC.cu.hulk.tcp_rows) + " (" + pct(TC.cu.hulk.fin, TC.cu.hulk.tcp_rows) + ")", nf(TC.moi.hulk.fin) + " trên " + nf(TC.moi.hulk.tcp_rows) + " (" + pct(TC.moi.hulk.fin, TC.moi.hulk.tcp_rows) + ")"],
  ["Hulk nằm trong vùng ba điều kiện", nf(TC.cu.hulk.zone) + " trên " + nf(TC.cu.hulk.tcp_rows), nf(TC.moi.hulk.zone) + " trên " + nf(TC.moi.hulk.tcp_rows)],
  ["Flow có từ 4 gói mỗi chiều mang FIN", nf(TC.cu.tcp_ge4pkts_each_way_fin) + " trên " + nf(TC.cu.tcp_ge4pkts_each_way) + " (" + pct(TC.cu.tcp_ge4pkts_each_way_fin, TC.cu.tcp_ge4pkts_each_way, 3) + ")", nf(TC.moi.tcp_ge4pkts_each_way_fin) + " trên " + nf(TC.moi.tcp_ge4pkts_each_way) + " (" + pct(TC.moi.tcp_ge4pkts_each_way_fin, TC.moi.tcp_ge4pkts_each_way, 1) + ")"],
  ["Flow TCP có cờ ACK", pct(TC.cu.tcp_ack_ge1, TC.cu.tcp_rows, 1), pct(TC.moi.tcp_ack_ge1, TC.moi.tcp_rows, 1)],
  ["Giá trị cờ FIN quan sát được", "Chỉ 0 hoặc 1", "Nhận 0 đến 5 và hơn nữa"],
]));
c.push(cap("Bảng 3. So sánh cờ TCP giữa hai bộ train. Mã nằm ở scripts/02_compare_train_sets.py, kết quả ở results/compare_train_sets.json."));
c.push(IMG("hinh2_fin_benign.png", 560, 253));
c.push(cap("Hình 1. Tỷ lệ flow Benign TCP mang cờ FIN trong hai bộ train."));
c.push(P(`Trong bộ train cũ, chỉ ${pct(TC.cu.tcp_ge4pkts_each_way_fin, TC.cu.tcp_ge4pkts_each_way, 3)} trong ${nf(TC.cu.tcp_ge4pkts_each_way)} flow có từ 4 gói trở lên ở mỗi chiều, tức những kết nối trông khá đầy đủ, mang cờ FIN. Theo giao thức TCP một kết nối hoàn chỉnh thường kết thúc bằng FIN, nên tỷ lệ này rất thấp, và bộ train improved có ${pct(TC.moi.tcp_ge4pkts_each_way_fin, TC.moi.tcp_ge4pkts_each_way, 1)}. Cờ ACK cũng chỉ có ở ${pct(TC.cu.tcp_ack_ge1, TC.cu.tcp_rows, 1)} flow TCP của bộ cũ dù hầu như mọi kết nối đều có gói ACK, và cả năm cột cờ chỉ nhận 0 hoặc 1. Các dấu hiệu này phù hợp với mô tả lỗi đếm cờ và lỗi cắt flow của CICFlowMeter-V3, nhưng chưa phải bằng chứng trực tiếp vì thiếu PCAP gốc.`));
c.push(P(`Hệ quả cho mô hình rất cụ thể. Ở bộ cũ vùng ba điều kiện chỉ chứa ${nf(TC.cu.zone_by_label["DoS attacks-Hulk"])} dòng Hulk, nên mô hình học vùng đó là Hulk. Ở bộ improved vùng đó chứa ${nf(TC.moi.zone_by_label.Benign)} dòng Benign, ${nf(TC.moi.zone_by_label["DDOS attack-HOIC"])} dòng HOIC, ${nf(TC.moi.zone_by_label.Bot)} dòng Bot và chỉ ${nf(TC.moi.zone_by_label["DoS attacks-Hulk"])} dòng Hulk, tức quy tắc cũ không còn đặc trưng cho Hulk. Cách giải thích phù hợp với số liệu là vì flow bị cắt ở gói FIN đầu tiên và cờ chỉ được ghi nhận ở gói đầu, Benign có dữ liệu của bộ cũ thường không mang FIN, còn Hulk dùng Connection: close nên FIN đi cùng dữ liệu. Giải thích này khớp các con số nhưng là giả thuyết.`));

c.push(H2("5.1 Hulk của hai bộ là hai kiểu lưu lượng khác nhau"));
const prof = (set, k) => TC[set][k].profile_median;
const rowsHP = [["Train cũ", "Hulk", "cu", "hulk"], ["Train cũ", "Benign", "cu", "benign"], ["Train improved", "Hulk", "moi", "hulk"], ["Train improved", "Benign", "moi", "benign"]].map(([s, n, a, b]) => {
  const p = prof(a, b);
  return [s + ", " + n, nf(TC[a][b].tcp_rows), nf(p["Tot Fwd Pkts"]), nf(p["Fwd Pkt Len Max"]), nf(p["Init Fwd Win Byts"]), nf(p["Fwd Seg Size Min"]), nf(p["FIN Flag Cnt"])];
});
c.push(T([2338, 1300, 1100, 1300, 1300, 1200, 1100], ["Nhóm (flow TCP)", "Số flow", "Tot Fwd Pkts", "Fwd Pkt Len Max", "Init Fwd Win Byts", "Fwd Seg Size Min", "FIN Flag Cnt"], rowsHP));
c.push(cap("Bảng 4. Trung vị đặc trưng của flow Hulk và Benign trong hai bộ train."));
c.push(P(`Hulk trong bộ train cũ có trung vị ${nf(prof("cu", "hulk")["Tot Fwd Pkts"])} gói chiều đi, Fwd Pkt Len Max bằng ${nf(prof("cu", "hulk")["Fwd Pkt Len Max"])} và FIN bằng ${nf(prof("cu", "hulk")["FIN Flag Cnt"])}, tức phần lớn là những flow rất ngắn không mang dữ liệu. Hulk trong bộ improved là kết nối HTTP đầy đủ với ${nf(prof("moi", "hulk")["Tot Fwd Pkts"])} gói chiều đi, Fwd Pkt Len Max ${nf(prof("moi", "hulk")["Fwd Pkt Len Max"])}, FIN ${nf(prof("moi", "hulk")["FIN Flag Cnt"])} và cửa sổ nhận ban đầu ${nf(prof("moi", "hulk")["Init Fwd Win Byts"])} so với ${nf(prof("cu", "hulk")["Init Fwd Win Byts"])}. Hai bộ vì vậy mô tả cùng một công cụ tấn công bằng hai kiểu đặc trưng khác nhau, và một mô hình học từ bộ này không thể nhận ra Hulk của bộ kia.`));

c.push(H2("5.2 Đặc trưng và nhãn"));
c.push(P("Cả 78 đặc trưng của mô hình đều có tương ứng trong bản improved, trong đó 48 đặc trưng chỉ khác tên và được ánh xạ bằng bảng results/mapping_features.csv. Bản improved có thêm 5 cột mà mô hình không dùng, gồm Fwd RST Flags, Bwd RST Flags, ICMP Code, ICMP Type và Total TCP Flow Time. Tập nhãn thì không giống nhau. Bản improved không có DoS attacks-SlowHTTPTest, và FTP-BruteForce chỉ có dạng Attempted. Các nhãn Attempted (tấn công thất bại) bị bỏ ra khỏi mọi thí nghiệm. Bốn loại Infiltration được gộp lại thành một lớp. Kết quả là không gian nhãn chung gồm 13 lớp, và bảng ánh xạ đầy đủ nằm ở results/mapping_labels_improved.csv."));

c.push(H2("5.3 Hai bộ liên quan và khác nhau thế nào"));
c.push(P("Hai bộ giống nhau ở nguồn gốc (CSE-CIC-IDS2018, cùng phòng lab và công cụ tấn công) và ở 78 tên đặc trưng của mô hình. Chúng khác nhau ở ba điểm. Thứ nhất, cách tính giá trị: bản improved dùng CICFlowMeter đã sửa lỗi nên cờ TCP không còn bị giới hạn ở 0 và 1, và cách cắt flow khác. Thứ hai, kiểu lưu lượng của cùng một nhãn: Hulk của hai bộ khác hẳn nhau (mục 5.1). Thứ ba, tập nhãn: bản improved không có SlowHTTPTest và FTP-BruteForce. Vì vậy một mô hình huấn luyện ở bộ này vẫn chạy được trên bộ kia, nhưng kết quả không còn mang cùng ý nghĩa (mục 7.5)."));

// ================= 6. THIẾT KẾ =================
c.push(H1("6. Thiết kế thực nghiệm mới"));
c.push(H2("6.1 Nguyên tắc làm đúng như mô hình cũ"));
c.push(T([2300, 3669, 3669], ["Hạng mục", "Mô hình cũ (RQ1, RQ2)", "Mô hình mới (RQ4)"], [
  ["Thuật toán và tham số", "XGBClassifier, 100 cây, độ sâu 8, learning rate 0,08, hist, seed 42", "Giống hệt, không quét lại tham số"],
  ["Đặc trưng", "78 đặc trưng float32, không Timestamp, không IP", "Giống hệt, đổi tên theo bảng ánh xạ"],
  ["Lấy mẫu", "3,5 triệu dòng, 70% Benign và 30% tấn công, giữ 100% lớp hiếm", "Cùng công thức, số mẫu mỗi lớp theo bộ cũ và bị chặn bởi số flow sẵn có"],
  ["Chia dữ liệu", "Stratified 80/20, seed 42", "Giống hệt, không bộ giữ riêng nào"],
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
c.push(T([3000, 1660, 1660, 1660, 1658], ["Lớp", "Train cũ", "Test cũ", "Train M1", "Test M1"],
  classes.map((k) => [k, nf(comp[k].old_train), nf(comp[k].old_test), nf(comp[k].d2_train), nf(comp[k].d2_test)])));
c.push(cap("Bảng 7. Thành phần các bộ dữ liệu. Hulk có đúng 155.042 dòng train ở cả hai bộ."));
c.push(P(`Bản improved được quét một lần duy nhất (khoảng 35 GB, ${nf(Object.values(D.scan.raw_label_counts).reduce((s, v) => s + v, 0))} flow), giữ toàn bộ flow của 12 lớp tấn công chung và 7% Benign ngẫu nhiên. Từ bộ nhớ đệm này, nhóm lấy ngẫu nhiên số mẫu mỗi lớp tấn công theo thành phần của bộ cũ, bị chặn bởi số flow có sẵn: Brute Force -Web chỉ còn 131 flow, Brute Force -XSS 113 và SQL Injection 39. Benign được lấy sao cho giữ tỷ lệ 70% và 30%. Sau đó chia stratified 80/20 với seed 42, đúng như RQ1. Không có vùng thời gian hay bộ giữ riêng nào, nên không có thí nghiệm nào dùng Timestamp hay địa chỉ IP.`));
c.push(T([1500, 4300, 3838], ["Mã", "Nội dung", "Ghi chú"], [
  ["T1", "Test cũ, giới hạn 13 lớp (694.758 dòng), và bản bỏ dòng trùng với train cũ", "Trong phân phối của M0 và M0b"],
  ["T2a", "Test 20% của bản improved (" + nf(D.leak.d2_test_rows) + " dòng), và bản bỏ trùng", "Trong phân phối của M1"],
  ["T3", nf(T3.t3_flows) + " flow realtime của máy người dùng, nguồn feeder_live, bỏ multicast và flow PCAP", "Nhãn Benign do người dùng xác nhận bằng lời ngày 26/10/2026, chưa có chi tiết hoạt động từng phiên"],
]));
c.push(cap("Bảng 8. Các bộ đánh giá."));
c.push(P(`Về trùng lặp, ${nf(D.leak.d2_test_rows_also_in_train)} trên ${nf(D.leak.d2_test_rows)} dòng test của M1 (${pct(D.leak.d2_test_rows_also_in_train, D.leak.d2_test_rows, 1)}) có 78 đặc trưng giống hệt một dòng trong train. Bộ cũ có ${pct(D.leak.old_test_rows_also_in_train, D.leak.old_test_rows, 2)}. Các công cụ tấn công trong lab gửi nhiều gói giống hệt nhau nên flow trùng xuất hiện tự nhiên khi chia ngẫu nhiên. Nhóm giữ nguyên cách chia để so sánh cùng điều kiện với RQ1, và bổ sung mọi bản bỏ trùng để kết luận không phụ thuộc vào dòng trùng.`));

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
const sets = [["T1_test_cu_sach", "T1 test cũ"], ["T2a_improved_stratified_sach", "T2a test improved"], ["T3_realtime_benign", "T3 realtime (Benign)"]];
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
c.push(P(`Chiều ngược lại cũng đáng chú ý. M0 nhận ${pc(m0z.hulk_recall_pct, 2)} flow Hulk của bản improved, nhưng nhiều khả năng nhờ dấu hiệu FIN, vì ${pct(TC.moi.hulk.fin, TC.moi.hulk.tcp_rows, 2)} flow Hulk của bộ train improved mang FIN. Điểm này làm cho độ nhận Hulk cao của M0 không phản ánh khả năng nhận diện hành vi tấn công.`));

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
c.push(H2("7.5 Đưa bộ test cũ vào M1"));
const o1 = cr("M1", "T1_test_cu"), o1s = cr("M1", "T1_test_cu_sach"), o0 = cr("M0b", "T1_test_cu");
c.push(P(`Test M1 trên bộ cũ là làm được, vì cả 78 đặc trưng đều có tương ứng ở hai bộ (48 đặc trưng chỉ khác tên và đã được ánh xạ), nên không cần bỏ đặc trưng nào, kể cả cờ FIN. Kết quả trên bộ test cũ giới hạn 13 lớp (${nf(o1.n)} dòng) rất khác so với M0b trên cùng bộ test này.`));
c.push(T([3600, 2000, 2000, 2038], ["Trên test cũ (13 lớp)", "M0b (train cũ)", "M1, bản đầy đủ", "M1, đã bỏ trùng"], [
  ["Accuracy", pc(o0.accuracy_pct, 1), pc(o1.accuracy_pct, 1), pc(o1s.accuracy_pct, 1)],
  ["Macro F1", pc(o0.macro_f1_13_pct, 1), pc(o1.macro_f1_13_pct, 1), pc(o1s.macro_f1_13_pct, 1)],
  ["Recall Hulk", pc(o0.hulk_recall_pct, 1), pc(o1.hulk_recall_pct, 1), pc(o1s.hulk_recall_pct, 1)],
  ["Benign bị báo thành tấn công", pc(o0.fpr_pct, 2), pc(o1.fpr_pct, 2), pc(o1s.fpr_pct, 2)],
  ["Tấn công bị báo thành Benign", pc(o0.fnr_pct, 1), pc(o1.fnr_pct, 1), pc(o1s.fnr_pct, 1)],
]));
c.push(cap("Bảng 13b. M1 trên bộ test cũ so với M0b trên cùng bộ test."));
c.push(P("Hai bộ dữ liệu có liên quan nhưng không giống nhau. Chúng cùng nguồn gốc (CSE-CIC-IDS2018, cùng phòng lab, cùng công cụ tấn công) và cùng tên đặc trưng, nhưng giá trị đặc trưng được tính khác nhau. Bản improved dùng CICFlowMeter đã sửa lỗi, nên cờ FIN nhận từ 0 đến 5 trở lên thay vì chỉ 0 hoặc 1, cách cắt flow khác, và Hulk của hai bộ là hai kiểu lưu lượng khác nhau (Bảng 4). Một mô hình học trên các giá trị này vì vậy không còn dùng được khi giá trị đặc trưng đổi nghĩa. Đây không phải lỗi mô hình, và cũng không có nghĩa là hai bộ không so sánh được. Nó chính là phát hiện của bài: hai phiên bản của cùng một bộ dữ liệu làm hai mô hình hành xử rất khác nhau."));
c.push(P("Nhóm chưa thử huấn luyện M1 không có các cột cờ TCP rồi test trên bộ cũ, nên chưa biết bỏ cờ có làm kết quả trên bộ cũ khá hơn không. Đây là thí nghiệm có thể làm thêm."));

c.push(H1("8. Kiểm tra riêng M1"));
const dg = D.diag, SA = D.standalone, LC = SA.learning_curve, ST = SA.shallow_trees, NN = SA.nearest_neighbor, PM = D.perclass;
const pv = SA.provenance_check;
const pvFound = Object.values(pv).reduce((s, v) => s + v.found_in_raw, 0), pvSamp = Object.values(pv).reduce((s, v) => s + v.sampled, 0), pvOk = Object.values(pv).reduce((s, v) => s + v.label_matches_mapping, 0);
c.push(P(`M1 đạt Accuracy ${pc(R.M1.acc)}, Macro F1 ${pc(R.M1.f1)} và FPR ${pc(R.M1.fpr, 4)}. Con số này quá cao nên nhóm kiểm tra M1 như một mô hình riêng, trước khi so với M0. M1 dùng đúng 78 đặc trưng của RQ1, không có Timestamp, địa chỉ IP hay mã định danh flow nào trong số đó, và bộ train và test lấy theo đúng công thức của RQ1.`));
c.push(T([2300, 4100, 3238], ["Kiểm tra", "Cách làm", "Kết quả"], [
  ["Nguồn dữ liệu", "Đối chiếu " + nf(pvSamp) + " dòng mẫu của ba ngày với tệp CSV improved theo khóa gồm thời điểm, thời lượng, số gói, tổng độ dài và cổng", nf(pvFound) + " dòng tìm thấy, " + nf(pvOk) + " dòng có nhãn đúng với bảng ánh xạ. Các dòng còn lại không khớp được khóa, chưa rõ lý do"],
  ["Nhãn mâu thuẫn", "Tìm các nhóm dòng giống hệt 78 đặc trưng nhưng khác nhãn", nf(SA.conflicting_label_groups) + " trên " + nf(SA.identical_feature_groups) + " nhóm"],
  ["Nhãn xáo trộn", "Huấn luyện lại với nhãn bị xáo ngẫu nhiên, đo trên test thật", "Accuracy " + pc(SA.shuffled_labels.accuracy, 2) + ", bằng đúng mức đoán lớp đông nhất (" + pc(SA.majority_baseline_accuracy, 2) + "), Macro F1 " + pc(SA.shuffled_labels.macro_f1, 1)],
  ["Đường cong học", "Chỉ dùng 0,1%, 1%, 10% dữ liệu train", "0,1% (" + nf(LC["0.001"].train_rows) + " dòng): Macro F1 " + pc(LC["0.001"].macro_f1, 1) + "; 1%: " + pc(LC["0.01"].macro_f1, 1) + "; 10%: " + pc(LC["0.1"].macro_f1, 1) + "; 100%: " + pc(R.M1.f1, 1)],
  ["Cây quyết định nông", "Độ sâu 2, 3, 5", "Accuracy " + pc(ST["2"].accuracy, 1) + ", " + pc(ST["3"].accuracy, 1) + ", " + pc(ST["5"].accuracy, 1) + "; Macro F1 " + pc(ST["2"].macro_f1, 1) + ", " + pc(ST["3"].macro_f1, 1) + ", " + pc(ST["5"].macro_f1, 1)],
  ["Dòng test gần giống train", "Khoảng cách tới dòng train gần nhất sau khi chuẩn hóa, " + nf(NN.n_test) + " dòng test cân bằng theo lớp", pc(NN.frac_below_0_01, 1) + " có dòng train gần như y hệt (dưới 0,01 độ lệch chuẩn), " + pc(NN.frac_below_0_1, 1) + " dưới 0,1"],
  ["Bỏ dòng trùng hệt", "Đo lại trên phần test không có dòng giống hệt train (bỏ " + nf(dg.M1_test_stratified_khong_trung.removed) + " dòng)", "Macro F1 " + pc(dg.M1_test_stratified_khong_trung.macro_f1, 2) + ", so với " + pc(R.M1.f1, 2)],
  ["Bỏ đặc trưng môi trường", "Huấn luyện lại không có Dst Port, Protocol, hai cửa sổ nhận ban đầu và Fwd Seg Size Min", "Macro F1 " + pc(dg.M1_bo_dac_trung_moi_truong_test_stratified.macro_f1, 2) + ", FPR " + pc(dg.M1_bo_dac_trung_moi_truong_test_stratified.fpr, 3) + ", recall Hulk " + pc(dg.M1_bo_dac_trung_moi_truong_test_stratified.hulk_recall, 2)],
]));
c.push(cap("Bảng 14. Các kiểm tra riêng M1 (scripts/09_diagnose_m1.py và 13_audit_m1_standalone.py)."));
c.push(P(`Nhãn xáo trộn chỉ đạt mức đoán lớp đông nhất nên không có đường rò rỉ nhãn vào đặc trưng. Không có hai dòng nào giống hệt nhau mà khác nhãn, nên điểm cao không đến từ việc nhãn mơ hồ. Điều nổi bật nhất là đường cong học: chỉ ${nf(LC["0.001"].train_rows)} dòng đã cho Macro F1 ${pc(LC["0.001"].macro_f1, 1)} và Accuracy ${pc(LC["0.001"].accuracy, 2)}. Bài toán phân loại này dễ, và cây sâu 5 đã đạt Accuracy ${pc(ST["5"].accuracy, 1)}. Thêm vào đó ${pc(NN.frac_below_0_01, 0)} dòng test có một dòng train gần như y hệt, vì các công cụ tấn công trong lab gửi lặp lại cùng một mẫu gói. Bỏ riêng các dòng trùng hệt không đổi điểm, vì phần gần giống nhưng không trùng hệt vẫn còn.`));
const tp = D.srcip;
c.push(T([3400, 1900, 1900, 2438], ["Lớp", "Số flow trong cache", "Số địa chỉ nguồn", "Địa chỉ đông nhất chiếm"], tp.map((r) => [r.Label, nf(r.flows_in_cache), nf(r.unique_src_ip), pc(100 * r.top1_ip_share, 1)])));
c.push(cap("Bảng 15. Số địa chỉ nguồn theo lớp trong bản improved (quét lại tệp CSV, results/srcip_per_class.csv)."));
c.push(P(`Bảng 15 cho thấy lý do không chia train và test tách theo máy gửi. Bảy trong mười hai lớp tấn công, gồm Hulk, GoldenEye, Slowloris, SSH-Bruteforce, Brute Force -Web, -XSS và SQL Injection, chỉ có một địa chỉ nguồn, nên không thể đưa toàn bộ máy tấn công của lớp đó sang phía test mà vẫn còn lớp để học. Địa chỉ IP và thời điểm không nằm trong 78 đặc trưng, nên mô hình không học thuộc được chúng trực tiếp. Tuy vậy mỗi lớp tấn công về bản chất là một công cụ chạy từ một hoặc mười máy trong một ngày, nên nhận ra lớp đó dễ hơn nhiều so với nhận ra tấn công nói chung. Benign thì có ${nf(tp.find((r) => r.Label === "Benign").unique_src_ip)} địa chỉ nguồn khác nhau.`));
const BK = D.blocked.filter((r) => r.bo === "khoi_thoi_gian_sach");
const bmean = (k) => BK.reduce((s, r) => s + r[k], 0) / BK.length;
c.push(P(`Để loại khả năng test trùng thời điểm với train, nhóm chạy thêm một phép chia chặt hơn phép chia của RQ1 (scripts/14_blocked_cv_m1.py). Mỗi lớp được cắt thành 5 đoạn thời gian liên tục, mỗi lượt giữ một đoạn làm test và huấn luyện trên bốn đoạn còn lại, bỏ 1% thứ hạng thời gian sát hai đầu đoạn test khỏi train, rồi bỏ khỏi test các dòng giống hệt dòng train. Cấu hình XGBoost vẫn là cấu hình RQ1. Kết quả năm lượt: Accuracy trung bình ${pc(bmean("accuracy"), 2)}, Macro F1 trung bình ${pc(bmean("macro_f1"), 2)} (thấp nhất ${pc(Math.min(...BK.map((r) => r.macro_f1)), 2)}, cao nhất ${pc(Math.max(...BK.map((r) => r.macro_f1)), 2)}), FPR trung bình ${pc(bmean("fpr_pct"), 4)}, FNR trung bình ${pc(bmean("fnr_pct"), 3)}. Điểm gần như không giảm so với phép chia ngẫu nhiên, nên con số cao không đến từ việc test trùng thời điểm với train. Các lớp yếu nhất là Slowloris (recall thấp nhất 81,4%) và SQL Injection (85,7%), cả hai chỉ có vài chục đến vài nghìn flow. Phép đo này vẫn nằm trong cùng một lab, cùng công cụ, cùng ngày, nên chỉ nguồn độc lập mới kiểm tra được khả năng tổng quát hóa, và ở đó M1 yếu như mục 7.2 cho thấy.`));
const imp = dg.importance_M1;
c.push(P(`Tổng gain của XGBoost cho thấy M1 dựa nhiều nhất vào Init Fwd Win Byts (${nf(imp["Init Fwd Win Byts"], 1)}%), Init Bwd Win Byts (${nf(imp["Init Bwd Win Byts"], 1)}%), Dst Port (${nf(imp["Dst Port"], 1)}%) và Fwd Seg Size Min (${nf(imp["Fwd Seg Size Min"], 1)}%), tổng khoảng ${nf(imp["Init Fwd Win Byts"] + imp["Init Bwd Win Byts"] + imp["Dst Port"] + imp["Fwd Seg Size Min"], 0)}%. Bỏ cả các đặc trưng này mô hình vẫn đạt Macro F1 ${pc(dg.M1_bo_dac_trung_moi_truong_test_stratified.macro_f1, 1)}, nên điểm cao không phụ thuộc vào vài đặc trưng cụ thể.`));
c.push(P(`So với M0b, phần lớn chênh lệch Macro F1 (${pc(R.M0b.f1, 1)} so với ${pc(R.M1.f1, 1)}) đến từ lớp Infilteration: F1 là ${nf(PM.m0b.Infilteration, 3)} ở M0b và ${nf(PM.m1.Infilteration, 3)} ở M1. Infilteration của bộ cũ khó nhận, còn Infilteration của bản improved (có quét cổng bằng Nmap) dễ tách. Các lớp còn lại gần như bằng nhau, trừ vài lớp nhỏ (SQL Injection ${nf(PM.m0b["SQL Injection"], 3)} so với ${nf(PM.m1["SQL Injection"], 3)}, Brute Force -Web ${nf(PM.m0b["Brute Force -Web"], 3)} so với ${nf(PM.m1["Brute Force -Web"], 3)}) mà test chỉ có vài chục flow. Vì vậy nhóm không kết luận bản improved làm mô hình tốt hơn nói chung. Kết luận hợp lý là: không phát hiện rò rỉ, điểm cao phản ánh bài toán dễ trong chính phòng lab với nhiều dòng gần trùng, và bằng chứng rõ nhất về giới hạn là M1 chỉ nhận ${pc(cr("M1", "T1_test_cu").hulk_recall_pct, 1)} số flow Hulk của bộ test cũ.`));

c.push(H2("8.1 Giải thích: vì sao M1 cao hơn mô hình cũ, và M1 có học từ bộ cũ không"));
c.push(P(`M1 không học từ bộ cũ. M1 được huấn luyện từ đầu, chỉ trên bộ train improved, không kế thừa trọng số hay dữ liệu của M0. Siêu tham số giống hệt RQ1: độ sâu 8, learning rate 0,08, 100 cây, tree_method hist, seed 42, không quét lại. Đặc trưng cũng giống: 78 đặc trưng, không Timestamp, không địa chỉ IP. Vì vậy mọi khác biệt giữa M1 và M0b chỉ đến từ dữ liệu huấn luyện và test.`));
c.push(P(`Macro F1 của M1 là ${pc(R.M1.f1, 1)}, của M0b là ${pc(R.M0b.f1, 1)} (cùng 13 lớp). Phần lớn chênh lệch đến từ một lớp. Infilteration có F1 ${nf(PM.m0b.Infilteration, 3)} ở bộ cũ, vì phần lớn flow bị đoán thành Benign, và ${nf(PM.m1.Infilteration, 3)} ở bộ improved, vì Infilteration của bản improved có quét cổng nên dễ tách. Hầu hết các lớp còn lại đạt khoảng 1,0 ở cả hai mô hình. Vài lớp nhỏ (SQL Injection, Brute Force -Web) chênh nhau nhưng test chỉ có vài chục flow. Điểm cao hơn của M1 do đó phản ánh bộ improved dễ hơn trong chính nó, không chứng minh M1 tốt hơn M0 nói chung. Phép chia theo khối thời gian ở trên và đường cong học cùng cho thấy điều này.`));

// ================= 9. THẢO LUẬN =================
c.push(H1("9. Thảo luận"));
c.push(P("Câu hỏi bộ dữ liệu cũ thiếu gì có câu trả lời cụ thể hơn sau thực nghiệm này. Bộ train cũ gần như không có Benign nào vừa đóng bằng FIN vừa mang dữ liệu, trong khi đó là " + pct(TC.moi.benign.fin_data_gt0, TC.moi.benign.tcp_rows, 1) + " flow Benign TCP của bộ train improved. Mô hình học từ bộ cũ đã gán nhãn Hulk cho toàn bộ vùng này, và điều đó được kiểm chứng ở hai cấp độ độc lập, gồm " + nf(cr("M0", "T2a_improved_stratified_sach").benign_zone_n) + " flow Benign trong vùng ở bộ test improved có nhãn thật, và " + nf(T3.t3_zone_flows) + " flow realtime do người dùng xác nhận."));
c.push(P("Thực nghiệm cũng cho thấy việc sửa dữ liệu không giải quyết hết vấn đề. Mô hình M1 loại bỏ được báo nhầm FIN nhưng vẫn dựa nhiều vào đặc trưng môi trường như cửa sổ nhận ban đầu và kích thước header tối thiểu. Những đặc trưng này khác nhau giữa các mạng, nên M1 có thể thất bại ở một môi trường khác dù đúng ở máy của người dùng. Đây cũng là điều Engelen và cộng sự cảnh báo khi nói về nguy cơ học đường tắt theo cấu hình lab."));
c.push(P("Với giải thích, SHAP đóng vai trò công cụ chẩn đoán trong cả hai mô hình. Nó chỉ ra FIN và Fwd Pkt Len Max ở M0, và chỉ ra các đặc trưng cửa sổ nhận ở M1, và kết quả của nó được kiểm chứng bằng cấu trúc cây và thử phản thực. LIME kém tin cậy hơn, đạt cổng chất lượng ở " + pc(100 * X.M1.lime_pass, 0) + " flow của M1 trong nhóm đánh giá, và theo kết quả RQ3 trước đó bị loại gần hết trên flow thật vì các flow này nằm quá xa dữ liệu nền mà LIME lấy mẫu quanh đó."));
c.push(H2("9.1 Những điều có thể và chưa thể kết luận"));
c.push(B("Có thể kết luận rằng dữ liệu train cũ không có Benign trong vùng ba điều kiện, rằng vùng này khớp các báo nhầm quan sát được, và rằng đặt FIN bằng 0 loại bỏ các báo nhầm đó ở M0."));
c.push(B("Có thể kết luận rằng bộ train cũ gần như không có Benign mang FIN và dữ liệu, trong khi bộ train improved có " + pct(TC.moi.benign.fin_data_gt0, TC.moi.benign.tcp_rows, 1) + "."));
c.push(B("Có thể kết luận rằng huấn luyện lại trên bản improved theo đúng quy trình cũ làm báo nhầm trên lưu lượng thật của máy người dùng từ " + pc(t3m0.fpr_pct, 1) + " xuống " + pc(t3m1.fpr_pct, 1) + "."));
c.push(B("Chưa thể kết luận rằng nguyên nhân duy nhất là thiếu mẫu Benign. Thí nghiệm M2 để tách thiếu mẫu khỏi khác định nghĩa đặc trưng đang được hoãn."));
c.push(B("Chưa thể kết luận rằng lỗi bắt nguồn từ công cụ trích xuất CICFlowMeter-V3, vì thiếu cặp PCAP và CSV gốc để kiểm chứng trực tiếp."));
c.push(B("Chưa thể kết luận gì về khả năng M1 phát hiện tấn công thật ngoài lab, vì chưa có dữ liệu tấn công độc lập."));

// ================= 10. HƯỚNG BÀI BÁO =================
c.push(H1("10. Hướng viết bài báo khoa học"));
c.push(H2("10.1 Câu chuyện"));
c.push(P("Bài báo bắt đầu từ một nghịch lý. Một mô hình phát hiện xâm nhập đạt hiệu năng nội bộ rất cao nhưng báo nhầm hàng loạt khi chạy trên lưu lượng thật. Câu hỏi đặt ra là điều gì che giấu lỗi trong phép đánh giá thông thường và giải thích mô hình có giúp tìm ra lỗi hay không."));
c.push(P("Phần tiếp theo kể quá trình truy tìm. SHAP chỉ vào cờ FIN. Phân tích cây quyết định cho ra một vùng ba điều kiện chỉ có Hulk trong dữ liệu train. Thử phản thực khẳng định vùng đó là thứ làm nhãn đổi. So sánh hai bộ train cho thấy bộ cũ không có Benign trong vùng này còn bộ improved có hơn một phần ba, và lỗi khớp với mô tả TCP appendices và cách đếm cờ sai của CICFlowMeter-V3 trong tài liệu của Engelen và cộng sự."));
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
c.push(cap("Bảng 16. Các việc còn lại."));

// ================= 11. HẠN CHẾ =================
c.push(H1("11. Hạn chế"));
c.push(B("Nhãn Benign của bộ realtime dựa trên lời xác nhận bằng lời của người dùng, chưa có nhật ký hoạt động chi tiết từng phiên."));
c.push(B("Bộ realtime có 784 flow từ hai mạng (Wi-Fi nhà và điểm phát sóng điện thoại) trong một ngày, nên chưa đại diện cho nhiều môi trường."));
c.push(B("Chưa có dữ liệu tấn công độc lập, nên chưa đo được khả năng phát hiện tấn công của mô hình mới ngoài lab."));
c.push(B("Thí nghiệm M2 bị hoãn, nên chưa tách được hai nguyên nhân là thiếu mẫu và khác định nghĩa đặc trưng."));
c.push(B("Lỗi lịch sử của công cụ trích xuất chưa được kiểm chứng trực tiếp vì thiếu cặp PCAP và CSV gốc."));
c.push(B("Bảy trong mười hai lớp tấn công chỉ có đúng một địa chỉ nguồn, nên không thể chia train và test tách theo máy gửi. Phép chia ngẫu nhiên theo RQ1 vì vậy cho điểm lạc quan hơn một phép chia tách theo máy."));
c.push(B("Ba lớp tấn công nhỏ nhất (Brute Force -Web, Brute Force -XSS, SQL Injection) chỉ có 26, 23 và 8 flow trong test M1, nên F1 của chúng dao động mạnh và kéo Macro F1 lên xuống."));
c.push(B("Hulk của CICFlowMeter-V3 có cài đặt lỗi theo tài liệu của Engelen và cộng sự, nên bài báo nên dùng Hulk như một ca nghiên cứu về học đường tắt, không dùng như bằng chứng khả năng phát hiện DoS nói chung."));
c.push(B("Cách chọn siêu tham số của RQ1 dựa trên điểm test của chính mô hình, và được giữ nguyên theo yêu cầu để so sánh cùng điều kiện."));

// ================= 12. TÁI LẬP =================
c.push(H1("12. Tái lập"));
c.push(P("Mã, kết quả và tài liệu nằm trong thư mục RQ4_Retrain_Compare. Các tập dữ liệu trung gian và file mô hình .pkl không được commit theo cấu hình của repo, nhưng mã và số liệu kết quả đều có trong git."));
c.push(T([2700, 6938], ["Tệp", "Nội dung"], [
  ["scripts/01_mapping_tables.py", "Bảng ánh xạ 78 đặc trưng và các nhãn giữa hai bản"],
  ["scripts/02_compare_train_sets.py", "So sánh hai bộ train: cờ TCP, vùng Hulk, hồ sơ Hulk và Benign"],
  ["scripts/03_build_improved_cache.py", "Quét bản improved một lần, lấy toàn bộ tấn công và 7% Benign"],
  ["scripts/04_build_datasets.py", "Dựng train và test M1 theo công thức lấy mẫu của RQ1"],
  ["scripts/05_train_models.py", "Huấn luyện M0b và M1 với tham số RQ1"],
  ["scripts/06_prepare_t3_realtime.py, 06b_confirm_t3.py", "Dựng bộ realtime T3 từ DB hệ thống"],
  ["scripts/07_evaluate_cross.py", "Đánh giá chéo, có bản bỏ trùng"],
  ["scripts/08_run_xai.py", "Chuỗi SHAP và LIME (GĐ0 đến GĐ13) cho một mô hình"],
  ["scripts/09_diagnose_m1.py, 13_audit_m1_standalone.py", "Chẩn đoán và kiểm tra riêng M1"],
  ["scripts/10_t3_explain.py", "SHAP và phản thực trên flow realtime"],
  ["scripts/11_report_data.py", "Gom số liệu và vẽ hình cho báo cáo"],
  ["results/ và xai_runs/m1/", "Kết quả CSV, JSON và hình của mọi bước"],
]));
c.push(cap("Bảng 17. Các tệp chính."));

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
