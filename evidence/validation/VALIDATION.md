# Clean-directory validation (2026-11-12, Asia/Jerusalem)

Package copied to an empty directory (/tmp/lc0-clean) without .venv, work/ or the Docker image
(image and base image deleted first). No path refers to /workspace.

| step | result |
|---|---|
| `./bootstrap.sh` (from scratch) | exit 0 in 28 s: venv + 82 pinned packages, base image pulled by digest, image built, base SHA 9f6b738… = expected |
| `./bootstrap.sh` (re-run) | exit 0, "venv up to date", image cached: idempotent |
| `./reproduce.sh val1` | **PASS** (exit 0) in 38 s: baseline VALID (F2P 0/9 on base, P2P 5/5); agent SUBMITTED, gemini-2.5-flash, 18 steps, $0.0186; eval ×2 PASS 9/9 + 5/5, identical |
| `LC0_STEP_LIMIT=2 ./reproduce.sh` | FAIL (exit 1), agent LIMIT_EXCEEDED steps, no final_sha, not evaluated |
| `LC0_COST_LIMIT=0.002 ./reproduce.sh` | FAIL (exit 1), agent LIMIT_EXCEEDED cost; partial work kept as workspace_sha on run/…-incomplete |

## Negative evaluator tests (negative-evaluator/*.json)
| # | case | decision | exit |
|---|---|---|---|
| 1 | evaluate.sh on base SHA | FAIL (F2P 0/9 failed, P2P passed) | 1 |
| 2 | broken image name | ERROR image_missing | 3 |
| 3 | docker run fails (125) | ERROR docker run failed | 3 |
| 4 | no JUnit XML | ERROR | 3 |
| 5 | invalid JUnit XML | ERROR invalid JUnit XML | 3 |
| 6 | product breaks import | FAIL collection_error | 1 |
| 7 | artifact adds conftest.py | ESCALATE | 4 |
| 8 | feature half-implemented | FAIL | 1 |
| 9 | unknown SHA | ERROR sha_not_found | 3 |
| 10 | hidden test file tampered | ERROR test_hash_mismatch_before | 3 |
| 11 | expected test id missing | FAIL missing=[…] | 1 |
| 12 | final SHA re-evaluated | PASS | 0 |
| 13 | run_agent.sh with docker missing | INFRA_ERROR | 30 |
| 14 | unexpected script error (trap) | ERROR unexpected_script_error, JSON still written | 3 |
