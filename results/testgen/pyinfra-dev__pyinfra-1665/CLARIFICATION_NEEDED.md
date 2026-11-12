# Clarification Needed for pyinfra server.reboot issue

I am unable to write an acceptance test that fails for the described bug, despite extensive mocking of `host.run_shell_command` to raise `paramiko.ssh_exception.SSHException`. My test setup consistently passes, even when debug output confirms the mock function is called and explicitly raises the `SSHException`.

This suggests that the `SSHException` is being caught and handled internally within `pyinfra` before it propagates to the `pytest.raises` block, or there's a more complex interaction with `MagicMock` or `gevent` that prevents the exception from being observed by the test framework.

To effectively write an acceptance test that *fails* on the unfixed code as described, I need clarification on the following:

1.  **Exact Exception Propagation Path:** Could you provide a more detailed call stack, specifically including any `try...except` blocks in `pyinfra`'s code that might be catching `paramiko.ssh_exception.SSHException` between `host.run_shell_command` (or `execute_command_with_sudo_retry`) and the point where it's expected to crash the pyinfra operation?
2.  **Mocking `paramiko`:** Is there a recommended way to mock `paramiko`'s SSH session or client objects within `pyinfra` tests to ensure `SSHException`s are raised and propagate as expected without being internally handled or converted to a different error state?
3.  **Expected Failure Mode:** When the `SSHException` occurs, is `pyinfra` expected to completely crash and exit, or does it transition to a specific error state that a test can assert (e.g., `host.results` showing a failure, or a specific `PyinfraError` being raised)? The bug report implies a full crash, but my tests cannot observe it.

Without understanding why the `SSHException` is not propagating and causing the test to fail, I cannot reliably create an acceptance test that demonstrates the unfixed bug's behavior.
