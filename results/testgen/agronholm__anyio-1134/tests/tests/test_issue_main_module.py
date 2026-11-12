import subprocess
import sys
import os
import pytest

def test_main_module_in_worker_process():
    # Construct the command to run the entry point runner script
    # We need to ensure the Python interpreter is the same as the test runner
    command = [sys.executable, "/tmp/entrypoint_runner.py"]
    
    # Execute the command as a subprocess
    # Capture stdout and stderr to check for the error
    result = subprocess.run(command, capture_output=True, text=True, check=False, env=os.environ.copy())
    
    # Print output for debugging if the test fails
    print("\n--- Subprocess stdout ---")
    print(result.stdout)
    print("\n--- Subprocess stderr ---")
    print(result.stderr)

    # The expected error message indicating that __main__ was not set up
    expected_error = "ModuleNotFoundError: No module named '__main__'"
    
    # Assert that the expected error is present in either stdout or stderr
    # The original issue shows the error in a traceback, so it could be in stderr.
    # However, because my `main` function prints the error to stdout, it might appear there too.
    if not (expected_error in result.stdout or expected_error in result.stderr):
        pytest.fail(
            f"Expected \"{expected_error}\" not found in subprocess output. "
            f"Stdout: {result.stdout}\nStderr: {result.stderr}"
        )

    # Also, assert that the subprocess exited with a non-zero status code, indicating an error
    if result.returncode == 0:
        pytest.fail(f"Subprocess unexpectedly succeeded with return code {result.returncode}. Output: {result.stdout} {result.stderr}")

