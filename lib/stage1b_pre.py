"""STAGE 1b — run frozen generated tests on PRE-FIX twice (no patch exists yet). Determines discriminating units."""
import json, os, sys, glob
sys.path.insert(0, os.path.dirname(__file__))
import dockrun
from common2 import ROOT, items, pytest_cmd
iid = sys.argv[1]; it = items()[iid]; od = f"{ROOT}/results/testgen/{iid}"
tests = {os.path.relpath(f, f"{od}/tests"): open(f).read() for f in glob.glob(f"{od}/tests/**/*.py", recursive=True)}
out = {"instance_id": iid, "n_files": len(tests)}
if tests:
    runs = [dockrun.run(it["docker_image"], [], files=tests, cmd=pytest_cmd(tests)) for _ in range(2)]
    oc = [r["outcomes"] for r in runs]
    out["pre_outcomes"] = oc; out["pre_deterministic"] = oc[0] == oc[1]; out["pre_timeout"] = any(r["timeout"] for r in runs)
    fails = lambda o: {k for k, v in o.items() if v in ("FAILED", "ERROR")}
    out["discriminating_units"] = sorted(fails(oc[0]) & fails(oc[1]))  # only units failing in BOTH pre runs
    out["non_discriminating_discarded"] = sorted(k for k, v in oc[0].items() if k not in out["discriminating_units"])
    out["no_outcomes"] = not oc[0]
    open(f"{ROOT}/work/runs/testgen/{iid}/pre_log.txt", "w").write(runs[0]["log"][-20000:])
else:
    out["discriminating_units"] = []
json.dump(out, open(f"{od}/pre_eval.json", "w"), indent=2)
print(iid, len(tests), "disc:", len(out["discriminating_units"]), "det:", out.get("pre_deterministic"))
