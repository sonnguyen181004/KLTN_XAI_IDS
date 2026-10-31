"""Basic consistency checks for main.tex (no TeX compiler is available on this machine)."""
import re

BASE = __import__("pathlib").Path(__file__).resolve().parents[1]
t = open(BASE / "main.tex", encoding="utf-8").read()
bs = chr(92)
pct = [m.start() for m in re.finditer("(?<!" + re.escape(bs) + ")%", t)]
print("unescaped percent signs:", len(pct), [t[max(0, i - 20):i + 5] for i in pct[:3]])
print("braces balance (0 is fine):", t.count("{") - t.count("}"))
envs = re.findall(re.escape(bs) + r"begin\{([a-zA-Z*]+)\}", t)
ends = re.findall(re.escape(bs) + r"end\{([a-zA-Z*]+)\}", t)
print("begin/end environments match:", sorted(envs) == sorted(ends), len(envs))
cites = set(k.strip() for g in re.findall(re.escape(bs) + r"cite\{([^}]*)\}", t) for k in g.split(","))
bib = set(re.findall(r"@\w+\{([\w]+),", open(BASE / "refs.bib", encoding="utf-8").read()))
print("cited but missing in refs.bib:", sorted(cites - bib))
print("in refs.bib but never cited:", sorted(bib - cites))
labels = set(re.findall(re.escape(bs) + r"label\{([^}]*)\}", t))
refs = set(re.findall(re.escape(bs) + r"ref\{([^}]*)\}", t))
print("labels without ref:", sorted(labels - refs), "| refs without label:", sorted(refs - labels))
macros = set(re.findall(re.escape(bs) + r"(rq[A-Za-z]+)", t))
defined = set(re.findall(re.escape(bs) + r"newcommand\{" + re.escape(bs) + r"(rq[A-Za-z]+)\}", open(BASE / "rq1_numbers.tex", encoding="utf-8").read()))
print("macros used but not defined:", sorted(macros - defined))
