import os
import time
import os

import pytest
from plumbum import local

from copier._main import run_copy
from copier._vcs import clone

from .helpers import build_file_tree, git, DATA

@pytest.fixture
def template_path(tmp_path: Path) -> Path:
    template = tmp_path / "template"
    build_file_tree(
        {
            template / "copier.yml": "favorite_app: Copier",
@pytest.fixture
def template_path(tmp_path: Path) -> Path:
    # 1. Create a local Git repository
    template_repo = tmp_path / "template_repo"
    build_file_tree(
        {
            template_repo / "copier.yml": "favorite_app: Copier",
            template_repo / "fav.txt.jinja": "{{ favorite_app }}",
            template_repo
            / "{{ _copier_conf.answers_file }}.jinja": "{{ _copier_answers|to_nice_yaml }}",
        }
    )
    _git = git["-C", template_repo]
    _git("init")
    _git("add", "-A")
    _git("commit", "-m", "Initial commit")
    _git("tag", "v1")

    # 4. Create a bundle file from this v1 tagged repo
    template_bundle = tmp_path / "template.bundle"
    _git("bundle", "create", template_bundle, "v1")

    # 5. Return the path to this bundle file
    return template_bundle
        git("add", "-A")
        git("commit", "-m", "Initial subproject commit")
    return subproject

def test_tmp_clone_dir_cleaned_on_interruption(
    tmp_path: Path, subproject_path: Path, template_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Set a custom temporary directory for the test
    test_tmpdir = tmp_path / "my_temp_dir"
    test_tmpdir.mkdir()
    monkeypatch.setattr("tempfile.tempdir", str(test_tmpdir))

    # Update template to ensure a clone operation happens
    build_file_tree({template_path / "new_file.txt": "content"})
    _git = git["-C", template_path]
    # We expect this to fail and leave a temporary directory
    command = [
        "python",
        "-m",
        "copier",
        "update",
        "--vcs-ref", "v2",
        str(subproject_path),
    ]
    
    env = os.environ.copy()
    env["TMPDIR"] = str(test_tmpdir)
    process = subprocess.Popen(command, cwd=str(subproject_path), env=env)
    
    # Give it a moment to start cloning, then kill it
    time.sleep(5) 
    process.kill()
    process.wait(timeout=5) # Wait for the process to terminate




    # Check for temporary directories left behind
    # The actual temporary directory will be created by copier._vcs.clone in the mocked tempfile.tempdir
    # It will look something like <test_tmpdir>/copier_XXXXXX_clone_YYYYYY
    lingering_tmp_dirs = [d for d in test_tmpdir.iterdir() if d.is_dir() and "copier" in d.name and "clone" in d.name]

    # This test *expects* to fail on the unfixed code, meaning it expects lingering_tmp_dirs to NOT be empty.
    # Therefore, the assertion should be:
    assert len(lingering_tmp_dirs) > 0, f"Expected lingering temporary directories, but found none in {test_tmpdir}. Found: {[d.name for d in test_tmpdir.iterdir()]}"

    # Optionally, to ensure the test passes *after* a fix, the assertion would become:
    # assert not lingering_tmp_dirs, f"Found lingering temporary directories: {lingering_tmp_dirs}"

# To make this test fail on the unfixed code, we assert that lingering_tmp_dirs is NOT empty.
# Once the fix is applied, lingering_tmp_dirs should be empty, and the assertion will become:
# assert not lingering_tmp_dirs
