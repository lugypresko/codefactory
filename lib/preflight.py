"""Amendment 2 preflight: start the test-writer sandbox from the exact mini config and run `python -m pytest --version`."""
import sys, yaml
from minisweagent.environments.docker import DockerEnvironment
cfg = yaml.safe_load(open(sys.argv[1]))["environment"]; cfg.pop("environment_class", None)
env = DockerEnvironment(**cfg)
out = env.execute({"command": "command -v python; python -m pytest --version"})
print("interpreter:", cfg.get("interpreter")); print(out["output"].strip()); print("returncode:", out["returncode"])
sys.exit(0 if out["returncode"] == 0 and "pytest" in out["output"] else 1)
