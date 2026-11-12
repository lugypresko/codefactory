"""Builds REPORT.md from committed results (read-only analysis; no model calls)."""
import json, os, math, glob, re, subprocess, time
ROOT = "/workspace/lc1a0"; os.chdir(ROOT)
S = json.load(open("sample_v2.json")); order = S["instance_ids_in_order"]; items = {x["instance_id"]: x for x in S["instances"]}
def wilson(k, n, z=1.96):
    if n == 0: return "n/a"
    p = k / n; d = 1 + z * z / n; c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return f"{k}/{n} = {p:.2f} [{max(0, c - h):.2f}, {min(1, c + h):.2f}]"
def J(p):
    try: return json.load(open(p))
    except Exception: return None
added = lambda d: [l[1:].strip() for l in d.splitlines() if l.startswith('+') and not l.startswith('+++') and len(l[1:].strip()) > 25]
rows = []; halted = None
STOP_AFTER = 20  # user decision 22:03 IST: stop after #20; #21-#30 not run
for n, iid in enumerate(order, 1):
    if n > STOP_AFTER: rows.append({"n": n, "iid": iid, "status": "NOT RUN (user stop)"}); continue
    tg = J(f"results/testgen/{iid}/record.json"); pre = J(f"results/testgen/{iid}/pre_eval.json"); pr = J(f"results/patches/{iid}/record.json")
    ev = J(f"results/eval_{iid}.json"); integ = J(f"results/integrity_fail_{iid}.json"); infra = J(f"results/testgen/{iid}/INFRA_FAIL.json")
    if not ev:
        if integ or infra or tg or pr: halted = (n, iid, "INTEGRITY_FAIL" if integ else ("INFRA_FAIL" if infra else "incomplete"))
        rows.append({"n": n, "iid": iid, "status": halted[2] if halted else "not run"}); continue
    tgc = (tg or {}).get("agent", {}).get("cost_usd") or 0.0; pc = (pr or {}).get("cost_usd") or 0.0
    ag = (pr or {}).get("agent", {}); px, ll = ag.get("proxy_metered_cost") or 0, ag.get("litellm_accumulated_cost") or 0
    gap = abs(px - ll) / max(px, ll) if max(px, ll) > 0 else 0
    # exposure grep: generator inputs + trajectory vs gold / test_patch / F2P / produced patch
    traj = ""
    for f in (f"work/runs/testgen/{iid}/trajectory.json", f"results/testgen/{iid}/task.txt"):
        if os.path.exists(f): traj += open(f, errors="replace").read()
    gold = open(f"work/inst/{iid}/gold.diff").read(); tp = open(f"work/inst/{iid}/test.diff").read()
    patch = open(f"results/patches/{iid}/patch.diff").read() if os.path.exists(f"results/patches/{iid}/patch.diff") else ""
    exp = {"gold": sum(l in traj for l in added(gold)), "test_patch": sum(l in traj for l in added(tp)),
           "f2p_names": sum(t.split("::")[-1].split("[")[0] in traj for t in items[iid]["FAIL_TO_PASS"] if len(t.split("::")[-1].split("[")[0]) > 12),
           "patch": sum(l in traj for l in added(patch)), "traj_available": bool(traj)}
    infra2 = "agent server not healthy" in str(pr.get("A_reason")) or (ag.get("execution_status") in (None, "") and ag.get("n_events") is None)
    ld = f"work/runs/patch/{iid}/llm_ledger.json"; proxy_file_cost = json.load(open(ld)).get("cost", 0) if os.path.exists(ld) else 0.0
    rows.append({"n": n, "iid": iid, "status": "INFRA_FAIL (stage 2: OpenHands agent-server crash)" if infra2 else "scored", "infra_detail": str(pr.get("A_reason"))[:160],
                 "proxy_file_cost": proxy_file_cost, "oh_wall": ag.get("wall_seconds"), "run_id": pr.get("artifact", {}).get("producer_run_id"), "nonempty": not pr["patch_empty"], "bytes": pr.get("artifact", {}).get("bytes"),
                 "gt": None if pr["patch_empty"] else bool(ev.get("gt_correct")), "A": ev["A_decision"], "A_reason": pr.get("A_reason"),
                 "unc": pr.get("final_message_uncertain"), "B": ev["B_decision"], "B_reason": ev.get("B_reason") or "", "B_detail": ev.get("B_detail", ""),
                 "tg_valid": (tg or {}).get("validity"), "tg_status": (tg or {}).get("agent", {}).get("status"), "n_disc": len((pre or {}).get("discriminating_units", [])),
                 "clar": (tg or {}).get("clarification"), "tg_cost": tgc, "patch_cost": pc, "gap": gap, "gt_f2p": ev.get("gt_f2p_failed"), "gt_p2p": ev.get("gt_p2p_failed"), "exp": exp})
