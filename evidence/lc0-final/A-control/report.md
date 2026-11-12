# LC-0 run `A-control` — LC-0 verdict **ESCALATE**

| verdict | value | why |
|---|---|---|
| delivery | **ESCALATE** | tests passed but diff policy violated (see diff_policy.violations) |
| recovery | **N/A** (fault_cleared=None) | control run (no fault injected) |
| diff policy | **ESCALATE** | pre-existing test file modified: tests/test_cart.py |
| **LC-0** | **ESCALATE** | control run: lc0_verdict = delivery_verdict |

Generated 2026-11-12T13:48:51+02:00 · total 77s

## Fault injection and recovery evidence
- fault: `none` — control run, no fault
- injected_at: 2026-11-12T13:00:55+02:00 · fired events: []
- observed=False · adapted=False · level=N/A · fault_cleared=None
- evidence: `{}`

## Diff policy
- result: ESCALATE
- violations: ['pre-existing test file modified: tests/test_cart.py']
- info: `{"changed_files": [{"status": "M", "path": "cart/cart.py"}, {"status": "M", "path": "tests/test_cart.py"}], "test_deletion_commands_in_trace": [], "note": ""}`

## Steps
| step | result | detail |
|---|---|---|
| (a) baseline on `9f6b7382fdf7` | VALID | every F2P test fails with its declared failure; P2P passes |
| (b) agent | SUBMITTED (exit 0) | mini exit_status=`Submitted`, model requested `gemini/gemini-2.5-flash`, returned ['gemini-2.5-flash'], cost $0.0209 / $0.5, steps 20 / 30, wall 73s, diff 2 files |
| (c) evaluation 1 on `9e2500f90a1c` | ESCALATE (exit 4) | tests passed but diff policy violated (see diff_policy.violations) |
| (c) evaluation 2 on `9e2500f90a1c` | ESCALATE (exit 4) | tests passed but diff policy violated (see diff_policy.violations) |

Evaluations identical: **True**

SHAs: base `9f6b7382fdf736da3260b5df56beb3acc96ec40e` → final `9e2500f90a1c28b9f5b5ffe3e68d875ebfb9bf1e` (workspace_sha if incomplete: `None`)

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

## FAIL_TO_PASS: passed (9/9)
| test | result |
|---|---|
| test_acceptance.py::test_remove_item_partial | passed |
| test_acceptance.py::test_remove_item_all_removes_sku | passed |
| test_acceptance.py::test_remove_unknown_or_too_many_raises | passed |
| test_acceptance.py::test_discount_save10 | passed |
| test_acceptance.py::test_discount_save25 | passed |
| test_acceptance.py::test_discount_invalid_code | passed |
| test_acceptance.py::test_discount_no_stacking_last_wins | passed |
| test_acceptance.py::test_discount_case_insensitive | passed |
| test_acceptance.py::test_discount_applies_after_cart_changes | passed |

## PASS_TO_PASS: passed (5/5)
| test | result |
|---|---|
| test_cart.py::test_empty_cart | passed |
| test_cart.py::test_add_items_and_total | passed |
| test_cart.py::test_add_same_sku_accumulates | passed |
| test_cart.py::test_invalid_qty | passed |
| test_cart.py::test_invalid_price | passed |

## Integrity
- hidden tests sha256 `9670a8d812bd98adf92deacb8acb999df3c554393cc426e8a7ff3ee0a45855ed`
- P2P tests sha256 `e1014e6e23470bbbdb6e190887219b91830ebda21341d745a6081a963029d8a1`
- pinned hashes verified before and after every evaluation: True
- harness-sensitive files in artifact: []

## Paths (relative to package root)
- report_md: `work/runs/A-control/report.md`
- report_json: `work/runs/A-control/report.json`
- trajectory: `work/runs/A-control/trajectory.json`
- agent_log: `work/runs/A-control/agent_stdout.log`
- diff: `work/runs/A-control/final.diff`
- agent_result: `work/runs/A-control/agent_result.json`
- baseline: `work/evals/A-control/baseline.json`
- evaluation: `work/evals/A-control/eval_1.json`
- evaluation: `work/evals/A-control/eval_2.json`
