"""Code Factory vertical slice: issue -> prep image (network) -> B freeze -> OpenHands patch
-> verify (B + project regression tests) -> at most 1 repair -> draft PR body or failure report.

usage:
  cf_run.py --repo DIR [--issue FILE] [--budget 2] [--smoke]
  cf_run.py --github OWNER/REPO --issue-number N [--budget 2] [--create-draft-pr]

--smoke: prep + wiring + report file; NO model calls, no PR.
--create-draft-pr: actually call `gh pr create --draft`. Default is write the body/report to a file.
Real model runs also require CF_RUN_MODELS=1 (approved separately).
Token (if a PR is ever created) is read from CF_GH_TOKEN or GH_TOKEN at runtime; never written to code or logs.
"""
import argparse, json, os, sys, subprocess, time, textwrap
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common2 import ROOT, ledger_path, runs_root, results_root
from failmin import minimize, CAP
os.chdir(ROOT)
PY = f"{ROOT}/.venv/bin/python"
IID = "cf-demo"
OUT = "results_cf"

def sh(*a, **k):
    return subprocess.run(a, capture_output=True, text=True, **k)
def log(m):
    line = f"[{time.strftime('%F %T')}] {m}"; print(line, flush=True)
    os.makedirs(OUT, exist_ok=True); open(f"{OUT}/cf_run.log", "a").write(line + "\n")
def die(m, code=1):
    log("ERROR: " + m); sys.exit(code)

def demo_env(image, issue_file, base_commit, lc_out=None, attempt=None):
    env = dict(os.environ,
               LC_IMAGE=image, LC_ISSUE_FILE=os.path.abspath(issue_file),
               LC_BASE_COMMIT=base_commit,
               LC_RESULTS=os.path.abspath(os.path.join(ROOT, OUT)),
               LC_RUNS=os.path.abspath(os.path.join(ROOT, OUT, "runs") + (f"/attempt{attempt}" if attempt else "")),
               LC_LEDGER=os.path.abspath(os.path.join(ROOT, OUT, "cost_ledger.jsonl")),
               LC_NO_GT="1", LC_CAPTURE_FAIL="1", LC_CAPTURE_FAIL_CAP=str(CAP))
    if lc_out: env["LC_OUT"] = lc_out
    return env

def prep_image(repo, tag="cf-demo:local"):
    """Build an isolated image WITH network: /testbed + venv at /opt/conda/envs/testbed (reuses oh_run/agent PATH).

    This environment's default docker-bridge DNS cannot resolve PyPI/Debian, so the
    build uses --network=host. Install still happens inside the container, not on the host.
    The bookworm `patch` package is fetched on the host and dpkg-installed in the image
    (apt inside the container hits a broken IPv4 intercept). dockrun uses git apply or patch -p1.
    """
    repo = os.path.abspath(repo)
    ctx = f"{ROOT}/work/cf/prep"; os.makedirs(ctx, exist_ok=True)
    deb = f"{ctx}/patch_2.7.6-7_amd64.deb"
    if not os.path.exists(deb) or os.path.getsize(deb) < 1000:
        log("fetching bookworm patch.deb (host curl; installed in the image)")
        u = "http://deb.debian.org/debian/pool/main/p/patch/patch_2.7.6-7_amd64.deb"
        r = sh("curl", "-fsSL", "--max-time", "30", "-o", deb, u)
        if r.returncode: die("failed to fetch patch.deb: " + (r.stderr or r.stdout))
    df = f"{ctx}/Dockerfile"
    open(df, "w").write(textwrap.dedent("""\\
        FROM python:3.12-slim-bookworm
        COPY patch_2.7.6-7_amd64.deb /tmp/patch.deb
        RUN dpkg -i /tmp/patch.deb && rm /tmp/patch.deb
        COPY repo /testbed
        WORKDIR /testbed
        RUN python -m venv /opt/conda/envs/testbed \\
            && /opt/conda/envs/testbed/bin/pip install --no-cache-dir -U pip setuptools pytest \\
            && /opt/conda/envs/testbed/bin/pip install --no-cache-dir -e /testbed
        ENV PATH=/opt/conda/envs/testbed/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
        ENV CONDA_DEFAULT_ENV=testbed
        """))
    rctx = f"{ctx}/repo"
    sh("rm", "-rf", rctx)
    r = sh("git", "clone", "--", repo, rctx)
    if r.returncode: die("git clone of local demo failed: " + (r.stderr or r.stdout))
    log(f"docker build {tag} (network=host for prep install only; later runs use --network none)")
    b = subprocess.run(["docker", "build", "--network=host", "-t", tag, "-f", df, ctx], capture_output=True, text=True)
    open(f"{ctx}/docker_build.log", "w").write((b.stdout or "") + (b.stderr or ""))
    if b.returncode: die("docker build failed; see work/cf/prep/docker_build.log")
    return tag

