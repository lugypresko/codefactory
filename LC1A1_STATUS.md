# LC-1A.1 status: INCOMPLETE

This experiment is **stopped**, not expanded, and is **not** marked ITERATE.
ITERATE would imply the planned five-issue loop was completed. It was not.

## Counts

- Executed: **1 / 5** (only `nesquena__hermes-webui-2056`).
- The other four issues (`fromager-1124`, `docsight-437`, `copier-2646`, `lsdb-1349`) were **not** run.
- Repaired (B APPROVE after feedback): **0 / 1**.
- False PASS: 0. INTEGRITY_FAIL: 0 (after the hook fix below). INFRA_FAIL: 0.

## R0 (frozen LC-1A.0, not re-run)

- A APPROVE, B REJECT (`REJECT_INVALID_PATCH`, discriminating tests fail on patch).
- `gate_units_passed`: [2, 2] of 4. P2P: 0/131 broken.
- GT incorrect: f2p 3/3 failed, p2p 0/54 failed. Patch 785 bytes. Cost $0.0206.

## R1 — `pa-nesquena__hermes-webui-2056-20261113T000752-37f90d7d`

- Started 2026-11-13 00:07:52 Asia/Jerusalem (UTC+2). OpenHands FINISHED. Wall 96 s. Ledger $0.02714332 (11 calls).
- Feedback sent (mixed counts, no unproven names): `2 of 4 discriminating tests failed`.
- A APPROVE, B REJECT (`REJECT_INVALID_PATCH`). Units still [2, 2] of 4. P2P 0/131 broken.
- GT incorrect: f2p 2/3 failed, p2p 0/54 failed. Patch 1667 bytes. Not a False PASS.
- Seal `b52c5a50e63e207716ecc3ebf2cc03a86446e576`. Eval `f7b8a03fb244653f50510c94d4c9b435a4f38ef1`.

## Mid-run fixes (no second model call for R1)

1. **`b02dafc2293d4a69efa456ac2843ce558e9ea346`** — stage3 could not write `eval.json` into the sealed `LC_OUT` directory (`0o555`). First stage3 crashed with `PermissionError`. Fix: opt-in `emit()` / `chmod u+w`. Then stage3 was re-run only.
2. **Workspace restore** — the first of those stage3 runs had a vacuous P2P gate (`no matching existing test files`) because LC-1A.0 had deleted `work/runs/testgen/.../ws`. The workspace was restored with `prep_ws` (same sanitized base SHA `026363d69bfcafba2855bdc73034d591f3ae25fa`) and stage3 was re-run. P2P then matched R0 (0/131 broken). B stayed REJECT.

## R2 — `pa-nesquena__hermes-webui-2056-20261113T001212-d974361f`

- Started 2026-11-13 00:12:12 Asia/Jerusalem (UTC+2), from the R1 patch + the same feedback string. OpenHands FINISHED. Wall 186 s. Ledger $0.06093433 (25 calls).
- A APPROVE, B REJECT. Units **regressed** to [0, 0] of 4. P2P 0/131 broken.
- GT incorrect: f2p still 2/3 failed; p2p **regressed** to 12/54 failed. Patch 3544 bytes. Not a False PASS.
- Seal `960ebed20c6c262c09542df88091ba5ca6939b7a`. Eval + summary `f1f64e8bdd58ef84c196ce793f7108131d242131`.

## Cost and isolation

- Repair LLM cost (R1+R2): $0.08808, well under $1.
- `results/` (LC-1A.0) was unchanged. No push; `master` stayed at `4faba03`.

The LITELLM local cost-map and dead-container health check held: both agent-servers became healthy (no INFRA_FAIL).
