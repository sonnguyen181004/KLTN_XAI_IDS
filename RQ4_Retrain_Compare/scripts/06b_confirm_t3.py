"""Dựng T3 từ nhật ký phiên. Người dùng xác nhận bằng lời ngày 26/10/2026 rằng toàn bộ các phiên realtime (feeder_live)
là lưu lượng bình thường. Nhật ký này chỉ có lời xác nhận đó, chưa có chi tiết từng hoạt động, nên T3 chỉ mạnh bằng lời xác nhận."""
import pandas as pd
from rq4_common import *

tpl = pd.read_csv(RESULTS / "t3_session_log_template.csv")
tpl["activity"] = "Người dùng xác nhận lưu lượng bình thường (không có tấn công); chưa ghi chi tiết hoạt động"
tpl["benign_confirmed"] = "yes"
tpl["confirmed_by"] = "người dùng, bằng lời, 26/10/2026"
tpl.to_csv(RESULTS / "t3_session_log.csv", index=False, encoding="utf-8-sig")
c = pd.read_parquet(DATA / "t3_candidates.parquet")
ok = c.run.isin(tpl.loc[tpl.benign_confirmed == "yes", "run"])
t3 = c[ok][FEATURES].copy(); t3["Label"] = "Benign"
t3.to_parquet(DATA / "t3_benign_confirmed.parquet", index=False)
print("T3:", len(t3), "flow Benign đã xác nhận")