sc = [r for r in rows if r["status"] == "scored"]; IF = [r for r in rows if r["status"].startswith("INFRA_FAIL")]; allrun = sc + IF; P = [r for r in sc if r["nonempty"]]
wrong = [r for r in P if not r["gt"]]; correct = [r for r in P if r["gt"]]
def metrics(arm, rs=None):
    rs = P if rs is None else rs; W = [r for r in rs if not r["gt"]]; C = [r for r in rs if r["gt"]]; Ap = [r for r in rs if r[arm] == "APPROVE"]
    ca = [r for r in Ap if r["gt"]]; wa = [r for r in Ap if not r["gt"]]
    cost = sum(r["patch_cost"] for r in sc) + (sum(r["tg_cost"] for r in sc) if arm == "B" else 0)
    return {"fpr": (len(wa), len(W)), "prec": (len(ca), len(Ap)), "ret": (len(ca), len(C)), "cost": cost, "cpca": cost / len(ca) if ca else float("inf")}
mA, mB = metrics("A"), metrics("B")
B2 = [r for r in P if r["B_reason"] != "REJECT_INSUFFICIENT_EVIDENCE"]; mB2 = metrics("B", B2)
frac = lambda t: t[0] / t[1] if t[1] else None
fA, fB = frac(mA["fpr"]), frac(mB["fpr"]); retB = frac(mB["ret"])
tg_tot = sum(r["tg_cost"] for r in sc); pa_tot = sum(r["patch_cost"] for r in sc); infra_cost = sum(r["tg_cost"] + max(r["patch_cost"], r["proxy_file_cost"]) for r in IF); overhead = tg_tot / pa_tot if pa_tot else None
grep_hits = [r["iid"] for r in allrun if r["exp"]["gold"] or r["exp"]["test_patch"] or r["exp"]["f2p_names"]]
# classify each grep hit by where it first appears: issue text (allowed input), a tool observation of the pre-fix repo (allowed input),
# or text the test-writer itself authored. Structural check: the generator's only mount is its sanitized pre-fix workspace.
def classify(iid):
    t = json.load(open(f"work/runs/testgen/{iid}/trajectory.json")); msgs = t.get("messages", []); task = open(f"results/testgen/{iid}/task.txt").read()
    out = []; rawt = open(f"work/runs/testgen/{iid}/trajectory.json", errors="replace").read() + task
    for kind, d in (("gold", open(f"work/inst/{iid}/gold.diff").read()), ("test_patch", open(f"work/inst/{iid}/test.diff").read())):
        for l in sorted(set(added(d))):
            if l not in rawt: continue  # only lines the grep check actually hit
            if l in task: out.append((kind, "ISSUE_TEXT", l)); continue
            for m in msgs:
                c = m.get("content"); c = c if isinstance(c, str) else json.dumps(c)
                if m.get("role") == "assistant": c += json.dumps(m.get("extra", {}).get("actions", ""))
                else: c += json.dumps(m.get("extra", {}))  # full (non-elided) tool output, e.g. extra.raw_output
                if l in c or l in c.replace("\\n", "\n").replace('\\"', '"'):
                    out.append((kind, "AGENT_AUTHORED" if m.get("role") == "assistant" else "PRE_FIX_REPO_OBSERVATION", l)); break
            else: out.append((kind, "UNEXPLAINED", l))
    for tname in items[iid]["FAIL_TO_PASS"]:
        nm = tname.split("::")[-1].split("[")[0]
        if len(nm) > 12 and nm in json.dumps(msgs) + task: out.append(("f2p_name", "ISSUE_TEXT" if nm in task else "UNEXPLAINED", nm))
    return out