def workspace_at_base(image, ws):
    import agent
    os.makedirs(os.path.dirname(ws), exist_ok=True)
    return agent.prep_ws(image, ws)

def dockrun_pytest(image, patches=(), cmd="pytest --no-header -rA --tb=short --color=no -p no:cacheprovider tests"):
    import dockrun
    return dockrun.run(image, patches, cmd=cmd)

def write_report(path, kind, body):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    open(path, "w").write(body)
    log(f"wrote {kind} {path}")
    return path

def pr_body(d):
    return textwrap.dedent(f"""\
    ## Code Factory draft (needs human approval)

    Closes: {d.get("issue_ref", "(local ISSUE.md)")}

    This is a **draft**. B's generated tests are evidence, not independent proof of correctness.
    A human must review the patch before any merge. No merge or deploy is performed by this driver.

    ### Change summary
    {d.get("change_summary", "(no patch)")}

    ### Tests run and results
    - Discriminating (B) tests fail on the pre-fix base: {d.get("disc_fail_on_base")}
    - Discriminating (B) tests pass on the patch: {d.get("disc_pass_on_patch")}
    - Project regression tests pass on the patch: {d.get("regression_pass")}
    - B decision: {d.get("B_decision")} ({d.get("B_reason") or "ok"})
    - Patch bytes: {d.get("patch_bytes")}  sha256: {d.get("patch_sha")}

    ### Verification limitations
    - There are no hidden gold tests in this slice. Producer-written (B) tests are not an independent verifier.
    - OpenHands never saw B's test source; it only received the issue text and, on repair, a minimized failure excerpt (test ids + assertion/exception lines, truncated).
    - Isolation: prep used network inside a container; B and OpenHands run with `--network none`.

    ### Cost
    Demo LLM cost (this run): ${d.get("cost_usd", 0):.4f}  (cap ${d.get("budget", 2):.2f})
    """).strip() + "\n"

def failure_report(d):
    return textwrap.dedent(f"""\
    # Code Factory failure report

    Issue: {d.get("issue_ref", "local ISSUE.md")}
    Status: {d.get("status")}
    B decision: {d.get("B_decision")} {d.get("B_reason") or ""}
    Discriminating tests fail on base: {d.get("disc_fail_on_base")}
    Discriminating tests pass on patch: {d.get("disc_pass_on_patch")}
    Project regression tests pass on patch: {d.get("regression_pass")}
    Cost: ${d.get("cost_usd", 0):.4f}

    A draft PR is **not** opened unless a discriminating test fails on the base, that test
    passes on the patch, and the project's regression tests pass. B's tests are evidence,
    not independent verification.
    """).strip() + "\n\n" + (d.get("detail") or "") + "\n"

def maybe_create_pr(flag, body_path, title, repo_slug=None):
    if not flag:
        log("PR not created (--create-draft-pr not set); body/report is on disk")
        return False
    token = os.environ.get("CF_GH_TOKEN") or os.environ.get("GH_TOKEN")
    if not token: die("--create-draft-pr set but CF_GH_TOKEN/GH_TOKEN is missing")
    env = dict(os.environ, GH_TOKEN=token)
    cmd = ["gh", "pr", "create", "--draft", "--title", title, "--body-file", body_path]
    if repo_slug: cmd.extend(["--repo", repo_slug])
    log("running gh pr create --draft (title only logged, no token)")
    r = subprocess.run(cmd, capture_output=True, text=True, env=env)
    out = ((r.stdout or "") + (r.stderr or "")).replace(token, "[redacted]")
    open(f"{OUT}/gh_pr.log", "w").write(out)
    if r.returncode: die("gh pr create failed; see results_cf/gh_pr.log")
    return True

def demo_cost():
    p = os.path.join(ROOT, OUT, "cost_ledger.jsonl")
    try: return sum(json.loads(l)["cost_usd"] or 0 for l in open(p))
    except FileNotFoundError: return 0.0

