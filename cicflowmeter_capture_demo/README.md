# CICFlowMeter capture demo

Muc tieu cua thu muc nay la duy nhat: bat traffic that tren Wi-Fi va xuat feature flow ra CSV. Khong co dashboard, API, model hay packet attack trong demo nay.

## Dieu kien

- Npcap da cai.
- Python 3.14 da cai va lenh `py -3.14 --version` hoat dong.
- Mo PowerShell hoac VS Code bang **Run as administrator**.

Python 3.11 se cai CICFlowMeter 0.2.0 cu, co loi ghi flow tren Windows. Demo nay dung CICFlowMeter 0.5.0 va vi vay can Python 3.12 tro len.

## Buoc 1 - Cai moi truong rieng

Mo PowerShell trong thu muc nay va chay:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\setup.ps1
```

## Buoc 2 - Bat flow

```powershell
.\capture.ps1 -Interface "Wi-Fi" -Output "flows.csv"
```

`capture.ps1` uses the included `capture_live.py` launcher. This avoids a parameter-order bug in the upstream CICFlowMeter 0.5.0 command-line entry point.

Mo Chrome, truy cap va tim kiem tren vai website trong 1-2 phut. Sau do nhan `Ctrl+C` mot lan de CICFlowMeter dong flow va ghi CSV.

## Buoc 3 - Kiem tra CSV

```powershell
.\.venv\Scripts\python.exe .\verify_csv.py .\flows.csv
```

Ket qua dung phai bao CSV khac 0 byte, co flow dau tien, va liet ke feature nhu `Destination Port`, `Protocol`, `Flow Duration`, `Total Fwd Packets`.

## Neu khong bat duoc

1. Kiem tra `Wi-Fi` dang co trang thai Up bang `Get-NetAdapter`.
2. Chay PowerShell bang Administrator.
3. Kiem tra Npcap da cai va chon dung network interface.
4. Khong dung `localhost` de test; truy cap website ben ngoai de traffic di qua Wi-Fi.