CL = {iid: classify(iid) for iid in grep_hits}
mounts_ok = all(len(J(f"results/testgen/{r['iid']}/record.json")["agent"]["mounts"]) == 1 and J(f"results/testgen/{r['iid']}/record.json")["agent"]["mounts"][0].endswith("/ws:/testbed") for r in allrun)
exposure = [iid for iid, v in CL.items() if any(src == "UNEXPLAINED" for _, src, _ in v)] + ([] if mounts_ok else ["STRUCTURAL"])
c1 = None if (len(wrong) < 5 or not fA) else (fB <= 0.5 * fA)
c2 = retB is not None and retB >= 0.90; c3 = overhead is not None and overhead <= 0.30; c4 = not exposure
if c1 is None: verdict = "INCONCLUSIVE on criterion 1 (" + ("fewer than 5 wrong patches" if len(wrong) < 5 else "FPR_A = 0") + ")"
elif not c1 or not c4: verdict = "STOP"
elif c2 and c3: verdict = "GO"
else: verdict = "ITERATE"
led = [json.loads(l) for l in open("work/cost_ledger.jsonl")]; total = sum(x["cost_usd"] or 0 for x in led)
L = []; w = L.append
w("# LC-1A.0 v2: Release-decision test. Does the gate (B) separate correct from wrong patches better than Patch Submission (A)?\n")
w(f"Generated {time.strftime('%F %T %Z')}. Protocol: PREREGISTRATION_v2.md, freezes fb24a8f, 2617a58, Amendment 2 9fc8e38, Amendment 3 fe54862 (code used for the scored run); GO checklist 479b4d3.")
w(f"Dataset nebius/SWE-rebench-leaderboard @ {S['dataset_revision']}. Patch producer: OpenHands SDK 1.62.0 agent-server in a sandboxed Docker container (--network none), gemini-2.5-flash. Test-writer: mini-SWE-agent, same model.\n")
w(f"EARLY STOP by user decision (22:03 IST): issues #1-#{STOP_AFTER} run in frozen order, #{STOP_AFTER+1}-#30 not run; per protocol the completed subset is reported.\n")
w(f"Scored: {len(sc)}/30" + (f". HALTED at #{halted[0]} {halted[1]}: {halted[2]} (completed subset reported in frozen order)" if halted else "") + ".\n")
w("## Verdict\n"); w(f"**{verdict}**" + (" (LOW CONFIDENCE: {len(IF)} INFRA_FAIL among {len(allrun)} issues run, more than 3)" if len(IF) > 3 else "") + "\n")
w(f"INFRA_FAIL issues (excluded from metric denominators under the frozen rule; never fixed mid-run): {len(IF)} {[r['iid'] for r in IF]}.\n")
w("| Criterion (preregistered) | Value | Holds |\n|---|---|---|")
w(f"| 1. FPR_B <= 0.5 x FPR_A | FPR_A {wilson(*mA['fpr'])}; FPR_B {wilson(*mB['fpr'])} | {c1 if c1 is not None else 'INCONCLUSIVE'} |")
w(f"| 2. Retention_B >= 0.90 | {wilson(*mB['ret'])} (based on n = {mB['ret'][1]} correct patches{'; INCONCLUSIVE at this n' if mB['ret'][1] < 10 else ''}) | {c2}{' (inconclusive, tiny n)' if mB['ret'][1] < 10 else ''} |")
w(f"| 3. Gate cost overhead <= 30% | test-writer ${tg_tot:.4f} / patch agent ${pa_tot:.4f} = {overhead if overhead is None else f'{overhead:.1%}'} | {c3} |")
w(f"| 4. Zero exposure of B to gold/hidden tests | structural: single sanitized pre-fix mount for all {len(allrun)} test-writer runs = {mounts_ok}; raw grep hits in {len(grep_hits)} issues, all traced to allowed inputs or agent-authored text (see Exposure check); confirmed exposures: {len(exposure)} | {c4} |\n")
w(f"Non-empty source patches: {len(P)}; **wrong patches: {len(wrong)}**; correct: {len(correct)}; empty/failed (not patches): {len(sc) - len(P)}.\n")
w("## Metrics (raw counts, Wilson 95% intervals)\n")
w("| Metric | A: Patch Submission Baseline | B: our gate | B secondary (excl. INSUFFICIENT_EVIDENCE) |\n|---|---|---|---|")
for k, name in (("fpr", "False PASS Rate (wrong approved / wrong)"), ("prec", "Verified Precision (correct approved / approved)"), ("ret", "Correct PR Retention (correct approved / correct)")):
    w(f"| {name} | {wilson(*mA[k])} | {wilson(*mB[k])} | {wilson(*mB2[k])} |")
