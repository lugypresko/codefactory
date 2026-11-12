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