def _assert_isolated(env):
    """Fail closed if a side-run env would still touch LC-1A.0 work/ ledgers or rundirs."""
    old = dict(os.environ); os.environ.clear(); os.environ.update(old); os.environ.update(env)
    try:
        lp, rr = ledger_path(), runs_root()
        forbidden_l = os.path.join(ROOT, "work", "cost_ledger.jsonl")
        forbidden_r = os.path.join(ROOT, "work", "runs")
        assert os.path.abspath(lp) != os.path.abspath(forbidden_l), lp
        assert not os.path.abspath(rr).startswith(os.path.abspath(forbidden_r) + os.sep) and os.path.abspath(rr) != os.path.abspath(forbidden_r), rr
        assert os.path.abspath(results_root()) != os.path.join(ROOT, "results")
        return lp, rr
    finally:
        os.environ.clear(); os.environ.update(old)

def smoke(repo, issue_file):
    repo, issue_file = os.path.abspath(repo), os.path.abspath(issue_file)
    orig = sh("git", "-C", repo, "rev-parse", "HEAD").stdout.strip()
    log(f"smoke: repo={repo} HEAD={orig}")
    tag = prep_image(repo)
    ws = f"{ROOT}/work/cf/smoke/ws"
    base = workspace_at_base(tag, ws)
    log(f"sanitized_base_sha={base} original_base_commit={orig}")
    r = dockrun_pytest(tag)
    failed = r["timeout"] or r["apply_fail"] or any(v in ("FAILED", "ERROR") for v in (r["outcomes"] or {}).values())
    if failed or not r["outcomes"]:
        die(f"smoke: project tests did not pass in the prepared image: exit={r['test_exit']} outcomes={r['outcomes']} log_tail={(r['log'] or '')[-800:]}")
    log(f"smoke: project tests PASSED ({len(r['outcomes'])} units) --network none")
    bug = dockrun_pytest(tag, cmd="python -c \"from cfdemo import split_even; p=split_even(10,3); print('parts',p,'sum',sum(p)); raise SystemExit(0 if sum(p)!=10 else 1)\"")
    if (bug["test_exit"] or 0) != 0:
        die("smoke: expected bug did not reproduce (split_even(10,3) already sums to 10)")
    log("smoke: bug still present on base (parts do not sum to total)")
    env = demo_env(tag, issue_file, orig, lc_out=f"{OUT}/patches/{IID}/attempt1", attempt=1)
    lp, rr = _assert_isolated(env)
    log(f"smoke: ledger would be {lp}; runs would be {rr}")
    from common2 import inst, issue_text
    old = dict(os.environ); os.environ.update(env)
    try:
        it = inst(IID); txt = issue_text(IID)
        assert it["docker_image"] == tag and it["base_commit"] == orig
        assert "split_even" in txt
    finally:
        os.environ.clear(); os.environ.update(old)
    sample = "_____________________ test_split_even_remainder _____________________\n>       assert sum(p) == 10\nE       assert 9 == 10\n"
    fb = minimize(sample, ["tests/test_issue.py::test_split_even_remainder"])
    assert "test_split_even_remainder" in fb and "E       assert 9 == 10" in fb and "assert sum(p)" not in fb
    # stage command wiring (not executed)
    stages = ["lib/stage1_testgen.py", "lib/stage1b_pre.py", "lib/stage2_patch.py", "lib/stage3_eval.py"]
    for rel in stages:
        assert os.path.exists(os.path.join(ROOT, rel)), rel
    body = failure_report({"status": "SMOKE (models not run; no PR)", "issue_ref": issue_file,
                           "B_decision": "n/a", "B_reason": "", "disc_fail_on_base": "n/a (no B run)",
                           "disc_pass_on_patch": "n/a", "regression_pass": True, "cost_usd": 0.0,
                           "detail": (f"prep image={tag}\nsanitized_base_sha={base}\noriginal_base_commit={orig}\n"
                                      f"project tests passed on base: yes\nbug demonstration (split_even(10,3) sum != 10): yes\n"
                                      f"LC_LEDGER={lp}\nLC_RUNS={rr}\nOpenHands/B: not started\n--create-draft-pr: not set")})
    path = write_report(f"{OUT}/SMOKE_REPORT.md", "smoke report", body)
    log("SMOKE OK")
    print(path)
    return 0

