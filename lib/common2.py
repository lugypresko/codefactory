import json, os, re, hashlib
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = lambda s: hashlib.sha256(s.encode() if isinstance(s, str) else s).hexdigest()
def sample(): return json.load(open(f"{ROOT}/sample_v2.json"))
def items(): return {x["instance_id"]: x for x in sample()["instances"]}
def _abs(p):
    return p if os.path.isabs(p) else os.path.abspath(os.path.join(ROOT, p))
def results_root():
    r = os.environ.get("LC_RESULTS")
    return _abs(r) if r else f"{ROOT}/results"
def runs_root():
    """Opt-in run dir. Default remains {ROOT}/work/runs. When LC_OUT or LC_RESULTS is set,
    never fall back to the LC-1A.0 work/runs tree (use a sibling of LC_OUT, or LC_RESULTS/runs)."""
    if os.environ.get("LC_RUNS"): return _abs(os.environ["LC_RUNS"])
    if os.environ.get("LC_OUT"): return _abs(os.environ["LC_OUT"]) + "_run"
    if os.environ.get("LC_RESULTS"): return os.path.join(results_root(), "runs")
    return f"{ROOT}/work/runs"
def ledger_path():
    """Opt-in cost ledger. Default remains work/cost_ledger.jsonl. Side runs (LC_OUT/LC_RESULTS) get their own file."""
    if os.environ.get("LC_LEDGER"): return _abs(os.environ["LC_LEDGER"])
    if os.environ.get("LC_OUT") or os.environ.get("LC_RESULTS"):
        return os.path.join(runs_root(), "cost_ledger.jsonl")
    return os.path.join(ROOT, "work", "cost_ledger.jsonl")
def inst(iid):
    """Instance metadata. LC_IMAGE (opt-in) bypasses sample_v2.json; defaults unchanged."""
    if os.environ.get("LC_IMAGE"):
        return {"instance_id": iid, "docker_image": os.environ["LC_IMAGE"],
                "base_commit": os.environ.get("LC_BASE_COMMIT", ""), "FAIL_TO_PASS": [], "P2P_eff": []}
    return items()[iid]
def issue_text(iid):
    p = os.environ.get("LC_ISSUE_FILE")
    return open(p if p else f"{ROOT}/work/inst/{iid}/issue.md").read()
TEST_DIR_RE = re.compile(r'(^|/)(tests?|testing)/')
def is_testish(path):
    b = os.path.basename(path)
    return (b.endswith(".py") and (b.startswith("test_") or b.endswith("_test.py") or b == "conftest.py")) or bool(TEST_DIR_RE.search(path))
def split_diff(diff):
    return [p for p in re.split(r'(?=^diff --git )', diff, flags=re.M) if p.startswith("diff --git ")]
def diff_path(part):
    m = re.match(r'diff --git a/(\S+) b/(\S+)', part); return m.group(2) if m else None
def strip_tests(diff):
    kept, dropped = [], []
    for p in split_diff(diff):
        (dropped if is_testish(diff_path(p)) else kept).append(p)
    return "".join(kept), [diff_path(p) for p in dropped]
def pytest_cmd(files): return "pytest --no-header -rA --tb=short --color=no -p no:cacheprovider " + " ".join(sorted(files))
