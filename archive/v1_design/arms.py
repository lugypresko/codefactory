"""Run Arm 1 / Arm 2 for one sample item.  usage: arms.py arm1|arm2 <instance_id>"""
import json, os, sys, shutil, subprocess, glob, re
sys.path.insert(0, os.path.dirname(__file__))
import agent, dockrun, prompts
ROOT = agent.ROOT
S = json.load(open(f"{ROOT}/sample.json"))
ITEMS = {x["instance_id"]: x for x in S["clear"] + S["vague"]}

def issue_text(iid): return open(f"{ROOT}/work/inst/{iid}/issue.md").read()

def strip_files(diff, paths):
    parts = re.split(r'(?=^diff --git )', diff, flags=re.M)
    kept, dropped = [], []
    for p in parts:
        m = re.match(r'diff --git a/(\S+) b/(\S+)', p)
        if m and (m.group(1) in paths or m.group(2) in paths or agent.is_test_file(m.group(2))): dropped.append(m.group(2)); continue
        kept.append(p)
    return "".join(kept), dropped

def pytest_cmd(files): return "pytest --no-header -rA --tb=short --color=no -p no:cacheprovider " + " ".join(sorted(files))

def save_final(arm, iid, rec, tests, clar):
    od = f"{ROOT}/results/{arm}/{iid}"; shutil.rmtree(od, ignore_errors=True); os.makedirs(od)
    for rel, c in tests.items():
        fp = os.path.join(od, "tests", rel); os.makedirs(os.path.dirname(fp), exist_ok=True); open(fp, "w").write(c)
    if clar is not None: open(f"{od}/CLARIFICATION_NEEDED.md", "w").write(clar)
    rec["final_test_files"] = sorted(tests); rec["clarification"] = clar is not None
    json.dump(rec, open(f"{od}/record.json", "w"), indent=2)
    return rec

def writer_run(role, rid, iid, rd, cost, steps, wall):
    img = ITEMS[iid]["docker_image"]; ws = f"{rd}/ws"
    base = agent.prep_ws(img, ws)
    res = agent.run(role, rid, img, prompts.WRITER.format(issue=issue_text(iid)), ws, rd, cost, steps, wall)
    cl = agent.classify(ws, base); res["classify"] = {k: (sorted(v) if k == "tests" else v) for k, v in cl.items() if k != "clarification"}
    res["clarification_written"] = cl["clarification"] is not None
    return res, cl, base

def arm1(iid):
    rd = f"{ROOT}/work/runs/arm1/{iid}"; shutil.rmtree(rd, ignore_errors=True); os.makedirs(rd)
    res, cl, _ = writer_run("arm1", f"arm1-{iid}", iid, rd, 0.30, 40, 900)
    rec = {"arm": "arm1", "instance_id": iid, "runs": [res], "cost_usd": res.get("cost_usd") or 0.0}
    if res["status"] == "BUDGET_STOP": rec["validity"] = "BUDGET_STOP"; return save_final("arm1", iid, rec, {}, None)
    rec["validity"] = "INVALID" if cl["violations"] else "VALID"
    rec["violations"] = cl["violations"]
    tests = {} if cl["violations"] else cl["tests"]
    return save_final("arm1", iid, rec, tests, None if cl["violations"] else cl["clarification"])

