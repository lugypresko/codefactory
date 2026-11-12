# LC-0 run `D-workspace-readonly` — LC-0 verdict **CONTROLLED_STOP**

| verdict | value | why |
|---|---|---|
| delivery | **FAIL** | agent did not deliver: EMPTY_DIFF |
| recovery | **CONTROLLED_STOP** (fault_cleared=None) | unrecoverable fault observed; run stopped with agent_status=EMPTY_DIFF, delivery FAIL |
| diff policy | **n/a** | no violations |
| **LC-0** | **CONTROLLED_STOP** | unrecoverable fault: agent stopped without delivery, no false PASS |

Generated 2026-11-12T13:22:42+02:00 · total 86s

## Fault injection and recovery evidence
- fault: `workspace_readonly` — the repository is mounted read-only: no change can be made; permanent
- injected_at: 2026-11-12T13:04:20+02:00 · fired events: []
- observed=True · adapted=True · level=CONTROLLED_STOP · fault_cleared=None
- evidence: `{"observed": {"step": 4, "command": "sed -i \"/def total(self) -> float:/i \\ def remove_item(self, sku: str, qty: int = 1) -> None:\\ if qty <= 0:\\ raise ValueError(\"qty must be positive\")\\ if sku not in self._items:\\ r…", "observation_excerpt": "self._items[sku]: No such file or directory sed: couldn't open temporary file /repo/cart/sedpdlxbF: Read-only file system"}, "next_action": {"step": 5, "command": "cat /repo/cart/cart.py", "identical_retry": false}, "signature_hits": 5, "total_steps": 24}`

## Diff policy
- result: None
- violations: None
- info: `{}`

## Steps
| step | result | detail |
|---|---|---|
| (a) baseline on `9f6b7382fdf7` | VALID | every F2P test fails with its declared failure; P2P passes |
| (b) agent | EMPTY_DIFF (exit 13) | mini exit_status=`Submitted`, model requested `gemini/gemini-2.5-flash`, returned ['gemini-2.5-flash'], cost $0.0459 / $0.5, steps 27 / 30, wall 85s, diff 0 files |

Evaluations identical: **None**

SHAs: base `9f6b7382fdf736da3260b5df56beb3acc96ec40e` → final `None` (workspace_sha if incomplete: `None`)

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

## Integrity
- hidden tests sha256 `9670a8d812bd98adf92deacb8acb999df3c554393cc426e8a7ff3ee0a45855ed`
- P2P tests sha256 `e1014e6e23470bbbdb6e190887219b91830ebda21341d745a6081a963029d8a1`
- pinned hashes verified before and after every evaluation: True
- harness-sensitive files in artifact: None

## Paths (relative to package root)
- report_md: `work/runs/D-workspace-readonly/report.md`
- report_json: `work/runs/D-workspace-readonly/report.json`
- trajectory: `work/runs/D-workspace-readonly/trajectory.json`
- agent_log: `work/runs/D-workspace-readonly/agent_stdout.log`
- diff: `work/runs/D-workspace-readonly/final.diff`
- agent_result: `work/runs/D-workspace-readonly/agent_result.json`
- baseline: `work/evals/D-workspace-readonly/baseline.json`
