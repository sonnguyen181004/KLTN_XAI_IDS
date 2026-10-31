# Chạy IDS_M1_Lab: API (8000) + Dashboard (8501) với điều khiển realtime bật sẵn.
# Chạy từ thư mục IDS_M1_Lab:  .\run_ids.ps1
$env:IDS_CAPTURE_CONTROL_TOKEN = 'ids-m1-lab-local-control-token-0123456789'
Start-Process powershell -ArgumentList '-NoExit','-Command',"cd '$PSScriptRoot'; uvicorn app.main:app --port 8000"
Start-Sleep -Seconds 15
Start-Process powershell -ArgumentList '-NoExit','-Command',"cd '$PSScriptRoot'; streamlit run app/dashboard.py --server.port 8501 --server.address 127.0.0.1"
