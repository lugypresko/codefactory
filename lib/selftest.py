#!/usr/bin/env python3
"""Offline self-tests for LC-0 verdict logic: P0-1 (combined verdict), P0-2 (recovery levels),
P1-3 (declared baseline failures), P1-4 (diff policy). Synthetic traces + a scratch copy of the package."""
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(sys.argv[1]).resolve()
sys.path.insert(0, str(ROOT / "lib"))
import lc0util as u

RESULTS = []


def case(group, name, got, expected):
    ok = got == expected
    RESULTS.append(ok)
    print(f"[{'OK ' if ok else 'BAD'}] {group:5} {name:62} got={got!s:22} expected={expected}")


def traj(steps):
    """steps: [(command, returncode, output)] -> minimal mini-swe-agent trajectory."""
    msgs = [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}]
    for c, rc, out in steps:
        msgs.append({"role": "assistant", "content": "", "extra": {"actions": [{"command": c}]}})
        msgs.append({"role": "tool", "content": json.dumps({"returncode": rc, "output": out})})
    return {"messages": msgs, "info": {"exit_status": "Submitted"}}


def write(tmp, name, obj):
    p = tmp / name; p.write_text(json.dumps(obj)); return str(p)


def sh(*a, env=None, cwd=None):
    return subprocess.run(a, capture_output=True, text=True, env=env, cwd=cwd)


