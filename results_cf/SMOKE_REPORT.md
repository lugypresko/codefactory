# Code Factory failure report

Issue: /workspace/cf-demo/ISSUE.md
Status: SMOKE (models not run; no PR)
B decision: n/a
Discriminating tests fail on base: n/a (no B run)
Discriminating tests pass on patch: n/a
Project regression tests pass on patch: True
Cost: $0.0000

A draft PR is **not** opened unless a discriminating test fails on the base, that test
passes on the patch, and the project's regression tests pass. B's tests are evidence,
not independent verification.

prep image=cf-demo:local
sanitized_base_sha=1c3628ea4d1333601110af19816582e2e1493cb5
original_base_commit=f7438077c0c16ff80c93915ea55fd432a2949859
project tests passed on base: yes
bug demonstration (split_even(10,3) sum != 10): yes
LC_LEDGER=/workspace/lc1a0/results_cf/cost_ledger.jsonl
LC_RUNS=/workspace/lc1a0/results_cf/runs/attempt1
OpenHands/B: not started
--create-draft-pr: not set
