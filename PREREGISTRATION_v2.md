# LC-1A.0 v2 — Release-decision test — PREREGISTRATION (frozen before any result-collecting run)

Date: 2026-11-12 (Asia/Jerusalem). Supersedes the v1 design (PREREGISTRATION.md, kept in git history and in the repo;
v1 artefacts archived in archive/v1_design/). Redesign and protocol amendments were approved by the user (Itay) before any
v2 run. Nothing below may change after results are seen. Any deviation is reported as such in REPORT.md.

## Question
Does our gate (independently generated acceptance tests + deterministic evaluator) separate correct patches from wrong ones
better than the Patch Submission Baseline, without rejecting too many correct patches, at acceptable cost?

## Dataset lock
- Source used: Hugging Face dataset `nebius/SWE-rebench-leaderboard`, main revision `34d5a58864acf91613740a09ec5d205228dcfa39`
  (lastModified 2026-07-28), read from the auto-converted parquet branch `refs/convert/parquet` @ `55f056ab01ea7452ed4e300b723688a0364804dd`,
  splits `2026_01`, `2026_02`, `2026_03` (file sha256 in data/SHA256SUMS).
- Not used (noted as a possible alternative source): SWE-rebench-V2 (github.com/SWE-rebench/SWE-rebench-V2).
- Verified sample: 30 instances, 7 candidates rejected in verification (geopython__pygeoapi-2338, graphistry__pygraphistry-1277,
  mempalace__mempalace-1004, pypa__twine-1309, pypa__build-1027, azure-samples__azure-search-openai-demo-3025,
  pdm-project__pdm-3759 (4/63 = 6.3% P2P failing on gold > 5%) — reasons in sample_v2.json; the 30 ids in order are listed there).
- Selection rule (unchanged from v1, lib/candidates.py): created_at DESC; drop non-empty `interface`; require docker_image,
  patch, test_patch, FAIL_TO_PASS; Docker Hub size <= 3.0 GB, amd64; max one instance per repo; walk in order; the first 30
  that verify on this box form the sample. Verification (lib/verify.py, --network none): with test_patch, every F2P fails on
  pre-fix and passes on gold; >=95% of P2P pass on gold (P2P failing on gold are dropped from the effective P2P set).
  Rejections logged in data/verification_log.jsonl. The 30 instance ids, images (repo digests) and content hashes are in
  sample_v2.json. Issues are processed in that frozen order.
- The 3 vague issues of v1 are dropped.
- Frozen order of the 30 instance ids (split = the parquet split each row came from; all are in 2026_01..2026_03):
1. schemathesis__schemathesis-4087
2. cs-si__eodag-2176
3. nesquena__hermes-webui-2056
4. youssofal__mtplx-21
5. raullenchai__rapid-mlx-289
6. python-wheel-build__fromager-1124
7. itsdnns__docsight-437
8. agronholm__anyio-1134
9. tox-dev__tox-3931
10. copier-org__copier-2646
11. hkuds__openharness-217
12. astronomy-commons__lsdb-1349
13. alibaba__opensandbox-816
14. apache__iceberg-python-3295
15. databricks__dbt-databricks-1428
16. zarr-developers__virtualizarr-979
17. ultraplot__ultraplot-696
18. pyinfra-dev__pyinfra-1665
19. pennylaneai__pennylane-9298
20. microsoft__qcodes-8039
21. pypsa__pypsa-1653
22. agentscope-ai__qwenpaw-3278
23. unit8co__darts-3065
24. meltano__meltano-9950
25. tobymao__sqlglot-7479
26. huggingface__huggingface_hub-4056
27. koxudaxi__datamodel-code-generator-3070
28. ucfopen__canvasapi-716
29. zauberzeug__nicegui-5914
30. oemof__tespy-921

## Patch producer — decided before any result (see ENGINE DECISION below; the text in this box was the pre-timebox fallback plan)
> Pre-timebox note (17:00): obstacles to OpenHands were the Docker daemon's `--bridge=none --iptables=false` (only host/none
> networks) and the need for an agent server in each instance sandbox. Fallback was mini-SWE-agent 2.4.6 for all 30.

### User decision (recorded 2026-11-12 17:01 Asia/Jerusalem, before any result-collecting run)
OpenHands gets a timebox until 18:00 (box clock, Asia/Jerusalem). Success = one full SANDBOXED OpenHands run (Docker
runtime, no local/process runtime under any circumstances) on one frozen instance that produces a patch end to end. If that
has not happened by 18:00, the predeclared fallback mini-SWE-agent is used for ALL 30 issues. No mixing engines, no switching
after results start. The final engine choice is appended below as "ENGINE DECISION" before stage runs begin.
(The paragraph above, written before the timebox, describes the obstacles and the fallback configuration.)