def _disc_pass(ev):
    p, n = ev.get("gate_units_passed"), ev.get("gate_units")
    return bool(isinstance(p, list) and n and all(c == n for c in p))

def _reg_ok(res):
    if res["timeout"] or res["apply_fail"]: return False
    if any(v in ("FAILED", "ERROR") for v in res["outcomes"].values()): return False
    return res["test_exit"] in (0, None) or (res["outcomes"] and all(v in ("PASSED", "SKIPPED", "XFAIL") for v in res["outcomes"].values()))

def run_real(repo, issue_file, budget, create_pr, issue_ref, repo_slug=None):
    repo, issue_file = os.path.abspath(repo), os.path.abspath(issue_file)
    orig = sh("git", "-C", repo, "rev-parse", "HEAD").stdout.strip()
    tag = prep_image(repo)
    log(f"real run: image={tag} base={orig} budget=${budget:.2f}")

    def env_for(attempt=None):
        lc_out = f"{OUT}/patches/{IID}/attempt{attempt}" if attempt else None
        e = demo_env(tag, issue_file, orig, lc_out=lc_out, attempt=attempt)
        _assert_isolated(e)
        return e

    def check_budget(need):
        if demo_cost() + need > budget:
            die(f"BUDGET_STOP: spent ${demo_cost():.4f} + ${need:.2f} would exceed ${budget:.2f}")

    check_budget(0.25)
    log("stage1 testgen")
    r = subprocess.run([PY, "lib/stage1_testgen.py", IID], env=env_for(), capture_output=True, text=True)
    log((r.stdout or r.stderr or "")[-1500:])
    if r.returncode == 3: die("INFRA_FAIL (stage1 preflight)", 3)
    if r.returncode: die("stage1 crashed")
    tg = f"{OUT}/testgen/{IID}"
    sh("git", "add", tg)
    sh("git", "commit", "-qm", f"CF FREEZE {IID} (generated tests + pre-fix eval, before patch generation)")
    log("stage1 frozen")
    r = subprocess.run([PY, "lib/stage1b_pre.py", IID], env=env_for(), capture_output=True, text=True)
    log((r.stdout or r.stderr or "")[-1500:])
    if r.returncode: die("stage1b crashed")
    # re-seal pre_eval into the freeze (amend would be wrong if already used; just a follow-up commit)
    sh("git", "add", tg)
    sh("git", "commit", "-qm", f"CF FREEZE {IID} pre_eval")
    pre = json.load(open(f"{tg}/pre_eval.json"))
    disc = pre.get("discriminating_units") or []
    disc_fail_on_base = bool(disc)
    log(f"discriminating units on base: {len(disc)}")

    def do_attempt(k, base_patch=None, feedback=""):
        check_budget(0.50)
        e = env_for(k)
        if base_patch: e["LC_BASE_PATCH"] = os.path.abspath(base_patch)
        if feedback: e["LC_FEEDBACK"] = feedback
        rid = f"cf-{IID}-{time.strftime('%Y%m%dT%H%M%S')}-{os.urandom(4).hex()}"
        log(f"stage2 attempt {k} run {rid}")
        r = subprocess.run([PY, "lib/stage2_patch.py", IID, rid], env=e, capture_output=True, text=True)
        log((r.stdout or r.stderr or "")[-1500:])
        if r.returncode == 4: die("INTEGRITY_FAIL (stage2)", 4)
        if r.returncode: die("stage2 crashed")
        od = e["LC_OUT"]
        assert sh("git", "add", od).returncode == 0
        assert sh("git", "commit", "-qm", f"CF SEAL {IID} attempt {k} run {rid} (artifact sealed before evaluation)").returncode == 0
        os.chmod(od, os.stat(od).st_mode | 0o200)
        log(f"stage3 attempt {k}")
        r = subprocess.run([PY, "lib/stage3_eval.py", IID, rid], env=e, capture_output=True, text=True)
        log((r.stdout or r.stderr or "")[-1500:])
        if r.returncode == 4: die("INTEGRITY_FAIL (stage3)", 4)
        if r.returncode: die("stage3 crashed")
        ev = json.load(open(f"{od}/eval.json"))
        patch = open(f"{od}/patch.diff").read()
        # never feed ev[gt_*] anywhere; skip if present
        reg = dockrun_pytest(tag, patches=[patch])
        return ev, patch, _reg_ok(reg), od

    ev, patch, reg_ok, od = do_attempt(1)
    disc_pass = _disc_pass(ev)
    ok = disc_fail_on_base and disc_pass and reg_ok
    used_repair = False
    if not ok and disc_fail_on_base:
        fmp = f"{od}/gate_fail_min.txt"
        fb = open(fmp).read() if os.path.exists(fmp) else ""
        if not fb:
            units = disc
            fb = minimize("", units)  # ids only if no capture file
        log("repair attempt 2 with minimized B failure output (no test source, no gt)")
        ev, patch, reg_ok, od = do_attempt(2, base_patch=f"{od}/patch.diff", feedback=fb)
        disc_pass = _disc_pass(ev)
        ok = disc_fail_on_base and disc_pass and reg_ok
        used_repair = True

    import hashlib
    d = {"issue_ref": issue_ref, "B_decision": ev.get("B_decision"), "B_reason": ev.get("B_reason") or "",
         "disc_fail_on_base": disc_fail_on_base, "disc_pass_on_patch": disc_pass, "regression_pass": reg_ok,
         "patch_bytes": len(patch.encode()), "patch_sha": hashlib.sha256(patch.encode()).hexdigest(),
         "cost_usd": demo_cost(), "budget": budget,
         "change_summary": f"Attempt {'2 (repair)' if used_repair else '1'}. {len(patch.splitlines())} diff lines. See {od}/patch.diff.",
         "status": "READY_FOR_DRAFT_PR" if ok else "FAILED_VERIFICATION",
         "detail": f"used_repair={used_repair}\nB_detail={ev.get('B_detail')}\ngate_units_passed={ev.get('gate_units_passed')}/{ev.get('gate_units')}\n"}
    if ok:
        path = write_report(f"{OUT}/PR_DRAFT.md", "draft PR body", pr_body(d))
        title = "fix: split_even should preserve the remainder (cf-demo)"
        maybe_create_pr(create_pr, path, title, repo_slug)
    else:
        write_report(f"{OUT}/FAILURE.md", "failure report", failure_report(d))
    log("done")
    return 0 if ok else 2