def arm2(iid):
    rd0 = f"{ROOT}/work/runs/arm2/{iid}"; shutil.rmtree(rd0, ignore_errors=True); os.makedirs(rd0)
    img = ITEMS[iid]["docker_image"]
    resA, clA, base = writer_run("arm2-A", f"arm2A-{iid}", iid, f"{rd0}/A", 0.14, 20, 420)
    rec = {"arm": "arm2", "instance_id": iid, "runs": [resA]}
    cost = lambda: sum((r.get("cost_usd") or 0.0) for r in rec["runs"])
    if resA["status"] == "BUDGET_STOP":
        rec["validity"] = "BUDGET_STOP"; rec["cost_usd"] = cost(); return save_final("arm2", iid, rec, {}, None)
    if clA["violations"]:
        rec.update(validity="INVALID", violations=clA["violations"], cost_usd=cost()); return save_final("arm2", iid, rec, {}, None)
    rec["validity"] = "VALID"
    testsA = clA["tests"]
    if not testsA:
        rec["stage"] = "A produced no tests" + (" (clarification)" if clA["clarification"] else "")
        rec["cost_usd"] = cost(); return save_final("arm2", iid, rec, {}, clA["clarification"])
    # ---- B: wrong fixes ----
    rdB = f"{rd0}/B"; os.makedirs(f"{rdB}/out"); os.chmod(f"{rdB}/out", 0o777)
    wsB = f"{rdB}/ws"; agent.prep_ws(img, wsB, extra_files=testsA)
    resB = agent.run("arm2-B", f"arm2B-{iid}", img, prompts.BREAKER.format(issue=issue_text(iid), test_files=", ".join(sorted(testsA))),
                     wsB, rdB, 0.06, 10, 180, extra_mounts=[f"{rdB}/out:/lc_out"])
    rec["runs"].append(resB)
    bpatches = []
    for f in sorted(glob.glob(f"{rdB}/out/wrong_*.diff")):
        d, dropped = strip_files(open(f).read(), set(testsA))
        bpatches.append({"file": os.path.basename(f), "diff": d, "dropped_test_hunks": dropped})
    # ---- harness: A's tests vs B's patches ----
    surv = []
    for bp in bpatches:
        if not bp["diff"].strip(): bp["result"] = "EMPTY"; continue
        r = dockrun.run(img, [bp["diff"]], files=testsA, cmd=pytest_cmd(testsA))
        if r["apply_fail"]: bp["result"] = "APPLY_FAIL"; continue
        oc = r["outcomes"]; allpass = bool(oc) and all(v in ("PASSED", "XFAIL", "SKIPPED") for v in oc.values()) and any(v == "PASSED" for v in oc.values())
        bp["result"] = "SURVIVED" if allpass else "KILLED"; bp["outcomes"] = oc
        if allpass: surv.append(bp)
    rec["breaker_patches"] = [{k: v for k, v in b.items() if k != "diff"} for b in bpatches]
    for b in bpatches: open(f"{rdB}/{b['file']}.stripped", "w").write(b["diff"])
    if not surv:
        rec["stage"] = "no surviving B patch; no revision round"; rec["cost_usd"] = cost()
        return save_final("arm2", iid, rec, testsA, clA["clarification"])
    # ---- A': one revision round ----
    rdR = f"{rd0}/R"; os.makedirs(f"{rdR}/in")
    names = []
    for i, b in enumerate(surv, 1):
        n = f"candidate_{i}.diff"; open(f"{rdR}/in/{n}", "w").write(b["diff"]); names.append(n)
    os.chmod(f"{rdR}/in", 0o755)
    wsR = f"{rdR}/ws"; baseR = agent.prep_ws(img, wsR, extra_files=testsA)
    remaining = max(0.0, 0.30 - cost())
    resR = agent.run("arm2-R", f"arm2R-{iid}", img, prompts.REVISER.format(issue=issue_text(iid), test_files=", ".join(sorted(testsA)), cands=", ".join(names)),
                     wsR, rdR, round(min(0.10, remaining), 4), 10, 300, extra_mounts=[f"{rdR}/in:/lc_in:ro"])
    rec["runs"].append(resR)
    clR = agent.classify(wsR, baseR)
    rec["revision_classify"] = {"violations_reverted_or_dropped": clR["violations"], "benign": clR["benign"]}
    rec["stage"] = f"revision round with {len(surv)} surviving patch(es)"
    rec["cost_usd"] = cost()
    return save_final("arm2", iid, rec, clR["tests"], clA["clarification"])

if __name__ == "__main__":
    which, iid = sys.argv[1], sys.argv[2]
    r = (arm1 if which == "arm1" else arm2)(iid)
    print(json.dumps({k: r[k] for k in ("arm", "instance_id", "validity", "cost_usd", "final_test_files", "clarification")}, default=str))
