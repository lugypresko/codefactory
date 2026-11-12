"""Throw-away copy of the package with a deterministic task repo, a committed 'good' solution (tests/fixtures/
solution.patch) and a fixture run, so integration tests never depend on a live agent run in work/."""
import json, os, shutil, subprocess, tempfile
from pathlib import Path

ID = ["-c", "user.name=lc0", "-c", "user.email=lc0@local"]
DATE = {"GIT_AUTHOR_DATE": "2026-01-01T00:00:00+00:00", "GIT_COMMITTER_DATE": "2026-01-01T00:00:00+00:00"}


class Scratch:
    def __init__(self, root):
        self.root = Path(root).resolve(); self.tmp = Path(tempfile.mkdtemp(prefix="lc0-scratch-"))
        self.pkg = self.tmp / "pkg"
        shutil.copytree(self.root, self.pkg, ignore=shutil.ignore_patterns(".venv", "work", "__pycache__", "evidence"))
        self.work = self.pkg / "work"; self.repo = self.work / "repo"; self.repo.mkdir(parents=True)
        shutil.copytree(self.root / "task" / "repo", self.repo, dirs_exist_ok=True)
        self.git("init", "-q", "-b", "main"); self.git("add", "-A"); self.git(*ID, "commit", "-q", "-m", "base: cart library", env=DATE)
        self.base = self.git("rev-parse", "HEAD")
        self.good = self.variant("good", lambda r: subprocess.run(["git", "apply", "--whitespace=nowarn", str(self.root / "tests/fixtures/solution.patch")],
                                                                   cwd=r, check=True), start=self.base)
        img = subprocess.run(["docker", "image", "inspect", os.environ.get("LC0_IMAGE", "lc0-env:1"), "--format", "{{.Id}}"],
                             capture_output=True, text=True).stdout.strip()
        (self.work / "environment.json").write_text(json.dumps({"image_id": img, "base_commit_sha": self.base}))
        self.env = dict(os.environ, LC0_WORK=str(self.work))

    def git(self, *a, env=None):
        return subprocess.run(["git", "-C", str(self.repo), *a], capture_output=True, text=True, check=True,
                              env=dict(os.environ, **(env or {}))).stdout.strip()

    def variant(self, name, mutate, start=None):
        """Commit `mutate(repo_path)` on top of `start` (default: the good solution) on its own branch; return SHA."""
        self.git("checkout", "-q", "-B", f"v/{name}", start or self.good); mutate(self.repo)
        self.git("add", "-A"); self.git(*ID, "commit", "-q", "--allow-empty", "-m", name)
        sha = self.git("rev-parse", "HEAD"); self.git("checkout", "-q", "main"); return sha

    def evaluate(self, sha):
        out = self.tmp / "ev.json"
        p = subprocess.run([str(self.pkg / "evaluate.sh"), sha, str(out)], capture_output=True, text=True, env=self.env)
        d = json.loads(out.read_text()) if out.exists() else {"decision": "NO_REPORT", "reason": p.stderr[-300:]}
        return d

    def fixture_run(self, run_id="fixture"):
        """Install the committed fixture run (agent_result + trajectory of run A) pointing at the good solution SHA."""
        rd = self.work / "runs" / run_id; rd.mkdir(parents=True, exist_ok=True)
        shutil.copy(self.root / "tests/fixtures/run/trajectory.json", rd / "trajectory.json")
        a = json.loads((self.root / "tests/fixtures/run/agent_result.json").read_text())
        a.update(run_id=run_id, base_sha=self.base, final_sha=self.good,
                 paths={"trajectory": str(rd / "trajectory.json"), "run_dir": str(rd)})
        (rd / "agent_result.json").write_text(json.dumps(a, indent=2))
        (rd / "final.diff").write_text(self.git("diff", self.base, self.good) + "\n")
        (rd / "config.yaml").write_text("fixture: true\n")
        return rd

    def close(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
