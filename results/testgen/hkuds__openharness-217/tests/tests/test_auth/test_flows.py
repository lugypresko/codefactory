import pytest
import unittest.mock as mock
import platform
import subprocess
import os

from src.openharness.auth.flows import DeviceCodeFlow

# Helper function to simulate a Windows environment
@pytest.fixture
def mock_windows_platform():
    # Create a dummy os.startfile for patching on non-Windows systems
    # This is necessary because os.startfile doesn't exist on Linux/macOS
    # and `mock.patch` requires the target attribute to exist.
    if not hasattr(os, 'startfile'):
        os.startfile = mock.Mock()

    with mock.patch("platform.system", return_value="Windows"):
        yield

# Test cases for the shell injection vulnerability
def test_try_open_browser_windows_shell_injection(mock_windows_platform):
    malicious_url = "https://example.com&calc.exe"
    
    # Mock subprocess.Popen to assert its arguments
    with mock.patch("subprocess.Popen") as mock_popen:
        flow = DeviceCodeFlow()
        flow._try_open_browser(malicious_url)

        # Assert that subprocess.Popen was called with shell=True and the malicious URL
        mock_popen.assert_called_once()
        args, kwargs = mock_popen.call_args
        assert kwargs.get("shell") is True
        assert ["start", "", malicious_url] == args[0]

def test_try_open_browser_windows_file_scheme_rejected(mock_windows_platform):
    file_url = "file:///C:/Windows/system32/cmd.exe"

    with mock.patch("subprocess.Popen") as mock_popen:
        with mock.patch("os.startfile") as mock_startfile:
            flow = DeviceCodeFlow()
            flow._try_open_browser(file_url)

            # Assert that neither Popen nor startfile were called for file:// scheme
            mock_popen.assert_not_called()
            mock_startfile.assert_not_called()

def test_try_open_browser_windows_javascript_scheme_rejected(mock_windows_platform):
    javascript_url = "javascript:alert(1)"

    with mock.patch("subprocess.Popen") as mock_popen:
        with mock.patch("os.startfile") as mock_startfile:
            flow = DeviceCodeFlow()
            flow._try_open_browser(javascript_url)

            # Assert that neither Popen nor startfile were called for javascript: scheme
            mock_popen.assert_not_called()
            mock_startfile.assert_not_called()

def test_try_open_browser_non_windows_safe():
    # Ensure that on non-Windows systems, shell=False is used
    with mock.patch("platform.system", return_value="Linux"):
        with mock.patch("subprocess.Popen") as mock_popen:
            safe_url = "https://example.com/login/device?param=value"
            flow = DeviceCodeFlow()
            flow._try_open_browser(safe_url)
            
            mock_popen.assert_called_once()
            args, kwargs = mock_popen.call_args
            assert kwargs.get('shell') is not True
            assert args[0][0] in ["xdg-open", "gnome-open", "kde-open", "wsl-browser"]
            assert safe_url == args[0][-1]

def test_try_open_browser_windows_http_scheme_safe_after_fix(mock_windows_platform):
    # This test will initially fail on the unfixed code because it expects os.startfile
    # to be called. On the unfixed code, subprocess.Popen with shell=True will be called.
    # After the fix, this test should pass.
    safe_url = "https://github.com/login/device"
    
    with mock.patch("subprocess.Popen") as mock_popen:
        with mock.patch("os.startfile") as mock_startfile:
            flow = DeviceCodeFlow()
            flow._try_open_browser(safe_url)

            # After fix, os.startfile should be called, and subprocess.Popen should not
            mock_startfile.assert_called_once_with(safe_url)
            mock_popen.assert_not_called()
