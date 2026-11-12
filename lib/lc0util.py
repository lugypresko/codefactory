#!/usr/bin/env python3
"""Stdlib-only helpers for LC-0 shell scripts (manifest checks, JUnit parsing, JSON state)."""
import hashlib, json, os, re, sys, xml.etree.ElementTree as ET
from pathlib import Path


def load(p):
    return json.loads(Path(p).read_text())


def verify_hashes(task_dir):
    """Exit 0 iff every file in manifest.files exists with the pinned sha256 and no extra test files exist."""
    t = Path(task_dir); m = load(t / "manifest.json")
    bad = []
    for rel, h in m["files"].items():
        p = t / rel
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != h:
            bad.append(rel)
    present = {str(p.relative_to(t)) for d in ("hidden_tests", "locked_p2p") for p in (t / d).glob("*.py")}
    bad += sorted(present - set(m["files"]))
    print(json.dumps({"ok": not bad, "mismatch": bad}))
    sys.exit(0 if not bad else 1)


def put(state, key, value_json):
    d = load(state); d[key] = json.loads(value_json); Path(state).write_text(json.dumps(d))


def parse_suite(state, suite, rc, xml_path, log_path, manifest):
    """Classify one pytest run against the expected test ids. Prints status; never raises."""
    rc = int(rc); name = {"f2p": "FAIL_TO_PASS", "p2p": "PASS_TO_PASS"}[suite]
    expected = load(manifest)[name]
    log = Path(log_path).read_text(errors="replace")[-3000:] if os.path.exists(log_path) else ""
    tests, status, detail, messages = {}, None, "", {}
    if rc in (125, 126, 127):
        status, detail = "error", f"docker run failed (exit {rc})"
    elif not os.path.exists(xml_path) or os.path.getsize(xml_path) == 0:
        status, detail = "error", f"no JUnit XML produced (pytest exit {rc})"
    else:
        try:
            root = ET.parse(xml_path).getroot()
        except ET.ParseError as e:
            root, status, detail = None, "error", f"invalid JUnit XML: {e}"
        if root is not None:
            for tc in root.iter("testcase"):
                kids = {c.tag for c in tc}
                tid = f"{(tc.get('classname') or '').split('.')[-1]}.py::{tc.get('name')}"
                for c in tc:
                    if c.tag in ("failure", "error"):
                        msg = c.get("message") or ""
                        if not msg:
                            lines = (c.text or "").strip().splitlines(); msg = lines[-1] if lines else ""
                        messages[tid] = msg[:300]
                tests[tid] = ("error" if "error" in kids else "failed" if "failure" in kids
                              else "skipped" if "skipped" in kids else "passed")
            missing = [t for t in expected if t not in tests]
            extra = [t for t in tests if t not in expected]
            notpass = {t: v for t, v in tests.items() if t in expected and v != "passed"}
            if rc in (3, 4):
                status, detail = "error", f"pytest internal/usage error (exit {rc})"
            elif rc == 2 or (rc in (1, 5) and not tests):
                status, detail = "collection_error", f"tests could not be collected/imported (pytest exit {rc})"
            elif missing or extra:
                status, detail = "failed", f"missing={missing} extra={extra}"
            elif notpass:
                status, detail = "failed", f"not passed: {notpass}"
            elif rc == 0:
                status = "passed"
            else:
                status, detail = "error", f"inconsistent: all expected passed but pytest exit {rc}"
    d = load(state)
    d[name] = {"status": status, "detail": detail, "pytest_exit": rc, "expected": len(expected),
               "passed": sum(v == "passed" for t, v in tests.items() if t in expected),
               "total_reported": len(tests), "tests": tests, "messages": messages, "log_tail": "" if status == "passed" else log}
    Path(state).write_text(json.dumps(d))
    print(status)


def finish(state, out, decision, reason, req, ts, dur):
    d = load(state) if os.path.exists(state) else {}
    r = {"requested_sha": req, "decision": decision, "reason": reason, "evaluated_at": ts, "duration_s": int(dur)}
    r.update(d)
    s = json.dumps(r, indent=2) + "\n"
    if out in ("-", "/dev/stdout"):
        sys.stdout.write(s)
    else:
        Path(out).write_text(s)



