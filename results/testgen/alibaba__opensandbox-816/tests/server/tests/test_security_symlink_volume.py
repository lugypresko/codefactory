import pytest
import os
import tempfile
import shutil

# Assuming these imports based on the project structure
from opensandbox_server.services.docker import DockerSandboxService
from opensandbox_server.config import AppConfig, StorageConfig, RuntimeConfig, ServerConfig, LogConfig, RenewIntentConfig, DockerConfig
from opensandbox_server.api.schema import Volume, Host
from fastapi.exceptions import HTTPException

@pytest.fixture
def setup_symlink_test_env():
    # Create a temporary directory for our whitelist
    tmp_dir = tempfile.mkdtemp()
    whitelisted_dir = os.path.join(tmp_dir, "whitelisted_mount")
    os.makedirs(whitelisted_dir)

    # Create a symbolic link inside the whitelisted directory pointing to '/'
    symlink_path = os.path.join(whitelisted_dir, "link_to_root")
    os.symlink("/", symlink_path)

    yield tmp_dir, whitelisted_dir, symlink_path

    # Clean up
    shutil.rmtree(tmp_dir)

def test_symlink_bypass_host_volume_validation(setup_symlink_test_env):
    tmp_dir, whitelisted_dir, symlink_path = setup_symlink_test_env

    # Setup AppConfig with the whitelisted path
    runtime_config = RuntimeConfig(type="docker", execd_image="execd:latest") # DockerSandboxService expects runtime.type
    storage_config = StorageConfig(allowed_host_paths=[whitelisted_dir])
    app_config = AppConfig(runtime=runtime_config, storage=storage_config, server=ServerConfig(), log=LogConfig(), renew_intent=RenewIntentConfig(), docker=DockerConfig()) # telemetry is optional

    # Instantiate DockerSandboxService with the app config
    docker_service = DockerSandboxService(config=app_config)

    # Create a Volume object that uses the symbolic link
    host_volume = Host(path=symlink_path)
    volume = Volume(name="test-volume", mount_path="/mnt/test", host=host_volume)

    # The current, unfixed code *will not* raise an HTTPException for this scenario.
    # Therefore, to make the test FAIL on unfixed code, we assert that an HTTPException *is* raised.
    # When the fix is implemented, an HTTPException *will* be raised, and the test will PASS.
    with pytest.raises(HTTPException) as excinfo:
        docker_service._validate_host_volume(volume, app_config.storage.allowed_host_paths)

    # Assert that the HTTPException has the expected status code and a relevant message
    assert excinfo.value.status_code == 400
    # The message might vary slightly after a fix, but "invalid host path" or "forbidden path" is a reasonable expectation.
    assert "invalid host path" in excinfo.value.detail.get("message", "").lower() or \
           "forbidden path" in excinfo.value.detail.get("message", "").lower()
