# LC-0 – Agreed simplified plan (summary of chat)

## Goal
Prove an agent can (a) autonomously deliver correct software and (b) recover by itself from a failure during development.

## Components (all open source)
- Agent + harness: mini-SWE-agent (Docker env, cost/step limits, trajectory)
- Isolation: Docker container; code env network cut, controlled LLM API access, deps pre-baked
- Verification: SWE-bench style – FAIL_TO_PASS (requirement) + PASS_TO_PASS (non-regression), hidden from agent, run in fresh container on final SHA
- Fault injection: small custom script, ONE injected fault per run
- Report: evaluate.sh <SHA> -> JSON

## Capability mapping
1 Functional Correctness -> FAIL_TO_PASS (each must fail on base commit)
2 Non-Regression -> PASS_TO_PASS (locked copy)
3 Failure Recovery -> injected dev-process fault + trace evidence (saw failure, attributed cause, changed action)
4 Autonomous Execution -> no human input channel; single uninterrupted trace
5 Constraint Compliance -> enforced externally (network, no push token, timeout, cost limit); breach = FAIL
6 Independent Verification -> tests never inside agent container; hash test suite before/after
7 Artifact Integrity -> evaluator takes SHA as input and records it
8 Reproducibility & Auditability -> evaluator run twice on same SHA; full trajectory saved

## Work plan
1. FG-0 (1 day): run agent in sandbox with budget, save trace + SHA, external evaluator
2. Task + evaluator: pick repo, write requirement, F2P/P2P tests
3. Fault injection: one fault per run, recovery criteria defined up front
4. 3 runs (one clean control run), report all 3 rows – no single aggregate PASS

## Success criteria
- Verified delivery: >=1 run completes requirement with no regression
- Autonomous recovery: >=1 run with injected fault, documented detection, recovery action, task completed
- Proof integrity: independent verification, hidden tests, identified artifact, re-checkable report
Three runs demonstrate feasibility, not general reliability.

## v1.5 (2026-11-12): entry condition for LC-1A (closes the C2 gap)
- Diff policy: `allowed_new_files` and `new_test_globs` per task. NEW_FILE_OUT_OF_SCOPE and INJECTED_ARTIFACT_IN_DIFF
  (by path or sha256, for every declared fault) give ESCALATE.
- Recovery contracts in `task/fault_manifest.json`: expected outcome, checks, and forbidden actions. Scoring fails closed
  (ERROR) on a missing or invalid contract or an unknown fault id.
- Process: the policy text (`tests/adversarial/SPEC_v1.5.md`) and the attacks came first, then the BEFORE run on v1.4.1,
  then the implementation, then the AFTER run. No existing rule was loosened. No agent runs and no LLM cost.

## LC-1A: Autonomous Verified PR, Definition of Done notes (agreed direction, not yet implemented)
- **Per-task counts, not hard-coded.** "All F2P and P2P tests declared in the task's `manifest.json` pass", not
  "9/9 + 5/5". Otherwise the DoD does not carry over to LC-1B.
- **Recovery is scored per scenario over 3 runs.** For each recovery scenario (Recovery A transient/environment,
  Recovery B persistent): at least 2 of 3 runs must reach true removal (`FAULT_REMOVED_AND_VERIFIED`, or the contract's
  `expected_outcome`), with **0 false PASS**. All runs are reported. This filters out luck. It is not a statistical
  reliability claim, which is LC-1B's job (about 50 git-mined tasks).
- **Independent verification:** the hidden tests move to a separate **private repo** that CI fetches only in the
  evaluator job. Today they sit next to the code, in a repo the agent could in theory read.
- **Who opens the PR:** a deterministic **broker with its own GitHub App identity** pushes the agent's diff to an
  isolated branch and opens the PR. The agent has no token (Zero Trust for Coding Agents). After that the ruleset is
  tightened: 1 approval, code-owner review, dismiss stale reviews, and required status checks.
- **"Signed" vs "hash-sealed":** today `evidence_manifest.json` is **hash-sealed** (sha256 integrity, no identity). A
  real signature means `actions/attest-build-provenance` (Sigstore-backed, with the workflow's OIDC identity) over the
  evidence bundle in CI. The DoD must use whichever word matches what is implemented.
- **Numeric operational limits:** **$0.50 per run, 15 minutes wall-clock, 40 steps**, plus retry counts, all enforced
  by the harness and visible in logs/metrics. Current defaults are $0.50, 30 min (`LC0_WALL_TIMEOUT=1800`) and 30 steps,
  so the wall limit must drop to 900 s and the step limit must be set to 40 for LC-1A.
- **Adversarial gate scenarios are deterministic prepared diffs**, not agent runs: blocked unauthorized business
  change, blocked edit of an existing test, SHA or evidence tampering, and a controlled stop. They are fed through the
  same evaluator pipeline (as `tests/adversarial/` already does), so they are cheap, repeatable and independent of the
  model's luck.
- Out of scope for LC-1A: multi-agent, Merge Queue, production deploys, UI, multi-tenant SaaS.