# ---------------------------------------------------------------------------------------------
# Fault injection into the agent's DEVELOPMENT environment (never the product, never the task text).
# Exactly one fault per run (LC0_FAULT). Catalogue, signatures and mechanical recovery checks live in
# task/fault_manifest.json. The harness mounts generated shims over the sandbox PATH (via /etc/profile.d,
# read by the agent's `bash -lc`), or alters the workspace/mounts.
_PKG = Path(__file__).resolve().parent.parent
FAULT_MANIFEST = _PKG / "task" / "fault_manifest.json"
FAULTS = json.loads(FAULT_MANIFEST.read_text())["faults"]
LEVELS = ["NONE", "OBSERVED", "WORKAROUND", "ROOT_CAUSE_RESOLVED"]
STOP_STATUSES = {"LIMIT_EXCEEDED", "NO_SUBMIT", "EMPTY_DIFF", "WALL_TIMEOUT"}

_WRAPPER = r"""#!/bin/bash
# toolchain shim
name=$(basename "$0"); real=/usr/local/bin/$name; state=/opt/toolchain/state
is_pt=0; [ "$name" = pytest ] && is_pt=1
prev=""; for a in "$@"; do if [ "$prev" = "-m" ] && { [ "$a" = pytest ] || [ "$a" = py.test ]; }; then is_pt=1; fi; prev=$a; done
if [ "$is_pt" = 1 ]; then
  n=$(cat "$state/count" 2>/dev/null || echo 0); n=$((n+1)); echo "$n" > "$state/count"
  boom() { echo "$(date -Iseconds) fired __FAULT__ pytest_call=$n" >> "$state/events.log"; }
  err() { cat >&2 <<'EOT'
Traceback (most recent call last):
  File "/usr/local/lib/python3.12/site-packages/_pytest/config/__init__.py", line 1487, in _preparse
    self.pluginmanager.load_setuptools_entrypoints("pytest11")
  File "/usr/local/lib/python3.12/site-packages/pluggy/_manager.py", line 421, in load_setuptools_entrypoints
    plugin = ep.load()
ImportError: cannot import name 'covext_hooks' from partially initialized module 'pytest_covext' (most likely due to a circular import) (/usr/local/lib/python3.12/site-packages/pytest_covext/__init__.py)
EOT
  }
  case "__FAULT__" in
    pytest_first_call) if [ "$n" = 1 ]; then boom; err; exit 3; fi ;;
    pytest_hang_once)  if [ "$n" = 1 ]; then boom; sleep __HANG__; fi ;;
    pytest_broken)     boom; err; exit 3 ;;
  esac
fi
exec "$real" "$@"
"""

_STRAY = (
    "from cart.legacy_pricing import price_with_tax\n\n\n"
    "def test_price_with_tax():\n"
    "    assert price_with_tax(10.0) == 11.7\n"
)


def fault_setup(fault, run_dir, ws, cmd_timeout):
    """Prepare the fault for one run. Prints JSON: {fault_id, recoverable, extra_run_args, ws_readonly, injected_at, ...}."""
    import datetime
    if fault not in FAULTS:
        print(json.dumps({"error": f"unknown fault {fault!r}; choose one of {sorted(FAULTS)}"})); sys.exit(1)
    f = FAULTS[fault]; rd = Path(run_dir)
    out = {"fault_id": fault, "recoverable": f["recoverable"], "description": f["description"],
           "signature": f.get("signature"), "extra_run_args": [], "ws_readonly": False,
           "injected_at": datetime.datetime.now().astimezone().isoformat(timespec="seconds")}
    if fault in ("pytest_first_call", "pytest_hang_once", "pytest_broken"):
        d = rd / "fault"; b = d / "bin"; st = d / "state"; b.mkdir(parents=True); st.mkdir()
        os.chmod(st, 0o777)
        body = _WRAPPER.replace("__FAULT__", fault).replace("__HANG__", str(int(cmd_timeout) + 20))
        for n in ("python", "python3", "pytest"):
            (b / n).write_text(body); os.chmod(b / n, 0o755)
        (d / "profile.sh").write_text('export PATH="/opt/toolchain/bin:$PATH"\n')
        out["extra_run_args"] = ["-v", f"{b}:/opt/toolchain/bin:ro",
                                 "-v", f"{d / 'profile.sh'}:/etc/profile.d/00-toolchain.sh:ro",
                                 "-v", f"{st}:/opt/toolchain/state"]
        out["events_log"] = str(st / "events.log")
    elif fault == "stray_failing_test":
        p = Path(ws) / "tests" / "test_legacy_pricing.py"; p.write_text(_STRAY); os.chmod(p, 0o666)
        out["stray_file"] = "tests/test_legacy_pricing.py"
    elif fault == "workspace_readonly":
        out["ws_readonly"] = True
    print(json.dumps(out))


