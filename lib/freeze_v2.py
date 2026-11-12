import json, subprocess, os, sys
sys.path.insert(0, "lib"); from common2 import H
rows = {r["instance_id"]: r for r in json.load(open("data/all_rows.json"))}
ver = [json.loads(l) for l in open("data/verification_log.jsonl")]
ok = [v for v in ver if v["verified"]][:30]
assert len(ok) == 30, len(ok)
inst = []
for v in ok:
    r = rows[v["instance_id"]]
    dig = subprocess.run(["docker", "image", "inspect", r["docker_image"], "--format", "{{index .RepoDigests 0}}"], capture_output=True, text=True).stdout.strip()
    inst.append({"instance_id": r["instance_id"], "repo": r["repo"], "created_at": r["created_at"], "base_commit": r["base_commit"],
                 "docker_image": r["docker_image"], "image_repo_digest": dig, "issue_sha256": H(r["problem_statement"]),
                 "gold_patch_sha256": H(r["patch"]), "test_patch_sha256": H(r["test_patch"]), "FAIL_TO_PASS": r["FAIL_TO_PASS"],
                 "n_effective_p2p": len(v["effective_p2p"]), "test_cmd": v["test_cmd"]})
s = {"dataset": "nebius/SWE-rebench-leaderboard", "dataset_revision": "34d5a58864acf91613740a09ec5d205228dcfa39",
     "parquet_ref": "refs/convert/parquet@55f056ab01ea7452ed4e300b723688a0364804dd", "splits": ["2026_01", "2026_02", "2026_03"],
     "parquet_sha256": [l for l in open("data/SHA256SUMS").read().split("\n") if l],
     "alternative_source_not_used": "github.com/SWE-rebench/SWE-rebench-V2",
     "selection_rule": "lib/candidates.py + PREREGISTRATION_v2.md", "preregistration_v2_sha256": H(open("PREREGISTRATION_v2.md").read()),
     "verification_rejections": [{"instance_id": v["instance_id"], "reason": v.get("reason")} for v in ver if not v["verified"] and ver.index(v) < ver.index(ok[-1])],
     "instance_ids_in_order": [x["instance_id"] for x in inst], "instances": inst}
json.dump(s, open("sample_v2.json", "w"), indent=1)
print(len(inst), s["verification_rejections"])
