# LC-0 run `val1` — **PASS**

baseline valid; agent submitted; F2P+P2P all passed; 2 identical evaluations

Generated 2026-11-12T12:25:01+02:00 · total 38s

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
| (b) agent | SUBMITTED (exit 0) | mini exit_status=`Submitted`, model requested `gemini/gemini-2.5-flash`, returned ['gemini-2.5-flash'], cost $0.0186 / $0.5, steps 18 / 30, wall 35s, diff 2 files |
| (c) evaluation 1 on `b965584ba21e` | PASS (exit 0) | all expected tests present and passed |
| (c) evaluation 2 on `b965584ba21e` | PASS (exit 0) | all expected tests present and passed |

Evaluations identical: **True**

SHAs: base `9f6b7382fdf736da3260b5df56beb3acc96ec40e` → final `b965584ba21eb7d3026fe3aec90952aa52403951` (workspace_sha if incomplete: `None`)

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
- report_md: `work/runs/val1/report.md`
- report_json: `work/runs/val1/report.json`
- trajectory: `work/runs/val1/trajectory.json`
- agent_log: `work/runs/val1/agent_stdout.log`
- diff: `work/runs/val1/final.diff`
- agent_result: `work/runs/val1/agent_result.json`
- baseline: `work/evals/val1/baseline.json`
- evaluation: `work/evals/val1/eval_1.json`
- evaluation: `work/evals/val1/eval_2.json`
