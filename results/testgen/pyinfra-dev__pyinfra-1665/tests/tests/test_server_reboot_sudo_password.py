import pytest
from unittest.mock import MagicMock

from pyinfra.connectors.util import remove_any_sudo_askpass_file
from pyinfra.api.command import StringCommand, QuoteString # Import these to avoid mocking issues

# Paramiko's SSHException is often imported as paramiko.ssh_exception.SSHException
# or just SSHException if paramiko is globally available.
# To be safe, we'll try to import it and define a fallback.
try:
    from paramiko.ssh_exception import SSHException
    PARAMIKO_SSH_EXCEPTION_LOADED = True
except ImportError:
    class SSHException(Exception):
        pass
    PARAMIKO_SSH_EXCEPTION_LOADED = False

def test_remove_sudo_askpass_file_crashes_after_reboot_with_sudo_password():
    # Mock a Host object
    mock_host = MagicMock()

    # Ensure mock_host.connector_data is a dictionary, not a MagicMock object
    mock_host.connector_data = {}
    askpass_path = "/tmp/pyinfra-sudo-askpass-mock"
    mock_host.connector_data["sudo_askpass_path"] = askpass_path

    # Simulate the host having _sudo_password set
    mock_host.data.sudo = True
    mock_host.data.sudo_password = "mysecretpassword"
    mock_host.sudo_password = "mysecretpassword" # Also set directly if accessed

    def mock_run_shell_command_side_effect(command, **kwargs):
        print(f"DEBUG: mock_run_shell_command called with command: {command!r}, type: {type(command)}")
        if isinstance(command, StringCommand) and "rm -f" in str(command):
            print("DEBUG: Raising SSHException from mock_run_shell_command")
            raise SSHException("SSH session not active")
        return 0, "" # Default success for other commands

    mock_host.run_shell_command.side_effect = mock_run_shell_command_side_effect

    print(f"DEBUG: mock_host.connector_data: {mock_host.connector_data}")
    print(f"DEBUG: sudo_askpass_path in connector_data: {mock_host.connector_data.get('sudo_askpass_path')}")
    print(f"DEBUG: Type of SSHException in test: {type(SSHException)}")
    print(f"DEBUG: Paramiko SSHException loaded: {PARAMIKO_SSH_EXCEPTION_LOADED}")

    # We expect SSHException to be raised when remove_any_sudo_askpass_file is called
    with pytest.raises(SSHException) as exc_info:
        remove_any_sudo_askpass_file(mock_host)

    print(f"DEBUG: mock_host.run_shell_command.called: {mock_host.run_shell_command.called}")

    assert "SSH session not active" in str(exc_info.value)
    # Ensure run_shell_command was called with the correct arguments
    mock_host.run_shell_command.assert_called_once_with(
        StringCommand("rm", "-f", QuoteString(askpass_path))
    )

