"""STAGE 3 — deterministic evaluation of one issue: gate (B) on pre+patch, and ground truth (hidden dev tests) for scoring only."""
import json, os, sys, glob, re, subprocess, hashlib
sys.path.insert(0, os.path.dirname(__file__))
import dockrun
from common2 import ROOT, items, pytest_cmd, is_testish, split_diff, diff_path
iid = sys.argv[1]; it = items()[iid]; img = it["docker_image"]
EXPECTED_RID = sys.argv[2] if len(sys.argv) > 2 else None
tg = f"{ROOT}/results/testgen/{iid}"; pdir = f"{ROOT}/results/patches/{iid}"
pre = json.load(open(f"{tg}/pre_eval.json")); prec = json.load(open(f"{pdir}/record.json"))
# ---- Amendment 3: every evaluation is bound to the exact artifact produced by run EXPECTED_RID ----
def integrity_fail(msg):
    json.dump({"instance_id": iid, "status": "INTEGRITY_FAIL", "detail": msg, "expected_run_id": EXPECTED_RID}, open(f"{ROOT}/results/integrity_fail_{iid}.json", "w"), indent=2)
    print(iid, "INTEGRITY_FAIL", msg); sys.exit(4)
def verify(where):
    try: R = json.load(open(f"{pdir}/record.json")); A = R["artifact"]
    except Exception as e: integrity_fail(f"[{where}] no valid stage-2 artifact record: {e!r}")
    b = open(f"{pdir}/patch.diff", "rb").read(); rb = open(f"{pdir}/patch_agent_output.diff", "rb").read() if os.path.exists(f"{pdir}/patch_agent_output.diff") else None
    chk = [("run ID", EXPECTED_RID is not None and A.get("producer_run_id") == EXPECTED_RID == A.get("producer_reported_run_id")),
           ("path", A.get("path") == os.path.relpath(f"{pdir}/patch.diff", ROOT)),
           ("sha256", hashlib.sha256(b).hexdigest() == A.get("sha256") == R.get("patch_sha256")),
           ("byte length", len(b) == A.get("bytes")),
           ("empty status", bool(A.get("empty")) == bool(R.get("patch_empty")) == (not b.decode(errors="replace").strip())),
           ("raw sha256/length", rb is not None and hashlib.sha256(rb).hexdigest() == A.get("raw_sha256") and len(rb) == A.get("raw_bytes")),
           ("base SHA", A.get("original_base_commit") == it["base_commit"] and A.get("base_sha") == json.load(open(f"{tg}/record.json")).get("sanitized_base_sha")),
           ("in-memory copy", "patch" not in globals() or hashlib.sha256(patch.encode()).hexdigest() == A.get("sha256"))]
    for f in ("patch.diff", "patch_agent_output.diff", "record.json"):
        rel = os.path.relpath(f"{pdir}/{f}", ROOT)
        chk.append((f"sealed {f}", not subprocess.run(["git", "-C", ROOT, "ls-files", "--error-unmatch", rel], capture_output=True).returncode
                    and not subprocess.run(["git", "-C", ROOT, "diff", "--quiet", "HEAD", "--", rel], capture_output=True).returncode))
    bad = [n for n, ok in chk if not ok]
    if bad: integrity_fail(f"[{where}] failed checks: {bad}")
    return b.decode(), R
patch, prec = verify("start")
tests = {os.path.relpath(f, f"{tg}/tests"): open(f).read() for f in glob.glob(f"{tg}/tests/**/*.py", recursive=True)}
out = {"instance_id": iid, "evaluated_patch_sha256": prec["artifact"]["sha256"], "evaluated_patch_bytes": prec["artifact"]["bytes"], "producer_run_id": EXPECTED_RID}
PASSY = ("PASSED",)
def unit_pass(unit, oc):
    if unit.endswith("::<COLLECTION_ERROR>"):
        f = unit.split("::")[0]; nodes = {k: v for k, v in oc.items() if k.split("::")[0] == f}
        return bool(nodes) and all(v in PASSY for v in nodes.values())
    return oc.get(unit) in PASSY

# ---------- gate P2P file selection (independent of hidden tests): existing test files that mention a changed module ----------
def gate_p2p_files():
    ws = f"{ROOT}/work/runs/testgen/{iid}/ws"
    tracked = subprocess.run(["git", "-C", ws, "-c", "safe.directory=*", "ls-files"], capture_output=True, text=True).stdout.split()
    tfiles = [f for f in tracked if f.endswith(".py") and (os.path.basename(f).startswith("test_") or f.endswith("_test.py"))]
    stems = set()
    for p in split_diff(patch):
        f = diff_path(p)
        if f and f.endswith(".py") and not is_testish(f):
            st = os.path.splitext(os.path.basename(f))[0]
            if st == "__init__": st = os.path.basename(os.path.dirname(f))
            if st: stems.add(st)
    sel = []
    for f in sorted(tfiles):
        try: txt = open(os.path.join(ws, f), errors="replace").read()
        except OSError: continue
        if any(re.search(r"(import|from)\s+[\w.]*\b%s\b" % re.escape(s), txt) for s in stems): sel.append(f)
    return sel[:10], sorted(stems)

