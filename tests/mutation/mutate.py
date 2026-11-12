#!/usr/bin/env python3
"""Small hand-rolled mutation check for lib/lc0util.py: mutates the TARGETS functions one operator at a
time and runs `selftest.py --unit-only --no-strict`. A mutant is KILLED if any unit case fails or the run crashes.
Usage: mutate.py <package_root> [out.json]"""
import json, re, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
# v1.4 targets + v1.5 targets (contract loader, scoring body, forbidden actions, combined verdict)
TARGETS = ["def diff_policy(", "def recovery(", "def _checks(", "def contract(", "def _score(", "def _forbidden(", "def lc0_verdict(",
           "def injected_artifacts(", "def _diff_paths(", "def _tree_hashes("]
OPS = [(r"==", "!="), (r"!=", "=="), (r"\band\b", "or"), (r"\bor\b", "and"), (r"\bnot\s+", ""), (r"\bTrue\b", "False"),
       (r"\bFalse\b", "True"), (r'"OK"', '"ESCALATE"'), (r"\ball\(", "any("), (r"\bany\(", "all("), (r"rc == 0", "rc != 0"),
       (r"\bis False\b", "is True"), (r"hit \+ 1", "hit")]
src = (ROOT / "lib/lc0util.py").read_text(); lines = src.splitlines(keepends=True)
ranges = []
for t in TARGETS:
    i = next(k for k, l in enumerate(lines) if l.startswith(t)); j = i + 1
    while j < len(lines) and (lines[j].startswith((" ", "\t", "\n")) or lines[j].strip() == ""):
        j += 1
    ranges.append((t, i, j))
mutants = []
for t, i, j in ranges:
    for k in range(i + 1, j):
        l = lines[k]; code = l.split("#")[0]
        if code.strip().startswith(('"""', "r = {", "print(")) or '"""' in code:
            continue
        for pat, rep in OPS:
            for m in re.finditer(pat, code):
                mutants.append((t, k, l[:m.start()] + rep + l[m.end():]))
        if any(x in code for x in ("viol.append(", "viol +=", "hits.append(", "raise ContractError(")) and not code.strip().startswith("if "):
            mutants.append((t, k, re.sub(r"\S.*", "pass  # mutant: dropped violation", l, count=1)))
res = []; tmp = Path(tempfile.mkdtemp())
try:
    pkg = tmp / "pkg"; shutil.copytree(ROOT, pkg, ignore=shutil.ignore_patterns(".venv", "work", "evidence", "__pycache__"))
    for t, k, new in mutants:
        mut = lines[:k] + [new] + lines[k + 1:]; (pkg / "lib/lc0util.py").write_text("".join(mut))
        p = subprocess.run(["python3", str(pkg / "lib/selftest.py"), str(pkg), "--unit-only", "--no-strict"], capture_output=True, text=True, timeout=60,
                           env={**__import__("os").environ, "PYTHONDONTWRITEBYTECODE": "1"})  # no stale .pyc between mutants
        killed = p.returncode != 0
        res.append({"function": t[4:-1], "line": k + 1, "original": lines[k].strip()[:110], "mutant": new.strip()[:110], "killed": killed})
finally:
    shutil.rmtree(tmp, ignore_errors=True)
k = sum(r["killed"] for r in res)
out = {"mutants": len(res), "killed": k, "score": round(k / len(res), 3) if res else None, "survivors": [r for r in res if not r["killed"]]}
if len(sys.argv) > 2:
    Path(sys.argv[2]).write_text(json.dumps(out, indent=2))
print(json.dumps({"mutants": out["mutants"], "killed": k, "score": out["score"]}))
for s in out["survivors"]:
    print(f"SURVIVED {s['function']}:{s['line']}  {s['original']}  ->  {s['mutant']}")
