#!/usr/bin/env python3
"""Offline gate: a sealed agent diff is admitted only when every check passes.

Nothing here mints a credential or contacts the network. A publisher, if one is
added later, must run only after verify() returns a receipt.

Checks, in order. The first failure exits non-zero with a JSON reason:
  DIFF_TOO_LARGE, BINARY_FILE, SYMLINK, MALFORMED_DIFF,
  PROTECTED_PATH, HIDDEN_TEST, TASK_INVALID, DIFF_HASH,
  EVIDENCE_HASH, EVIDENCE_INVALID, VERDICT, STALE_BASE,
  EXISTING_TEST, OUT_OF_SCOPE, DIFF_POLICY, UNSUPPORTED_CHANGE.
"""
import argparse
import hashlib
import hmac
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lib.lc0util import diff_policy  # noqa: E402

MAX_DIFF_BYTES = 100_000
_ALLOWED_MODES = {"100644", "100755"}
_MODE = re.compile(r"(?m)^(?:(?:new|old|deleted) file mode|(?:new|old) mode) ([0-7]{6})\b")
_INDEX_MODE = re.compile(r"(?m)^index [0-9a-f]+\.\.[0-9a-f]+ ([0-7]{6})\b")
_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_REF = re.compile(r"[A-Za-z0-9._/-]+")


class GateFailure(Exception):
    def __init__(self, reason, detail=""):
        super().__init__(reason)
        self.reason = reason
        self.detail = detail


def _clip(text, n=400):
    text = (text or "").strip()
    return text if len(text) <= n else text[:n] + "..."


