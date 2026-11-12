# LC-1A.0 v2: Release-decision test. Does the gate (B) separate correct from wrong patches better than Patch Submission (A)?

Generated 2026-11-12 22:07:00 IST. Protocol: PREREGISTRATION_v2.md, freezes fb24a8f, 2617a58, Amendment 2 9fc8e38, Amendment 3 fe54862 (code used for the scored run); GO checklist 479b4d3.
Dataset nebius/SWE-rebench-leaderboard @ 34d5a58864acf91613740a09ec5d205228dcfa39. Patch producer: OpenHands SDK 1.62.0 agent-server in a sandboxed Docker container (--network none), gemini-2.5-flash. Test-writer: mini-SWE-agent, same model.

EARLY STOP by user decision (22:03 IST): issues #1-#20 run in frozen order, #21-#30 not run; per protocol the completed subset is reported.

Scored: 16/30.

## Verdict

**ITERATE** (LOW CONFIDENCE: {len(IF)} INFRA_FAIL among {len(allrun)} issues run, more than 3)

INFRA_FAIL issues (excluded from metric denominators under the frozen rule; never fixed mid-run): 4 ['cs-si__eodag-2176', 'agronholm__anyio-1134', 'databricks__dbt-databricks-1428', 'pennylaneai__pennylane-9298'].

| Criterion (preregistered) | Value | Holds |
|---|---|---|
| 1. FPR_B <= 0.5 x FPR_A | FPR_A 13/13 = 1.00 [0.77, 1.00]; FPR_B 0/13 = 0.00 [0.00, 0.23] | True |
| 2. Retention_B >= 0.90 | 1/1 = 1.00 [0.21, 1.00] (based on n = 1 correct patches; INCONCLUSIVE at this n) | True (inconclusive, tiny n) |
| 3. Gate cost overhead <= 30% | test-writer $0.7934 / patch agent $0.7127 = 111.3% | False |
| 4. Zero exposure of B to gold/hidden tests | structural: single sanitized pre-fix mount for all 20 test-writer runs = True; raw grep hits in 8 issues, all traced to allowed inputs or agent-authored text (see Exposure check); confirmed exposures: 0 | True |

Non-empty source patches: 14; **wrong patches: 13**; correct: 1; empty/failed (not patches): 2.

## Metrics (raw counts, Wilson 95% intervals)

| Metric | A: Patch Submission Baseline | B: our gate | B secondary (excl. INSUFFICIENT_EVIDENCE) |
|---|---|---|---|
| False PASS Rate (wrong approved / wrong) | 13/13 = 1.00 [0.77, 1.00] | 0/13 = 0.00 [0.00, 0.23] | 0/8 = 0.00 [0.00, 0.32] |
| Verified Precision (correct approved / approved) | 1/14 = 0.07 [0.01, 0.31] | 1/1 = 1.00 [0.21, 1.00] | 1/1 = 1.00 [0.21, 1.00] |
| Correct PR Retention (correct approved / correct) | 1/1 = 1.00 [0.21, 1.00] | 1/1 = 1.00 [0.21, 1.00] | 1/1 = 1.00 [0.21, 1.00] |
| Cost per Correct Approved PR | $0.7127 (agent $0.7127) | $1.5061 (agent + gate $1.5061) | n/a |

B outcome breakdown over all 16 scored issues: {'REJECT_INSUFFICIENT_EVIDENCE': 5, 'REJECT_INVALID_PATCH': 8, 'NO_PATCH': 2, 'APPROVE': 1}. INSUFFICIENT_EVIDENCE frequency: 5/16 = 0.31 [0.14, 0.56].

**Evidence Coverage** (stage 1 produced >= 1 discriminating test, i.e. failing deterministically on pre-fix): 11/16 = 0.69 [0.44, 0.86] of scored issues (15/20 incl. INFRA_FAIL issues, whose stage 1 ran normally).
**B rejections by reason** (scored issues): test-caught (REJECT_INVALID_PATCH) 8; insufficient evidence 5; no patch 2; approvals 1. Among wrong patches: B test-caught 8, insufficient evidence 5, approved 0. Among correct patches: approved 1, test-rejected 0, insufficient evidence 0.

