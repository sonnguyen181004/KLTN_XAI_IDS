from pathlib import Path
import sys, ast, math
ROOT=Path(__file__).resolve().parents[1]
QA=ROOT/'Report/.qa_en'; QA.mkdir(exist_ok=True)
sys.path.append(str(QA/'deps'))
from PIL import Image,ImageDraw,ImageFont

labels={
'DỮ LIỆU VÀ PHẠM VI':'DATA AND SCOPE',
'CSE-CIC-IDS2018 • 78 đặc trưng • 15 lớp':'CSE-CIC-IDS2018 • 78 features • 15 classes',
'RQ1   SO SÁNH VÀ CHỌN MÔ HÌNH':'RQ1   MODEL COMPARISON AND SELECTION',
'Thử siêu tham số Random Forest và XGBoost\nSo sánh chỉ số phân loại và ghi rõ giới hạn cách chọn cấu hình':'Test Random Forest and XGBoost hyperparameters\nCompare classification metrics and state configuration-selection limitations',
'RQ2   ĐÁNH GIÁ SHAP VÀ LIME':'RQ2   SHAP AND LIME EVALUATION',
'Giữ nguyên mô hình • cố định tập mẫu và cấu hình\nĐồng thuận, mức khớp cục bộ, ổn định và độ trung thực':'Keep the model unchanged • fix the sample set and configuration\nAgreement, local fit, stability, and faithfulness',
'RQ3   TRIỂN KHAI VÀ KIỂM THỬ NGUYÊN MẪU':'RQ3   PROTOTYPE IMPLEMENTATION AND TESTING',
'CSV, PCAP và bắt trực tiếp dùng chung mô hình\nKiểm tra pipeline, giao diện, vòng đời capture và tài nguyên\nPhân tích cảnh báo thực tế trong phạm vi có bằng chứng':'CSV, PCAP, and live capture share the same model\nTest the pipeline, interface, capture lifecycle, and resources\nAnalyze real-traffic alerts within the available evidence',
'CSV ĐẶC TRƯNG':'FEATURE CSV','Dữ liệu có sẵn\nKhông trích xuất lại gói':'Existing feature data\nNo packet re-extraction',
'TỆP PCAP':'PCAP FILE','Gói tin đã lưu\nTrích xuất ngoại tuyến':'Stored packets\nOffline extraction',
'CARD MẠNG':'NETWORK ADAPTER','Bắt trực tiếp bằng Npcap\nTiến trình capture':'Live capture with Npcap\nCapture process',
'BỘ TRÍCH XUẤT FLOW':'FLOW EXTRACTOR',
'Gom gói theo vòng đời flow • tính đặc trưng\nXuất CSV và metadata khi flow được đóng':'Group packets by flow lifecycle • compute features\nExport CSV and metadata when a flow closes',
'CHUẨN HÓA VÀ API DỰ ĐOÁN':'NORMALIZATION AND PREDICTION API',
'Bộ cấp dữ liệu gửi flow • kiểm tra 78 cột, thứ tự và đơn vị\nXGBoost trả nhãn, xác suất • lưu flow và cảnh báo vào SQLite':'Feeder submits flows • check 78 columns, order, and units\nXGBoost returns labels and probabilities • store flows and alerts in SQLite',
'SHAP CHẠY NỀN':'BACKGROUND SHAP',
'Cảnh báo vào hàng đợi tối đa 200 tác vụ\nLuồng nền tính SHAP và các cờ lưu ý\nHàng đợi đầy vẫn giữ dự đoán, cảnh báo':'Alerts enter a queue of up to 200 tasks\nBackground thread computes SHAP and flags\nPredictions and alerts retained if queue is full',
'LIME THEO YÊU CẦU':'LIME ON REQUEST',
'Chỉ chạy khi người dùng yêu cầu\nKiểm tra vùng mẫu và mô hình cục bộ\nThông báo rõ khi chưa giải thích được':'Runs only on user request\nCheck the neighborhood and local model\nClearly report unavailable explanations',
'LƯU TRỮ VÀ GIAO DIỆN':'STORAGE AND INTERFACE',
'SQLite lưu kết quả • Streamlit truy vấn qua API\nHiển thị flow, dự đoán, SHAP, LIME và nhánh lưu ý A hoặc B':'SQLite stores results • Streamlit queries through the API\nDisplay flows, predictions, SHAP, LIME, and advisory branch A or B',
'ĐIỀU KHIỂN CAPTURE DO API QUẢN LÝ':'API-MANAGED CAPTURE CONTROL',
'Giao diện gửi lệnh bắt hoặc dừng • API quản lý capture và bộ cấp dữ liệu\nTheo dõi trạng thái, ngăn phiên trùng • làm mới trang không tạo phiên mới':'Interface sends start or stop commands • API manages capture and feeder\nMonitor status and prevent duplicate sessions • refresh does not create a session',
}
tree=ast.parse((ROOT/'Report/revise_chapters34.py').read_text(encoding='utf-8'))
fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='diagram')
exec(compile(ast.Module(body=[fn],type_ignores=[]),'diagram','exec'))
# Keep the original geometry, shapes, and arrows; translate labels only.
def convert(obj):
    if isinstance(obj,str): return labels.get(obj,obj)
    if isinstance(obj,(list,tuple)): return type(obj)(convert(v) for v in obj)
    return obj
