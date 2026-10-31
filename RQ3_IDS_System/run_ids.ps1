# Chạy RQ3_IDS_System: API (8000) + Dashboard (8501) cùng một token điều khiển realtime.
# Chạy từ thư mục RQ3_IDS_System:  .un_ids.ps1   (mở PowerShell bằng quyền Administrator nếu Npcap yêu cầu)
# Token tạo mới mỗi lần chạy, không lưu vào file. Không chạy song song với bản IDS_M1_Lab (cùng cổng 8000 và 8501).
$env:IDS_CAPTURE_CONTROL_TOKEN = [guid]::NewGuid().ToString('N')
$env:IDS_CAPTURE_API_URL = 'http://127.0.0.1:8000'
$env:IDS_API_URL = 'http://127.0.0.1:8000'
Remove-Item Env:IDS_DB_PATH -ErrorAction SilentlyContinue
Remove-Item Env:IDS_CAPTURE_SESSION_DIR -ErrorAction SilentlyContinue
Start-Process powershell -ArgumentList '-NoExit','-Command',"cd '$PSScriptRoot'; python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1"
Start-Sleep -Seconds 15
Start-Process powershell -ArgumentList '-NoExit','-Command',"cd '$PSScriptRoot'; python -m streamlit run app/dashboard.py --server.address 127.0.0.1 --server.port 8501"
Write-Host 'Mở http://127.0.0.1:8501 rồi vào tab Realtime. Hai cửa sổ mới mang cùng token; đóng cả hai cửa sổ để dừng.'
