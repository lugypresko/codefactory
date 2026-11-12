# SMOKE2 root-cause analysis: the 2,171-byte results/patches/schemathesis__schemathesis-4087/patch.diff
All times are Asia/Jerusalem (UTC+2). OpenHands event timestamps are UTC, so add 2 h.

## (1) Provenance
- The 2,171 B file has sha256 24542c19e5fb55160cc77ef53c7243f2bafe4e453357a5b70ce63914ee7d76f4. That is byte-identical to the GOLD patch at work/inst/<iid>/gold.diff (2,171 B).
- No sandbox, container or agent run wrote it. My ad-hoc diagnostic shell on the box wrote it at repo HEAD 1723d17, via host bash PID 376695 and its child stage3_eval.py PID 376711. The full transcript is in diagnostic_shell_transcript.txt.
- The command was: `cp work/inst/$I/gold.diff results/patches/$I/patch.diff`, plus a hand-made 57 B record.json `{"patch_empty": false, "A_decision": "n/a (diagnostic)"}`. The diagnostic's aim was to see whether the generated tests pass on gold.
- That diagnostic first moved the real SMOKE2 artefacts to /tmp. It then wrote gold.diff into the canonical results/ path and started stage3_eval.py, which hung in Docker for 15 minutes until it was killed at 17:59:50.
- The file does NOT belong to SMOKE2 stage 2. The copy is in exhibit_diagnostic_overwrite/.

## (2) Timing (events, then logs, then mtimes)
- OpenHands trace (events.json, 41 events): run start 17:43:11.9. The only edits were three str_replace calls on /testbed/test/data/petstore_v3.yaml, at 17:43:53.8, 17:44:03.9 and 17:44:07.0. FinishAction came at 17:44:10.685 and the last state update at 17:44:10.704. No action touched a source file.
- oh_run.py removes the container (line 76) BEFORE extracting the diff (line 80, `git add -A; git diff --cached base`). So nothing in the sandbox could write after extraction.
- patch_raw.diff (434 B) was written at 17:44:16.414 and oh_result.json at 17:44:16.418.
- stage2 decided A = REJECT EMPTY_DIFF and wrote patch.diff (0 B) and record.json at 17:44:17.770.
- stage3 wrote eval (A REJECT, B NO_PATCH, GT False) at 17:44:19.106. smoke2.log shows "SMOKE2 end 17:44:19".
- The diagnostic overwrote the file with gold at 17:44:43.702, 24 s AFTER the verdict, and from outside the pipeline.

## (3) Content
- **SMOKE2's real patch:** patch_raw.diff, 434 B, 1 file, `test/data/petstore_v3.yaml +5/-0`. It adds a wildcard query parameter `_` to a test fixture. It applies cleanly to base e5fcd1c (`git apply --check` rc 0), but it touches only test data. The preregistered normalisation strips it, so the source patch is 0 B and logically empty. EMPTY_DIFF is correct.
- **The 2,171 B file:** the gold fix, `CHANGELOG.md +1`, `src/schemathesis/specs/openapi/checks.py +9/-1`. It applies cleanly to base (rc 0). It is a real change, but it is not the agent's.

## (4) Consistency (traced through the code)
- **A (stage2_patch.py):** reads work/runs/patch/<iid>/patch_raw.diff, which oh_run.py wrote. It drops benign and test-like sections in memory to get `src`, decides on `src`, and writes results/patches/<iid>/patch.diff = `src` together with record.patch_sha256 = sha256(src).
- **B and ground truth (stage3_eval.py):** read results/patches/<iid>/patch.diff ONCE into `patch`. The same string goes to both gate runs and the ground-truth run, so they do not extract the diff independently.
- **Defect:** stage3 never checks patch.diff against record.patch_sha256. It also takes "empty" from record.patch_empty instead of from the bytes. It does not require the artefact to be committed or sealed, and the pipeline commits results/patches only AFTER stage 3.
- So any file placed at that path after the verdict (stale, late, or a diagnostic copy) is evaluated silently. Regression test (c) reproduces exactly this event on the frozen code.

## Root cause
1. **Process error (mine).** An ad-hoc diagnostic, not part of the protocol, wrote the GOLD patch and a fake record into the canonical results/ path after the SMOKE2 verdict. SMOKE2's own chain was consistent: test-data-only edit, then EMPTY_DIFF, then A REJECT, B NO_PATCH, GT not correct. No generator ever saw that path (Stage 1 was already frozen at 1723d17; the generator container mounts only its own workspace), but placing gold under results/ breaks the hygiene rules.
2. **Latent integrity defect in the frozen code.** The evaluator is not bound to the produced artefact (no sha256 check, no seal), which is what let (1) go undetected.
3. **SMOKE2 also failed as a smoke test.** Because the patch was empty, B's patch path, gate-P2P and the ground-truth run were never exercised. The test-writer also ended with LIMIT_EXCEEDED (step cap 40) but was still classed VALID, which is consistent with the prereg (only violations make a run invalid). It produced 1 discriminating unit, deterministic in both pre-fix runs. Whether that test passes on gold was not established, because the diagnostic was killed.

## Proposed Amendment 3 (NOT committed; exact diff in AMENDMENT3_proposed.diff)
- **pipeline.py:** directly after stage 2, run `git add results/patches/<iid>` and commit "STAGE2 SEAL <iid>". If stage 3 exits with code 4 (EVAL_INTEGRITY_FAIL), the pipeline halts.
- **stage3_eval.py:** before any evaluation, require all of the following, or else write results/integrity_fail_<iid>.json and exit 4 (no B or GT verdict):
  - record.patch_sha256 is present;
  - sha256(patch.diff bytes) equals record.patch_sha256;
  - patch_empty equals (content is blank);
  - patch.diff and record.json are both tracked and unchanged since HEAD (sealed).
  The eval record also gets evaluated_patch_sha256 and evaluated_patch_path.
- **Process rule:** no ad-hoc writes to results/ or work/runs/. Diagnostics run only in a scratch copy with its own ROOT. The gold patch or test_patch is never copied under results/. SMOKE2 artefacts are moved out of results/ to evidence/smoke2/results/ (done), so #1 re-runs from scratch.
- **Unchanged:** prompts, model, caps, sandbox, the test-file rule, metrics and thresholds. This is an integrity fix only.

## Regression (adversarial; written and run before any fix)
Hermetic harness: fake OpenHands runner and fake evaluator Docker layer that records the sha256 of every patch it receives. No model calls.
- **On the frozen code:** 5 of 9 fail (regress_BEFORE_fix_frozen_code.txt).
  - (a) evaluation not bound to a sha;
  - (c) late non-empty file after an EMPTY verdict was evaluated (the SMOKE2 event);
  - (c2) a late overwrite of a non-empty patch was evaluated;
  - (c3) an unsealed artefact was evaluated;
  - (e) no seal between stage 2 and stage 3.
  - These 4 pass: (b) and (b2) empty classified correctly, (c4) late write in the agent run directory ignored, (d) stale previous artefacts replaced.
- **On a scratch copy with Amendment 3 applied:** 9 of 9 pass (regress_AFTER_fix_scratch_copy.txt). The frozen code is untouched.