fm = lambda x: "n/a (no correct approved)" if x == float("inf") else f"${x:.4f}"
w(f"| Cost per Correct Approved PR | {fm(mA['cpca'])} (agent ${mA['cost']:.4f}) | {fm(mB['cpca'])} (agent + gate ${mB['cost']:.4f}) | n/a |\n")
from collections import Counter
bc = Counter(r["B_reason"] or "APPROVE" for r in sc)
w(f"B outcome breakdown over all {len(sc)} scored issues: {dict(bc)}. INSUFFICIENT_EVIDENCE frequency: {wilson(bc.get('REJECT_INSUFFICIENT_EVIDENCE', 0), len(sc))}.")
lost = [r for r in correct if r["B"] != "APPROVE"]
iss_all = len(allrun)
cov = [r for r in sc if r["n_disc"] > 0]; covall = [r for r in allrun if r["n_disc"] > 0]
w(f"\n**Evidence Coverage** (stage 1 produced >= 1 discriminating test, i.e. failing deterministically on pre-fix): {wilson(len(cov), len(sc))} of scored issues ({len(covall)}/{len(allrun)} incl. INFRA_FAIL issues, whose stage 1 ran normally).")
w(f"**B rejections by reason** (scored issues): test-caught (REJECT_INVALID_PATCH) {bc.get('REJECT_INVALID_PATCH', 0)}; insufficient evidence {bc.get('REJECT_INSUFFICIENT_EVIDENCE', 0)}; no patch {bc.get('NO_PATCH', 0)}; approvals {bc.get('APPROVE', 0)}. Among wrong patches: B test-caught {sum(r['B_reason']=='REJECT_INVALID_PATCH' for r in wrong)}, insufficient evidence {sum(r['B_reason']=='REJECT_INSUFFICIENT_EVIDENCE' for r in wrong)}, approved {sum(r['B']=='APPROVE' for r in wrong)}. Among correct patches: approved {sum(r['B']=='APPROVE' for r in correct)}, test-rejected {sum(r['B_reason']=='REJECT_INVALID_PATCH' for r in correct)}, insufficient evidence {sum(r['B_reason']=='REJECT_INSUFFICIENT_EVIDENCE' for r in correct)}.\n")
w(f"Sensitivity (INFRA_FAIL counted as agent failures): INFRA_FAIL runs produced no patch, so the patch-level metrics above (FPR, precision, retention) have the same values. Issue-level yield of correct approved patches: A {mA['ret'][0]}/{len(sc)} excluding vs {mA['ret'][0]}/{iss_all} including INFRA_FAIL; B {mB['ret'][0]}/{len(sc)} vs {mB['ret'][0]}/{iss_all}. Rejections incl. INFRA_FAIL: A {sum(r['A'] != 'APPROVE' for r in sc) + len(IF)}/{iss_all}, B {sum(r['B'] != 'APPROVE' for r in sc) + len(IF)}/{iss_all}.")
w("INFRA_FAIL root cause (diagnosed from server.log; NOT fixed, frozen code): the OpenHands agent-server crashed at startup. Without network, litellm's background model-cost-map fetch fails and the retry path hits a circular import ('LoggerContext' in litellm.rust_bridge.catalog), so the server never became healthy. oh_run.py then waited ~10.5 min for health before giving up. Proposed fix for a future protocol (not applied): set LITELLM_LOCAL_MODEL_COST_MAP=True in the agent-server container + fail fast on health.")
for r in IF: w(f"INFRA_FAIL {r['iid']} run {r['run_id']}: {r['infra_detail']!r}. Proxy-metered cost ${r['proxy_file_cost']:.4f} (no llm_ledger.json means no LLM call reached the proxy); ledger entry ${r['patch_cost']:.4f}; test-writer ${r['tg_cost']:.4f}.")
w(f"Retention losses (correct patches B rejected): {[(r['iid'], r['B_reason']) for r in lost]}.\n")
w("## Per-issue table (frozen order)\n")
w("| # | Instance | Patch produced (source bytes) | Hidden-test truth | A verdict | B verdict | Test-writer (validity, disc. units) | Cost test-writer / patch agent ($) | Cost flag |\n|---|---|---|---|---|---|---|---|---|")
for r in rows:
    if r["status"].startswith("INFRA_FAIL"): w(f"| {r['n']} | {r['iid']} | INFRA_FAIL | n/a | not scored (pipeline logged REJECT {r['A_reason'][:12]}) | not scored | {r['tg_valid']}, {r['n_disc']} | {r['tg_cost']:.4f} / {r['patch_cost']:.4f} | proxy ${r['proxy_file_cost']:.4f} |"); continue
    if r["status"] != "scored": w(f"| {r['n']} | {r['iid']} | {r['status']} | | | | | | |"); continue
    gt = "n/a (no patch)" if r["gt"] is None else ("CORRECT" if r["gt"] else f"WRONG (F2P fail {r['gt_f2p']}, P2P fail {r['gt_p2p']})")
    a = r["A"] + ("" if r["A"] == "APPROVE" else f" ({r['A_reason']})") + (" [uncertain msg]" if r["unc"] else "")
    b = r["B"] + (f" ({r['B_reason']})" if r["B_reason"] else "")
    w(f"| {r['n']} | {r['iid']} | {'yes (' + str(r['bytes']) + ')' if r['nonempty'] else 'no (empty)'} | {gt} | {a} | {b} | {r['tg_valid']}{', clarification' if r['clar'] else ''}, {r['n_disc']} | {r['tg_cost']:.4f} / {r['patch_cost']:.4f} | {'GAP ' + format(r['gap'], '.1%') if r['gap'] > 0.01 else ''} |")
