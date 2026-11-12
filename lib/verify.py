"""Verify candidates in frozen order until 12 verify. Usage: verify.py N"""
import json, sys, time, subprocess
sys.path.insert(0, "lib"); import dockrun
N = int(sys.argv[1]) if len(sys.argv) > 1 else 12
rows = {r["instance_id"]: r for r in json.load(open("data/all_rows.json"))}
cands = [c for c in json.load(open("data/candidates.json")) if not c["excluded"]]
logf = "data/verification_log.jsonl"
done = {}
try:
    for l in open(logf): x = json.loads(l); done[x["instance_id"]] = x
except FileNotFoundError: pass
ok = [k for k, v in done.items() if v["verified"]]
for c in cands:
    if len(ok) >= N: break
    iid = c["instance_id"]
    if iid in done: continue
    r = rows[iid]; img = r["docker_image"]; t0 = time.time()
    rec = {"instance_id": iid, "verified": False}
    pr = subprocess.run(["docker", "pull", "-q", img], capture_output=True, text=True)
    if pr.returncode: rec["reason"] = "pull_failed: " + pr.stderr[-200:]
    else:
        cmd = r["install_config"]["test_cmd"]
        cmd = cmd if isinstance(cmd, str) else " && ".join(cmd)
        pre = dockrun.run(img, [r["test_patch"]], cmd=cmd)
        gold = dockrun.run(img, [r["patch"], r["test_patch"]], cmd=cmd)
        f2p, p2p = r["FAIL_TO_PASS"], r["PASS_TO_PASS"]
        rec.update(test_cmd=cmd, pre_timeout=pre["timeout"], gold_timeout=gold["timeout"],
                   pre_apply_fail=pre["apply_fail"], gold_apply_fail=gold["apply_fail"])
        f2p_pre_pass = [t for t in f2p if pre["outcomes"].get(t) == "PASSED"]
        f2p_gold_notpass = [t for t in f2p if gold["outcomes"].get(t) != "PASSED"]
        p2p_gold_fail = [t for t in p2p if gold["outcomes"].get(t) != "PASSED"]
        rec.update(n_f2p=len(f2p), n_p2p=len(p2p), f2p_pass_on_pre=f2p_pre_pass, f2p_not_pass_on_gold=f2p_gold_notpass,
                   p2p_not_pass_on_gold=p2p_gold_fail, n_outcomes_gold=len(gold["outcomes"]))
        if pre["apply_fail"] or gold["apply_fail"]: rec["reason"] = "patch_apply_failed"
        elif pre["timeout"] or gold["timeout"]: rec["reason"] = "timeout_15min"
        elif f2p_gold_notpass: rec["reason"] = f"{len(f2p_gold_notpass)}/{len(f2p)} F2P not passing on gold"
        elif f2p_pre_pass: rec["reason"] = f"{len(f2p_pre_pass)}/{len(f2p)} F2P already pass on pre-fix"
        elif p2p and len(p2p_gold_fail) > 0.05 * len(p2p): rec["reason"] = f"{len(p2p_gold_fail)}/{len(p2p)} P2P fail on gold (>5%)"
        else: rec["verified"] = True; rec["effective_p2p"] = [t for t in p2p if t not in p2p_gold_fail]
        if not rec["verified"]:
            rec["gold_log_tail"] = gold["log"][-1500:]
    rec["seconds"] = round(time.time() - t0)
    open(logf, "a").write(json.dumps(rec) + "\n")
    if rec["verified"]: ok.append(iid)
    print(iid, rec["verified"], rec.get("reason", ""), rec["seconds"], flush=True)
print("verified:", len(ok), ok)
