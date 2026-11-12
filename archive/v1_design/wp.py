"""Author a wrong patch: wp.py <iid> <n> <spec.py>; spec defines EDITS=[(file, old, new), ...] and DESC='...'."""
import sys, os, subprocess, json
iid, n, spec = sys.argv[1], sys.argv[2], sys.argv[3]
ns = {}; exec(open(spec).read(), ns)
ws = f"work/scratch/{iid}"; g = lambda *a: subprocess.run(["git", "-C", ws, "-c", "safe.directory=*", *a], capture_output=True, text=True)
g("checkout", "-q", "--", ".")
if ns.get("APPLY_GOLD"):
    r = subprocess.run(["git", "-C", ws, "-c", "safe.directory=*", "apply", "--exclude=CHANGELOG*", os.path.abspath(f"work/inst/{iid}/gold.diff")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
for f, old, new in ns["EDITS"]:
    p = os.path.join(ws, f); s = open(p).read()
    assert s.count(old) == 1, f"{f}: old text found {s.count(old)} times"
    open(p, "w").write(s.replace(old, new))
d = g("diff").stdout; g("checkout", "-q", "--", "."); g("clean", "-fdq")
os.makedirs(f"wrong_patches/{iid}", exist_ok=True)
open(f"wrong_patches/{iid}/w{n}.diff", "w").write(d)
open(f"wrong_patches/{iid}/w{n}.md", "w").write(ns["DESC"].strip() + "\n")
print(d)
