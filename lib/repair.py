"""LC-1A.1 repair loop: apply R0 (or prior attempt), pass B feedback (test names only), reseal, re-eval.
usage: repair.py [iid ...]  (short names or full ids; default: 5 test-caught issues; max 2 attempts; stop on B APPROVE)"""
import json, os, sys, subprocess, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common2 import ROOT, sample
os.chdir(ROOT)
PY = f"{ROOT}/.venv/bin/python"
DEFAULTS = ["hermes-webui-2056", "fromager-1124", "docsight-437", "copier-2646", "lsdb-1349"]
def sh(*a): return subprocess.run(a, capture_output=True, text=True)
def resolve(name):
    ids = sample()["instance_ids_in_order"]
    hits = [i for i in ids if i == name or i.endswith("__" + name)]
    assert len(hits) == 1, f"unknown/ambiguous iid {name!r}: {hits}"
    return hits[0]
def feedback(pre_path, ev_path):
    """gate_* only; NEVER read gt_*. Names only when every run passed 0 units; mixed counts: 'N of M' with no names."""
    ev, pre = json.load(open(ev_path)), json.load(open(pre_path))
    gate = {k: ev[k] for k in ev if k.startswith("gate_")}
    assert all(not k.startswith("gt_") for k in gate)
    units = list(pre["discriminating_units"])
    passed, n = gate.get("gate_units_passed"), gate.get("gate_units", len(units))
    broken = gate.get("gate_p2p_broken") or []
    failed, exact, lines = [], False, []
    if isinstance(passed, list) and n is not None:
        if all(c == 0 for c in passed):
            failed, exact = units, True
            lines += ["Failing discriminating tests:"] + [f"- {u}" for u in failed]
        elif all(c == n for c in passed):
            exact = True
        elif len(set(passed)) == 1:
            lines.append(f"{n - passed[0]} of {n} discriminating tests failed")
        else:
            lines.append(f"discriminating tests failed (passed {passed} of {n} across two runs)")
    if broken:
        lines += ["P2P tests broken by the patch:"] + [f"- {u}" for u in broken]
    return "\n".join(lines), {"failed_units": failed, "p2p_broken": broken, "gate_units_passed": passed, "failing_subset_stored": exact}
def main():
    iids = [resolve(x) for x in (sys.argv[1:] or DEFAULTS)]
    summary = []; os.makedirs("results_lc1a1", exist_ok=True)
    def save():
        json.dump({"issues": summary, "converted": sum(1 for x in summary if x.get("converted"))}, open("results_lc1a1/summary.json", "w"), indent=2)
    for iid in iids:
        pre_path, ev_path, base_patch = f"{ROOT}/results/testgen/{iid}/pre_eval.json", f"{ROOT}/results/eval_{iid}.json", f"{ROOT}/results/patches/{iid}/patch.diff"
        rec = {"instance_id": iid, "attempts": []}
        for k in (1, 2):
            fb, meta = feedback(pre_path, ev_path)
            od = f"results_lc1a1/{iid}/attempt{k}"
            rid = f"pa-{iid}-{time.strftime('%Y%m%dT%H%M%S')}-{os.urandom(4).hex()}"
            env = dict(os.environ, LC_BASE_PATCH=os.path.abspath(base_patch), LC_FEEDBACK=fb, LC_OUT=od)
            r = subprocess.run([PY, "lib/stage2_patch.py", iid, rid], env=env, capture_output=True, text=True)
            att = {"attempt": k, "run_id": rid, "stage2_rc": r.returncode, "stage2_out": (r.stdout or r.stderr)[-500:], "feedback": meta}
            if r.returncode:
                rec["attempts"].append(att); rec["halt"] = "INTEGRITY_FAIL stage2" if r.returncode == 4 else "stage2 crashed"
                summary.append(rec); save()
                if r.returncode == 4: print(iid, "INTEGRITY_FAIL stage2"); sys.exit(4)
                break
            assert sh("git", "add", od).returncode == 0
            assert sh("git", "commit", "-qm", f"LC-1A.1 SEAL {iid} attempt {k} run {rid} (artifact sealed before evaluation)").returncode == 0
            att["seal_commit"] = sh("git", "rev-parse", "--short", "HEAD").stdout.strip()
            r = subprocess.run([PY, "lib/stage3_eval.py", iid, rid], env=env, capture_output=True, text=True)
            att["stage3_rc"] = r.returncode; att["stage3_out"] = (r.stdout or r.stderr)[-500:]
            if r.returncode:
                rec["attempts"].append(att); rec["halt"] = "INTEGRITY_FAIL stage3" if r.returncode == 4 else "stage3 crashed"
                summary.append(rec); save()
                if r.returncode == 4: print(iid, "INTEGRITY_FAIL stage3"); sys.exit(4)
                break
            ev = json.load(open(f"{od}/eval.json"))
            att["B_decision"], att["B_reason"] = ev.get("B_decision"), ev.get("B_reason")  # never ev[gt_*]
            rec["attempts"].append(att)
            if ev.get("B_decision") == "APPROVE": rec["converted"] = True; break
            ev_path, base_patch = f"{od}/eval.json", f"{od}/patch.diff"
        else:
            rec.setdefault("converted", False)
        if rec not in summary: summary.append(rec)
        save()
    print(json.dumps({"converted": sum(1 for x in summary if x.get("converted")), "n": len(summary)}))
if __name__ == "__main__":
    main()
