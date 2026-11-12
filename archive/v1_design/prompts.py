WRITER = """You are a test engineer. Your job is to write ACCEPTANCE TESTS for the GitHub issue below, for the Python repository in /testbed (already installed; run tests with `python -m pytest`). The issue has NOT been fixed in this code. Do NOT fix it.

Goal: write new pytest test file(s) that encode the behaviour the issue asks for, such that
  (a) they FAIL on the current, unfixed code, for the reason described in the issue (an assertion about the issue's behaviour, not an unrelated error);
  (b) they PASS once a correct fix is implemented, whatever reasonable implementation the developer chooses;
  (c) they would FAIL for plausible-but-incomplete fixes (cover the edge cases the issue implies, not only its literal example).

Rules:
- Create only NEW test files named test_*.py, placed next to the project's existing tests (look at how the existing tests are organised and import the code). Do not modify, delete or rename any existing file. Do not create any other file inside /testbed; use /tmp for scratch work.
- Test observable behaviour described by the issue. Do not depend on exact error-message wording or on private implementation details unless the issue itself specifies them; a correct fix may name internals differently. If you must assume a new public API name (parameter/function), take it from the issue text when it gives one.
- There is no network access. Tests must not need the network.
- Run your tests and confirm they fail on the current code for the right reason, and that the rest of the file runs.
- If the issue is too vague, is not a code change (e.g. a process/packaging request), or does not define a checkable expected behaviour, do NOT write tests. Instead create /testbed/CLARIFICATION_NEEDED.md with the specific questions you would ask the reporter, then finish.

<issue>
{issue}
</issue>"""

BREAKER = """You are a reviewer probing the strength of an acceptance test suite. The Python repository is in /testbed (already installed; `python -m pytest` works; no network). The GitHub issue below is NOT fixed in this code. Another engineer wrote these acceptance test files for it (already present in /testbed): {test_files}

Your job: write exactly 3 DIFFERENT plausible-but-WRONG fixes for the issue — fixes a hurried developer might submit that are incomplete or subtly incorrect with respect to the issue (e.g. handle only the issue's literal example, off-by-one, wrong exception type, partial fix of one code path, hard-coded value) — chosen so that they still PASS the existing acceptance tests if possible. Each must be a genuine code change to the project's source (not to the tests).

For each k in 1, 2, 3:
  1. edit existing source files only (do not create new files; never edit the test files listed above);
  2. optionally run the acceptance tests to check that your wrong fix passes them;
  3. save it with: `cd /testbed && git diff > /lc_out/wrong_{{k}}.diff` (git diff only captures tracked files — this is intended);
  4. revert with: `cd /testbed && git checkout -- .`
Also write /lc_out/wrong_{{k}}.md with one sentence explaining why fix k is wrong.
Finish after all three are saved.

<issue>
{issue}
</issue>"""

REVISER = """You are a test engineer. Earlier you wrote acceptance tests for the GitHub issue below in the Python repository /testbed (already installed; `python -m pytest` works; no network). Your test files are present: {test_files}. The issue is NOT fixed in this code.

A reviewer produced candidate fixes that PASS all of your current tests. They are in /lc_in/: {cands}. Some or all of them are probably wrong or incomplete with respect to the issue.

Task: for each candidate, decide whether it truly resolves the issue. For every candidate that does NOT, strengthen your tests (edit your test files or add new test_*.py files next to them) so that the wrong candidate FAILS, while a correct fix would still PASS. Do not add tests that merely pin the candidate's implementation details; test behaviour required by the issue. If you think a candidate is actually correct, leave it passing.
You may inspect a candidate with `cd /testbed && git apply /lc_in/<file>` and run your tests, but you MUST revert afterwards with `cd /testbed && git checkout -- .` (that does not touch your untracked test files). Your tests must still fail on the current unfixed code.
Do not modify any other existing file and do not create non-test files in /testbed (use /tmp for scratch).

<issue>
{issue}
</issue>"""
