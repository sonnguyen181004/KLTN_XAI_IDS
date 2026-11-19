# M0_Lab_Adaptation_Trial: thử huấn luyện tiếp M0 bằng flow tấn công lab

Thử nghiệm offline. Không sửa M0, M1, dashboard hay DB. Kết quả: [docs/findings.md](docs/findings.md). Kế hoạch và tiến độ: [docs/plan.md](docs/plan.md), [docs/progress.md](docs/progress.md).

## Chạy lại (từ gốc repo)

```powershell
python M0_Lab_Adaptation_Trial/scripts/01_inventory.py                 # mã băm PCAP, M0, thứ tự đặc trưng
python M0_Lab_Adaptation_Trial/scripts/02_extractor_packet_audit.py    # đối soát packet và flow Java
python M0_Lab_Adaptation_Trial/scripts/03_flag_convention_audit.py     # quy ước cột cờ
python M0_Lab_Adaptation_Trial/scripts/04_build_labeled_and_splits.py  # gán nhãn, chia lượt
python M0_Lab_Adaptation_Trial/scripts/05_continue_train.py            # huấn luyện tiếp, cấu hình configs/continue_v1.yaml
python M0_Lab_Adaptation_Trial/scripts/06_evaluate.py                  # lab, test gốc, thử đường tắt
```

Đầu vào: PCAP và CSV Java đã trích trong `Java_CICFlowMeter_M0_Trial/` (`output/attack_load_report_20261118/`), `dataset/CICID-2018_processed/`. `data/` và `models/` không đưa vào git; dựng lại bằng các script trên.