def _emit(obj):
    sys.stdout.write(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _eq(left, right) -> bool:
    if not isinstance(left, str) or not isinstance(right, str) or len(left) != len(right):
        return False
    return hmac.compare_digest(left, right)


def _load_json(path: Path, reason: str):
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise GateFailure(reason, f"{path.name}: {exc}") from exc


def _task_key(owner, repo, number, body) -> str:
    digest = _sha((body or "").encode("utf-8"))
    return f"{owner}/{repo}#{number}:{digest}"


def _check_task(task):
    for key in ("owner", "repo", "issue_number", "body", "base_sha", "task_key"):
        if key not in task:
            raise GateFailure("TASK_INVALID", f"missing {key}")
    number = task["issue_number"]
    if not isinstance(number, int) or isinstance(number, bool) or number < 1:
        raise GateFailure("TASK_INVALID", "issue_number must be a positive integer")
    if not isinstance(task["owner"], str) or not isinstance(task["repo"], str):
        raise GateFailure("TASK_INVALID", "owner and repo must be strings")
    if not _HEX40.fullmatch(str(task["base_sha"])):
        raise GateFailure("TASK_INVALID", "base_sha must be 40 hex characters")
    expect = _task_key(task["owner"], task["repo"], number, task.get("body") or "")
    if not _eq(str(task["task_key"]), expect):
        raise GateFailure("TASK_INVALID", "task_key does not match the issue body")
    ref = task.get("base_ref") or "main"
    if not isinstance(ref, str) or not _REF.fullmatch(ref) or ref.startswith("/") or ".." in ref.split("/"):
        raise GateFailure("TASK_INVALID", "bad base_ref")
    return ref


def _modes(text: str):
    found = [m.group(1) for m in _MODE.finditer(text)]
    found += [m.group(1) for m in _INDEX_MODE.finditer(text)]
    for mode in found:
        if mode == "120000":
            raise GateFailure("SYMLINK", "diff contains file mode 120000")
        if mode not in _ALLOWED_MODES:
            raise GateFailure("UNSUPPORTED_CHANGE", f"file mode {mode}")


def _split_header(rest: str):
    def take(src):
        if src.startswith('"'):
            i = 1
            while i < len(src):
                if src[i] == "\\":
                    i += 2
                    continue
                if src[i] == '"':
                    return src[1:i], src[i + 1:].lstrip()
                i += 1
            raise GateFailure("MALFORMED_DIFF", "unterminated quoted path")
        cut = src.find(" ")
        if cut < 0:
            return src, ""
        return src[:cut], src[cut + 1:]

    left, rest = take(rest)
    right, extra = take(rest)
    if extra.strip() or not left.startswith("a/") or not right.startswith("b/"):
        raise GateFailure("MALFORMED_DIFF", "diff header is not 'a/<path> b/<path>'")
    return left[2:], right[2:]


def _path_reason(path: str):
    if path.startswith("/") or "\\" in path:
        raise GateFailure("MALFORMED_DIFF", f"refusing path {path}")
    parts = path.split("/")
    if any(part in ("", ".", "..") for part in parts):
        raise GateFailure("MALFORMED_DIFF", f"refusing path {path}")
    if parts[0] in (".github", ".git") or parts[-1] == "CODEOWNERS":
        return "PROTECTED_PATH"
    if "hidden_tests" in parts or "locked_p2p" in parts:
        return "HIDDEN_TEST"
    return None


def _check_paths(text: str):
    headers = [line[len("diff --git "):] for line in text.splitlines() if line.startswith("diff --git ")]
    if not headers:
        raise GateFailure("MALFORMED_DIFF", "not a unified diff")
    reason = None
    for header in headers:
        for path in _split_header(header):
            hit = _path_reason(path)
            if hit and reason is None:
                reason = (hit, path)
    if reason:
        raise GateFailure(reason[0], reason[1])


def _screen_diff(data: bytes) -> str:
    if len(data) > MAX_DIFF_BYTES:
        raise GateFailure("DIFF_TOO_LARGE", f"{len(data)} bytes exceeds {MAX_DIFF_BYTES}")
    if b"\0" in data or b"\nGIT binary patch\n" in data or data.startswith(b"GIT binary patch\n") or b"\nBinary files " in data:
        raise GateFailure("BINARY_FILE", "binary diff")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise GateFailure("MALFORMED_DIFF", "diff is not utf-8 text") from exc
    _modes(text)
    _check_paths(text)
    return text


def _resolve(manifest_path: Path, key: str) -> Path:
    if not isinstance(key, str) or key.count("/") != 1:
        raise GateFailure("EVIDENCE_HASH", f"bad evidence path {key!r}")
    kind, name = key.split("/", 1)
    run_dir = manifest_path.parent
    if kind == "run":
        return run_dir / name
    if kind == "evals" and run_dir.parent.name == "runs":
        return run_dir.parent.parent / "evals" / run_dir.name / name
    raise GateFailure("EVIDENCE_HASH", f"cannot resolve {key}")


def _check_evidence(manifest_path: Path, manifest: dict, diff: bytes, task_base: str):
    digest = _sha(diff)
    recorded = manifest.get("git_diff_base_final_sha256")
    sealed_diff = (manifest.get("inputs") or {}).get("run/final.diff") if isinstance(manifest.get("inputs"), dict) else None
    if not _eq(recorded, digest) or not _eq(sealed_diff, digest):
        raise GateFailure("DIFF_HASH", "diff sha256 does not match the sealed evidence")
    if not isinstance(manifest.get("inputs"), dict) or not isinstance(manifest.get("outputs"), dict):
        raise GateFailure("EVIDENCE_INVALID", "manifest inputs/outputs missing")
    if "run/report.json" not in manifest["outputs"]:
        raise GateFailure("EVIDENCE_HASH", "verdict report is not sealed")
    for key, expect in {**manifest["inputs"], **manifest["outputs"]}.items():
        path = _resolve(manifest_path, key)
        if not path.is_file():
            raise GateFailure("EVIDENCE_HASH", f"missing {key}")
        if not _eq(_sha(path.read_bytes()), expect):
            raise GateFailure("EVIDENCE_HASH", f"sha256 mismatch {key}")
    report = _load_json(_resolve(manifest_path, "run/report.json"), "EVIDENCE_INVALID")
    verdict = report.get("lc0_verdict")
    if verdict != "PASS" or ("decision" in report and report.get("decision") != "PASS"):
        raise GateFailure("VERDICT", f"lc0_verdict is {verdict!r}")
    if not _eq(str(manifest.get("base_sha") or ""), task_base):
        raise GateFailure("STALE_BASE", "evidence base_sha does not match the task")
    agent_path = _resolve(manifest_path, "run/agent_result.json")
    if agent_path.is_file():
        agent = _load_json(agent_path, "EVIDENCE_INVALID")
        agent_base = agent.get("base_sha")
        if agent_base and not _eq(str(agent_base), task_base):
            raise GateFailure("STALE_BASE", "agent_result base_sha does not match the task")
    return digest, verdict


def _tip(repo: Path, ref: str) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--verify", "--end-of-options", f"refs/heads/{ref}"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        raise GateFailure("STALE_BASE", f"local branch {ref} has no tip")
    tip = proc.stdout.strip()
    if not _HEX40.fullmatch(tip):
        raise GateFailure("STALE_BASE", f"local branch {ref} tip is not a commit")
    return tip


def _policy_reason(violations) -> str:
    if any(v.startswith("pre-existing test") for v in violations):
        return "EXISTING_TEST"
    if any("UNSUPPORTED_CHANGE_TYPE" in v for v in violations):
        return "SYMLINK"
    if any(v.startswith("outside task scope") or v.startswith("NEW_FILE_OUT_OF_SCOPE") for v in violations):
        return "OUT_OF_SCOPE"
    if any(v.startswith("protected path") for v in violations):
        return "PROTECTED_PATH"
    return "DIFF_POLICY"


def _git_env():
    env = os.environ.copy()
    env.update({
        "GIT_AUTHOR_NAME": "codefactory-gate",
        "GIT_AUTHOR_EMAIL": "gate@codefactory.local",
        "GIT_COMMITTER_NAME": "codefactory-gate",
        "GIT_COMMITTER_EMAIL": "gate@codefactory.local",
        "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z",
        "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z",
    })
    return env


def _apply_and_policy(repo: Path, base: str, diff_path: Path, policy: Path) -> str:
    wt = Path(tempfile.mkdtemp(prefix="cf-gate-"))
    hooks = Path(tempfile.mkdtemp(prefix="cf-hooks-"))
    try:
        add = subprocess.run(
            ["git", "-C", str(repo), "worktree", "add", "--detach", str(wt), base],
            capture_output=True, text=True,
        )
        if add.returncode != 0:
            raise GateFailure("STALE_BASE", _clip(add.stderr) or "cannot check out base")
        for args in (["apply", "--check", str(diff_path)], ["apply", "--index", str(diff_path)]):
            proc = subprocess.run(["git", "-C", str(wt), *args], capture_output=True, text=True)
            if proc.returncode != 0:
                raise GateFailure("MALFORMED_DIFF", _clip(proc.stderr) or "git apply --check failed")
        listed = subprocess.run(["git", "-C", str(wt), "ls-files", "-s"], capture_output=True, text=True, check=True)
        for line in listed.stdout.splitlines():
            mode, _, _, name = line.split(None, 3)
            if mode == "120000":
                raise GateFailure("SYMLINK", name)
            if mode not in _ALLOWED_MODES:
                raise GateFailure("UNSUPPORTED_CHANGE", f"{mode} {name}")
        committed = subprocess.run(
            ["git", "-C", str(wt), "-c", "commit.gpgsign=false", "-c", f"core.hooksPath={hooks}",
             "commit", "-qm", "gate: check diff"],
            capture_output=True, text=True, env=_git_env(),
        )
        if committed.returncode != 0:
            raise GateFailure("MALFORMED_DIFF", _clip(committed.stderr) or "nothing to commit")
        head = subprocess.run(
            ["git", "-C", str(wt), "rev-parse", "HEAD"], capture_output=True, text=True, check=True,
        ).stdout.strip()
        try:
            result = diff_policy(str(repo), base, head, str(policy))
        except Exception as exc:
            raise GateFailure("DIFF_POLICY", _clip(f"{type(exc).__name__}: {exc}")) from exc
        violations = result.get("violations") or []
        if result.get("result") != "OK":
            raise GateFailure(_policy_reason(violations), _clip("; ".join(violations)))
        return head
    finally:
        subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", str(wt)], capture_output=True)
        shutil.rmtree(wt, ignore_errors=True)
        shutil.rmtree(hooks, ignore_errors=True)


def verify(task_path, diff_path, evidence_path, repo, policy) -> dict:
    task_path, diff_path = Path(task_path), Path(diff_path)
    evidence_path, repo, policy = Path(evidence_path), Path(repo), Path(policy)
    task = _load_json(task_path, "TASK_INVALID")
    ref = _check_task(task)
    if not diff_path.is_file():
        raise GateFailure("MALFORMED_DIFF", "diff file is missing")
    diff = diff_path.read_bytes()
    _screen_diff(diff)
    manifest = _load_json(evidence_path, "EVIDENCE_INVALID")
    digest, verdict = _check_evidence(evidence_path, manifest, diff, task["base_sha"])
    tip = _tip(repo, ref)
    if not _eq(tip, task["base_sha"]):
        raise GateFailure("STALE_BASE", f"branch {ref} is {tip}, task base is {task['base_sha']}")
    if not policy.is_file():
        raise GateFailure("DIFF_POLICY", f"policy not found: {policy}")
    head = _apply_and_policy(repo, task["base_sha"], diff_path, policy)
    return {
        "ok": True,
        "reason": "PASS",
        "task_key": task["task_key"],
        "base_sha": task["base_sha"],
        "diff_sha256": digest,
        "verdict": verdict,
        "policy": "OK",
        "checked_sha": head,
        "published": False,
    }


def _write_receipt(path: Path, receipt: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    os.replace(tmp, path)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="gate")
    sub = parser.add_subparsers(dest="cmd", required=True)
    verify_cmd = sub.add_parser("verify")
    verify_cmd.add_argument("--task", required=True)
    verify_cmd.add_argument("--diff", required=True)
    verify_cmd.add_argument("--evidence", required=True)
    verify_cmd.add_argument("--repo", required=True)
    verify_cmd.add_argument("--policy", default=str(ROOT / "task" / "diff_policy.json"))
    verify_cmd.add_argument("--receipt")
    args = parser.parse_args(argv)
    try:
        receipt = verify(args.task, args.diff, args.evidence, args.repo, args.policy)
    except GateFailure as exc:
        _emit({"ok": False, "reason": exc.reason, "detail": exc.detail})
        return 1
    _emit(receipt)
    if args.receipt:
        _write_receipt(Path(args.receipt), receipt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