w(f"\n## Cost\nScored issues: test-writer ${tg_tot:.4f}, patch agent ${pa_tot:.4f}, total ${tg_tot + pa_tot:.4f}. INFRA_FAIL issues: ${infra_cost:.4f} (counted in the ledger, excluded from the cost metrics). Ledger total incl. feasibility, smokes and voided runs: ${total:.4f} of the $25 cap.")
w("Cost method: recorded cost = max(proxy metered from Gemini usageMetadata at pinned prices, OpenHands/litellm accumulated_cost); gaps > 1% flagged above. Test-writer cost = mini-SWE-agent/litellm instance_cost (not proxied).\n")
w("## Exposure check (criterion 4)\nFor each issue, the test-writer's task and trajectory were grepped for added lines (>25 chars) of the gold patch and the test_patch, for FAIL_TO_PASS test function names (>12 chars), and (post hoc) for lines of the produced patch.")
w("| Instance | gold lines | test_patch lines | F2P names | produced-patch lines |\n|---|---|---|---|---|")
for r in allrun: w(f"| {r['iid']} | {r['exp']['gold']} | {r['exp']['test_patch']} | {r['exp']['f2p_names']} | {r['exp']['patch']} |")
w("\nOrigin of every grep hit (first occurrence in the test-writer's task/trajectory). ISSUE_TEXT and PRE_FIX_REPO_OBSERVATION are allowed inputs: gold/test_patch lines that already exist in the issue or the pre-fix code. AGENT_AUTHORED = written by the test-writer before it appeared in any observation, e.g. a natural import line. UNEXPLAINED would count as a confirmed exposure.\n")
w("| Instance | Kind | Origin | Line |\n|---|---|---|---|")
for iid, v in CL.items():
    for k, src, l in v: w(f"| {iid} | {k} | {src} | `{l[:80].replace('|', '/')}` |")