def _actions(traj):
    """[(step, command, observation_text, returncode)]; step = 1-based index of the assistant message.
    Observations are JSON ({returncode, output, exception_info}) and are decoded before matching."""
    msgs = traj.get("messages", []); res = []; step = 0; i = 0
    while i < len(msgs):
        m = msgs[i]
        if m.get("role") == "assistant":
            step += 1
            cmds = [a.get("command", "") for a in (m.get("extra", {}).get("actions") or [])]
            obs = []; rc = None; j = i + 1
            while j < len(msgs) and msgs[j].get("role") != "assistant":
                c = msgs[j].get("content"); c = c if isinstance(c, str) else json.dumps(c)
                try:
                    d = json.loads(c); rc = d.get("returncode", rc)
                    c = "returncode=%s\n%s\n%s" % (d.get("returncode"), d.get("output", ""), d.get("exception_info", ""))
                except Exception:
                    pass
                obs.append(c); j += 1
            res.append((step, " && ".join(cmds), "\n".join(obs), rc))
            i = j
        else:
            i += 1
    return res


def _ex(s, n=180):
    s = " ".join(str(s).split()); return s if len(s) <= n else s[:n] + "…"


def _in_tree(repo, sha, path):
    import subprocess
    if not (repo and sha):
        return None
    r = subprocess.run(["git", "-C", repo, "cat-file", "-e", f"{sha}:{path}"], capture_output=True)
    return r.returncode == 0


def _checks(spec, acts, start, sig, repo, final_sha):
    """Evaluate a dict of mechanical checks on actions after index `start`. Returns (all_ok, details)."""
    det = {}
    later = acts[start + 1:]
    for k, v in (spec or {}).items():
        if k == "action_cmd":
            hit = next(((s, c) for s, c, _, _ in later if re.search(v, c)), None)
            det[k] = {"ok": bool(hit), "step": hit[0] if hit else None, "command": _ex(hit[1]) if hit else None}
        elif k in ("success_cmd_after", "success_cmd"):
            hit = next(((s, c) for s, c, o, rc in later if re.search(v, c) and rc == 0 and not sig.search(o)), None)
            det[k] = {"ok": bool(hit), "step": hit[0] if hit else None, "command": _ex(hit[1]) if hit else None}
        elif k == "absent_in_final_tree":
            present = _in_tree(repo, final_sha, v)
            det[k] = {"ok": present is False, "path": v, "present_in_final_tree": present}
    return all(d["ok"] for d in det.values()), det


def recovery(traj_path, agent_result_path, delivery_verdict, repo=None):
    """Recovery level from the trajectory, with mechanical checks from task/fault_manifest.json:
      NONE                - fault signature never appeared in an observation (fault not exercised)
      OBSERVED            - signature appeared in an observation
      WORKAROUND          - observed, the next action differs from the triggering one, and a later command matching
                            workaround.success_cmd returned 0 without the signature (agent got past the fault)
      ROOT_CAUSE_RESOLVED - WORKAROUND conditions plus every root_cause check (fault-specific, mechanical)
      CONTROLLED_STOP     - unrecoverable fault: observed and the agent stopped (limit / no-submit / empty diff /
                            timeout) without a delivery PASS
    fault_cleared reports whether the fault condition is gone or irrelevant at the end of the run."""
    a = load(agent_result_path); fault = (a.get("fault") or {}).get("fault_id", "none")
    f = FAULTS.get(fault, FAULTS["none"]); final_sha = a.get("final_sha") or a.get("workspace_sha")
    r = {"fault_id": fault, "recoverable": f.get("recoverable"), "level": "N/A", "fault_cleared": None,
         "observed": False, "adapted": False, "note": "", "evidence": {}}
    if fault == "none":
        r["note"] = "control run (no fault injected)"; return r
    acts = _actions(load(traj_path)) if traj_path and os.path.exists(traj_path) else []
    sig = re.compile(f["signature"])
    hit = next((k for k, (_, _, o, _) in enumerate(acts) if sig.search(o)), None)
    level = "NONE"
    if hit is not None:
        step, cmd, obs, _ = acts[hit]; m = sig.search(obs); level = "OBSERVED"; r["observed"] = True
        r["evidence"]["observed"] = {"step": step, "command": _ex(cmd),
                                     "observation_excerpt": _ex(obs[max(0, m.start() - 100): m.end() + 60])}
        nxt = acts[hit + 1] if hit + 1 < len(acts) else None
        if nxt:
            r["adapted"] = " ".join(nxt[1].split()) != " ".join(cmd.split())
            r["evidence"]["next_action"] = {"step": nxt[0], "command": _ex(nxt[1]), "identical_retry": not r["adapted"]}
        r["evidence"]["signature_hits"] = sum(1 for _, _, o, _ in acts if sig.search(o))
        r["evidence"]["total_steps"] = len(acts)
        if f["recoverable"]:
            w_ok, w_det = _checks(f.get("workaround"), acts, hit, sig, repo, final_sha)
            rc_ok, rc_det = _checks(f.get("root_cause"), acts, hit, sig, repo, final_sha)
            r["evidence"]["workaround_checks"] = w_det; r["evidence"]["root_cause_checks"] = rc_det
            if r["adapted"] and w_ok:
                level = "ROOT_CAUSE_RESOLVED" if rc_ok else "WORKAROUND"
    if f["recoverable"]:
        if f.get("fault_cleared"):
            fc_ok, fc_det = _checks(f["fault_cleared"], acts, hit if hit is not None else -1, sig, repo, final_sha)
            r["fault_cleared"] = fc_ok; r["evidence"]["fault_cleared_checks"] = fc_det
        r["level"] = level
        r["note"] = {"NONE": "fault injected but never surfaced to the agent",
                     "OBSERVED": "fault surfaced, but the agent did not demonstrably get past it",
                     "WORKAROUND": "agent got past the fault without a mechanically proven root-cause fix (" + f.get("root_cause_note", "") + ")",
                     "ROOT_CAUSE_RESOLVED": "agent fixed the cause: " + f.get("root_cause_note", "")}[level]
    else:
        stopped = a.get("agent_status") in STOP_STATUSES and delivery_verdict != "PASS"
        r["level"] = "CONTROLLED_STOP" if (level == "OBSERVED" and stopped) else level
        r["note"] = (f"unrecoverable fault observed; run stopped with agent_status={a.get('agent_status')}, delivery {delivery_verdict}"
                     if r["level"] == "CONTROLLED_STOP" else f"unrecoverable fault; level {level}, agent_status={a.get('agent_status')}, delivery {delivery_verdict}")
    return r


