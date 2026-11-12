"""STAGE 2 — patch production with OpenHands (SDK 1.62.0 agent-server in a Docker sandbox, --network none, LLM via host proxy).
Runs only after the issue's stage-1 outputs are frozen (git commit)."""
import json, os, sys, shutil, subprocess, re
sys.path.insert(0, os.path.dirname(__file__))
import agent
from common2 import ROOT, H, items, strip_tests
iid = sys.argv[1]
if agent.spent() + 0.50 > agent.BUDGET: print(iid, "BUDGET_STOP"); sys.exit(0)
rd = f"{ROOT}/work/runs/patch/{iid}"; shutil.rmtree(rd, ignore_errors=True); os.makedirs(rd)
env = dict(os.environ, LC_ROLE="patch-openhands", LC_RUNID=f"pa-{iid}")
p = subprocess.run(["timeout", "1700", f"{ROOT}/.ohvenv/bin/python", f"{ROOT}/oh/oh_run.py", iid, rd, "0.50", "50", "1200"], env=env, capture_output=True, text=True)
open(f"{rd}/oh_stdout.log", "w").write(p.stdout[-50000:] + "\n---stderr---\n" + p.stderr[-50000:])
res = json.load(open(f"{rd}/oh_result.json")) if os.path.exists(f"{rd}/oh_result.json") else {"error": f"oh_run exit {p.returncode}", "cost_usd": None}
if not os.path.exists(f"{rd}/oh_result.json"):  # crashed before ledger write: record proxy ledger if any
    lj = f"{rd}/llm_ledger.json"; c = json.load(open(lj))["cost"] if os.path.exists(lj) else 0.0
    open(agent.LEDGER, "a").write(json.dumps({"run_id": f"pa-{iid}", "role": "patch-openhands", "cost_usd": c, "note": "oh_run crashed"}) + "\n"); res["cost_usd"] = c
raw = open(f"{rd}/patch_raw.diff").read() if os.path.exists(f"{rd}/patch_raw.diff") else ""
parts = [x for x in re.split(r'(?=^diff --git )', raw, flags=re.M) if x.startswith("diff --git ")]
raw = "".join(x for x in parts if not any(b in x.split("\n", 1)[0] for b in agent.BENIGN))
src, dropped = strip_tests(raw)
last = res.get("final_message", "") or ""
UNC = re.compile(r"\b(partial(ly)?|uncertain|not sure|unsure|could not|couldn't|unable|cannot verify|may not|might not|TODO|workaround|not fully)\b", re.I)
od = f"{ROOT}/results/patches/{iid}"; shutil.rmtree(od, ignore_errors=True); os.makedirs(od)
open(f"{od}/patch_raw.diff", "w").write(raw); open(f"{od}/patch.diff", "w").write(src); open(f"{od}/final_message.txt", "w").write(last)
finished = "FINISHED" in str(res.get("execution_status")) and not res.get("wall_timeout") and not res.get("error") and not res.get("run_error")
A = "APPROVE" if (finished and src.strip()) else "REJECT"
reason = "" if A == "APPROVE" else ("EMPTY_DIFF" if finished else ("WALL_TIMEOUT" if res.get("wall_timeout") else ("ERROR/LIMIT: " + str(res.get("error") or res.get("run_error") or res.get("execution_status"))[:200])))
rec = {"instance_id": iid, "engine": "OpenHands SDK 1.62.0 agent-server (Docker sandbox)", "agent": {k: v for k, v in res.items() if k not in ("final_message",)},
       "cost_usd": res.get("cost_usd"), "patch_sha256": H(src), "patch_raw_sha256": H(raw), "patch_empty": not src.strip(),
       "dropped_test_files": [d for d in dropped], "A_decision": A, "A_reason": reason,
       "final_message_uncertain": bool(UNC.search(last)), "uncertainty_matches": sorted({m.group(0).lower() for m in UNC.finditer(last)})}
json.dump(rec, open(f"{od}/record.json", "w"), indent=2, default=str)
shutil.rmtree(f"{rd}/conda", ignore_errors=True); shutil.rmtree(f"{rd}/ws", ignore_errors=True)
print(iid, A, reason, res.get("cost_usd"), len(src))
