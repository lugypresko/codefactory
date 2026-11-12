"""check_wrong.py <iid> : run each wrong_patches/<iid>/w*.diff (+ dev test_patch) vs dev tests. Writes check.json"""
import sys, json, os, glob
sys.path.insert(0, os.path.dirname(__file__)); import dockrun
iid = sys.argv[1]; d = f"work/inst/{iid}"; meta = json.load(open(f"{d}/meta.json"))
test = open(f"{d}/test.diff").read(); out = {}
for w in sorted(glob.glob(f"wrong_patches/{iid}/w*.diff")):
    r = dockrun.run(meta["image"], [open(w).read(), test], cmd=meta["test_cmd"])
    f2p_fail = [t for t in meta["F2P"] if r["outcomes"].get(t) != "PASSED"]
    p2p_fail = [t for t in meta["P2P_eff"] if r["outcomes"].get(t) != "PASSED"]
    ok = (not r["apply_fail"]) and (not r["timeout"]) and len(f2p_fail) > 0
    out[os.path.basename(w)] = {"valid_wrong": ok, "apply_fail": r["apply_fail"], "f2p_failed": f"{len(f2p_fail)}/{len(meta['F2P'])}",
                                "p2p_failed": f"{len(p2p_fail)}/{len(meta['P2P_eff'])}", "p2p_failed_ids": p2p_fail[:10]}
    print(os.path.basename(w), out[os.path.basename(w)], flush=True)
    if r["apply_fail"]: print(r["log"][-800:])
json.dump(out, open(f"wrong_patches/{iid}/check.json", "w"), indent=1)