### ENGINE DECISION (recorded 2026-11-12 ~17:12 Asia/Jerusalem, before any of the 30 result-collecting runs)
**Engine = OpenHands** (Software Agent SDK / agent-server 1.62.0, image `ghcr.io/openhands/agent-server:1.62.0-python`, default
agent preset `get_default_agent(cli_mode=True)`: terminal, file editor, task tracker; condenser default), model
gemini/gemini-2.5-flash, for ALL 30 issues. No mini-SWE-agent patches, no engine mixing, no switching after results start.
Feasibility PASSED at 17:07 (within the 18:00 timebox): one full sandboxed OpenHands run on frozen instance
schemathesis__schemathesis-4087 finished (execution_status FINISHED) and produced a non-empty patch (546 bytes); repeated at
17:10 to validate cost capture. Those feasibility patches are discarded (not used as results); the issue is re-run in order.
Runtime = SANDBOXED DOCKER runtime, NOT local/process: the OpenHands agent server and all its tools (bash, file edits, test
runs) execute inside a Docker container started from the official agent-server image, `--network none`, `--cap-drop ALL`,
`no-new-privileges`, 2 GB, 1 CPU, 512 pids. Mounts: sanitized pre-fix /testbed copy (rw; image .git removed, fresh 1-commit
history), the instance's /opt/conda env (ro), relay scripts (ro), a socket dir. The host SDK client is a RemoteWorkspace /
RemoteConversation client only; it reaches the server through `docker exec -i` stdio relays (no published port). LLM egress:
container loopback:4000 -> UNIX socket -> host proxy (oh/llm_proxy.py) that only forwards gemini-2.5-flash generateContent to
generativelanguage.googleapis.com, injects the real key host-side (the container only holds a dummy key), meters cost and
refuses calls once the per-issue cap is reached. The sandbox therefore has no internet (cannot fetch upstream fixes).
Prompt: fixed message in oh/oh_run.py + issue text. Caps per issue: $0.50 (proxy-enforced; one in-flight call may overshoot),
max_iteration_per_run 50, wall 20 min (conversation paused at the deadline).
Arm A for OpenHands: APPROVE iff execution_status == FINISHED (agent called finish), no wall timeout, no error, and the
normalised source patch is non-empty; otherwise REJECT. Uncertainty column = regex (see Arm A) over the agent's final
message/finish event (incl. its reasoning text) — informative only.

### Cost accounting (pinned)
Price table = litellm model_cost["gemini/gemini-2.5-flash"]: $0.30/M uncached input, $0.03/M cached input, $2.50/M output incl.
thinking tokens. Gate cost = mini-SWE-agent (litellm) cost of the test generator. Patch-agent cost = max(proxy-metered cost with
the pinned table, agent-server litellm accumulated_cost). The ledger (work/cost_ledger.jsonl) uses the same max for the $25 cap.
Feasibility spend so far (ledger): v1 aborted smoke $0.0247; OH attempts 1-2 $0 (proxy refused before forwarding); OH attempt 3
$0.0156 (backfilled from accumulated_cost: proxy metering bug, fixed); OH attempt 4 $0.1294 (proxy, before the cache-aware table).

## Arm A — Patch Submission Baseline
APPROVE iff the agent finished (OpenHands: execution_status FINISHED, see ENGINE DECISION) AND the source patch is non-empty. REJECT otherwise
(gave up / limit / timeout / crash / empty diff). Extra column (does not change A): whether the agent's final two assistant
messages contain an uncertainty marker (regex: partial(ly)|uncertain|not sure|unsure|could not|couldn't|unable|cannot verify|
may not|might not|TODO|workaround|not fully). Never described as "agent self-confidence".

## Patch normalisation (both arms and ground truth)
From the agent's diff, file sections whose path is test-like (test_*.py, *_test.py, conftest.py, or under a tests/, test/,
testing/ directory) and benign artefacts (__pycache__, .pytest_cache, *.pyc, ...) are removed. The remaining source patch is
what A, B and ground truth evaluate (patch.diff, sha256 recorded).

## Arm B — our gate
Stage 1 (test generation) for an issue runs BEFORE that issue's patch is generated; its outputs are hashed and committed to
git before stage 2 of the issue starts (see Execution order). Generator: mini-SWE-agent + gemini-2.5-flash, prompt prompts/testgen.txt.
- ALLOWED inputs: issue text (in the prompt), original base SHA (recorded; the repo copy has a fresh 1-commit history), the
  pre-fix repo (sanitized /testbed copy = the ONLY mount), the dependencies installed in the instance image.
- FORBIDDEN: agent patch, gold fix, test_patch, hidden FAIL_TO_PASS/PASS_TO_PASS (names or contents), hints_text, patch-
  producer logs/trajectories. Structural enforcement: separate container per run with a single mount; --network none (LLM
  only via the host process); no env forwarded; stage ordering (patches do not exist yet).
