"""INJECTED-PATCH smoke only (scratch worktree): stands in for oh/oh_run.py. No model calls. Prepares the sanitized workspace
exactly like the real runner (agent.prep_ws), applies a KNOWN non-empty patch, extracts the diff the same way, writes oh_result."""
import json, os, sys, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__))); sys.path.insert(0, f"{ROOT}/lib")
import agent as A
iid, out = sys.argv[1], os.path.abspath(sys.argv[2]); os.makedirs(out, exist_ok=True); ws = f"{out}/ws"
img = {x["instance_id"]: x for x in json.load(open(f"{ROOT}/sample_v2.json"))["instances"]}[iid]["docker_image"]
base = A.prep_ws(img, ws)
r = subprocess.run(["git", "-C", ws, "-c", "safe.directory=*", "apply", os.environ["LC_INJECT_PATCH"]], capture_output=True, text=True)
g = lambda *a: subprocess.run(["git", "-C", ws, "-c", "safe.directory=*", *a], capture_output=True, text=True).stdout
g("add", "-A"); diff = g("diff", "--cached", base); open(f"{out}/patch_raw.diff", "w").write(diff)
json.dump({"execution_status": "ConversationExecutionStatus.FINISHED", "cost_usd": 0.0, "final_message": "injected known patch",
           "run_id": os.environ.get("LC_RUNID"), "base_sha": base, "inject_apply_rc": r.returncode, "injected": True}, open(f"{out}/oh_result.json", "w"))
print(json.dumps({"apply_rc": r.returncode, "diff_bytes": len(diff), "base": base}))
