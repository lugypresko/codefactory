I have created the test file `/testbed/test/specs/openapi/test_issue_1303.py` and the associated schema `/testbed/test/specs/openapi/schema_issue_1303.yaml` to address the reported issue.

The test is designed to fail on the current, unfixed code (by explicitly calling `pytest.fail()` if the `additionalProperties` validation error occurs for query parameters) and pass once the fix is implemented.

However, I was unable to execute the tests to confirm this behavior due to environment issues. The instructions state to "run tests with `python -m pytest`", but the `python` command is not found. When attempting to use `python3 -m pytest`, it reported "No module named pytest". Attempts to install `pytest` or `tox` (after finding `tox.ini`) with `pip` or `pip3` also failed as these commands were not found.

To proceed, I need clarification on how to execute the tests within this environment. Specifically:

1.  What is the correct command or method to run `pytest` for the `/testbed` repository?
2.  Is there a specific Python executable or virtual environment that needs to be activated or used?
3.  Are there any setup steps I missed for the environment to have `pytest` and other necessary tools available?
