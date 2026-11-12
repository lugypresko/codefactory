"""Base/Gold verification counts for the 30 frozen instances -> data/manifest_30.json (no model calls)."""
import json, sys, os, subprocess, concurrent.futures as cf
sys.path.insert(0, "lib"); import dockrun
s = json.load(open("sample_v2.json")); rows = {r["instance_id"]: r for r in json.load(open("data/all_rows.json"))}
ver = {json.loads(l)["instance_id"]: json.loads(l) for l in open("data/verification_log.jsonl")}
def one(it):
    iid = it["instance_id"]; r = rows[iid]; img = r["docker_image"]
    if subprocess.run(["docker", "image", "inspect", img], capture_output=True).returncode: subprocess.run(["docker", "pull", "-q", img], capture_output=True)
    dig = subprocess.run(["docker", "image", "inspect", img, "--format", "{{index .RepoDigests 0}}"], capture_output=True, text=True).stdout.strip()
    base = dockrun.run(img, [r["test_patch"]], cmd=it["test_cmd"]); gold = dockrun.run(img, [r["patch"], r["test_patch"]], cmd=it["test_cmd"])
    f2p, p2p, eff = r["FAIL_TO_PASS"], r["PASS_TO_PASS"], ver[iid]["effective_p2p"]
    cnt = lambda oc, L, want: sum(1 for t in L if (oc.get(t) == "PASSED") == want)
    return {"instance_id": iid, "repo": r["repo"], "created_at": r["created_at"], "base_commit": r["base_commit"], "docker_image": img,
            "image_repo_digest": dig, "digest_matches_frozen": dig == it["image_repo_digest"],
            "n_F2P": len(f2p), "F2P_fail_on_base": cnt(base["outcomes"], f2p, False), "F2P_pass_on_gold": cnt(gold["outcomes"], f2p, True),
            "n_P2P": len(p2p), "P2P_pass_on_base": cnt(base["outcomes"], p2p, True), "P2P_pass_on_gold": cnt(gold["outcomes"], p2p, True),
            "n_P2P_effective": len(eff), "P2P_effective_pass_on_base": cnt(base["outcomes"], eff, True), "P2P_effective_pass_on_gold": cnt(gold["outcomes"], eff, True),
            "base_timeout": base["timeout"], "gold_timeout": gold["timeout"], "apply_fail": base["apply_fail"] or gold["apply_fail"],
            "network": "none", "runs": "this re-run (manifest) + original verification in data/verification_log.jsonl"}
with cf.ThreadPoolExecutor(2) as ex: res = list(ex.map(one, s["instances"]))
out = {"dataset": s["dataset"], "dataset_revision": s["dataset_revision"], "parquet_ref": s["parquet_ref"], "splits": s["splits"],
       "note": "Base = base_commit + dev test_patch; Gold = base + gold patch + test_patch; instance test_cmd; --network none. P2P effective = P2P passing on gold in verification (scoring set).",
       "instances": res}
json.dump(out, open("data/manifest_30.json", "w"), indent=1)
for x in res: print(x["instance_id"], x["F2P_fail_on_base"], "/", x["n_F2P"], x["F2P_pass_on_gold"], x["P2P_pass_on_base"], x["P2P_pass_on_gold"], "/", x["n_P2P"], x["digest_matches_frozen"])
