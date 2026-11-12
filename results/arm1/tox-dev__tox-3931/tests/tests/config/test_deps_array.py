import pytest
import subprocess
import sys
import textwrap
from pathlib import Path

@pytest.fixture
def create_test_project(tmp_path: Path):
    project_path = tmp_path / "my_project"
    project_path.mkdir()

    # Create a minimal pyproject.toml to satisfy tox
    (project_path / "pyproject.toml").write_text(textwrap.dedent(f"""
        [project]
        name = "my-package"
        version = "0.1.0"
    """))

    # Create a tox.toml with deps as an array, similar to documentation
    (project_path / "tox.toml").write_text(textwrap.dedent(f"""
        [tox]
        min_version = "4.0"
        env_list = ["py"]

        [testenv:py]
        package = "skip"
        deps =
            pip >= 23.0
            -r requirements.txt
        commands =
            python -c "print('Hello from tox!')"
    """))

    # Create a dummy requirements.txt
    (project_path / "requirements.txt").write_text("setuptools")

    return project_path

def test_tox_with_array_deps_succeeds(create_test_project: Path):
    project_path = create_test_project
    print(f"Running tox in: {project_path}")
    result = subprocess.run(
        [sys.executable, "-m", "tox", "-c", str(project_path / "tox.toml"), "-e", "py", "--not-portable"],
        capture_output=True,
        text=True,
        cwd=project_path,
    )

    print("Tox stdout:")
    print(result.stdout)
    print("Tox stderr:")
    print(result.stderr)

    assert result.returncode == 0, f"Tox failed with exit code {result.returncode}. Output: {result.stdout}\n{result.stderr}"
    assert "Hello from tox!" in result.stdout or "Hello from tox!" in result.stderr
    assert "DEPRECATION" not in result.stderr.upper() # Check for deprecation warnings that might cause issues later

# Edge case: deps as empty array
@pytest.fixture
def create_test_project_empty_deps(tmp_path: Path):
    project_path = tmp_path / "my_project_empty_deps"
    project_path.mkdir()

    (project_path / "pyproject.toml").write_text(textwrap.dedent(f"""
        [project]
        name = "my-package"
        version = "0.1.0"
    """))

    (project_path / "tox.toml").write_text(textwrap.dedent(f"""
        [tox]
        min_version = "4.0"
        env_list = ["py"]

        [testenv:py]
        package = "skip"
        deps =
        commands =
            python -c "print('Hello from tox empty deps!')"
    """))
    return project_path

def test_tox_with_empty_array_deps_succeeds(create_test_project_empty_deps: Path):
    project_path = create_test_project_empty_deps
    print(f"Running tox in: {project_path}")
    result = subprocess.run(
        [sys.executable, "-m", "tox", "-c", str(project_path / "tox.toml"), "-e", "py", "--not-portable"],
        capture_output=True,
        text=True,
        cwd=project_path,
    )

    print("Tox stdout:")
    print(result.stdout)
    print("Tox stderr:")
    print(result.stderr)

    assert result.returncode == 0, f"Tox failed with exit code {result.returncode}. Output: {result.stdout}\n{result.stderr}"
    assert "Hello from tox empty deps!" in result.stdout or "Hello from tox empty deps!" in result.stderr
    assert "DEPRECATION" not in result.stderr.upper()