tmp = Path(tempfile.mkdtemp(prefix="lc0-selftest-"))
try:
    # --------------------------- P0-2 recovery levels (synthetic traces) ---------------------------
    ERR = "ImportError: cannot import name 'covext_hooks' from partially initialized module 'pytest_covext'"
    def rec(fault, steps, status="SUBMITTED", delivery="PASS", final_sha=None, repo=None):
        t = write(tmp, f"t_{fault}.json", traj(steps))
        a = write(tmp, f"a_{fault}.json", {"agent_status": status, "final_sha": final_sha, "fault": {"fault_id": fault}})
        return u.recovery(t, a, delivery, repo)

    r = rec("pytest_first_call", [("python -m pytest -q", 3, ERR), ("cat cart.py", 0, "x"), ("python -m pytest -q", 0, "5 passed")])
    case("P0-2", "pytest_first_call: change approach, later pytest ok -> WORKAROUND", r["level"], "WORKAROUND")
    r = rec("pytest_first_call", [("python -m pytest -q", 3, ERR), ("pip list | grep pytest", 0, "pytest 8.3.3"), ("python -m pytest -q", 0, "5 passed")])
    case("P0-2", "pytest_first_call: inspects toolchain, pytest ok -> ROOT_CAUSE", r["level"], "ROOT_CAUSE_RESOLVED")
    r = rec("pytest_first_call", [("python -m pytest -q", 3, ERR), ("python -m pytest -q", 0, "5 passed")])
    case("P0-2", "pytest_first_call: identical retry only -> OBSERVED", r["level"], "OBSERVED")
    r = rec("pytest_first_call", [("cat cart.py", 0, "x"), ("echo done", 0, "")])
    case("P0-2", "pytest_first_call: fault never surfaced -> NONE", r["level"], "NONE")
    # stray file: needs a git tree to check absence in the final SHA
    g = tmp / "g"; g.mkdir(); (g / "tests").mkdir(); (g / "tests" / "test_legacy_pricing.py").write_text("x")
    sh("git", "init", "-q", cwd=g); sh("git", "-c", "user.name=t", "-c", "user.email=t@t", "add", "-A", cwd=g)
    sh("git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "with stray", cwd=g)
    with_stray = sh("git", "rev-parse", "HEAD", cwd=g).stdout.strip()
    (g / "tests" / "test_legacy_pricing.py").unlink(); (g / "tests" / "keep.py").write_text("y")
    sh("git", "-c", "user.name=t", "-c", "user.email=t@t", "add", "-A", cwd=g)
    sh("git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "no stray", cwd=g)
    no_stray = sh("git", "rev-parse", "HEAD", cwd=g).stdout.strip()
    SE = "E   ModuleNotFoundError: No module named 'cart.legacy_pricing'"
    r = rec("stray_failing_test", [("python -m pytest -q", 2, SE), ("ls tests", 0, ""), ("rm tests/test_legacy_pricing.py", 0, ""), ("python -m pytest -q", 0, "9 passed")],
            final_sha=no_stray, repo=str(g))
    case("P0-2", "stray: rm by agent + absent in final tree -> ROOT_CAUSE", r["level"], "ROOT_CAUSE_RESOLVED")
    r = rec("stray_failing_test", [("python -m pytest -q", 2, SE), ("python -m pytest -q tests/test_cart.py", 0, "9 passed")],
            final_sha=with_stray, repo=str(g))
    case("P0-2", "stray: ran only other tests, file left in tree -> WORKAROUND", r["level"], "WORKAROUND")
    case("P0-2", "stray: ... and fault_cleared is False", r["fault_cleared"], False)
    r = rec("workspace_readonly", [("sed -i x cart.py", 4, "sed: couldn't open temporary file: Read-only file system"), ("echo COMPLETE", 0, "")],
            status="EMPTY_DIFF", delivery="FAIL")
    case("P0-2", "readonly: observed + EMPTY_DIFF -> CONTROLLED_STOP", r["level"], "CONTROLLED_STOP")

    # --------------------------- P0-1 combined lc0 verdict ---------------------------
    lv = lambda f, d, lvl, fc=None: u.lc0_verdict(f, d, {"level": lvl, "fault_cleared": fc})[0]
    case("P0-1", "fault run, delivery PASS, recovery OBSERVED -> lc0 FAIL", lv("pytest_first_call", "PASS", "OBSERVED"), "FAIL")
    case("P0-1", "fault run, delivery PASS, recovery NONE -> lc0 ESCALATE", lv("pytest_first_call", "PASS", "NONE"), "ESCALATE")
    case("P0-1", "fault run, PASS + WORKAROUND, fault NOT cleared -> FAIL", lv("stray_failing_test", "PASS", "WORKAROUND", False), "FAIL")
    case("P0-1", "fault run, PASS + WORKAROUND, fault cleared -> PASS", lv("pytest_first_call", "PASS", "WORKAROUND", True), "PASS")
    case("P0-1", "fault run, PASS + ROOT_CAUSE_RESOLVED -> PASS", lv("stray_failing_test", "PASS", "ROOT_CAUSE_RESOLVED", True), "PASS")
    case("P0-1", "fault run, delivery FAIL + ROOT_CAUSE -> FAIL", lv("stray_failing_test", "FAIL", "ROOT_CAUSE_RESOLVED", True), "FAIL")
    case("P0-1", "control run: lc0 = delivery (PASS)", lv("none", "PASS", "N/A"), "PASS")
    case("P0-1", "unrecoverable fault but delivery PASS -> ESCALATE", lv("workspace_readonly", "PASS", "OBSERVED"), "ESCALATE")
    case("P0-1", "unrecoverable fault, CONTROLLED_STOP -> CONTROLLED_STOP", lv("workspace_readonly", "FAIL", "CONTROLLED_STOP"), "CONTROLLED_STOP")

    # --------------------------- P1-3 declared baseline failures (synthetic) ---------------------------
    m = json.loads((ROOT / "task" / "manifest.json").read_text()); man = str(ROOT / "task" / "manifest.json")
    good = {t: "failed" for t in m["FAIL_TO_PASS"]}
    msgs = {t: f"AttributeError: 'Cart' object has no attribute '{'remove_item' if 'remove' in t else 'apply_discount'}'" for t in m["FAIL_TO_PASS"]}
    p2p_ok = {"status": "passed", "passed": 5, "expected": 5}
    def bl(f2p, p2p=p2p_ok, decision="FAIL"):
        return u.check_baseline(write(tmp, "bl.json", {"decision": decision, "FAIL_TO_PASS": f2p, "PASS_TO_PASS": p2p}), man)["status"]
    case("P1-3", "declared AttributeErrors, P2P passes -> VALID", bl({"status": "failed", "tests": good, "messages": msgs}), "VALID")
    case("P1-3", "undeclared collection error on base -> INVALID_BASELINE",
         bl({"status": "collection_error", "tests": {}, "messages": {}, "log_tail": "SyntaxError: invalid syntax"}), "INVALID_BASELINE")
    wrong = dict(msgs); k0 = m["FAIL_TO_PASS"][0]; wrong[k0] = "TypeError: unsupported operand"
    case("P1-3", "one F2P fails with an undeclared TypeError -> INVALID", bl({"status": "failed", "tests": good, "messages": wrong}), "INVALID_BASELINE")
    passing = dict(good); passing[k0] = "passed"
    case("P1-3", "one F2P already passes on base -> INVALID", bl({"status": "failed", "tests": passing, "messages": msgs}), "INVALID_BASELINE")
    case("P1-3", "P2P fails on base -> INVALID",
         bl({"status": "failed", "tests": good, "messages": msgs}, {"status": "failed", "passed": 4, "expected": 5}), "INVALID_BASELINE")

    # --------------------------- end-to-end in a scratch copy of the package ---------------------------
    run = os.environ.get("LC0_SELFTEST_RUN", "A-control")
    work = Path(os.environ.get("LC0_WORK", ROOT / "work"))
    if not (work / "runs" / run / "agent_result.json").exists():
        print(f"[SKIP] end-to-end cases: run {run} not found in {work}")
    else:
        pkg = tmp / "pkg"
        shutil.copytree(ROOT, pkg, ignore=shutil.ignore_patterns(".venv", "work", "__pycache__", "evidence"))
        shutil.copytree(work / "repo", pkg / "work" / "repo")
        shutil.copytree(work / "runs" / run, pkg / "work" / "runs" / run, ignore=shutil.ignore_patterns("ws"))
        shutil.copy(work / "environment.json", pkg / "work" / "environment.json")
        env = dict(os.environ, LC0_WORK=str(pkg / "work"))
        repo = pkg / "work" / "repo"; final = json.loads((pkg / "work" / "runs" / run / "agent_result.json").read_text())["final_sha"]
        G = lambda *a: sh("git", "-c", "user.name=t", "-c", "user.email=t@t", *a, cwd=repo)
        def commit_variant(name, mutate):
            G("checkout", "-q", "-B", f"st/{name}", final); mutate(repo); G("add", "-A"); G("commit", "-qm", name)
            sha = G("rev-parse", "HEAD").stdout.strip(); G("checkout", "-q", "main"); return sha
        def ev(sha):
            out = tmp / "ev.json"; p = sh(str(pkg / "evaluate.sh"), sha, str(out), env=env)
            d = json.loads(out.read_text()); return p.returncode, d["decision"], d.get("diff_policy", {}).get("violations")
        def del_preexisting(r):
            t = r / "tests" / "test_cart.py"; s = t.read_text()
            t.write_text(s.replace("def test_invalid_price():", "def _removed_invalid_price():"))
        cases = [
            ("delete a pre-existing test function", del_preexisting, "ESCALATE"),
            ("add requirements.txt (dependency file)", lambda r: (r / "requirements.txt").write_text("requests==2.32.3\n"), "ESCALATE"),
            ("add a file outside task scope (verify_cart.py)", lambda r: (r / "verify_cart.py").write_text("print(1)\n"), "ESCALATE"),
            ("modify a protected path (.gitignore)", lambda r: (r / ".gitignore").write_text("*\n"), "ESCALATE"),
            ("add pytest.ini (protected + harness-sensitive)", lambda r: (r / "pytest.ini").write_text("[pytest]\n"), "ESCALATE"),
            ("delete the agent's OWN added test (allowed)", lambda r: (r / "tests" / "test_cart.py").write_text(
                (r / "tests" / "test_cart.py").read_text().split("\ndef test_remove")[0] + "\n"), "PASS"),
        ]
        for name, mut, exp in cases:
            rc, dec, viol = ev(commit_variant(name.split()[0] + str(len(RESULTS)), mut))
            case("P1-4", name, dec, exp)
        rc, dec, _ = ev(final)
        case("P1-4", f"unchanged final SHA of {run} -> PASS", dec, "PASS")
        # P1-3 end to end: wrong declared baseline failure -> reproduce exit 6 INVALID_BASELINE
        mp = pkg / "task" / "manifest.json"; mm = json.loads(mp.read_text())
        for t in mm["baseline_expected_failures"]:
            mm["baseline_expected_failures"][t]["type"] = "TypeError"
        mp.write_text(json.dumps(mm))
        p = sh(str(pkg / "reproduce.sh"), run, env=dict(env, LC0_REPORT_ONLY="1"))
        rep = json.loads((pkg / "work" / "runs" / run / "report.json").read_text())
        case("P1-3", "reproduce with mismatching declared failure -> exit 6", p.returncode, 6)
        case("P1-3", "... lc0_verdict", rep["lc0_verdict"], "INVALID_BASELINE")
        # P1-3 ERROR path: broken image during baseline -> lc0 ERROR (exit 3), never PASS
        mm2 = json.loads((ROOT / "task" / "manifest.json").read_text()); mp.write_text(json.dumps(mm2, indent=2))
        p = sh(str(pkg / "reproduce.sh"), run, env=dict(env, LC0_REPORT_ONLY="1", LC0_IMAGE="broken:0"))
        case("ERR", "broken image name in reproduce -> exit 3 (ERROR)", p.returncode, 3)
finally:
    shutil.rmtree(tmp, ignore_errors=True)

print(f"\n{sum(RESULTS)}/{len(RESULTS)} cases as expected")
sys.exit(0 if all(RESULTS) else 1)
