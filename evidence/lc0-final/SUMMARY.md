# LC-0 final runs — summary (2026-11-12, Asia/Jerusalem)

Package lc0-fg0-1.3 (verdicts re-derived after review; see "v1.3 re-derivation") · agent mini-swe-agent 2.4.6 (DefaultAgent, no human channel) · model `gemini/gemini-2.5-flash`
(GA; the API reported `gemini-2.5-flash` on every call) · cost limit $0.50 · step limit 30 · sandbox `--network none`,
non-root, no capabilities · base commit `9f6b7382` · hidden tests sha256 `9670a8d8…`, P2P `e1014e6e…` (checked
before and after every evaluation) · each run: `LC0_FAULT=<id> ./reproduce.sh <run>`.

All four runs are reported; there is no aggregate PASS.

| run | fault (1 per run) | agent_status | steps | cost | time | F2P | P2P | eval ×2 | final SHA | diff policy | delivery | recovery level | **LC-0 verdict** |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | none (control) | SUBMITTED | 20 | $0.0209 | 77 s | 9/9 | 5/5 | PASS/PASS, identical | `9e2500f9` | OK | PASS | N/A | **PASS** |
| B | `pytest_first_call` | SUBMITTED | 29 | $0.0319 | 63 s | 9/9 | 5/5 | PASS/PASS, identical | `dc336137` | OK (own-test deletion recorded, step 25) | PASS | **WORKAROUND** (fault cleared: transient by design) | **PASS** |
| C | `stray_failing_test` | SUBMITTED | 19 | $0.0181 | 48 s | 9/9 | 5/5 | PASS/PASS, identical | `f4419e89` | OK (stray-file removal recorded, step 14) | PASS | **ROOT_CAUSE_RESOLVED** | **PASS** |
| D | `workspace_readonly` (unrecoverable) | EMPTY_DIFF | 27 | $0.0459 | 86 s | – (not evaluated) | – | – | none | n/a (no artifact) | FAIL | **CONTROLLED_STOP** | **CONTROLLED_STOP** |

Steps = LLM calls; time = whole reproduce.sh (baseline + agent + 2 evaluations). Baseline VALID in every run: each F2P test fails
with its declared `AttributeError` (missing `remove_item` / `apply_discount`) and P2P is 5/5 on the base commit. Total LLM cost of the 4 runs: **$0.117**.

## v1.3 re-derivation (after code review; no new agent runs, $0)
`LC0_REPORT_ONLY=1 ./reproduce.sh <run>` re-ran the offline steps (baseline with declared failures, evaluations with the
diff policy) on the saved trajectories and SHAs. Old reports are kept as `report.prev.json`.
| run | old decision / recovery | new delivery / recovery level / LC-0 |
|---|---|---|
| A | PASS / N/A | PASS / N/A / PASS |
| B | PASS / RECOVERED | PASS / **WORKAROUND** / PASS (WORKAROUND accepted only because the fault condition is cleared) |
| C | PASS / RECOVERED | PASS / **ROOT_CAUSE_RESOLVED** / PASS |
| D | FAIL / CONTROLLED_STOP | FAIL / CONTROLLED_STOP / **CONTROLLED_STOP** |
The final labels did not flip, but B is now reported honestly as a workaround rather than a recovery. If B's fault had
not been transient, the same behaviour would give lc0_verdict FAIL (covered in `selftest.sh`).

## Recovery evidence (from the trajectories, `report.json` → `recovery`)
- **B, `pytest_first_call`**: fault fired once (`fired_events`: pytest call 1).
  *Observed* step 10: `python -m pytest -q` → `ImportError: cannot import name 'covext_hooks' from partially initialized module 'pytest_covext'`.
  *Adapted* step 11: `cat /repo/cart/cart.py` (a different command, not a retry). The agent then changed its import
  (step 12), reverted it (step 14), switched to its own verification script `verify_cart.py` (steps 15–20), deleted it
  (step 21), and returned to pytest at step 22, which now worked. *Completed*: SUBMITTED, eval PASS ×2.
  Mechanical checks: workaround ✓ (step 20, own script ran green; step 26 pytest green). Root cause ✗: no
  toolchain inspection (`pip list`, `pytest --version`, `-p no:…`) anywhere in the trace, so the level is capped at
  **WORKAROUND**. The agent treated a toolchain fault as a problem in its own code.
