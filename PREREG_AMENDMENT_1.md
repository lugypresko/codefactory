# Amendment 1 (made BEFORE any generation run; no results existed)
Operational details not covered by PREREGISTRATION.md:
1. Benign artefacts ignored by the invalid-run check: paths containing `__pycache__/`, `.pytest_cache/`, `.hypothesis/`,
   `.mypy_cache/`, `.ruff_cache/`, or ending in `.pyc` / `.coverage`. They are listed in the run record.
2. Arm 2 revision round (A'): A' is explicitly allowed to `git apply` the surviving candidate patches to inspect them.
   Therefore for A' ONLY, modifications of tracked source files are reverted by the harness and recorded (not INVALID);
   only A's own test files (new `test_*.py`/`*_test.py`) are taken as the final suite. Any non-test new file is dropped
   and recorded. If A' leaves no test files, A's original tests are kept? NO — fail-closed: the final suite is whatever
   test files exist in A' workspace at the end (A's files are pre-seeded there, so deleting them removes them).
3. Agent B (Arm 2) writes its patches as `git diff` output files to a mounted output dir; hunks that touch A's test files
   are stripped by the harness (recorded). B's patches that fail to apply are ignored (recorded).
4. If Agent A asks for clarification (no tests), Arm 2 ends for that issue (no B, no revision).
5. Vague issues: 3 real GitHub issues (see sample.json "vague"); none synthetic.
6. Wrong patches: 3 per clear issue (36 total), list + hashes in wrong_patches/MANIFEST.json, authoring log in
   wrong_patches/AUTHORING_LOG.md, dev-test validation in wrong_patches/<iid>/check.json. Three of the 36 also fail
   a P2P test because the defect inherently breaks an existing test (fromager w1, tox w1) — kept and disclosed.