- Evidence: per issue task.txt (exact prompt), config.yaml (exact mounts/limits), trajectory, record.json; a grep of all
  generator prompts and trajectories for gold-patch / test_patch / F2P content is reported (and, after stage 2, for patch content).
- Caps: $0.25, 40 steps, 15 min per issue. Output: new test_*.py files only (any other change => run INVALID, tests discarded),
  or CLARIFICATION_NEEDED.md.
Stage 1b (still before patches): the frozen tests run twice on pre-fix. Discriminating unit = a test node that FAILS/ERRORS in
both runs (a file-level collection error is one unit covering all tests of that file). Tests passing on pre-fix (or flaky)
are discarded as non-discriminating.
Stage 3 decision on pre-fix + patch (two independent runs each):
- APPROVE iff every discriminating unit PASSES in both runs AND gate-P2P is OK.
- Gate-P2P (independent of hidden P2P): existing tracked test files of the pre-fix repo that import a module whose file the
  patch changes (stem match; max 10 files, sorted). Tests passing in both pre-fix runs must pass in both patched runs.
  Timeout => fail-closed.
- REJECT_INVALID_PATCH: a discriminating unit or gate-P2P fails on the patch (or the patch does not apply).
- REJECT_INSUFFICIENT_EVIDENCE: no discriminating unit (no tests / clarification / invalid generator run / all pass on pre-fix).
- Empty patch: REJECT (NO_PATCH) for B as well.

## Ground truth (scoring only; never shown to A or B)
Source patch + dev test_patch, instance test_cmd: CORRECT iff all FAIL_TO_PASS pass and all effective PASS_TO_PASS pass.
Apply failure or timeout => WRONG (listed). WRONG patch = non-empty source patch that is not CORRECT. Empty patches are not
patches: counted and reported separately, excluded from the "wrong" and "approved" populations (neither arm approves them).

## Metrics (for A and for B, raw counts + Wilson 95% intervals)
- False PASS Rate = wrong approved / all wrong
- Verified Precision = correct approved / all approved
- Correct PR Retention = correct approved / all correct
- Cost per Correct Approved PR = (patch-agent cost + gate cost) / correct approved   (A: agent cost only; gate cost = stage-1
  model spend; evaluator compute is $0 model spend, wall time reported)
- B rejection breakdown: INVALID_PATCH vs INSUFFICIENT_EVIDENCE; retention losses by reason; frequency of
  INSUFFICIENT_EVIDENCE over all 30.
- SECONDARY analysis (labelled as such): all B metrics recomputed excluding issues where B = REJECT_INSUFFICIENT_EVIDENCE.

## GO thresholds (frozen)
1. B reduces the False PASS Rate by >= 50% relative to A:  FPR_B <= 0.5 * FPR_A.
2. B retains >= 90% of correct patches: Retention_B >= 0.90.
3. Cost overhead <= 30%: total gate cost / total patch-agent cost <= 0.30.
4. Zero exposure of B to gold patch / hidden tests (structural + grep check; any confirmed exposure => fails).
Verdict: GO = all four; ITERATE = 1 holds (it discriminates) but retention < 90% and/or cost > 30%; STOP = 1 does not hold
(no measurable advantage) or 4 fails. If fewer than 5 wrong patches occur, the false-PASS result is declared INCONCLUSIVE and
the verdict is reported as INCONCLUSIVE on criterion 1. If FPR_A = 0 the relative reduction is undefined => INCONCLUSIVE.

## Budget
Hard cap $25 total model spend (ledger work/cost_ledger.jsonl, includes the aborted v1 smoke run $0.0247). A run is not
started if spend + its cap would exceed $25. If the budget runs out, the completed subset (in frozen order) is reported
under these unchanged rules.

## Execution order (disk constraint: one issue at a time)
0 freeze (this file + sample_v2.json, git commit). Then for each issue, strictly in the frozen order, one at a time:
  1 test generation -> 1b pre-fix runs -> hash + git-commit the stage-1 outputs of that issue (commit timestamp precedes
  the patch run) -> 2 patch generation -> 3 evaluation (gate + ground truth) -> record image digest -> docker rmi + prune.
For every issue the generator therefore runs and is frozen before that issue's patch exists; the generator container never
has any patch-producer path mounted. Free-disk floor 20 GB: if reached, stop and report the completed subset.
Stage 2 of issue i may coexist in time only with stages of the SAME issue (no parallelism).

## Known limitations (stated in advance)
One model (gemini-2.5-flash) for both producer and test generator; harness and gate written by the same author (this agent);
sample from SWE-rebench, which pre-filters toward clear, test-verifiable issues; n = 30; gate-P2P is a heuristic subset.
