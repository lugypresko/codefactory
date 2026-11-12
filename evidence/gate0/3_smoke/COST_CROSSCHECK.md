# Gate-0 smoke: schemathesis__schemathesis-4087 (OpenHands agent-server 1.62.0, sandboxed Docker)
- Sandbox: container lc1a0_oh_e75ee067, `--network none --cap-drop ALL --security-opt no-new-privileges`, mem 2g, 1 cpu, pids 512; /testbed = sanitized pre-fix workspace; LLM egress only via unix-socket to host proxy (full docker run cmd in oh_result.json). No local/process runtime.
- Status: ConversationExecutionStatus.FINISHED, 13 LLM calls, 43 events, wall 84 s (started 17:12, finished 17:13:56 Asia/Jerusalem). Caps: $0.50, 50 steps, 1200 s.
- Trace: events.json (full OpenHands event log), server.log (agent-server), oh_cli_output.log (CLI stdout).
- Patch: patch.diff, 684 bytes, sha256 a2d19478f47e4b05ae07a5b8c411efd54e560be0b239f647b936ca8459fcf9a6 (1 file: src/schemathesis/specs/openapi/adapter/parameters.py; query params -> additionalProperties True). Not scored; not a result.

## Cost (three independent readings agree exactly)
| Source | input tok | cached input | output tok (incl. thinking) | USD |
|---|---|---|---|---|
| Host proxy, from Gemini usageMetadata per response (llm_ledger.json) | 205,636 | 157,049 | 3,391 | 0.02776507 |
| Agent-server litellm metrics (events.json accumulated_token_usage / accumulated_cost) | 205,636 | 157,049 | 3,391 (2,426 reasoning) | 0.02776507 |
| OH CLI reported (oh_cli_output.log) | 205.64K | 76.37% hit | 3.39K | 0.0278 |
| Hand recompute with pinned table: 48,587x0.30e-6 + 157,049x0.03e-6 + 3,391x2.50e-6 | | | | 0.01457610 + 0.00471147 + 0.00847750 = 0.02776507 |
Method: pinned price table (litellm model_cost gemini/gemini-2.5-flash): $0.30/M uncached input, $0.03/M cached input, $2.50/M output incl. thinking. Ledger entry: work/cost_ledger.jsonl run_id gate0-smoke-schemathesis__schemathesis-4087 = 0.02776507.
