"""Amendment 3 (user spec 18:42) adversarial integrity tests. Written BEFORE the fix. Reuses the hermetic harness of
test_patch_integrity.py (fake OpenHands runner + fake evaluator Docker layer recording the sha256 of every patch it receives).
Run: python3 tests/regress/test_integrity_v3.py"""
import json, os, sys, stat, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_patch_integrity import *  # noqa
GOLD = SRC_DIFF.replace("return 2", "return 42")  # stands in for the gold fix (in the harness only, never in production dirs)
def integrity_failed(r, q):
    return q.returncode == 4 and os.path.exists(os.path.join(r, "results", f"integrity_fail_{IID}.json")) and ev(r) is None
def chmod_w(path):  # an adversary/diagnostic with owner rights first removes protection, then edits
    for root, ds, fs in os.walk(path):
        os.chmod(root, 0o755); [os.chmod(os.path.join(root, f), 0o644) for f in fs]
def edit_record(r, fn):
    chmod_w(pdir(r)); R = rec(r); fn(R); json.dump(R, open(os.path.join(pdir(r), "record.json"), "w"), indent=2); seal(r)  # re-sealed: only content checks can catch it
def produced(raw=SRC_DIFF):
    r = make_root(); p = stage2(r, raw); assert p.returncode == 0, p.stdout + p.stderr; seal(r); return r

def test_v3_gold_substitution_reproduced_and_refused():
    r = produced(TEST_ONLY_DIFF)                       # SMOKE2: legitimate EMPTY_DIFF
    chmod_w(pdir(r)); open(os.path.join(pdir(r), "patch.diff"), "w").write(GOLD)
    json.dump({"patch_empty": False, "A_decision": "n/a (diagnostic)"}, open(os.path.join(pdir(r), "record.json"), "w")); seal(r)
    q = stage3(r); assert integrity_failed(r, q) and H(GOLD) not in evaluated_shas(r), q.stdout + q.stderr
def test_v3_changed_bytes_same_length():
    r = produced(); chmod_w(pdir(r)); b = open(os.path.join(pdir(r), "patch.diff")).read()
    open(os.path.join(pdir(r), "patch.diff"), "w").write(b.replace("return 2", "return 9")); seal(r)
    q = stage3(r); assert integrity_failed(r, q) and evaluated_shas(r) == set(), q.stdout
def test_v3_wrong_hash_in_record():
    r = produced(); edit_record(r, lambda R: R["artifact"].__setitem__("sha256", "0" * 64) if "artifact" in R else R.__setitem__("patch_sha256", "0" * 64))
    q = stage3(r); assert integrity_failed(r, q), q.stdout
def test_v3_wrong_size_in_record():
    r = produced(); edit_record(r, lambda R: R.setdefault("artifact", {}).__setitem__("bytes", 1))
    q = stage3(r); assert integrity_failed(r, q), q.stdout
def test_v3_wrong_run_id():
    r = produced(); q = stage3(r, rid="pa-fake__repo-1-OTHER-RUN"); assert integrity_failed(r, q) and evaluated_shas(r) == set(), q.stdout
def test_v3_empty_flag_mismatch():
    r = produced(); edit_record(r, lambda R: (R.__setitem__("patch_empty", True), R.get("artifact", {}).__setitem__("empty", True)))
    q = stage3(r); assert integrity_failed(r, q), q.stdout
def test_v3_wrong_base_sha():
    r = make_root(); stage2(r, SRC_DIFF, env_extra={"LC_FAKE_BASE": "c" * 40}); seal(r)
    q = stage3(r); assert integrity_failed(r, q), q.stdout
def test_v3_raw_and_filtered_hashes_kept_separately():
    r = produced(SRC_DIFF + TEST_ONLY_DIFF); A = rec(r).get("artifact", {})
    assert A.get("sha256") == H(SRC_DIFF) and A.get("raw_sha256") == H(SRC_DIFF + TEST_ONLY_DIFF) and A.get("raw_sha256") != A.get("sha256")
    assert A.get("bytes") == len(SRC_DIFF.encode()) and A.get("producer_run_id") == RID and A.get("base_sha") == "b" * 40
    assert A.get("path") == f"results/patches/{IID}/patch.diff"
def test_v3_legit_filtered_empty_diff_is_ordinary_outcome():
    r = produced(TEST_ONLY_DIFF); q = stage3(r)
    assert q.returncode == 0 and ev(r)["B_reason"] == "NO_PATCH" and ev(r)["A_decision"] == "REJECT"
    assert not os.path.exists(os.path.join(r, "results", f"integrity_fail_{IID}.json")) and ev(r).get("evaluated_patch_sha256") == H("")
def test_v3_tamper_between_gt_and_gate_is_caught():   # verification immediately before BOTH ground truth and the B decision
    r = produced(); q = stage3(r, env_extra={"LC_FAKE_TAMPER_AFTER_FIRST_RUN": "1"})
    assert integrity_failed(r, q), q.stdout
def test_v3_canonical_artifacts_read_only_after_production():
    r = produced(); f = os.path.join(pdir(r), "patch.diff")
    try: open(f, "w").write(GOLD); wrote = True
    except PermissionError: wrote = False
    assert not wrote and not (os.stat(pdir(r)).st_mode & stat.S_IWUSR), "a plain cp/write by a diagnostic must fail"
def test_v3_c_c2_variants_with_owner_chmod():  # c/c2 of the 9-suite, but the adversary first lifts the read-only protection
    r = produced(); chmod_w(pdir(r)); open(os.path.join(pdir(r), "patch.diff"), "w").write(LATE_DIFF)   # c2: late overwrite, not re-sealed
    q = stage3(r); assert integrity_failed(r, q) and H(LATE_DIFF) not in evaluated_shas(r), q.stdout
    r = produced(TEST_ONLY_DIFF); chmod_w(pdir(r)); open(os.path.join(pdir(r), "patch.diff"), "w").write(LATE_DIFF)  # c: after EMPTY verdict
    json.dump({"patch_empty": False, "A_decision": "n/a (diagnostic)"}, open(os.path.join(pdir(r), "record.json"), "w"))
    q = stage3(r); assert integrity_failed(r, q) and H(LATE_DIFF) not in evaluated_shas(r), q.stdout
def test_v3_pipeline_refuses_gold_bytes_in_results():
    s = open(os.path.join(REPO, "lib", "pipeline.py")).read()
    assert "gold_scan" in s and "INTEGRITY_FAIL" in s, "pipeline must scan production dirs for gold/test_patch bytes and halt"

if __name__ == "__main__":
    fails = 0
    for n, f in [(k, v) for k, v in list(globals().items()) if k.startswith("test_v3_")]:
        try: f(); print(f"PASS {n}")
        except Exception as e: fails += 1; print(f"FAIL {n}: {type(e).__name__}: {str(e)[:200]}")
    print(f"{fails} failed"); sys.exit(1 if fails else 0)
