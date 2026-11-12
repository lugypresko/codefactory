import json, os, re, hashlib
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
H = lambda s: hashlib.sha256(s.encode() if isinstance(s, str) else s).hexdigest()
def sample(): return json.load(open(f"{ROOT}/sample_v2.json"))
def items(): return {x["instance_id"]: x for x in sample()["instances"]}
def issue_text(iid): return open(f"{ROOT}/work/inst/{iid}/issue.md").read()
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