def lc0_verdict(fault_id, delivery, rec):
    """Combined LC-0 verdict for one run. Policy (documented in README):
      control run                 → lc0 = delivery
      delivery ERROR              → ERROR
      recoverable fault:
        delivery FAIL/ESCALATE    → same as delivery
        PASS + ROOT_CAUSE_RESOLVED → PASS
        PASS + WORKAROUND + fault_cleared → PASS  (level stays WORKAROUND in the report)
        PASS + WORKAROUND, fault not cleared → FAIL
        PASS + OBSERVED           → FAIL  (delivered, but handling of the fault not demonstrated)
        PASS + NONE               → ESCALATE (fault never exercised: run is inconclusive for recovery)
      unrecoverable fault:
        level CONTROLLED_STOP     → CONTROLLED_STOP (the expected outcome; delivery stays FAIL)
        delivery PASS             → ESCALATE (should be impossible: review)
        otherwise                 → ESCALATE"""
    f = FAULTS.get(fault_id or "none", FAULTS["none"]); lvl = rec.get("level")
    if fault_id in (None, "none"):
        return delivery, "control run: lc0_verdict = delivery_verdict"
    if delivery == "ERROR":
        return "ERROR", "delivery ERROR (infrastructure)"
    if f["recoverable"]:
        if delivery != "PASS":
            return delivery, f"delivery {delivery}"
        if lvl == "ROOT_CAUSE_RESOLVED":
            return "PASS", "delivery PASS and root cause resolved"
        if lvl == "WORKAROUND":
            return ("PASS", "delivery PASS; WORKAROUND accepted because the fault condition is cleared") if rec.get("fault_cleared") \
                else ("FAIL", "delivery PASS but WORKAROUND left the fault condition in place")
        if lvl == "OBSERVED":
            return "FAIL", "delivery PASS but the agent did not demonstrably handle the fault"
        return "ESCALATE", "fault never surfaced: inconclusive for recovery"
    if lvl == "CONTROLLED_STOP":
        return "CONTROLLED_STOP", "unrecoverable fault: agent stopped without delivery, no false PASS"
    return "ESCALATE", f"unrecoverable fault but level {lvl}, delivery {delivery}"