w(f"\nSensitivity: if every raw grep hit were treated as exposure, criterion 4 would fail ({len(grep_hits)} issues) and the verdict would be STOP.")
# ---- POST-HOC descriptive timing (user request 19:21; NOT a preregistered metric) ----
from datetime import datetime
log = open("work/pipeline.log").read().split("START SCORED RUN", 1)[-1].splitlines()
T = {}; cur = None; nxt = None
for line in log:
    m = re.match(r"\[(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\] (.*)", line)
    if not m: continue
    t = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S"); msg = m.group(2)
    mm = re.match(r"#\d+ (\S+): (stage1 testgen|stage2 patch|stage3 eval|done)", msg)
    if mm:
        cur = mm.group(1); T.setdefault(cur, {})[mm.group(2)] = t; nxt = "s3out" if mm.group(2) == "stage3 eval" else None; continue
    if cur and msg.startswith("stage1 frozen"): T[cur]["frozen"] = t
    elif cur and msg.startswith("stage2 sealed"): T[cur]["sealed"] = t
    elif cur and nxt == "s3out": T[cur]["s3out"] = t; nxt = None
for r in sc:
    t = T.get(r["iid"], {}); d = lambda a, b: (t[b] - t[a]).total_seconds() if a in t and b in t else None
    r["t1"], r["t2"], r["t3"] = d("stage1 testgen", "frozen"), d("stage2 patch", "sealed"), d("stage3 eval", "s3out")
    ws2 = r.get("oh_wall")
    if ws2: r["t2"] = ws2  # OpenHands run artifact wall_seconds preferred (log start can precede the actual OpenHands start)