def main():
    ap = argparse.ArgumentParser(description="Code Factory vertical-slice driver")
    ap.add_argument("--repo", help="local git repo path")
    ap.add_argument("--issue", help="path to issue title+body file (default: <repo>/ISSUE.md)")
    ap.add_argument("--github", help="owner/repo (clone during prep; not used by --smoke unless set)")
    ap.add_argument("--issue-number", type=int)
    ap.add_argument("--budget", type=float, default=2.0)
    ap.add_argument("--smoke", action="store_true", help="prep + wiring + report; no models, no PR")
    ap.add_argument("--create-draft-pr", action="store_true", help="actually run gh pr create --draft (default: write file only)")
    args = ap.parse_args()
    repo_slug, issue_ref = None, None
    if args.github and args.issue_number and not args.repo:
        dest = f"{ROOT}/work/cf/src/{args.github.replace('/', '__')}"
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if args.smoke: die("refusing to clone GitHub in --smoke; pass --repo for the local demo")
        r = sh("git", "clone", "--", f"https://github.com/{args.github}.git", dest)
        if r.returncode: die("git clone failed")
        args.repo = dest
        ir = sh("gh", "issue", "view", str(args.issue_number), "-R", args.github, "--json", "title,body")
        if ir.returncode: die("gh issue view failed")
        meta = json.loads(ir.stdout)
        issue_file = f"{dest}/.cf_issue.md"
        open(issue_file, "w").write("# " + meta["title"] + "\n\n" + meta["body"] + "\n")
        args.issue = issue_file
        repo_slug, issue_ref = args.github, f"{args.github}#{args.issue_number}"
    if not args.repo: die("need --repo DIR (or --github owner/repo --issue-number N)")
    issue_file = os.path.abspath(args.issue or os.path.join(args.repo, "ISSUE.md"))
    if not os.path.exists(issue_file): die("issue file not found: " + issue_file)
    if not issue_ref: issue_ref = issue_file
    if args.smoke:
        sys.exit(smoke(args.repo, issue_file))
    if os.environ.get("CF_RUN_MODELS") != "1":
        die("real run (models, budget $%.2f) is gated: set CF_RUN_MODELS=1 after user approval, or pass --smoke" % args.budget)
    sys.exit(run_real(args.repo, issue_file, args.budget, args.create_draft_pr, issue_ref, repo_slug))

if __name__ == "__main__":
    main()