if prec["patch_empty"]:
    out.update(B_decision="REJECT", B_reason="NO_PATCH", gt_correct=False, gt_note="empty patch")
else:
    # ---------- ground truth (scoring only; never shown to A or B) ----------
    verify("before ground truth")
    gt = dockrun.run(img, [patch, open(f"{ROOT}/work/inst/{iid}/test.diff").read()], cmd=it["test_cmd"])
    f2p_fail = [t for t in it["FAIL_TO_PASS"] if gt["outcomes"].get(t) != "PASSED"]
    p2p = json.load(open(f"{ROOT}/work/inst/{iid}/meta.json"))["P2P_eff"]
    p2p_fail = [t for t in p2p if gt["outcomes"].get(t) != "PASSED"]
    out.update(gt_apply_fail=gt["apply_fail"], gt_timeout=gt["timeout"], gt_f2p_failed=f"{len(f2p_fail)}/{len(it['FAIL_TO_PASS'])}",
               gt_p2p_failed=f"{len(p2p_fail)}/{len(p2p)}", gt_correct=(not gt["apply_fail"]) and (not gt["timeout"]) and not f2p_fail and not p2p_fail)
    if gt["apply_fail"]: out["gt_note"] = "patch + test_patch did not apply -> scored wrong"
    # ---------- gate ----------
    units = pre["discriminating_units"]
    if not units:
        out.update(B_decision="REJECT", B_reason="REJECT_INSUFFICIENT_EVIDENCE",
                   B_detail="clarification requested" if os.path.exists(f"{tg}/CLARIFICATION_NEEDED.md") else ("no tests" if not tests else "no generated test fails on pre-fix"))
    else:
        verify("before B gate")
        runs = [dockrun.run(img, [patch], files=tests, cmd=pytest_cmd(tests)) for _ in range(2)]
        if any(r["apply_fail"] for r in runs):
            out.update(B_decision="REJECT", B_reason="REJECT_INVALID_PATCH", B_detail="patch does not apply")
        else:
            res = [[unit_pass(u, r["outcomes"]) for u in units] for r in runs]
            out["gate_units_passed"] = [sum(x) for x in res]; out["gate_units"] = len(units)
            out["gate_deterministic"] = res[0] == res[1]
            ok_tests = all(res[0]) and all(res[1])
            files, stems = gate_p2p_files(); out["gate_p2p_files"] = files; out["gate_p2p_stems"] = stems
            p2p_ok, p2p_detail = True, "no matching existing test files"
            if files:
                cmd = pytest_cmd(files)
                pre_r = [dockrun.run(img, [], cmd=cmd) for _ in range(2)]
                pat_r = [dockrun.run(img, [patch], cmd=cmd) for _ in range(2)]
                if any(r["timeout"] for r in pre_r + pat_r):
                    p2p_ok, p2p_detail = False, "gate P2P timeout (fail-closed)"
                else:
                    stable = {k for k, v in pre_r[0]["outcomes"].items() if v == "PASSED" and pre_r[1]["outcomes"].get(k) == "PASSED"}
                    broke = sorted(k for k in stable if any(r["outcomes"].get(k) != "PASSED" for r in pat_r))
                    p2p_ok = not broke; p2p_detail = f"{len(broke)}/{len(stable)} stable pre-fix passing tests broken"
                    out["gate_p2p_broken"] = broke[:20]
            out["gate_p2p_ok"] = p2p_ok; out["gate_p2p_detail"] = p2p_detail
            if ok_tests and p2p_ok: out.update(B_decision="APPROVE", B_reason="")
            else:
                out.update(B_decision="REJECT", B_reason="REJECT_INVALID_PATCH",
                           B_detail=("discriminating tests fail on patch" if not ok_tests else "") + ("; " if (not ok_tests and not p2p_ok) else "") + ("P2P broken: " + p2p_detail if not p2p_ok else ""))
verify("before verdict")
out["A_decision"] = prec["A_decision"]
json.dump(out, open(f"{ROOT}/results/eval_{iid}.json", "w"), indent=2)
print(iid, "A", out["A_decision"], "B", out["B_decision"], out.get("B_reason"), "GT", out.get("gt_correct"))
