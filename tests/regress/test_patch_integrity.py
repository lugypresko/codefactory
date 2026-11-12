"""SMOKE2-RCA regression tests (written BEFORE the Amendment-3 fix; several MUST fail on the frozen code).
Hermetic: copies lib/ into a temp ROOT, replaces the OpenHands runner (oh/oh_run.py) with a fake that emits a chosen diff,
and replaces lib/dockrun.py with a fake that records the sha256 of every patch handed to the evaluator. No model calls, no Docker.
Run: python3 tests/regress/test_patch_integrity.py   (exit 0 = all pass)"""
import hashlib, json, os, shutil, subprocess, sys, tempfile, traceback
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PY = os.path.join(REPO, ".venv", "bin", "python")
IID = "fake__repo-1"
H = lambda b: hashlib.sha256(b if isinstance(b, bytes) else b.encode()).hexdigest()
SRC_DIFF = """diff --git a/pkg/mod.py b/pkg/mod.py
index 1111111..2222222 100644
--- a/pkg/mod.py
+++ b/pkg/mod.py
@@ -1,2 +1,2 @@
 def f():
-    return 1
+    return 2
"""
TEST_ONLY_DIFF = """diff --git a/test/data/spec.yaml b/test/data/spec.yaml
index 1111111..2222222 100644
--- a/test/data/spec.yaml
+++ b/test/data/spec.yaml
@@ -1 +1,2 @@
 a: 1
+b: 2
"""
LATE_DIFF = SRC_DIFF.replace("return 2", "return 3")  # e.g. a gold/diagnostic file dropped in after the verdict
FAKE_OH = r'''import json, os, sys
iid, out = sys.argv[1], sys.argv[2]; os.makedirs(out, exist_ok=True)
open(os.path.join(out, "patch_raw.diff"), "w").write(open(os.environ["LC_FAKE_RAW"]).read())
json.dump({"execution_status": "ConversationExecutionStatus.FINISHED", "cost_usd": 0.0, "final_message": "done",
           "run_id": os.environ.get("LC_RUNID"), "base_sha": os.environ.get("LC_FAKE_BASE", "b" * 40)}, open(os.path.join(out, "oh_result.json"), "w"))
'''
FAKE_DOCKRUN = r'''import json, os, hashlib
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
class AllPass(dict):
    def get(self, k, d=None): return "PASSED"
def parse_pytest(s): return {}
def run(image, patches=(), files=None, cmd="", timeout=900, mem="3g", label="x"):
    open(os.path.join(ROOT, "work", "dockrun_calls.jsonl"), "a").write(json.dumps({"patch_sha256": [hashlib.sha256(p.encode()).hexdigest() for p in patches], "n_files": len(files or {})}) + "\n")
    if os.environ.get("LC_FAKE_TAMPER_AFTER_FIRST_RUN"):
        import glob, stat
        for f in glob.glob(os.path.join(ROOT, "results", "patches", "*", "patch.diff")):
            os.chmod(os.path.dirname(f), 0o755); os.chmod(f, 0o644); open(f, "a").write("+tampered\n")
    return {"outcomes": AllPass(), "rc": 0, "timeout": False, "apply_fail": False, "test_exit": 0, "log": ""}
'''
def make_root():
    r = tempfile.mkdtemp(prefix="lc_regress_")
    shutil.copytree(os.path.join(REPO, "lib"), os.path.join(r, "lib"), ignore=shutil.ignore_patterns("__pycache__"))
    open(os.path.join(r, "lib", "dockrun.py"), "w").write(FAKE_DOCKRUN)
    os.makedirs(os.path.join(r, "oh")); open(os.path.join(r, "oh", "oh_run.py"), "w").write(FAKE_OH)
    os.symlink(os.path.join(REPO, ".venv"), os.path.join(r, ".ohvenv")); os.symlink(os.path.join(REPO, ".venv"), os.path.join(r, ".venv"))
    os.makedirs(os.path.join(r, "work", "inst", IID)); os.makedirs(os.path.join(r, "results", "testgen", IID, "tests", "pkg"))
    json.dump({"instances": [{"instance_id": IID, "docker_image": "fake:latest", "base_commit": "0" * 40, "test_cmd": "pytest x",
                              "FAIL_TO_PASS": ["t::f2p"], "image_repo_digest": "fake@sha256:0"}], "instance_ids_in_order": [IID]},
              open(os.path.join(r, "sample_v2.json"), "w"))
    open(os.path.join(r, "work", "inst", IID, "test.diff"), "w").write("")
    json.dump({"P2P_eff": ["t::p2p"]}, open(os.path.join(r, "work", "inst", IID, "meta.json"), "w"))
    open(os.path.join(r, "results", "testgen", IID, "tests", "pkg", "test_gen.py"), "w").write("def test_x():\n    assert True\n")
    json.dump({"discriminating_units": ["pkg/test_gen.py::test_x"]}, open(os.path.join(r, "results", "testgen", IID, "pre_eval.json"), "w"))
    json.dump({"instance_id": IID, "sanitized_base_sha": "b" * 40}, open(os.path.join(r, "results", "testgen", IID, "record.json"), "w"))
    open(os.path.join(r, "work", "cost_ledger.jsonl"), "w").write("")
    for c in (["init", "-q"], ["add", "-A"], ["-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"]):
        subprocess.run(["git", "-C", r, *c], capture_output=True)
    return r
