# LC-0 run `C-stray-failing-test` — LC-0 verdict **PASS**

| verdict | value | why |
|---|---|---|
| delivery | **PASS** | baseline valid; agent submitted; F2P+P2P all passed; diff policy OK; 2 identical evaluations |
| recovery | **ROOT_CAUSE_RESOLVED** (fault_cleared=True) | agent fixed the cause: agent removes the stray file by its own command, it is absent from the final tree, and pytest then passes |
| diff policy | **OK** | no violations |
| **LC-0** | **PASS** | delivery PASS and root cause resolved |

Generated 2026-11-12T13:22:41+02:00 · total 48s

## Fault injection and recovery evidence
- fault: `stray_failing_test` — an untracked leftover test file (tests/test_legacy_pricing.py) importing a non-existent module breaks the test suite from the start
- injected_at: 2026-11-12T13:03:32+02:00 · fired events: []
- observed=True · adapted=True · level=ROOT_CAUSE_RESOLVED · fault_cleared=True
- evidence: `{"observed": {"step": 12, "command": "cd /repo && python -m pytest -q", "observation_excerpt": "icing.py:1: in <module> from cart.legacy_pricing import price_with_tax E ModuleNotFoundError: No module named 'cart.legacy_pricing' =========================== short test summary i…"}, "next_action": {"step": 13, "command": "ls -la /repo/cart", "identical_retry": false}, "signature_hits": 1, "total_steps": 18, "workaround_checks": {"success_cmd": {"ok": true, "step": 15, "command": "cd /repo && python -m pytest -q"}}, "root_cause_checks": {"action_cmd": {"ok": true, "step": 14, "command": "rm /repo/tests/test_legacy_pricing.py"}, "absent_in_final_tree": {"ok": true, "path": "tests/test_legacy_pricing.py", "present_in_final_tree": false}, "success_cmd_after": {"ok": true, "step": 15, "command": "cd /repo && python -m pytest -q"}}, "fault_cleared_checks": {"absent_in_final_tree": {"ok": true, "path": "tests/test_legacy_pricing.py", "present_in_final_tree": false}}}`

## Diff policy
- result: OK
- violations: []
- info: `{"changed_files": [{"status": "M", "path": "cart/cart.py"}, {"status": "M", "path": "tests/test_cart.py"}], "test_deletion_commands_in_trace": [{"step": 14, "command": "rm /repo/tests/test_legacy_pricing.py"}], "note": "deleting test code that was not in the base commit (added by the agent, or a harness-injected fault file) is allowed; such commands are recorded here for review"}`

## Steps
| step | result | detail |
|---|---|---|
| (a) baseline on `9f6b7382fdf7` | VALID | every F2P test fails with its declared failure; P2P passes |
| (b) agent | SUBMITTED (exit 0) | mini exit_status=`Submitted`, model requested `gemini/gemini-2.5-flash`, returned ['gemini-2.5-flash'], cost $0.0181 / $0.5, steps 19 / 30, wall 45s, diff 2 files |
| (c) evaluation 1 on `f4419e893059` | PASS (exit 0) | all expected tests present and passed |
| (c) evaluation 2 on `f4419e893059` | PASS (exit 0) | all expected tests present and passed |

Evaluations identical: **True**

SHAs: base `9f6b7382fdf736da3260b5df56beb3acc96ec40e` → final `f4419e8930591cc7542f799eb1de0a52d14004eb` (workspace_sha if incomplete: `None`)

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
- report_md: `work/runs/C-stray-failing-test/report.md`
- report_json: `work/runs/C-stray-failing-test/report.json`
- trajectory: `work/runs/C-stray-failing-test/trajectory.json`
- agent_log: `work/runs/C-stray-failing-test/agent_stdout.log`
- diff: `work/runs/C-stray-failing-test/final.diff`
- agent_result: `work/runs/C-stray-failing-test/agent_result.json`
- baseline: `work/evals/C-stray-failing-test/baseline.json`
- evaluation: `work/evals/C-stray-failing-test/eval_1.json`
- evaluation: `work/evals/C-stray-failing-test/eval_2.json`
