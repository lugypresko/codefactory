#!/usr/bin/env python3
"""Build report.json + report.md for one LC-0 run and exit with the lc0_verdict code."""
import datetime, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lc0util as u

EXIT = {"PASS": 0, "FAIL": 1, "ERROR": 3, "ESCALATE": 4, "CONTROLLED_STOP": 5, "INVALID_BASELINE": 6}


def main(root, rd, ev, brc, arc, e1, e2, dur):
    brc, arc, e1, e2 = map(int, (brc, arc, e1, e2))
    L = lambda p: json.load(open(p)) if os.path.exists(p) else None
    rel = lambda p: os.path.relpath(p, root) if p else None
    work = os.environ.get("LC0_WORK", os.path.join(root, "work")); repo = os.path.join(work, "repo")
    env = L(os.path.join(work, "environment.json")); agent = L(os.path.join(rd, "agent_result.json")) or {}
    base = L(os.path.join(ev, "baseline.json")); ev1 = L(os.path.join(ev, "eval_1.json")); ev2 = L(os.path.join(ev, "eval_2.json"))
    strip = lambda d: {k: v for k, v in (d or {}).items() if k not in ("evaluated_at", "duration_s")}

    bl = u.check_baseline(os.path.join(ev, "baseline.json"), os.path.join(root, "task", "manifest.json"))
    ast = agent.get("agent_status", "INFRA_ERROR")
    same = ev1 is not None and ev2 is not None and strip(ev1) == strip(ev2)
    decs = [d["decision"] for d in (ev1, ev2) if d]
    # ---- delivery verdict (meaning unchanged: was the product delivered and independently verified?) ----
    if bl["status"] == "ERROR":          dv, why = "ERROR", "baseline evaluation error: " + "; ".join(map(str, bl["problems"]))
    elif bl["status"] != "VALID":        dv, why = "INVALID_BASELINE", "; ".join(bl["problems"])
    elif ast == "INFRA_ERROR":           dv, why = "ERROR", f"agent infra error: {agent.get('reason')}"
    elif ast == "AGENT_CRASH":           dv, why = "ESCALATE", f"agent crashed: {agent.get('reason')}"
    elif ast != "SUBMITTED":             dv, why = "FAIL", f"agent did not deliver: {ast} {agent.get('limit_hit') or ''}".strip()
    elif "ERROR" in decs or len(decs) < 2: dv, why = "ERROR", "evaluator error: " + "; ".join(d.get("reason", "") for d in (ev1, ev2) if d)
    elif not same:                       dv, why = "ESCALATE", "the two evaluations of the same SHA disagree"
    elif decs[0] == "ESCALATE":          dv, why = "ESCALATE", ev1["reason"]
    elif decs[0] == "FAIL":              dv, why = "FAIL", ev1["reason"]
    else:                                dv, why = "PASS", "baseline valid; agent submitted; F2P+P2P all passed; diff policy OK; 2 identical evaluations"
    # ---- recovery + combined verdict ----
    tp = (agent.get("paths") or {}).get("trajectory")
    tp = tp if tp and os.path.exists(tp) else os.path.join(rd, "trajectory.json")
    fault_id = (agent.get("fault") or {}).get("fault_id", "none")
    rec = u.recovery(tp, os.path.join(rd, "agent_result.json"), dv, repo) if agent else {"level": "N/A", "note": "no agent result"}
    if dv == "INVALID_BASELINE":
        lv, lwhy = "INVALID_BASELINE", "baseline does not fail as declared; the run proves nothing"
    else:
        lv, lwhy = u.lc0_verdict(fault_id, dv, rec)
    dp = (ev1 or {}).get("diff_policy")

    rep = {"run_id": os.path.basename(rd), "lc0_verdict": lv, "lc0_reason": lwhy, "delivery_verdict": dv, "delivery_reason": why,
           "recovery": rec, "diff_policy": dp, "decision": lv,
           "generated_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "total_seconds": int(dur),
           "environment": env, "fault": agent.get("fault"),
           "baseline": {"status": bl["status"], "problems": bl["problems"], "evaluator_exit": brc, "sha": (base or {}).get("sha"),
                        "report": rel(os.path.join(ev, "baseline.json"))},
           "agent": agent, "agent_exit": arc,
           "evaluations": [{"exit": c, "decision": (d or {}).get("decision"), "reason": (d or {}).get("reason"), "report": rel(os.path.join(ev, n))}
                           for c, d, n in ((e1, ev1, "eval_1.json"), (e2, ev2, "eval_2.json")) if d],
           "evaluations_identical": same if ev1 else None,
           "tests": {"FAIL_TO_PASS": (ev1 or {}).get("FAIL_TO_PASS"), "PASS_TO_PASS": (ev1 or {}).get("PASS_TO_PASS")},
           "integrity": {"hidden_tests_sha256": (ev1 or base or {}).get("hidden_tests_sha256"),
                         "p2p_tests_sha256": (ev1 or base or {}).get("p2p_tests_sha256"),
                         "verified_before_and_after": all(d.get("test_hashes_verified_before") and d.get("test_hashes_verified_after") for d in (base, ev1, ev2) if d),
                         "harness_sensitive_files": (ev1 or {}).get("harness_sensitive_files")},
           "paths": {"report_md": rel(os.path.join(rd, "report.md")), "report_json": rel(os.path.join(rd, "report.json")),
                     "trajectory": rel(tp), "agent_log": rel(os.path.join(rd, "agent_stdout.log")),
                     "diff": rel(os.path.join(rd, "final.diff")), "agent_result": rel(os.path.join(rd, "agent_result.json"))}}
    json.dump(rep, open(os.path.join(rd, "report.json"), "w"), indent=2)

    a = agent; e = env or {}; f = a.get("fault") or {}
    md = [f"# LC-0 run `{rep['run_id']}` — LC-0 verdict **{lv}**", "",
          "| verdict | value | why |", "|---|---|---|",
          f"| delivery | **{dv}** | {why} |",
          f"| recovery | **{rec.get('level')}** (fault_cleared={rec.get('fault_cleared')}) | {rec.get('note')} |",
          f"| diff policy | **{(dp or {}).get('result', 'n/a')}** | {'; '.join((dp or {}).get('violations', [])) or 'no violations'} |",
          f"| **LC-0** | **{lv}** | {lwhy} |", "",
          f"Generated {rep['generated_at']} · total {dur}s", "",
          "## Fault injection and recovery evidence",
          f"- fault: `{f.get('fault_id')}` — {f.get('description', '')}",
          f"- injected_at: {f.get('injected_at')} · fired events: {f.get('fired_events')}",
          f"- observed={rec.get('observed')} · adapted={rec.get('adapted')} · level={rec.get('level')} · fault_cleared={rec.get('fault_cleared')}",
          f"- evidence: `{json.dumps(rec.get('evidence', {}), ensure_ascii=False)}`", "",
          "## Diff policy", f"- result: {(dp or {}).get('result')}", f"- violations: {(dp or {}).get('violations')}",
          f"- info: `{json.dumps((dp or {}).get('info', {}), ensure_ascii=False)}`", "",
          "## Steps", "| step | result | detail |", "|---|---|---|",
          f"| (a) baseline on `{(base or {}).get('sha', '?')[:12]}` | {bl['status']} | {'; '.join(bl['problems']) or 'every F2P test fails with its declared failure; P2P passes'} |",
          f"| (b) agent | {ast} (exit {arc}) | mini exit_status=`{a.get('mini_exit_status')}`, model requested `{a.get('model_requested')}`, returned {a.get('models_returned_by_api')}, cost ${a.get('cost_usd') or 0:.4f} / ${a.get('cost_limit_usd')}, steps {a.get('api_calls')} / {a.get('step_limit')}, wall {a.get('wall_seconds')}s, diff {a.get('diff_files')} files |"]
    for i, r in enumerate(rep["evaluations"], 1):
        md.append(f"| (c) evaluation {i} on `{(a.get('final_sha') or '')[:12]}` | {r['decision']} (exit {r['exit']}) | {r['reason']} |")
    md += ["", f"Evaluations identical: **{rep['evaluations_identical']}**", "",
           f"SHAs: base `{a.get('base_sha')}` → final `{a.get('final_sha')}` (workspace_sha if incomplete: `{a.get('workspace_sha')}`)", "",
           "## Versions", "| item | value |", "|---|---|"] + [f"| {k} | `{v}` |" for k, v in e.items()] + [""]
    for s in ("FAIL_TO_PASS", "PASS_TO_PASS"):
        t = rep["tests"][s]
        if t:
            md += [f"## {s}: {t['status']} ({t['passed']}/{t['expected']})", "| test | result |", "|---|---|"] + [f"| {k} | {v} |" for k, v in t["tests"].items()] + [""]
    md += ["## Integrity", f"- hidden tests sha256 `{rep['integrity']['hidden_tests_sha256']}`", f"- P2P tests sha256 `{rep['integrity']['p2p_tests_sha256']}`",
           f"- pinned hashes verified before and after every evaluation: {rep['integrity']['verified_before_and_after']}",
           f"- harness-sensitive files in artifact: {rep['integrity']['harness_sensitive_files']}", "", "## Paths (relative to package root)"] + \
          [f"- {k}: `{v}`" for k, v in rep["paths"].items()] + [f"- baseline: `{rep['baseline']['report']}`"] + [f"- evaluation: `{r['report']}`" for r in rep["evaluations"]]
    open(os.path.join(rd, "report.md"), "w").write("\n".join(md) + "\n")
    return EXIT.get(lv, 3)


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