RID = "pa-fake__repo-1-test-0001"  # producer run ID minted by the pipeline and passed to stage 2 and stage 3 (frozen code ignores the extra argv)
def stage2(r, raw, rid=RID, env_extra=None):
    p = os.path.join(r, "raw_in.diff"); open(p, "w").write(raw)
    return subprocess.run([PY, os.path.join(r, "lib", "stage2_patch.py"), IID, rid], cwd=r, capture_output=True, text=True, env=dict(os.environ, LC_FAKE_RAW=p, **(env_extra or {})))
def stage3(r, rid=RID, env_extra=None):
    return subprocess.run([PY, os.path.join(r, "lib", "stage3_eval.py"), IID, rid], cwd=r, capture_output=True, text=True, env=dict(os.environ, **(env_extra or {})))
def seal(r):  # what the pipeline does between stage 2 and stage 3 (Amendment 3 makes this a mandatory, checked seal commit)
    subprocess.run(["git", "-C", r, "add", "-A"], capture_output=True); subprocess.run(["git", "-C", r, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "seal"], capture_output=True)
pdir = lambda r: os.path.join(r, "results", "patches", IID)
rec = lambda r: json.load(open(os.path.join(pdir(r), "record.json")))
ev = lambda r: json.load(open(os.path.join(r, "results", f"eval_{IID}.json"))) if os.path.exists(os.path.join(r, "results", f"eval_{IID}.json")) else None
calls = lambda r: [json.loads(l) for l in open(os.path.join(r, "work", "dockrun_calls.jsonl"))] if os.path.exists(os.path.join(r, "work", "dockrun_calls.jsonl")) else []
def evaluated_shas(r): return {s for c in calls(r) for s in c["patch_sha256"] if s != H("")}

# (a) valid patch -> A APPROVE; evaluator gets exactly the produced bytes; eval output names the sha it evaluated
def test_a_valid_patch_classified_and_bound():
    r = make_root(); p = stage2(r, SRC_DIFF); assert p.returncode == 0, p.stderr
    R = rec(r); body = open(os.path.join(pdir(r), "patch.diff"), "rb").read()
    assert R["A_decision"] == "APPROVE" and not R["patch_empty"]
    assert R["patch_sha256"] == H(body) == H(SRC_DIFF)
    seal(r); q = stage3(r); assert q.returncode == 0, q.stderr
    assert evaluated_shas(r) == {H(SRC_DIFF)}, "evaluator must receive exactly the produced patch"
    assert ev(r).get("evaluated_patch_sha256") == R["patch_sha256"], "eval record must bind the evaluated artifact's sha256 (missing => unbound)"

