import json,os
rows={r["instance_id"]:r for r in json.load(open("data/all_rows.json"))}
for l in open("data/verification_log.jsonl"):
    x=json.loads(l)
    if not x["verified"]: continue
    r=rows[x["instance_id"]]; d=f"work/inst/{r['instance_id']}"; os.makedirs(d,exist_ok=True)
    open(f"{d}/issue.md","w").write(r["problem_statement"]); open(f"{d}/gold.diff","w").write(r["patch"]); open(f"{d}/test.diff","w").write(r["test_patch"])
    json.dump({"F2P":r["FAIL_TO_PASS"],"P2P_eff":x["effective_p2p"],"test_cmd":x["test_cmd"],"image":r["docker_image"],"repo":r["repo"],"created_at":r["created_at"],"base_commit":r["base_commit"]},open(f"{d}/meta.json","w"),indent=1)
