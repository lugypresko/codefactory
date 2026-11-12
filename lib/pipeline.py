"""Sequential per-issue pipeline in frozen order. usage: pipeline.py [max_issues]"""
import json, os, sys, subprocess, shutil, time
sys.path.insert(0, os.path.dirname(__file__))
import agent
from common2 import ROOT, H, sample
os.chdir(ROOT)
PY = f"{ROOT}/.venv/bin/python"
def sh(*a): return subprocess.run(a, capture_output=True, text=True)
def log(m):
    line = f"[{time.strftime('%F %T')}] {m}"; print(line, flush=True); open(f"{ROOT}/work/pipeline.log", "a").write(line + "\n")
def free_gb(): st = os.statvfs("/"); return st.f_bavail * st.f_frsize / 1e9
order = sample()["instance_ids_in_order"]; items = {x["instance_id"]: x for x in sample()["instances"]}
lim = int(sys.argv[1]) if len(sys.argv) > 1 else 30
for n, iid in enumerate(order[:lim], 1):
    if os.path.exists(f"{ROOT}/results/eval_{iid}.json"): continue
    if free_gb() < 20: log(f"STOP: free disk {free_gb():.1f} GB < 20 GB floor"); break
    if agent.spent() + 0.25 + 0.50 > 25.0: log(f"STOP: budget (spent {agent.spent():.3f})"); break
    img = items[iid]["docker_image"]
    if sh("docker", "image", "inspect", img).returncode: 
        r = sh("docker", "pull", "-q", img); log(f"pull {img}: rc={r.returncode}")
    dig = sh("docker", "image", "inspect", img, "--format", "{{index .RepoDigests 0}}").stdout.strip()
    assert dig == items[iid]["image_repo_digest"], f"digest mismatch {dig}"
    log(f"#{n} {iid}: stage1 testgen")
    r = sh(PY, "lib/stage1_testgen.py", iid); log(r.stdout.strip() or r.stderr[-1500:])
    if r.returncode == 3: log("INFRA_FAIL (preflight) -> pipeline halted; not scored as a B reject"); break
    if r.returncode: log("stage1 crashed; stopping"); break
    r = sh(PY, "lib/stage1b_pre.py", iid); log(r.stdout.strip() or r.stderr[-1500:])
    if r.returncode: log("stage1b crashed; stopping"); break
    # freeze stage-1 outputs before the patch exists
    man = {}
    for root, _, fs in os.walk(f"results/testgen/{iid}"):
        for f in fs: p = os.path.join(root, f); man[p] = H(open(p, "rb").read())
    json.dump({"instance_id": iid, "frozen_at": time.strftime("%FT%T%z"), "patch_exists": os.path.exists(f"results/patches/{iid}"), "files": man},
              open(f"results/testgen/{iid}/FREEZE.json", "w"), indent=1)
    sh("git", "add", f"results/testgen/{iid}"); c = sh("git", "commit", "-qm", f"STAGE1 FREEZE {iid} (generated tests + pre-fix eval, before patch generation)")
    log(f"stage1 frozen: commit {sh('git','rev-parse','--short','HEAD').stdout.strip()}")
    log(f"#{n} {iid}: stage2 patch")
    r = sh(PY, "lib/stage2_patch.py", iid); log(r.stdout.strip() or r.stderr[-1500:])
    if r.returncode: log("stage2 crashed; stopping"); break
    log(f"#{n} {iid}: stage3 eval")
    r = sh(PY, "lib/stage3_eval.py", iid); log(r.stdout.strip() or r.stderr[-1500:])
    if r.returncode: log("stage3 crashed; stopping"); break
    open(f"{ROOT}/results/digests.jsonl", "a").write(json.dumps({"instance_id": iid, "image": img, "repo_digest": dig, "scored_at": time.strftime("%FT%T%z")}) + "\n")
    sh("git", "add", f"results/patches/{iid}", f"results/eval_{iid}.json", "results/digests.jsonl"); sh("git", "commit", "-qm", f"STAGE2+3 {iid}")
    # cleanup: workspaces + image
    for d in (f"work/runs/testgen/{iid}/ws", f"work/runs/patch/{iid}/ws"):
        if os.path.exists(d): shutil.rmtree(d, ignore_errors=True)
    sh("docker", "rmi", "-f", img); sh("docker", "image", "prune", "-f")
    log(f"#{n} {iid}: done; spent ${agent.spent():.4f}; free {free_gb():.1f} GB")