# (b) empty patch (agent changed only test data, like SMOKE2) -> A REJECT EMPTY_DIFF, B NO_PATCH, evaluator never runs a patch
def test_b_empty_patch_classified():
    r = make_root(); p = stage2(r, TEST_ONLY_DIFF); assert p.returncode == 0, p.stderr
    R = rec(r); assert R["A_decision"] == "REJECT" and R["A_reason"] == "EMPTY_DIFF" and R["patch_empty"]
    assert open(os.path.join(pdir(r), "patch.diff")).read() == "" and R["dropped_test_files"] == ["test/data/spec.yaml"]
    seal(r); q = stage3(r); assert q.returncode == 0, q.stderr
    assert ev(r)["B_reason"] == "NO_PATCH" and ev(r)["gt_correct"] is False and evaluated_shas(r) == set()

def test_b2_truly_empty_raw():
    r = make_root(); stage2(r, ""); R = rec(r); assert R["A_decision"] == "REJECT" and R["patch_empty"]

# (c) late-arriving patch: the exact SMOKE2 RCA event — verdict EMPTY_DIFF, then a non-empty patch.diff (+ a hand-made
#     record without hashes) is written into results/ after the verdict. The evaluator must refuse (integrity failure),
#     must not evaluate the late file, and must not produce a normal B/GT verdict.
def test_c_late_patch_after_empty_verdict_is_refused():
    r = make_root(); stage2(r, TEST_ONLY_DIFF); seal(r)
    open(os.path.join(pdir(r), "patch.diff"), "w").write(LATE_DIFF)
    json.dump({"patch_empty": False, "A_decision": "n/a (diagnostic)"}, open(os.path.join(pdir(r), "record.json"), "w"))
    q = stage3(r)
    assert H(LATE_DIFF) not in evaluated_shas(r), "late file was evaluated"
    assert q.returncode != 0 and (ev(r) is None or ev(r).get("B_decision") not in ("APPROVE", "REJECT")), "late artifact not refused"

def test_c2_late_overwrite_of_nonempty_patch_is_refused():
    r = make_root(); stage2(r, SRC_DIFF); seal(r)
    open(os.path.join(pdir(r), "patch.diff"), "w").write(LATE_DIFF)  # stale/late copy replaces the produced one; record untouched
    q = stage3(r)
    assert H(LATE_DIFF) not in evaluated_shas(r), "evaluator evaluated a file that is not the produced artifact"
    assert q.returncode != 0, "sha mismatch must halt (EVAL_INTEGRITY_FAIL)"

def test_c3_unsealed_patch_is_refused():
    r = make_root(); stage2(r, SRC_DIFF)  # no seal commit between stage 2 and stage 3
    q = stage3(r); assert q.returncode != 0 and evaluated_shas(r) == set(), "evaluation must require the stage-2 seal commit"

def test_c4_late_write_in_agent_rundir_ignored():
    r = make_root(); stage2(r, SRC_DIFF); seal(r)
    open(os.path.join(r, "work", "runs", "patch", IID, "patch_raw.diff"), "w").write(LATE_DIFF)  # agent dir touched after verdict
    q = stage3(r); assert evaluated_shas(r) == {H(SRC_DIFF)}

def test_d_stale_previous_artifacts_replaced():
    r = make_root(); os.makedirs(pdir(r)); open(os.path.join(pdir(r), "patch.diff"), "w").write(LATE_DIFF)
    json.dump({"patch_empty": False, "A_decision": "APPROVE", "patch_sha256": H(LATE_DIFF)}, open(os.path.join(pdir(r), "record.json"), "w"))
    stage2(r, TEST_ONLY_DIFF); R = rec(r)
    assert open(os.path.join(pdir(r), "patch.diff")).read() == "" and R["patch_empty"] and R["patch_sha256"] == H("")

def test_e_pipeline_seals_before_eval():
    s = open(os.path.join(REPO, "lib", "pipeline.py")).read()
    i2 = s.index('lib/stage2_patch.py'); i3 = s.index('lib/stage3_eval.py')
    assert "STAGE2 SEAL" in s[i2:i3], "pipeline must commit (seal) results/patches/<iid> between stage 2 and stage 3"

if __name__ == "__main__":
    fails = 0
    for n, f in [(k, v) for k, v in list(globals().items()) if k.startswith("test_")]:
        try: f(); print(f"PASS {n}")
        except Exception as e: fails += 1; print(f"FAIL {n}: {type(e).__name__}: {str(e)[:300]}")
    print(f"{fails} failed"); sys.exit(1 if fails else 0)