for n in tree.body:
    if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Name) and n.value.func.id=='diagram':
        args=[convert(ast.literal_eval(a)) for a in n.value.args]
        diagram(*args)

# Reuse the original plotting code and original numerical data; change labels
# and output destination only.
src=(ROOT/'Report/plot_chapter4.py').read_text(encoding='utf-8')
src=src.replace('fig.savefig(A/name','fig.savefig(QA/name')
repl={
'Số flow (thang logarit)':'Flow count (logarithmic scale)',
'Nhãn thật':'True label','Nhãn dự đoán':'Predicted label','Tỷ lệ theo hàng':'Row proportion',
'Ngưỡng 0,3':'Threshold 0.3','R² cục bộ của LIME':'Local LIME R²','Số flow':'Flow count',
'Số đặc trưng top-k':'Number of top-k features','Jaccard trung bình':'Mean Jaccard',
'Trung vị train':'Training median','Trung bình train':'Training mean','Trung vị Benign':'Benign median',
'Mức giảm xác suất trung bình':'Mean probability decrease','Flow API đã nhận':'Flows received by API',
'Thời gian đã chạy (phút)':'Elapsed time (minutes)','RSS quan sát (MiB)':'Observed RSS (MiB)',
'Đóng góp SHAP vào điểm thô của lớp Hulk':'SHAP contribution to the raw Hulk class score',
}
for vi,en in repl.items(): src=src.replace(vi,en)
exec(compile(src,'plot_chapter4_en','exec'))
import pandas as pd
import matplotlib.pyplot as plt
noise=pd.read_csv(ROOT/'Report/chapter4_assets/revision_rq2/gd9_stability_robustness/rq2_2_noise_robustness.csv')
with plt.rc_context({'font.size':12,'axes.spines.top':True,'axes.spines.right':True}):
    fig,ax=plt.subplots(figsize=(9,6))
    x=[0]+(noise.sigma_fraction*100).tolist()
    ax.plot(x,[1]+noise.shap_mean_jaccard5.tolist(),'-o',label='SHAP')
    ax.plot(x,[1]+noise.lime_mean_jaccard5.tolist(),'-s',label='LIME')
    ax.set(title='Robustness to input perturbations',xlabel='Noise level (% of feature standard deviation)',ylabel='Jaccard@5 against the original explanation')
    ax.legend();fig.tight_layout();fig.savefig(QA/'noise_robustness.png',dpi=180);plt.close(fig)
print('Translated 2 diagrams and 7 charts without changing numerical inputs.')