Sensitivity (INFRA_FAIL counted as agent failures): INFRA_FAIL runs produced no patch, so the patch-level metrics above (FPR, precision, retention) have the same values. Issue-level yield of correct approved patches: A 1/16 excluding vs 1/20 including INFRA_FAIL; B 1/16 vs 1/20. Rejections incl. INFRA_FAIL: A 6/20, B 19/20.
INFRA_FAIL root cause (diagnosed from server.log; NOT fixed, frozen code): the OpenHands agent-server crashed at startup. Without network, litellm's background model-cost-map fetch fails and the retry path hits a circular import ('LoggerContext' in litellm.rust_bridge.catalog), so the server never became healthy. oh_run.py then waited ~10.5 min for health before giving up. Proposed fix for a future protocol (not applied): set LITELLM_LOCAL_MODEL_COST_MAP=True in the agent-server container + fail fast on health.
INFRA_FAIL cs-si__eodag-2176 run pa-cs-si__eodag-2176-20261112T191634-d775cd77: 'ERROR/LIMIT: RuntimeError(\'agent server not healthy:\\nException in thread litellm-model-cost-map-retry:\\nTraceback (most recent call last):\\n  File "__main__.py'. Proxy-metered cost $0.0000 (no llm_ledger.json means no LLM call reached the proxy); ledger entry $0.0000; test-writer $0.0314.
INFRA_FAIL agronholm__anyio-1134 run pa-agronholm__anyio-1134-20261112T202746-30e3317d: 'ERROR/LIMIT: RuntimeError(\'agent server not healthy:\\n  File "pyimod02_importers.py", line 457, in exec_module\\n  File "openhands/agent_server/logging_config.py'. Proxy-metered cost $0.0000 (no llm_ledger.json means no LLM call reached the proxy); ledger entry $0.0000; test-writer $0.0381.
INFRA_FAIL databricks__dbt-databricks-1428 run pa-databricks__dbt-databricks-1428-20261112T211516-9388241f: 'ERROR/LIMIT: RuntimeError(\'agent server not healthy:\\nException in thread litellm-model-cost-map-retry:\\nTraceback (most recent call last):\\n  File "__main__.py'. Proxy-metered cost $0.0000 (no llm_ledger.json means no LLM call reached the proxy); ledger entry $0.0000; test-writer $0.0730.
INFRA_FAIL pennylaneai__pennylane-9298 run pa-pennylaneai__pennylane-9298-20261112T214933-d072776b: 'ERROR/LIMIT: RuntimeError(\'agent server not healthy:\\nException in thread litellm-model-cost-map-retry:\\nTraceback (most recent call last):\\n  File "__main__.py'. Proxy-metered cost $0.0000 (no llm_ledger.json means no LLM call reached the proxy); ledger entry $0.0000; test-writer $0.0638.
Retention losses (correct patches B rejected): [].

## Per-issue table (frozen order)