def stats(v):
    v = sorted(x for x in v if x is not None)
    if not v: return "n/a"
    med = v[len(v) // 2] if len(v) % 2 else (v[len(v) // 2 - 1] + v[len(v) // 2]) / 2
    p90 = v[min(len(v) - 1, math.ceil(0.9 * len(v)) - 1)]
    return f"median {med/60:.1f} min, p90 {p90/60:.1f} min, total {sum(v)/60:.1f} min (n={len(v)})"
w("\n## Post-hoc descriptive timing (NOT preregistered; user request 19:21)\nWall-clock from work/pipeline.log timestamps (1 s resolution). Stage 1 = test-writer + 2 pre-fix runs + freeze commit; Stage 2 = OpenHands run wall_seconds from its run artifact (log-derived if missing); Stage 3 = evaluation (ground truth + gate), excluding image removal.\n")
w("| Stage | Timing |\n|---|---|")
w(f"| Stage 1 (test-writer incl. pre-fix eval) | {stats([r['t1'] for r in sc])} |")
for st in sorted({r['tg_status'] for r in sc}, key=str): w(f"| Stage 1, test-writer outcome {st} | {stats([r['t1'] for r in sc if r['tg_status'] == st])} |")
w(f"| Stage 2 (OpenHands) | {stats([r['t2'] for r in sc])} |")
w(f"| Stage 3 (evaluation) | {stats([r['t3'] for r in sc])} |")
sA = sum(r["t2"] or 0 for r in sc); sB = sum((r["t1"] or 0) + (r["t2"] or 0) + (r["t3"] or 0) for r in sc)
caA, caB = mA["ret"][0], mB["ret"][0]
per = lambda x, k: f"{x/k/60:.1f} min" if k else "n/a (no correct approved)"
w(f"\nTime and cost per correct approved patch: A {per(sA, caA)} and {fm(mA['cpca'])} (Stage 2 time only); B {per(sB, caB)} and {fm(mB['cpca'])} (Stages 1+2+3).")
w("\n| # | Instance | Stage 1 (s) | test-writer outcome | Stage 2 (s) | Stage 3 (s) |\n|---|---|---|---|---|---|")
for r in sc: w(f"| {r['n']} | {r['iid']} | {r['t1']} | {r['tg_status']} | {r['t2']} | {r['t3']} |")
notest = [r for r in sc if r["n_disc"] == 0]
w("\n## Caveats\n")
w(f"- Early stop by user decision after #{STOP_AFTER}/30 (22:03 IST); #{STOP_AFTER+1}-#30 not run. Small n: all intervals are wide.")
w("- Three protocol amendments before any scored result: (1) Amendment 1 (v1 design, archived); (2) Amendment 2: test-writer sandbox env parity (`bash -c`, testbed PATH) + fail-closed pytest preflight, after the first attempt at #1 ran with no usable python/pytest (voided, kept in git fd918db/b97ed01); (3) Amendment 3: every evaluation bound to the exact sealed patch artifact (run ID, sha256, bytes, base SHA, raw/filtered hashes, git seal, read-only), after an operator diagnostic copied the gold patch into results/ post-verdict in SMOKE2 (RCA evidence/smoke2_rca). Scored run used fe54862 unchanged; GO checklist 479b4d3.")
w(f"- REJECT_INSUFFICIENT_EVIDENCE frequency: {wilson(bc.get('REJECT_INSUFFICIENT_EVIDENCE', 0), len(sc))} of scored issues. Stage-1 produced no discriminating test in {wilson(len(notest), len(sc))} (incl. INVALID runs, clarification requests, tests passing on pre-fix). A large share of B's rejections therefore reflects missing evidence, not a detected defect.")
w(f"- Test-writer runs ending at the 40-step limit: {sum(r['tg_status'] == 'LIMIT_EXCEEDED' for r in sc)}/{len(sc)}; stage-1 INVALID (non-test file created): {sum(r['tg_valid'] == 'INVALID' for r in sc)}/{len(sc)}.")
w(f"- INFRA_FAIL: {len(IF)}/{len(allrun)} (OpenHands agent-server crash at start), excluded from denominators; see sensitivity line." + (" More than 3, so the verdict is LOW CONFIDENCE." if len(IF) > 3 else ""))
w("- One model (gemini-2.5-flash) for producer and test-writer; harness, gate and analysis written by the same agent; SWE-rebench pre-selects clear, test-verifiable issues; n is small and Wilson intervals are wide; gate-P2P is a heuristic subset. A's verdict ('Patch Submission Baseline') is not agent self-confidence.")
w("- Run-to-run variance of the test-writer is large (schemathesis-4087: 1 discriminating unit in SMOKE2, 0 in smoke3, 0 in the scored run).")
w(f"- Cost-gap flags (>1% proxy vs litellm): {[r['iid'] for r in sc if r['gap'] > 0.01]}; recorded cost = max of the two.")
open("REPORT.md", "w").write("\n".join(L) + "\n")
json.dump({"rows": rows, "verdict": verdict}, open("results/summary.json", "w"), indent=1, default=str)
print(verdict, len(sc), "scored; wrong", len(wrong), "correct", len(correct))
