"""Opt-in env hooks leave LC-1A.0 default paths unchanged, and isolate side-run ledgers/runs."""
import os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "lib"))
import common2 as c
# common2.ROOT is derived from its file location (= repo root)

def _clear():
    for k in ("LC_OUT", "LC_RESULTS", "LC_RUNS", "LC_LEDGER", "LC_IMAGE", "LC_ISSUE_FILE", "LC_BASE_COMMIT", "LC_NO_GT", "LC_CAPTURE_FAIL"):
        os.environ.pop(k, None)

def test_defaults_match_lc1a0():
    _clear()
    assert c.results_root() == os.path.join(c.ROOT, "results")
    assert c.runs_root() == os.path.join(c.ROOT, "work", "runs")
    assert c.ledger_path() == os.path.join(c.ROOT, "work", "cost_ledger.jsonl")

def test_lc_out_does_not_touch_work():
    _clear()
    os.environ["LC_OUT"] = "results_lc1a1/iid/attempt1"
    rr, lp = c.runs_root(), c.ledger_path()
    work_runs = os.path.join(c.ROOT, "work", "runs")
    work_led = os.path.join(c.ROOT, "work", "cost_ledger.jsonl")
    assert not rr.startswith(work_runs + os.sep) and rr != work_runs
    assert lp != work_led
    assert rr.endswith("attempt1_run")
    assert lp.endswith("attempt1_run/cost_ledger.jsonl")
    assert os.path.abspath(c.results_root()) == os.path.join(c.ROOT, "results")  # LC_RESULTS not set
    _clear()

def test_lc_results_and_explicit_ledger():
    _clear()
    os.environ["LC_RESULTS"] = "results_cf"
    assert c.results_root() == os.path.join(c.ROOT, "results_cf")
    assert c.runs_root() == os.path.join(c.ROOT, "results_cf", "runs")
    assert c.ledger_path() == os.path.join(c.ROOT, "results_cf", "runs", "cost_ledger.jsonl")
    os.environ["LC_LEDGER"] = "results_cf/cost_ledger.jsonl"
    os.environ["LC_RUNS"] = "results_cf/runs"
    assert c.ledger_path() == os.path.join(c.ROOT, "results_cf", "cost_ledger.jsonl")
    assert c.runs_root() == os.path.join(c.ROOT, "results_cf", "runs")
    _clear()

def test_inst_and_issue_opt_in(tmp_path=None):
    _clear()
    # default inst() needs sample_v2; just check LC_IMAGE bypass
    os.environ["LC_IMAGE"] = "cf-demo:local"
    os.environ["LC_BASE_COMMIT"] = "abc"
    it = c.inst("cf-demo")
    assert it["docker_image"] == "cf-demo:local" and it["base_commit"] == "abc" and it["FAIL_TO_PASS"] == []
    _clear()

if __name__ == "__main__":
    test_defaults_match_lc1a0(); test_lc_out_does_not_touch_work(); test_lc_results_and_explicit_ledger(); test_inst_and_issue_opt_in()
    print("cf_env ok")