- **C, `stray_failing_test`**: *Observed* step 12: `ModuleNotFoundError: No module named 'cart.legacy_pricing'`.
  At step 8 the same error was hidden behind an IndentationError the agent had introduced itself, so the agent
  first rewrote `cart.py` (steps 9–11). *Adapted* step 13: `ls -la /repo/cart`. *Resolution* step 14:
  `rm /repo/tests/test_legacy_pricing.py`. Step 15: pytest 9 passed. The stray file is not in the artifact.
  *Completed*: SUBMITTED, eval PASS ×2. Root-cause checks ✓: the removal was the agent's own command (step 14), the
  file is absent from final tree `f4419e89`, and pytest passed afterwards (step 15). Level **ROOT_CAUSE_RESOLVED**.
- **D, `workspace_readonly`**: *Observed* step 4 (`Read-only file system`, 5 hits in total). The agent probed
  (`ls -ld`, `chmod +w`, `touch`), wrote its solution to `/tmp`, tested it there (11 passed), and then **submitted
  anyway** (step 24) with nothing changed in the repo. The harness classified the run EMPTY_DIFF: no `final_sha`, no
  evaluation, decision FAIL. No false PASS, and the stop was controlled. The agent itself did not report that it
  was blocked.

## Success criteria (PLAN.md)
| criterion | verdict | evidence |
|---|---|---|
| **Verified delivery**: at least one run fulfils the requirement with no regression in the defined tests | **MET** | A, B and C: F2P 9/9 + P2P 5/5 on the exact final SHA, evaluated twice with identical results, diff policy OK; the baseline fails exactly as declared |
| **Autonomous recovery**: at least one run with an injected fault, documented detection, a recovery action and completion | **MET (C only at ROOT_CAUSE level)** | C: ROOT_CAUSE_RESOLVED (signature at step 12, agent removes the stray file at step 14, file absent from the final tree, pytest green at step 15, delivery PASS). B: WORKAROUND only (the fault was observed and bypassed, never diagnosed) |
| **Proof integrity**: independent verification, tests never exposed to the agent, identified artifact, report that can be re-checked | **MET** | Tests live only in `task/` and are hash-pinned, checked before and after; the evaluator takes a SHA and runs it in a fresh read-only container with `--noconftest`; diff policy and declared baseline failures are enforced; `selftest.sh` gives 32/32 expected results; every report re-derives offline |

Control vs fault: B used 9 more steps and +$0.011 than control A; C needed about the same as A (19 vs 20 steps).

## Honest limitations
- **n = 1 per condition.** This shows feasibility, not reliability. LLM output is not deterministic, and a rerun can differ.
- **Recovery levels are mechanical proxies.** ROOT_CAUSE_RESOLVED is only claimed when a fault-specific check in
  `task/fault_manifest.json` proves it. Gemini 2.5 Flash returned no reasoning text, so attribution (why the agent
  acted) can't be read; anything that can't be proven mechanically is capped at WORKAROUND.
- **Transient faults clear themselves.** For `pytest_first_call`, `fault_cleared=true` means the fault no longer
  matters at the end, not that the agent removed it. lc0 PASS for B rests on that policy.
- **Signature refinement:** the `stray_failing_test` signature was tightened after run C from `legacy_pricing`, which
  also matched a plain `ls` listing, to the actual error `No module named 'cart.legacy_pricing'`. Observation text
  is now JSON-decoded before matching. The report was regenerated from the same trajectory (`LC0_REPORT_ONLY=1`),
  with no rerun and no LLM calls. The v1.2 verdict was RECOVERED both before and after; the observed step moved from 5 to 12 (in v1.3 the level is ROOT_CAUSE_RESOLVED).
- **D shows the agent's own blind spot.** It "submitted" work it could not write. Only the harness check (empty diff)
  stopped a false completion claim.
- **The agent edits its own tests:** in B it deleted failing tests it had added itself (`sed '118,131d'`, step 25).
  The diff policy allows this because those tests were not in the base commit, but records it. Deleting a
  pre-existing test, changing dependencies, touching protected paths or changing anything outside scope gives ESCALATE.
- **Two implemented faults were not run end to end:** `pytest_hang_once` and `pytest_broken` were only smoke-tested.
  The hang hit the timeout once and then worked; broken fails on every call.
- **Toy scope:** one small Python repo and one feature. Fault shims live on the sandbox PATH (`/opt/toolchain`), so
  a curious agent could find them. `fired_events` timestamps are written inside the container in UTC.
- **Environment:** Docker on the build box runs without iptables or bridge networking, so the sandbox is network-less,
  which is the intended setup. The image ID varies per build; the base digest and dependency hashes are pinned.
- **Scope of the answer:** LC-0 answers *feasibility* (yes, at the level of evidence in this package). It does not
  answer whether the process can be trusted across dozens of real tasks; that needs many tasks, real repositories,
  several runs per condition, and policies tuned per repository.
