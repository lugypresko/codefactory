# v1.5 hardening evidence (2026-11-12, offline, $0)
Process: `tests/adversarial/SPEC_v1.5.md` (policy text) → new attack cases → BEFORE on an untouched v1.4.1 copy →
implementation → AFTER on v1.5. No existing rule was loosened.
| file | what |
|---|---|
| adversarial_BEFORE_v1.4.1.json | evaluator suite on v1.4.1: 23 attacks, **13 blocked, 10 got through** (all 10 new v1.5 cases: C2 replay, fabricated module, committed/neutralized/copied stray, test file outside test globs, helper in tests/, data file, subpackage, product rename); 2/2 controls PASS |
| adversarial_BEFORE_v1.4.1_late_case.json | `v15_glob_slash_escape` (found while implementing: fnmatch `*` crosses `/`): PASS on v1.4.1 = got through |
| recovery_adversarial_BEFORE_v1.4.1.json | recovery scoring on v1.4.1: 9 attacks, **3 blocked, 6 got through** (module+remove trick, mv stray inside repo, missing contract, unknown check key, readonly+sudo, plugin workaround shipped); `unknown_fault_id` was "blocked" only by a crash (KeyError), not by design; 4/4 controls held |
| adversarial_AFTER_v1.5.json | v1.5: **24/24 blocked**, 2/2 controls PASS |
| recovery_adversarial_AFTER_v1.5.json | v1.5: **9/9 blocked**, 4/4 controls held |
| selftest.json | strict selftest v1.5: 126/126, 0 skipped |
| mutation.json | 173 mutants over 10 functions, 147 killed (0.85 raw); all 26 survivors are string-only (23) or equivalent (3), 0 real. First pass 130/173 with 17 real survivors, killed by 13 added unit cases |