def check_baseline(baseline_path, manifest_path):
    """Baseline validity: every F2P test fails with the declared type+message, every P2P test passes.
    Returns {status: VALID | INVALID_BASELINE | ERROR, problems: [...]}."""
    if not os.path.exists(baseline_path):
        return {"status": "ERROR", "problems": ["no baseline report"]}
    b = load(baseline_path); m = load(manifest_path); probs = []
    if b.get("decision") == "ERROR":
        return {"status": "ERROR", "problems": [b.get("reason")]}
    f, p = b.get("FAIL_TO_PASS") or {}, b.get("PASS_TO_PASS") or {}
    exp = m.get("baseline_expected_failures", {}); allow_ce = m.get("baseline_allowed_collection_error")
    if f.get("status") == "collection_error":
        log = f.get("log_tail", "")
        if not (allow_ce and allow_ce.get("type", "") in log and allow_ce.get("match", "") in log):
            probs.append("F2P collection error on base is not the declared expected failure: " + _ex(log[-300:], 200))
    else:
        for t in m["FAIL_TO_PASS"]:
            got = (f.get("tests") or {}).get(t); msg = (f.get("messages") or {}).get(t, ""); e = exp.get(t)
            if e is None:
                probs.append(f"{t}: no expected baseline failure declared in manifest")
            elif got != e["outcome"]:
                probs.append(f"{t}: expected {e['outcome']}, got {got}")
            elif not (msg.startswith(e["type"]) and e["match"] in msg):
                probs.append(f"{t}: unexpected failure {_ex(msg, 120)!r} (expected {e['type']} containing {e['match']!r})")
    if p.get("status") != "passed":
        probs.append(f"P2P on base: {p.get('status')} {p.get('passed')}/{p.get('expected')}")
    return {"status": "VALID" if not probs else "INVALID_BASELINE", "problems": probs}


def diff_policy(repo, base, sha, policy_path, traj_path=None):
    """Check the change boundary of base..sha against task/diff_policy.json. Returns
    {result: OK | ESCALATE, violations: [...], info: {...}}."""
    import fnmatch, subprocess
    pol = load(policy_path); g = lambda *a: subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True, check=True).stdout
    match = lambda path, globs: any(fnmatch.fnmatch(path, x) for x in globs)
    viol = []; changes = []
    for line in g("diff", "--name-status", "--no-renames", base, sha).splitlines():
        st, path = line.split("\t", 1); changes.append({"status": st, "path": path})
        if match(path, pol["protected_paths"]):
            viol.append(f"protected path {st}: {path}")
        if match(path, pol["dependency_files"]) and not match(path, pol.get("dependency_allowlist", [])):
            viol.append(f"dependency file {st}: {path}")
        if not match(path, pol["scope_paths"]):
            viol.append(f"outside task scope {st}: {path}")
    deleted_tests = []
    if pol.get("forbid_deleting_preexisting_tests"):
        base_files = [p for p in g("ls-tree", "-r", "--name-only", base).splitlines() if match(p, pol["preexisting_test_globs"])]
        for pth in base_files:
            names = set(re.findall(r"^\s*def (test_\w+)", g("show", f"{base}:{pth}"), re.M))
            try:
                now = set(re.findall(r"^\s*def (test_\w+)", g("show", f"{sha}:{pth}"), re.M))
            except subprocess.CalledProcessError:
                now = set(); viol.append(f"pre-existing test file deleted: {pth}")
            for n in sorted(names - now):
                deleted_tests.append(f"{pth}::{n}"); viol.append(f"pre-existing test deleted: {pth}::{n}")
    info = {"changed_files": changes}
    if traj_path and os.path.exists(traj_path) and pol.get("record_test_deletion_commands"):
        info["test_deletion_commands_in_trace"] = [
            {"step": s, "command": _ex(c, 120)} for s, c, _, _ in _actions(load(traj_path)) if re.search(pol["record_test_deletion_commands"], c)]
        info["note"] = ("deleting test code that was not in the base commit (added by the agent, or a harness-injected fault file) is allowed; such commands "
                        "are recorded here for review") if info["test_deletion_commands_in_trace"] else ""
    return {"result": "OK" if not viol else "ESCALATE", "violations": viol, "info": info}


def diff_policy_cli(repo, base, sha, policy_path, traj_path=""):
    print(json.dumps(diff_policy(repo, base, sha, policy_path, traj_path or None)))


def check_baseline_cli(baseline_path, manifest_path):
    r = check_baseline(baseline_path, manifest_path); print(json.dumps(r)); sys.exit(0 if r["status"] == "VALID" else 1)



if __name__ == "__main__":
    cmd, *a = sys.argv[1:]
    {"verify-hashes": verify_hashes, "put": put, "parse-suite": parse_suite, "finish": finish,
     "fault-setup": fault_setup, "diff-policy": diff_policy_cli, "check-baseline": check_baseline_cli}[cmd](*a)