| # | Instance | Patch produced (source bytes) | Hidden-test truth | A verdict | B verdict | Test-writer (validity, disc. units) | Cost test-writer / patch agent ($) | Cost flag |
|---|---|---|---|---|---|---|---|---|
| 1 | schemathesis__schemathesis-4087 | yes (546) | WRONG (F2P fail 2/2, P2P fail 0/104) | APPROVE | REJECT (REJECT_INSUFFICIENT_EVIDENCE) | INVALID, 0 | 0.0938 / 0.0228 |  |
| 2 | cs-si__eodag-2176 | INFRA_FAIL | n/a | not scored (pipeline logged REJECT ERROR/LIMIT:) | not scored | VALID, 4 | 0.0314 / 0.0000 | proxy $0.0000 |
| 3 | nesquena__hermes-webui-2056 | yes (785) | WRONG (F2P fail 3/3, P2P fail 0/54) | APPROVE | REJECT (REJECT_INVALID_PATCH) | VALID, 4 | 0.0206 / 0.0206 |  |
| 4 | youssofal__mtplx-21 | yes (3326) | WRONG (F2P fail 2/4, P2P fail 1/5) | APPROVE | REJECT (REJECT_INSUFFICIENT_EVIDENCE) | VALID, 0 | 0.0261 / 0.0234 |  |
| 5 | raullenchai__rapid-mlx-289 | no (empty) | n/a (no patch) | REJECT (WALL_TIMEOUT) [uncertain msg] | REJECT (NO_PATCH) | VALID, 1 | 0.0168 / 0.2920 | GAP 3.6% |
| 6 | python-wheel-build__fromager-1124 | yes (4446) | WRONG (F2P fail 6/7, P2P fail 7/28) | APPROVE | REJECT (REJECT_INVALID_PATCH) | VALID, 1 | 0.0733 / 0.0347 |  |
| 7 | itsdnns__docsight-437 | yes (2102) | WRONG (F2P fail 5/5, P2P fail 0/40) | APPROVE | REJECT (REJECT_INVALID_PATCH) | VALID, 4 | 0.0302 / 0.0188 |  |
| 8 | agronholm__anyio-1134 | INFRA_FAIL | n/a | not scored (pipeline logged REJECT ERROR/LIMIT:) | not scored | VALID, 1 | 0.0381 / 0.0000 | proxy $0.0000 |
| 9 | tox-dev__tox-3931 | yes (652) | WRONG (F2P fail 1/1, P2P fail 1/2) | APPROVE | REJECT (REJECT_INSUFFICIENT_EVIDENCE) | VALID, clarification, 0 | 0.0115 / 0.0160 |  |
| 10 | copier-org__copier-2646 | yes (881) | WRONG (F2P fail 1/1, P2P fail 0/6) | APPROVE | REJECT (REJECT_INVALID_PATCH) | VALID, 1 | 0.0879 / 0.0328 |  |
| 11 | hkuds__openharness-217 | yes (1360) | CORRECT | APPROVE | APPROVE | VALID, 3 | 0.0386 / 0.0117 |  |
| 12 | astronomy-commons__lsdb-1349 | yes (4504) | WRONG (F2P fail 1/1, P2P fail 20/21) | APPROVE | REJECT (REJECT_INVALID_PATCH) | VALID, 2 | 0.0159 / 0.0488 |  |
| 13 | alibaba__opensandbox-816 | yes (7013) | WRONG (F2P fail 0/1, P2P fail 2/108) | APPROVE | REJECT (REJECT_INVALID_PATCH) | VALID, 1 | 0.0745 / 0.0520 |  |
| 14 | apache__iceberg-python-3295 | yes (382) | WRONG (F2P fail 7/7, P2P fail 0/164) | APPROVE | REJECT (REJECT_INVALID_PATCH) | VALID, 3 | 0.0132 / 0.0452 |  |
| 15 | databricks__dbt-databricks-1428 | INFRA_FAIL | n/a | not scored (pipeline logged REJECT ERROR/LIMIT:) | not scored | VALID, 1 | 0.0730 / 0.0000 | proxy $0.0000 |
| 16 | zarr-developers__virtualizarr-979 | no (empty) | n/a (no patch) | REJECT (EMPTY_DIFF) | REJECT (NO_PATCH) | VALID, 1 | 0.0581 / 0.0137 |  |
| 17 | ultraplot__ultraplot-696 | yes (737) | WRONG (F2P fail 2/2, P2P fail 0/49) | APPROVE | REJECT (REJECT_INSUFFICIENT_EVIDENCE) | VALID, clarification, 0 | 0.0863 / 0.0554 |  |
| 18 | pyinfra-dev__pyinfra-1665 | yes (860) | WRONG (F2P fail 1/1, P2P fail 0/33) | APPROVE | REJECT (REJECT_INSUFFICIENT_EVIDENCE) | VALID, clarification, 0 | 0.1378 / 0.0164 |  |
| 19 | pennylaneai__pennylane-9298 | INFRA_FAIL | n/a | not scored (pipeline logged REJECT ERROR/LIMIT:) | not scored | VALID, 1 | 0.0638 / 0.0000 | proxy $0.0000 |
| 20 | microsoft__qcodes-8039 | yes (866) | WRONG (F2P fail 2/2, P2P fail 1/6) | APPROVE | REJECT (REJECT_INVALID_PATCH) | VALID, 1 | 0.0089 / 0.0083 |  |
| 21 | pypsa__pypsa-1653 | NOT RUN (user stop) | | | | | | |
| 22 | agentscope-ai__qwenpaw-3278 | NOT RUN (user stop) | | | | | | |
| 23 | unit8co__darts-3065 | NOT RUN (user stop) | | | | | | |
| 24 | meltano__meltano-9950 | NOT RUN (user stop) | | | | | | |
| 25 | tobymao__sqlglot-7479 | NOT RUN (user stop) | | | | | | |
| 26 | huggingface__huggingface_hub-4056 | NOT RUN (user stop) | | | | | | |
| 27 | koxudaxi__datamodel-code-generator-3070 | NOT RUN (user stop) | | | | | | |
| 28 | ucfopen__canvasapi-716 | NOT RUN (user stop) | | | | | | |
| 29 | zauberzeug__nicegui-5914 | NOT RUN (user stop) | | | | | | |
| 30 | oemof__tespy-921 | NOT RUN (user stop) | | | | | | |

