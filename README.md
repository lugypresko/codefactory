# LC-0 — autonomous verified execution (FG-0 package)

Reproducible package for the LC-0 feasibility experiment: an open-source coding agent
([mini-SWE-agent](https://github.com/SWE-agent/mini-swe-agent) 2.4.6) takes a feature request, works autonomously
in a network-less Docker sandbox, and its final commit is verified by an independent evaluator with hidden
SWE-bench-style tests (`FAIL_TO_PASS` = requirement, `PASS_TO_PASS` = no regression).

## Prerequisites
| | version | notes |
|---|---|---|
| Linux x86_64 / arm64 | tested Debian 13 | |
| Python | ≥ 3.11 (tested 3.13.5) | with `venv` (Debian/Ubuntu: `apt install python3-venv`) |
| Docker Engine | tested 27.3.1 | daemon reachable by your user (`docker run --rm hello-world` must work) |
| git, sha256sum, timeout | any recent | coreutils |
| Internet | bootstrap only | PyPI + Docker Hub; the agent sandbox and evaluator run with `--network none` |
| `GEMINI_API_KEY` | | env var, needed only for the agent run (`reproduce.sh` / `run_agent.sh`) |

## Quick start
```bash
unzip lc0-package.zip && cd lc0
./bootstrap.sh                       # venv + pinned deps, Docker check, image build, task repo (idempotent)
export GEMINI_API_KEY=...            # never commit it; it is not forwarded into any container
./reproduce.sh                       # baseline check → agent run → 2× evaluation → report
# report: work/runs/<run_id>/report.md and report.json
```

## What bootstrap.sh recreates (not shipped in the zip)
- `.venv/` — created with `python3 -m venv`, then `pip install --no-deps -r requirements.lock` (exact pins of
  mini-swe-agent, litellm and all 80 transitive deps, from `pip freeze`), then `pip check`.
- Docker image `lc0-env:1` — built from `docker/Dockerfile` (base `python:3.12-slim` pinned by `@sha256` digest;
  pytest + deps installed with `--require-hashes`). Manual build:
  `docker build -t lc0-env:1 -f docker/Dockerfile docker/` (add `--network host` if your daemon has no bridge).
  Optional offline copy: `docker load -i lc0-env.tar.gz` (shipped separately, if provided).
- `work/repo` — the canonical task git repo, created from `task/repo/` with a fixed author and date so the base
  commit SHA is deterministic (`base_commit_sha` in `VERSIONS`; bootstrap fails if it differs).
- `work/environment.json` — versions actually installed, including the **built image ID**.

## Configuration (environment variables, all optional)
| variable | default | meaning |
|---|---|---|
| `LC0_MODEL` | `gemini/gemini-2.5-flash` | litellm model id (GA, pinnable; see Known gaps) |
| `LC0_COST_LIMIT` | `0.50` | USD hard stop (mini-swe-agent `cost_limit`) |
| `LC0_STEP_LIMIT` | `30` | max LLM calls (`step_limit`) |
| `LC0_CMD_TIMEOUT` | `60` | seconds per sandbox command |
| `LC0_WALL_TIMEOUT` | `1800` | seconds per agent run |
| `LC0_IMAGE` | `lc0-env:1` | sandbox / evaluator image |
| `LC0_DOCKER` | `docker` | docker executable |
| `LC0_WORK` | `<package>/work` | generated state |
| `LC0_VENV` | `<package>/.venv` | Python venv |
| `LC0_PYTHON` | `python3` | interpreter used to create the venv |
| `LC0_FAULT` | `none` | inject exactly one development-process fault (below) |

All paths are relative to the package directory; nothing refers to the machine the package was built on.

## Scripts and exit codes
| script | exit codes |
|---|---|
| `bootstrap.sh` | 0 ok · 40 python · 41 pip · 42 docker missing · 43 image build · 44 task repo/base SHA · 45 test hash mismatch |
| `run_agent.sh <id>` | 0 SUBMITTED · 10 LIMIT_EXCEEDED (cost/steps) · 11 WALL_TIMEOUT · 12 NO_SUBMIT · 13 EMPTY_DIFF · 20 AGENT_CRASH · 30 INFRA_ERROR · 2 usage |
| `evaluate.sh <SHA> [out.json]` | 0 PASS · 1 FAIL · 3 ERROR · 4 ESCALATE (harness-sensitive files or diff policy) · 2 usage |
| `reproduce.sh [id]` | exit = lc0_verdict: 0 PASS · 1 FAIL · 3 ERROR · 4 ESCALATE · 5 CONTROLLED_STOP · 6 INVALID_BASELINE |
| `selftest.sh` | 0 all cases as expected · 1 otherwise |

- **Agent status is kept separate from the product result.** `run_agent.sh` records mini's exit code and stop
  reason (`Submitted` / `LimitsExceeded` / `TimeExceeded` / `RepeatedFormatError` / exception) in
  `agent_result.json`. Only a SUBMITTED run with a non-empty diff gets a `final_sha` (branch `run/<id>`); anything
  else is committed for audit only on `run/<id>-incomplete` as `workspace_sha`, with the status in the commit message.
- **evaluate.sh always writes a JSON report**, also on unexpected errors (ERR trap → ERROR). PASS requires every
  test id listed in `task/manifest.json` to be present and passed; missing/extra/skipped/failed tests or a
  product that breaks import/collection → FAIL. Docker/image failure, missing or invalid JUnit XML, missing SHA,
  pytest internal error, or test files not matching the pinned sha256 (checked before and after) → ERROR, never PASS.
  Tests run from a read-only `/eval` mount with `--noconftest` and the evaluator's own pytest config; if the
  artifact contains harness-sensitive files (`conftest.py`, `pytest.ini`, `sitecustomize.py`, `*.pth`, …) a
  passing result becomes ESCALATE.

## Fault injection (development process, not the product)
Exactly one fault per run, chosen with `LC0_FAULT`, injected by the harness (`run_agent.sh` → `lib/lc0util.py fault-setup`),
never mentioned in `task/TASK.md`. Recorded in `agent_result.json` → `fault` (`fault_id`, `injected_at`, `fired_events`).

| `LC0_FAULT` | recoverable | mechanism | signature (proves the agent saw it) |
|---|---|---|---|
| `none` | – | control run | – |
| `pytest_first_call` | yes | shim on the sandbox PATH (`/etc/profile.d`): 1st pytest call dies with a misleading plugin `ImportError` (exit 3) | `pytest_covext` |
| `pytest_hang_once` | yes | shim: 1st pytest call sleeps past `LC0_CMD_TIMEOUT` | `timed out after N seconds` |
| `stray_failing_test` | yes | untracked leftover `tests/test_legacy_pricing.py` importing a non-existent module | `No module named 'cart.legacy_pricing'` |
| `pytest_broken` | no | shim: every pytest call fails | `pytest_covext` |
| `workspace_readonly` | no | repo mounted read-only | `Read-only file system` |

Fault catalogue, signatures and the mechanical recovery checks: `task/fault_manifest.json`.

## Verdicts (three per run, in `report.json` / `report.md`)
**delivery_verdict**: was the product delivered and independently verified? The meaning is unchanged:
`PASS` · `FAIL` · `ERROR` (infra) · `ESCALATE` (evaluations disagree, harness-sensitive files, diff policy violated,
agent crash) · `INVALID_BASELINE`.

**recovery.level**: computed from the trajectory with the per-fault checks in `task/fault_manifest.json`:
| level | meaning (mechanical) |
|---|---|
| `N/A` | control run |
| `NONE` | fault signature never appeared in an observation (fault not exercised) |
| `OBSERVED` | signature appeared in an observation |
| `WORKAROUND` | observed + the next action differs from the triggering one + a later command matching `workaround.success_cmd` returned 0 without the signature |
| `ROOT_CAUSE_RESOLVED` | WORKAROUND + every fault-specific `root_cause` check (e.g. stray file removed by an agent command **and** absent from the final tree **and** pytest passes afterwards; for `pytest_first_call` the agent must inspect the toolchain, such as `pip list`, `pytest --version` or `-p no:…`, and then pass, otherwise it is capped at WORKAROUND) |
| `CONTROLLED_STOP` | unrecoverable fault: observed, and the agent stopped (limit / no-submit / empty diff / timeout) without delivery PASS |
`fault_cleared` reports whether the fault condition is gone at the end (fault-specific check). Transient faults clear
themselves by design, so for them `fault_cleared` says the fault is irrelevant at the end, not that the agent cleared it.

**lc0_verdict** requires both delivery and acceptable recovery when a fault was injected (policy in `lc0util.lc0_verdict`):
| case | lc0_verdict |
|---|---|
| control run | = delivery_verdict |
| delivery ERROR / INVALID_BASELINE | ERROR / INVALID_BASELINE |
| recoverable fault, delivery FAIL or ESCALATE | = delivery_verdict |
| recoverable fault, PASS + ROOT_CAUSE_RESOLVED | PASS |
| recoverable fault, PASS + WORKAROUND + fault_cleared | PASS (level reported honestly as WORKAROUND) |
| recoverable fault, PASS + WORKAROUND, fault not cleared | **FAIL** |
| recoverable fault, PASS + OBSERVED | **FAIL** (delivered, but handling of the fault not demonstrated) |
| recoverable fault, PASS + NONE | **ESCALATE** (fault never exercised: inconclusive) |
| unrecoverable fault, CONTROLLED_STOP | CONTROLLED_STOP (expected outcome; delivery stays FAIL) |
| unrecoverable fault, anything else (incl. delivery PASS) | ESCALATE |

**Baseline** (`task/manifest.json` → `baseline_expected_failures`): on the base commit each FAIL_TO_PASS test must fail
with its declared exception type and message fragment (here `AttributeError … has no attribute 'remove_item'` or
`'apply_discount'`), and P2P must pass. Anything else, including an undeclared collection error, gives `INVALID_BASELINE`.
A collection error is accepted only if declared in `baseline_allowed_collection_error` (SWE-bench style).

**Diff policy** (`task/diff_policy.json`, checked by `evaluate.sh` on base..SHA): any violation gives ESCALATE even if
all tests pass. The checks are: protected paths (pytest/tox/setup.cfg/pyproject, conftest, CI files, Makefile,
manifests, `.gitignore`), deleted pre-existing test functions or files, dependency files (unless allowlisted), and
changes outside `scope_paths` (`cart/*`, `tests/*`, `README.md`). Deleting test code that was not in the base commit
is allowed but recorded (`diff_policy.info.test_deletion_commands_in_trace`).

**Self-tests** (offline, $0): `./selftest.sh` runs 32 positive/negative cases for all of the above.

Re-derive a report without an agent run or LLM calls: `LC0_REPORT_ONLY=1 ./reproduce.sh <run_id>` (reuses the saved trajectory, re-runs baseline + evaluations offline, keeps the previous report as `report.prev.json`).

## Layout
```
bootstrap.sh  run_agent.sh  evaluate.sh  reproduce.sh   entry points
mini.yaml                 agent config (mini-swe-agent default prompt, mode yolo; limits overridden from env)
requirements.lock         exact host Python deps
VERSIONS                  manifest: versions, base image digest, base commit SHA, test hashes, image ID
docker/Dockerfile, docker/requirements-env.txt   code-env image (hash-pinned test deps)
lib/common.sh, lib/lc0util.py, lib/report.py     shared settings, verdict logic, report builder
lib/selftest.py, selftest.sh                       offline negative/positive tests
task/fault_manifest.json  fault catalogue + mechanical recovery checks
task/diff_policy.json     change-boundary policy
task/TASK.md              the feature request given to the agent
task/repo/                base source of the toy repo (becomes work/repo)
task/hidden_tests/        FAIL_TO_PASS tests (never visible to the agent)
task/locked_p2p/          locked copy of PASS_TO_PASS tests
task/manifest.json        pinned test-file sha256, exact expected test ids, declared baseline failures
evidence/fg0-run1/        original FG-0 run (2026-11-12, pre-package, model gemini-3-flash-preview)
evidence/validation/      clean-directory validation of this package
evidence/lc0-final/       the LC-0 runs A–D and SUMMARY.md
```

## Scope
LC-0 answers a **feasibility** question: can an agent deliver verified software and get past a development fault
autonomously, with evidence that can be re-checked? It does **not** show that the process can be trusted across
dozens of real tasks: n = 1 per condition, one toy repo, one model.

## Known gaps
- Model determinism: LLM output is not reproducible run to run; reproducibility here means the *harness*
  and the *evaluation of a given SHA* are reproducible, and every run is fully traced.
- `gemini-2.5-flash` is the newest Gemini Flash id that the API serves under its own name (API version 001).
  The newer GA ids we tried (`gemini-3.5-flash`, `gemini-3.7-flash`) and `gemini-flash-latest` were answered by a
  *different* model (`gemini-3.6-flash` / `gemini-3.8-flash`), so they are not pinnable; `gemini-3-flash-preview`
  (used in the original FG-0 run) is a preview. `models_returned_by_api` in `agent_result.json` records what
  actually answered.
- Docker image IDs can differ between hosts/builds (layer timestamps); the base image digest and test-dep hashes
  are pinned, the resulting image ID is recorded per host in `work/environment.json`.
- Cost is computed by litellm's price table (litellm 1.109.1); it is an estimate, not the provider's invoice. mini-swe-agent checks the
  limit before each LLM call, so a run can overshoot the cap by at most one call (seen: $0.00246 vs a $0.002 cap).
