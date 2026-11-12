"""Run a test command in a fresh instance container (--network none) after applying patches and adding files."""
import json, os, re, subprocess, tempfile, shutil, uuid

STATUSES = ("PASSED", "FAILED", "ERROR", "SKIPPED", "XFAIL", "XPASS")

def parse_pytest(out):
    res = {}
    for line in out.splitlines():
        line = line.strip()
        for st in STATUSES:
            if line.startswith(st + " "):
                rest = line[len(st) + 1:]
                if st in ("FAILED", "ERROR"):
                    rest = re.split(r" - ", rest, 1)[0]
                nid = rest.strip()
                if "::" not in nid and st == "ERROR":  # collection error of a file
                    nid = nid + "::<COLLECTION_ERROR>"
                # worst outcome wins if a node appears twice (e.g. PASSED then ERROR in teardown)
                prev = res.get(nid)
                if prev is None or prev == "PASSED" or st in ("FAILED", "ERROR"):
                    res[nid] = st
                break
    return res

def run(image, patches=(), files=None, cmd="", timeout=900, mem="3g", label="lc1a0"):
    d = tempfile.mkdtemp(prefix="lc1a0_")
    try:
        os.makedirs(f"{d}/files")
        for i, p in enumerate(patches):
            open(f"{d}/p{i:02d}.diff", "w").write(p)
        for rel, content in (files or {}).items():
            fp = os.path.join(d, "files", rel); os.makedirs(os.path.dirname(fp), exist_ok=True)
            open(fp, "w").write(content)
        script = """set -u
cd /testbed
for p in /lc_in/p*.diff; do [ -e "$p" ] || continue
  git apply --whitespace=nowarn "$p" 2>/tmp/applyerr || patch -p1 --forward --batch < "$p" >/tmp/applyerr2 2>&1 || { echo "@@LC_APPLY_FAIL $p"; cat /tmp/applyerr; exit 97; }
done
cp -r /lc_in/files/. /testbed/ 2>/dev/null
echo "@@LC_START"
""" + cmd + """
echo "@@LC_EXIT $?"
"""
        open(f"{d}/run.sh", "w").write(script)
        os.chmod(d, 0o755)
        for root, dirs, fs in os.walk(d):
            for x in dirs: os.chmod(os.path.join(root, x), 0o755)
            for x in fs: os.chmod(os.path.join(root, x), 0o644)
        name = f"lc1a0_{uuid.uuid4().hex[:10]}"
        argv = ["docker", "run", "--rm", "--name", name, "--network", "none", "--memory", mem, "--cpus", "2",
                "--pids-limit", "1024", "--label", label, "-e", "HOME=/tmp", "-e", "PYTHONDONTWRITEBYTECODE=1",
                "-v", f"{d}:/lc_in:ro", image, "bash", "/lc_in/run.sh"]
        try:
            p = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
            out, rc, to = p.stdout + "\n" + p.stderr, p.returncode, False
        except subprocess.TimeoutExpired as e:
            subprocess.run(["docker", "rm", "-f", name], capture_output=True)
            out, rc, to = (e.stdout or b"").decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or ""), None, True
        apply_fail = "@@LC_APPLY_FAIL" in out
        m = re.search(r"@@LC_EXIT (\d+)", out)
        return {"outcomes": parse_pytest(out.split("@@LC_START", 1)[-1]), "rc": rc, "timeout": to,
                "apply_fail": apply_fail, "test_exit": int(m.group(1)) if m else None, "log": out}
    finally:
        shutil.rmtree(d, ignore_errors=True)
