"""Đối chiếu mọi con số của bản tiếng Anh với bản tiếng Việt (sau khi đổi sang cách viết Việt)."""
import re
import subprocess
import sys

SC = r"C:\Users\LOQ\AppData\Local\Temp\claude\c--Users-LOQ-Downloads-SELF-KLTN\96b00ab1-186e-47c7-b074-f796ff82f25e\scratchpad"


def plain(tex):
    out = subprocess.run(["pandoc", tex, "-t", "plain", "--wrap=none"], capture_output=True, encoding="utf-8").stdout
    cut = out.find("Tài liệu tham khảo")
    return out if cut < 0 else out[:cut]


from pathlib import Path
BASE = Path(__file__).resolve().parents[1]
en = plain(str(BASE / "main.tex"))
vi = plain(str(BASE / "main_vi.tex"))
en = en[: en.find("References")] if "References" in en else en


def tokens(t):
    t = re.sub(r"\[[a-z]+:[a-z0-9]+\]", " ", t)          # nhãn tham chiếu
    return re.findall(r"\d[\d,\.]*\d|\d", t)


def to_vn(tok):
    if re.fullmatch(r"\d{1,3}(,\d{3})+", tok):            # 2,800,000 -> 2.800.000
        return tok.replace(",", ".")
    if re.fullmatch(r"\d+\.\d+", tok):                    # 97.91 -> 97,91
        return tok.replace(".", ",")
    return tok


vi_tokens = set(tokens(vi))
vi_text = vi
missing = []
for tok in sorted(set(tokens(en))):
    v = to_vn(tok)
    if v not in vi_tokens and v not in vi_text:
        missing.append((tok, v))
print("so token so trong ban Anh:", len(set(tokens(en))), "| khong thay trong ban Viet:", len(missing))
for tok, v in missing:
    i = en.find(tok)
    print("  ", tok, "->", v, "| ngu canh EN:", en[max(0, i - 40):i + 30].replace("\n", " "))
