# LC-1A.0 — Preregistration (frozen before any generation run)

Question: can an agent produce good acceptance tests from a real issue, given ONLY the issue text and the pre-fix code?

Frozen: 2026-11-12 (Asia/Jerusalem). Thresholds were approved by the user (Itay) before the run. This file is
committed to the local git repo before sample verification and before any agent run; its sha256 is recorded
in sample.json and in the evidence manifest. It must not change after results are seen.

## Thresholds (approved by the user before the run) — per arm
| # | metric | threshold |
|---|---|---|
| T1 | F2P discrimination: share of the 12 clear issues where >=1 generated test FAILS on pre-fix and PASSES with the developer's fix | >= 70% (i.e. >= 9/12) |
| T2 | Mutation catch: share of all frozen wrong patches (all clear issues) that are caught | >= 80% |
| T3 | False PASS: wrong patches that the final accepted test suite passes | = 0 |

Reported without threshold: False Rejection (generated tests that fail/error on the developer's correct fix),
clarification detection on the 3 vague issues (and false clarifications on clear issues), cost.

## Metric definitions (operational)
- "Generated test" = each pytest node id collected from the new test file(s) the agent wrote. A file-level
  collection error makes every test in that file count as failing (node id `<file>::<COLLECTION_ERROR>`).
- Conditions, each in a fresh container of the instance image, `--network none`:
  PRE = base commit; GOLD = base + developer `patch` (source only; never `test_patch`);
  WRONG_k = base + frozen wrong patch k. Generated test files are copied in on top.
- "Final accepted test suite" = all generated tests as submitted (Arm 2: after the revision round). No filtering
  by gold — in production the gold fix does not exist.
- T1: issue counts iff >=1 test has outcome FAIL/ERROR on PRE and PASS on GOLD.
- T2: a wrong patch is caught iff >=1 generated test PASSES on GOLD and FAILS/ERRORS on WRONG_k
  (a catch must come from a test the correct fix satisfies; a suite that rejects everything does not "catch").
  Denominator = all frozen wrong patches of all 12 clear issues (issues with no tests / clarification / invalid run
  contribute uncaught patches).
- T3: False PASS iff the suite is non-empty and EVERY generated test PASSES on WRONG_k.
  (Rejections only explained by a gold-failing test are reported separately as "rejected-for-wrong-reason".)
- False Rejection: count/share of generated tests whose outcome on GOLD is FAIL/ERROR; and number of issues where
  the suite as a whole fails GOLD.
- Determinism: every condition is evaluated twice in independent containers; per-node-id outcomes must be identical.
  Any mismatch → that issue/arm is ERROR and counts as failing T1, as uncaught for T2 (fail-closed). It is listed.
- P2P: once per (arm, issue) the instance's original test command runs on GOLD + generated files; P2P tests that
  passed in verification must still pass (generated files must not break the existing suite). Breakage → listed
  and the suite is treated as failing GOLD for False Rejection.
- Invalid run: any change other than NEW test files (`test_*.py` / `*_test.py`, anywhere) or a root-level
  `CLARIFICATION_NEEDED.md` (any modification/deletion of a tracked file, any other new file, HEAD moved) → the
  run is INVALID, its tests are not used, and the issue counts as failing T1 and uncaught for T2.
- Clarification: the agent wrote `CLARIFICATION_NEEDED.md`. On a vague issue that is the expected outcome (correct
  iff it writes the file; if it also writes tests, report it as "both"). On a clear issue it is a false clarification
  (no credit for T1/T2; tests written alongside are still evaluated).

## Sample selection rule (frozen; see lib/candidates.py)
Source: HF `nebius/SWE-rebench-leaderboard`, parquet splits 2026_01..2026_03 (sha256 in data/SHA256SUMS).
1. sort by created_at DESC (tie: instance_id ASC); 2. drop rows with non-empty `interface`; 3. require
docker_image/patch/test_patch/FAIL_TO_PASS; 4. Docker Hub compressed size <= 3.0 GB and amd64; 5. max one instance
per repo; 6. walk in order, verify on this box, first 12 that verify form the sample. No skipping for "difficulty".
Verification (lib/verify.py), `--network none`, mem 3g:
- PRE+test_patch: every FAIL_TO_PASS test must not PASS.
- GOLD+test_patch: every FAIL_TO_PASS test must PASS; >=95% of PASS_TO_PASS must PASS (P2P failing here are dropped
  from the effective P2P set and logged); the run must finish within 15 min.
Failures are logged with the reason in data/verification_log.jsonl and replaced by the next candidate.

Vague issues (3): real issues from the repos of the sample if suitable ones can be found via the public GitHub API
(criteria: issue lacks a precise expected behaviour — e.g. labelled question/needs-info/needs-reproduction or
closed without a code fix); otherwise hand-written and labelled `synthetic`. Pre-fix code = the image of the
sample instance from the same repo. Expected outcome = CLARIFICATION_NEEDED.

## Wrong patches (frozen before generation)
3-5 per clear issue, written by the harness author (this executor agent; NOT the test-generating agent, NOT Gemini).
Kinds: off-by-one, partial fix, special-case-the-example, wrong exception type, constant return, etc.
Each must apply to PRE, must FAIL >=1 developer FAIL_TO_PASS test (with test_patch), and should pass the effective P2P.
A candidate that passes all dev F2P is discarded and replaced. All frozen with sha256 in wrong_patches/MANIFEST.json.
Caveat: the user wanted human-written wrong patches; these are author-written and reviewable in wrong_patches/.

## Arms (model gemini/gemini-2.5-flash via litellm, mini-swe-agent 2.4.6, temperature default)
Sandbox: the instance image, `--network none`, non-root uid, cap-drop ALL, no-new-privileges, mem 1.5g, 1 cpu,
pids 256. Working copy of /testbed with a FRESH single-commit git history (the image's .git is removed so future
commits cannot leak the fix). No patch / test_patch / F2P names / hints given.
- Arm 1 (single agent): writes new pytest file(s) or CLARIFICATION_NEEDED.md. Caps: $0.30, 40 steps, 15 min.
- Arm 2 (graph): A writes tests (caps $0.14 / 20 steps / 7 min); B (separate prompt, sees issue + A's tests,
  not gold) writes 3 plausible wrong fixes ($0.06 / 10 steps / 3 min); harness runs A's tests vs B's patches;
  A gets ONE revision round with surviving patches shown ($0.10 / 10 steps / 5 min). Total per issue = $0.30 /
  40 steps / 15 min. Same model for A and B (correlation is a stated limitation).
Budget: hard total cap $10 model spend across everything; stop and report if exceeded.
