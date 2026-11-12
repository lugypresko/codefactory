"""One mini-SWE-agent run inside an instance-image sandbox (network cut) on a sanitized /testbed copy."""
import json, os, re, subprocess, time, shutil, fnmatch
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VENV = os.path.join(ROOT, ".venv")
MODEL = os.environ.get("LC1A0_MODEL", "gemini/gemini-2.5-flash")
LEDGER = os.path.join(ROOT, "work", "cost_ledger.jsonl")
BUDGET = 25.0
BENIGN = ("__pycache__/", ".pytest_cache/", ".hypothesis/", ".coverage", ".pyc", ".mypy_cache/", ".ruff_cache/")

def spent():
    try: return sum(json.loads(l)["cost_usd"] or 0 for l in open(LEDGER))
    except FileNotFoundError: return 0.0

def sh(*a, **k):
    return subprocess.run(a, capture_output=True, text=True, **k)

def git(ws, *a):
    return sh("git", "-C", ws, "-c", "safe.directory=*", *a)

def prep_ws(image, ws, extra_files=None):
    """Copy /testbed out of the image; replace its git history with one fresh commit (no future commits leak)."""
    if os.path.exists(ws): shutil.rmtree(ws, ignore_errors=True) or sh("docker", "run", "--rm", "-v", f"{os.path.dirname(ws)}:/x", "busybox", "rm", "-rf", f"/x/{os.path.basename(ws)}")
    os.makedirs(os.path.dirname(ws), exist_ok=True)
    cid = sh("docker", "create", image).stdout.strip()
    try:
        r = sh("docker", "cp", f"{cid}:/testbed", ws)
        if r.returncode: raise RuntimeError("docker cp failed: " + r.stderr)
    finally:
        sh("docker", "rm", "-f", cid)
    shutil.rmtree(os.path.join(ws, ".git"), ignore_errors=True)
    env = dict(os.environ, GIT_AUTHOR_NAME="lc1a0", GIT_AUTHOR_EMAIL="lc1a0@local", GIT_COMMITTER_NAME="lc1a0",
               GIT_COMMITTER_EMAIL="lc1a0@local", GIT_AUTHOR_DATE="2026-01-01T00:00:00Z", GIT_COMMITTER_DATE="2026-01-01T00:00:00Z")
    for c in (["init", "-q"], ["add", "-A"], ["commit", "-q", "--no-verify", "-m", "base (sanitized)"]):
        r = subprocess.run(["git", "-C", ws, "-c", "safe.directory=*", *c], capture_output=True, text=True, env=env)
        if r.returncode: raise RuntimeError("git " + " ".join(c) + ": " + r.stderr)
    base = git(ws, "rev-parse", "HEAD").stdout.strip()
    for rel, content in (extra_files or {}).items():
        fp = os.path.join(ws, rel); os.makedirs(os.path.dirname(fp), exist_ok=True); open(fp, "w").write(content)
    sh("chmod", "-R", "a+rwX", ws)
    return base

def is_test_file(path):
    b = os.path.basename(path)
    return b.endswith(".py") and (b.startswith("test_") or b.endswith("_test.py"))

def classify(ws, base):
    """Return dict: tests{path:content}, clarification, violations[], benign[]"""
    head = git(ws, "rev-parse", "HEAD").stdout.strip()
    st = git(ws, "status", "--porcelain=v1", "--untracked-files=all", "-z").stdout
    out = {"tests": {}, "clarification": None, "violations": [], "benign": [], "head_moved": head != base}
    if head != base:
        out["violations"].append(f"HEAD moved {base[:8]}->{head[:8]}")
    ents = [e for e in st.split("\0") if e]
    for e in ents:
        code, path = e[:2], e[3:]
        if any(b in path or path.endswith(b) for b in BENIGN):
            out["benign"].append(path); continue
        if code == "??":
            if path == "CLARIFICATION_NEEDED.md":
                out["clarification"] = open(os.path.join(ws, path), errors="replace").read()
            elif is_test_file(path):
                out["tests"][path] = open(os.path.join(ws, path), errors="replace").read()
            else:
                out["violations"].append(f"new non-test file: {path}")
        else:
            out["violations"].append(f"{code.strip()} tracked file: {path}")
    return out