## Cost
Scored issues: test-writer $0.7934, patch agent $0.7127, total $1.5061. INFRA_FAIL issues: $0.2063 (counted in the ledger, excluded from the cost metrics). Ledger total incl. feasibility, smokes and voided runs: $2.5693 of the $25 cap.
Cost method: recorded cost = max(proxy metered from Gemini usageMetadata at pinned prices, OpenHands/litellm accumulated_cost); gaps > 1% flagged above. Test-writer cost = mini-SWE-agent/litellm instance_cost (not proxied).

## Exposure check (criterion 4)
For each issue, the test-writer's task and trajectory were grepped for added lines (>25 chars) of the gold patch and the test_patch, for FAIL_TO_PASS test function names (>12 chars), and (post hoc) for lines of the produced patch.
| Instance | gold lines | test_patch lines | F2P names | produced-patch lines |
|---|---|---|---|---|
| schemathesis__schemathesis-4087 | 0 | 0 | 0 | 0 |
| nesquena__hermes-webui-2056 | 0 | 0 | 0 | 0 |
| youssofal__mtplx-21 | 4 | 0 | 0 | 1 |
| raullenchai__rapid-mlx-289 | 0 | 1 | 0 | 0 |
| python-wheel-build__fromager-1124 | 2 | 23 | 0 | 20 |
| itsdnns__docsight-437 | 0 | 5 | 0 | 0 |
| tox-dev__tox-3931 | 0 | 0 | 0 | 0 |
| copier-org__copier-2646 | 0 | 0 | 0 | 0 |
| hkuds__openharness-217 | 0 | 0 | 0 | 0 |
| astronomy-commons__lsdb-1349 | 0 | 0 | 0 | 0 |
| alibaba__opensandbox-816 | 0 | 0 | 0 | 3 |
| apache__iceberg-python-3295 | 0 | 0 | 0 | 0 |
| zarr-developers__virtualizarr-979 | 0 | 1 | 0 | 0 |
| ultraplot__ultraplot-696 | 0 | 1 | 0 | 0 |
| pyinfra-dev__pyinfra-1665 | 0 | 3 | 0 | 0 |
| microsoft__qcodes-8039 | 0 | 0 | 0 | 0 |
| cs-si__eodag-2176 | 2 | 0 | 0 | 0 |
| agronholm__anyio-1134 | 0 | 0 | 0 | 0 |
| databricks__dbt-databricks-1428 | 0 | 0 | 0 | 0 |
| pennylaneai__pennylane-9298 | 0 | 0 | 0 | 0 |

