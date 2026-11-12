"""STAGE 1 — acceptance-test generation (before ANY patch exists). usage: stage1_testgen.py <iid>
Inputs: issue text (prompt) + sanitized pre-fix /testbed copy (only mount) + image deps. Container --network none."""
import json, os, sys, shutil
sys.path.insert(0, os.path.dirname(__file__))
import agent
from common2 import ROOT, H, items, issue_text
iid = sys.argv[1]; it = items()[iid]; img = it["docker_image"]
rd = f"{ROOT}/work/runs/testgen/{iid}"; shutil.rmtree(rd, ignore_errors=True); os.makedirs(rd)
ws = f"{rd}/ws"; base = agent.prep_ws(img, ws)
task = open(f"{ROOT}/prompts/testgen.txt").read().replace("{issue}", issue_text(iid))
res = agent.run("testgen", f"tg-{iid}", img, task, ws, rd, 0.25, 40, 900)
cl = agent.classify(ws, base)
od = f"{ROOT}/results/testgen/{iid}"; shutil.rmtree(od, ignore_errors=True); os.makedirs(od)
valid = not cl["violations"] and res["status"] != "BUDGET_STOP"
tests = cl["tests"] if valid else {}
for rel, c in tests.items():
    fp = f"{od}/tests/{rel}"; os.makedirs(os.path.dirname(fp), exist_ok=True); open(fp, "w").write(c)
if cl["clarification"] is not None: open(f"{od}/CLARIFICATION_NEEDED.md", "w").write(cl["clarification"])
rec = {"instance_id": iid, "agent": res, "validity": "BUDGET_STOP" if res["status"] == "BUDGET_STOP" else ("INVALID" if cl["violations"] else "VALID"),
       "violations": cl["violations"], "benign": cl["benign"], "sanitized_base_sha": base, "original_base_commit": it["base_commit"],
       "task_sha256": H(task), "test_files": {k: H(v) for k, v in sorted(tests.items())}, "clarification": cl["clarification"] is not None,
       "input_manifest": {"prompt": "prompts/testgen.txt with issue text substituted (task.txt saved)", "mounts": [f"{ws}:/testbed (sanitized pre-fix copy of image /testbed, fresh 1-commit git)"],
                          "network": "container --network none; LLM API called by host-side mini process", "env_forwarded": [], "image": img}}
json.dump(rec, open(f"{od}/record.json", "w"), indent=2)
shutil.copy(f"{rd}/task.txt", f"{od}/task.txt"); shutil.copy(f"{rd}/config.yaml", f"{od}/config.yaml")
print(iid, rec["validity"], res["status"], res.get("cost_usd"), sorted(tests), rec["clarification"])
