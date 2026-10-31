"""Read RQ1 repeat-run results and write rq1_numbers.tex (macros used by main.tex)."""
import glob
import json
import statistics as st
from pathlib import Path

RUNS = Path(r"C:\Users\LOQ\Downloads\SELF_KLTN\RQ1_Model_Training_xboost\results\repeat_runs")
OUT = Path(r"C:\Users\LOQ\Downloads\SELF_KLTN\Paper_IEEE\rq1_numbers.tex")
runs = [json.load(open(f, encoding="utf-8")) for f in sorted(glob.glob(str(RUNS / "seed_*.json")))]
n = len(runs)
names = {"accuracy": "Acc", "macro_precision": "Prec", "macro_recall": "Rec", "macro_f1": "Fone", "fpr": "Fpr", "fnr": "Fnr"}
lines = [f"\\newcommand{{\\rqRuns}}{{{n}}}"]
summary = {}
for part, pre in (("full", "Full"), ("dedup", "Dedup")):
    for key, short in names.items():
        v = [r[part][key] for r in runs]
        mean, sd = st.mean(v), (st.stdev(v) if n > 1 else 0.0)
        dec = 3 if key in ("accuracy", "fpr", "fnr") else 2
        lines.append(f"\\newcommand{{\\rq{pre}{short}}}{{{mean:.{dec}f} $\\pm$ {sd:.{dec}f}}}")
        summary[f"{part}_{key}"] = (round(mean, 4), round(sd, 4))
share = st.mean(r["duplicated_with_train"] / r["test_rows"] * 100 for r in runs)
lines.append(f"\\newcommand{{\\rqDupShare}}{{{share:.1f}}}")
OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
json.dump(dict(n=n, seeds=[r["seed"] for r in runs], summary=summary, dup_share=share), open(RUNS / "summary_from_seed_files.json", "w"), indent=1)
print(n, "runs;", OUT)
for k, v in summary.items():
    print(k, v)
print("dup share %.2f" % share)