def run(role, rid, image, task, ws, run_dir, cost, steps, wall, extra_mounts=(), base_cfg=None):
    base_cfg = base_cfg or os.path.join(ROOT, "mini_base.yaml")
    os.makedirs(run_dir, exist_ok=True)
    if spent() + cost > BUDGET:
        return {"status": "BUDGET_STOP", "cost_usd": 0.0, "spent_before": spent()}
    cfg = f"""agent:
  step_limit: {steps}
  cost_limit: {cost}
  wall_time_limit_seconds: {wall}
environment:
  environment_class: docker
  image: {image}
  executable: docker
  cwd: /testbed
  timeout: 120
  forward_env: []
  env: {{HOME: /tmp, PAGER: cat, MANPAGER: cat, PYTHONDONTWRITEBYTECODE: "1", PIP_NO_INDEX: "1"}}
  run_args: ["--rm", "--network", "none", "--user", "{os.getuid()}:{os.getgid()}", "--cap-drop", "ALL",
             "--security-opt", "no-new-privileges", "--memory", "1536m", "--cpus", "1", "--pids-limit", "256",
             "--label", "lc1a0.run={rid}", "-v", "{ws}:/testbed"{''.join(', "-v", "%s"' % m for m in extra_mounts)}]
"""
    open(f"{run_dir}/config.yaml", "w").write(cfg)
    open(f"{run_dir}/task.txt", "w").write(task)
    env = dict(os.environ, MSWEA_CONFIGURED="true", MSWEA_SILENT_STARTUP="1",
               MSWEA_GLOBAL_CONFIG_DIR=os.path.join(ROOT, "work", ".mswea"))
    t0 = time.time(); rc = None
    with open(f"{run_dir}/agent_stdout.log", "w") as lf:
        try:
            rc = subprocess.run(["timeout", "--kill-after=30", str(wall + 120), f"{VENV}/bin/mini", "--agent-class", "default",
                                 "-m", MODEL, "-c", base_cfg, "-c", f"{run_dir}/config.yaml", "-t", task,
                                 "-o", f"{run_dir}/trajectory.json"], stdin=subprocess.DEVNULL, stdout=lf, stderr=lf, env=env).returncode
        finally:
            ids = sh("docker", "ps", "-aq", "--filter", f"label=lc1a0.run={rid}").stdout.split()
            if ids: sh("docker", "rm", "-f", *ids)
    res = {"base_config": base_cfg, "mounts": [f"{ws}:/testbed"] + list(extra_mounts), "network": "none (container); LLM calls from host process only", "role": role, "run_id": rid, "mini_rc": rc, "wall_seconds": round(time.time() - t0),
           "caps": {"cost": cost, "steps": steps, "wall": wall}, "model_requested": MODEL}
    tp = f"{run_dir}/trajectory.json"
    if os.path.exists(tp):
        t = json.load(open(tp)); info = t.get("info", {}); s = info.get("model_stats", {})
        res.update(exit_status=info.get("exit_status"), cost_usd=s.get("instance_cost"), api_calls=s.get("api_calls"),
                   models_returned=sorted({m.get("extra", {}).get("response", {}).get("model") for m in t.get("messages", [])
                                           if m.get("role") == "assistant" and m.get("extra", {}).get("response")} - {None}))
    else:
        res.update(exit_status=None, cost_usd=None, api_calls=None)
    if rc in (124, 137) or res.get("exit_status") == "TimeExceeded": res["status"] = "WALL_TIMEOUT"
    elif res.get("exit_status") == "Submitted": res["status"] = "SUBMITTED"
    elif res.get("exit_status") == "LimitsExceeded": res["status"] = "LIMIT_EXCEEDED"
    elif res.get("exit_status") is None: res["status"] = "AGENT_CRASH"
    else: res["status"] = str(res.get("exit_status"))
    with open(LEDGER, "a") as f:
        f.write(json.dumps({"run_id": rid, "role": role, "cost_usd": res.get("cost_usd") or 0.0, "ts": time.strftime("%FT%T%z")}) + "\n")
    res["spent_total_after"] = round(spent(), 4)
    json.dump(res, open(f"{run_dir}/agent_result.json", "w"), indent=2)
    return res
