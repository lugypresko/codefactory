# LC-0 run `neg-costlimit` — **FAIL**

agent did not deliver: LIMIT_EXCEEDED cost

Generated 2026-11-12T12:26:17+02:00 · total 10s

## Versions
| item | value |
|---|---|
| python | `3.13.5` |
| mini_swe_agent | `2.4.6` |
| litellm | `1.109.1` |
| docker_server | `27.3.1` |
| image_tag | `lc0-env:1` |
| image_id | `sha256:19ad674b97f2264775a8edf3c492f66aa19cbc8cda92645f5d962caf3a35621c` |
| base_image_digest | `sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b` |
| base_commit_sha | `9f6b7382fdf736da3260b5df56beb3acc96ec40e` |
| hidden_tests_sha256 | `9670a8d812bd98adf92deacb8acb999df3c554393cc426e8a7ff3ee0a45855ed` |
| p2p_tests_sha256 | `e1014e6e23470bbbdb6e190887219b91830ebda21341d745a6081a963029d8a1` |
| os | `Linux-6.12.94+-x86_64-with-glibc2.41` |

## Steps
| step | result | detail |
|---|---|---|
| (a) baseline on `9f6b7382fdf7` | VALID | F2P passed on base: 0/9 (must be 0); P2P: passed 5/5 |
| (b) agent | LIMIT_EXCEEDED (exit 10) | mini exit_status=`LimitsExceeded`, model requested `gemini/gemini-2.5-flash`, returned ['gemini-2.5-flash'], cost $0.0025 / $0.002, steps 4 / 30, wall 9s, diff 1 files |

Evaluations identical: **None**

SHAs: base `9f6b7382fdf736da3260b5df56beb3acc96ec40e` → final `None` (workspace_sha if incomplete: `37f28026e94a3aa62f4c3bf9cb2668c3e05475d2`)

## Integrity
- hidden tests sha256 `9670a8d812bd98adf92deacb8acb999df3c554393cc426e8a7ff3ee0a45855ed`
- P2P tests sha256 `e1014e6e23470bbbdb6e190887219b91830ebda21341d745a6081a963029d8a1`
- pinned hashes verified before and after every evaluation: True
- harness-sensitive files in artifact: None

## Paths (relative to package root)
- report_md: `work/runs/neg-costlimit/report.md`
- report_json: `work/runs/neg-costlimit/report.json`
- trajectory: `work/runs/neg-costlimit/trajectory.json`
- agent_log: `work/runs/neg-costlimit/agent_stdout.log`
- diff: `work/runs/neg-costlimit/final.diff`
- agent_result: `work/runs/neg-costlimit/agent_result.json`
- baseline: `work/evals/neg-costlimit/baseline.json`
