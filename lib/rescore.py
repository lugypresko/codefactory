#!/usr/bin/env python3
"""Offline re-scoring of SEALED run evidence with the current package version (no agent run, no LLM calls, $0).
For each run directory under <evidence_dir> (e.g. evidence/lc0-final/<run>): copies the package + canonical repo + the run
into a scratch dir, runs `LC0_REPORT_ONLY=1 reproduce.sh <run>` there (verifies the sealed evidence_manifest first; any
mismatch => ERROR), and writes the new report + evaluations to <out_dir>/<run>/. The sealed evidence is never written:
its files are hashed before and after and the run fails if anything changed. <out_dir>/rescore_manifest.json binds it all.
Usage: rescore.py <package_root> <evidence_dir> <out_dir> <run> [<run> ...]"""
import datetime, hashlib, json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
tree = lambda d: {str(p.relative_to(d)): sha(p) for p in sorted(Path(d).rglob("*")) if p.is_file()}


def main(root, evd, out, *runs):
    root, evd, out = Path(root).resolve(), Path(evd).resolve(), Path(out).resolve(); out.mkdir(parents=True, exist_ok=True)
    before = tree(evd); tmp = Path(tempfile.mkdtemp(prefix="lc0-rescore-", dir=os.environ.get("LC0_RESCORE_TMP")))
    vers = dict(l.split("=", 1) for l in (root / "VERSIONS").read_text().splitlines() if "=" in l and not l.startswith("#"))
    res = {}
    try:
        pkg = tmp / "pkg"
        shutil.copytree(root, pkg, ignore=shutil.ignore_patterns(".venv", "work", "evidence", "__pycache__"))
        (pkg / "work/runs").mkdir(parents=True)
        shutil.copytree(root / "work/repo", pkg / "work/repo", symlinks=True)
        shutil.copy(root / "work/environment.json", pkg / "work/environment.json")
        env = dict(os.environ, LC0_WORK=str(pkg / "work"), LC0_REPORT_ONLY="1")
        for run in runs:
            src = evd / run; rd = pkg / "work/runs" / run
            shutil.copytree(src, rd)
            for f in ("report.json", "report.md"):  # the old report is kept for comparison, not as an input
                if (rd / f).exists():
                    (rd / f).rename(rd / f.replace("report", "report.prev_v14"))
            a = json.loads((rd / "agent_result.json").read_text()); man = json.loads((rd / "evidence_manifest.json").read_text())
            tp = (a.get("paths") or {}).get("trajectory")  # report.py prefers this absolute path if it exists: it must be the sealed file
            traj_note = None
            if tp and os.path.exists(tp):
                traj_note = {"path": tp, "matches_sealed": sha(tp) == man["inputs"].get("run/trajectory.json")}
                if not traj_note["matches_sealed"]:
                    raise SystemExit(f"{run}: trajectory at {tp} differs from the sealed one")
            p = subprocess.run([str(pkg / "reproduce.sh"), run], env=env, capture_output=True, text=True)
            o = out / run; o.mkdir(exist_ok=True)
            for f in ("report.json", "report.md", "evidence_verify.json"):
                if (rd / f).exists():
                    shutil.copy(rd / f, o / f)
            for f in ("baseline.json", "eval_1.json", "eval_2.json"):
                if (pkg / "work/evals" / run / f).exists():
                    shutil.copy(pkg / "work/evals" / run / f, o / f)
            (o / "reproduce.log").write_text(p.stderr[-6000:])
            old = json.loads((src / "report.json").read_text()) if (src / "report.json").exists() else {}
            new = json.loads((o / "report.json").read_text()) if (o / "report.json").exists() else {}
            pick = lambda r: {"delivery": r.get("delivery_verdict"), "recovery": (r.get("recovery") or {}).get("level"),
                              "diff_policy": (r.get("diff_policy") or {}).get("result"), "lc0": r.get("lc0_verdict")}
            res[run] = {"exit": p.returncode, "v1.4": pick(old), "v1.5": pick(new),
                        "v1.5_violations": (new.get("diff_policy") or {}).get("violations"),
                        "v1.5_forbidden": (new.get("recovery") or {}).get("forbidden"),
                        "v1.5_lc0_reason": new.get("lc0_reason"), "trajectory_path_check": traj_note}
            print(f"{run:24} exit={p.returncode} v1.4={pick(old)} v1.5={pick(new)}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    after = tree(evd)
    m = {"what": "offline re-scoring of sealed evidence with the current package (LC0_REPORT_ONLY=1, no LLM calls)",
         "package_version": vers.get("package_version"), "rescored_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
         "policy_files_sha256": {f: sha(root / f) for f in ("lib/lc0util.py", "lib/report.py", "task/fault_manifest.json", "task/diff_policy.json", "evaluate.sh", "reproduce.sh")},
         "sealed_evidence_dir": str(evd.relative_to(root)) if evd.is_relative_to(root) else str(evd),
         "sealed_evidence_unchanged": before == after, "sealed_evidence_sha256": before,
         "runs": res, "outputs_sha256": {str(p.relative_to(out)): sha(p) for p in sorted(out.rglob("*")) if p.is_file() and p.name != "rescore_manifest.json"}}
    (out / "rescore_manifest.json").write_text(json.dumps(m, indent=2) + "\n")
    print(json.dumps({"sealed_evidence_unchanged": m["sealed_evidence_unchanged"], "runs": len(res)}))
    return 0 if m["sealed_evidence_unchanged"] else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