Origin of every grep hit (first occurrence in the test-writer's task/trajectory). ISSUE_TEXT and PRE_FIX_REPO_OBSERVATION are allowed inputs: gold/test_patch lines that already exist in the issue or the pre-fix code. AGENT_AUTHORED = written by the test-writer before it appeared in any observation, e.g. a natural import line. UNEXPLAINED would count as a confirmed exposure.

| Instance | Kind | Origin | Line |
|---|---|---|---|
| youssofal__mtplx-21 | gold | ISSUE_TEXT | `if self._START_MARKER.startswith(lowered):` |
| youssofal__mtplx-21 | gold | ISSUE_TEXT | `lowered = stripped.lower()` |
| youssofal__mtplx-21 | gold | ISSUE_TEXT | `return [{"content": content}]` |
| youssofal__mtplx-21 | gold | ISSUE_TEXT | `stripped = self._pending.lstrip()` |
| raullenchai__rapid-mlx-289 | test_patch | AGENT_AUTHORED | `from vllm_mlx.reasoning.gemma4_parser import Gemma4ReasoningParser` |
| python-wheel-build__fromager-1124 | gold | PRE_FIX_REPO_OBSERVATION | `------------------------------` |
| python-wheel-build__fromager-1124 | gold | PRE_FIX_REPO_OBSERVATION | `req_type: RequirementType / None = None,` |
| python-wheel-build__fromager-1124 | test_patch | PRE_FIX_REPO_OBSERVATION | `_, version = resolver.resolve(` |
| python-wheel-build__fromager-1124 | test_patch | PRE_FIX_REPO_OBSERVATION | `assert result is _COOLDOWN` |
| python-wheel-build__fromager-1124 | test_patch | PRE_FIX_REPO_OBSERVATION | `ctx = _make_ctx(tmp_path, cooldown=_COOLDOWN)` |
| python-wheel-build__fromager-1124 | test_patch | PRE_FIX_REPO_OBSERVATION | `ctx = context.WorkContext(` |
| python-wheel-build__fromager-1124 | test_patch | AGENT_AUTHORED | `from fromager.requirements_file import RequirementType` |
| python-wheel-build__fromager-1124 | test_patch | PRE_FIX_REPO_OBSERVATION | `json=_cooldown_json_response,` |
| python-wheel-build__fromager-1124 | test_patch | AGENT_AUTHORED | `req_type=RequirementType.TOP_LEVEL,` |
| python-wheel-build__fromager-1124 | test_patch | PRE_FIX_REPO_OBSERVATION | `result = resolver.resolve_package_cooldown(` |
| python-wheel-build__fromager-1124 | test_patch | PRE_FIX_REPO_OBSERVATION | `with requests_mock.Mocker() as r:` |
| itsdnns__docsight-437 | test_patch | PRE_FIX_REPO_OBSERVATION | `from app.modules.comparison.routes import _aggregate_period` |
| itsdnns__docsight-437 | test_patch | PRE_FIX_REPO_OBSERVATION | `from app.modules.comparison.routes import _aggregate_period, _compute_delta` |
| itsdnns__docsight-437 | test_patch | PRE_FIX_REPO_OBSERVATION | `result = _aggregate_period([SNAPSHOT_A])` |
| zarr-developers__virtualizarr-979 | test_patch | AGENT_AUTHORED | `parser = KerchunkJSONParser()` |
| ultraplot__ultraplot-696 | test_patch | ISSUE_TEXT | `axs[-1].set_visible(False)` |
| pyinfra-dev__pyinfra-1665 | test_patch | PRE_FIX_REPO_OBSERVATION | `remove_any_sudo_askpass_file(host)` |
| cs-si__eodag-2176 | gold | PRE_FIX_REPO_OBSERVATION | `+ eodag_queryable_fieldinfo.metadata` |
| cs-si__eodag-2176 | gold | PRE_FIX_REPO_OBSERVATION | `field_definition[1].metadata` |

Sensitivity: if every raw grep hit were treated as exposure, criterion 4 would fail (8 issues) and the verdict would be STOP.

## Post-hoc descriptive timing (NOT preregistered; user request 19:21)
Wall-clock from work/pipeline.log timestamps (1 s resolution). Stage 1 = test-writer + 2 pre-fix runs + freeze commit; Stage 2 = OpenHands run wall_seconds from its run artifact (log-derived if missing); Stage 3 = evaluation (ground truth + gate), excluding image removal.

| Stage | Timing |
|---|---|
| Stage 1 (test-writer incl. pre-fix eval) | median 1.7 min, p90 4.4 min, total 41.6 min (n=16) |
| Stage 1, test-writer outcome LIMIT_EXCEEDED | median 2.8 min, p90 4.4 min, total 8.9 min (n=3) |
| Stage 1, test-writer outcome SUBMITTED | median 1.1 min, p90 2.3 min, total 16.2 min (n=12) |
| Stage 1, test-writer outcome WALL_TIMEOUT | median 16.5 min, p90 16.5 min, total 16.5 min (n=1) |
| Stage 2 (OpenHands) | median 1.9 min, p90 3.1 min, total 52.2 min (n=16) |
| Stage 3 (evaluation) | median 0.2 min, p90 4.8 min, total 17.3 min (n=16) |

Time and cost per correct approved patch: A 52.2 min and $0.7127 (Stage 2 time only); B 111.1 min and $1.5061 (Stages 1+2+3).

| # | Instance | Stage 1 (s) | test-writer outcome | Stage 2 (s) | Stage 3 (s) |
|---|---|---|---|---|---|
| 1 | schemathesis__schemathesis-4087 | 170.0 | LIMIT_EXCEEDED | 75 | 10.0 |
| 3 | nesquena__hermes-webui-2056 | 38.0 | SUBMITTED | 69 | 18.0 |
| 4 | youssofal__mtplx-21 | 991.0 | WALL_TIMEOUT | 125 | 2.0 |
| 5 | raullenchai__rapid-mlx-289 | 27.0 | SUBMITTED | 1606 | 0.0 |
| 6 | python-wheel-build__fromager-1124 | 115.0 | SUBMITTED | 114 | 230.0 |
| 7 | itsdnns__docsight-437 | 50.0 | SUBMITTED | 140 | 12.0 |
| 9 | tox-dev__tox-3931 | 25.0 | SUBMITTED | 71 | 1.0 |
| 10 | copier-org__copier-2646 | 263.0 | LIMIT_EXCEEDED | 127 | 288.0 |
| 11 | hkuds__openharness-217 | 83.0 | SUBMITTED | 59 | 4.0 |
| 12 | astronomy-commons__lsdb-1349 | 41.0 | SUBMITTED | 119 | 328.0 |
| 13 | alibaba__opensandbox-816 | 108.0 | SUBMITTED | 140 | 15.0 |
| 14 | apache__iceberg-python-3295 | 31.0 | SUBMITTED | 121 | 14.0 |
| 16 | zarr-developers__virtualizarr-979 | 101.0 | LIMIT_EXCEEDED | 56 | 0.0 |
| 17 | ultraplot__ultraplot-696 | 137.0 | SUBMITTED | 186 | 78.0 |
| 18 | pyinfra-dev__pyinfra-1665 | 184.0 | SUBMITTED | 62 | 1.0 |
| 20 | microsoft__qcodes-8039 | 133.0 | SUBMITTED | 60 | 39.0 |

## Caveats

- Early stop by user decision after #20/30 (22:03 IST); #21-#30 not run. Small n: all intervals are wide.
- Three protocol amendments before any scored result: (1) Amendment 1 (v1 design, archived); (2) Amendment 2: test-writer sandbox env parity (`bash -c`, testbed PATH) + fail-closed pytest preflight, after the first attempt at #1 ran with no usable python/pytest (voided, kept in git fd918db/b97ed01); (3) Amendment 3: every evaluation bound to the exact sealed patch artifact (run ID, sha256, bytes, base SHA, raw/filtered hashes, git seal, read-only), after an operator diagnostic copied the gold patch into results/ post-verdict in SMOKE2 (RCA evidence/smoke2_rca). Scored run used fe54862 unchanged; GO checklist 479b4d3.
- REJECT_INSUFFICIENT_EVIDENCE frequency: 5/16 = 0.31 [0.14, 0.56] of scored issues. Stage-1 produced no discriminating test in 5/16 = 0.31 [0.14, 0.56] (incl. INVALID runs, clarification requests, tests passing on pre-fix). A large share of B's rejections therefore reflects missing evidence, not a detected defect.
- Test-writer runs ending at the 40-step limit: 3/16; stage-1 INVALID (non-test file created): 1/16.
- INFRA_FAIL: 4/20 (OpenHands agent-server crash at start), excluded from denominators; see sensitivity line. More than 3, so the verdict is LOW CONFIDENCE.
- One model (gemini-2.5-flash) for producer and test-writer; harness, gate and analysis written by the same agent; SWE-rebench pre-selects clear, test-verifiable issues; n is small and Wilson intervals are wide; gate-P2P is a heuristic subset. A's verdict ('Patch Submission Baseline') is not agent self-confidence.
- Run-to-run variance of the test-writer is large (schemathesis-4087: 1 discriminating unit in SMOKE2, 0 in smoke3, 0 in the scored run).
- Cost-gap flags (>1% proxy vs litellm): ['raullenchai__rapid-mlx-289']; recorded cost = max of the two.
