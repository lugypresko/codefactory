"""Attack tests for the offline gate. Written from the gate rules before the implementation.

A sealed PASS verdict must not launder a bad diff. The gate is pure offline: no token,
no network, no pull request.
"""
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
POLICY = ROOT / "task" / "diff_policy.json"
SRC = ROOT / "task" / "repo"
BODY = "Add sku_count to Cart.\n"
OWNER, REPO_NAME, NUMBER = "acme", "widget", 7


def _git(repo, *args, env=None):
    e = os.environ.copy()
    e.update({
        "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
        "GIT_AUTHOR_DATE": "2026-01-01T00:00:00Z",
        "GIT_COMMITTER_DATE": "2026-01-01T00:00:00Z",
    })
    if env:
        e.update(env)
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True, env=e)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _task_key(body: str = BODY) -> str:
    return f"{OWNER}/{REPO_NAME}#{NUMBER}:{_sha(body.encode('utf-8'))}"


@pytest.fixture
def product(tmp_path):
    repo = tmp_path / "repo"
    shutil.copytree(SRC, repo)
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True, capture_output=True)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "base")
    base = _git(repo, "rev-parse", "HEAD").stdout.strip()
    return repo, base


def _capture(repo: Path, mutate) -> bytes:
    mutate(repo)
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True, capture_output=True)
    diff = subprocess.run(
        ["git", "-C", str(repo), "diff", "--cached", "--binary"],
        check=True, capture_output=True,
    ).stdout
    subprocess.run(["git", "-C", str(repo), "reset", "-q", "--hard"], check=True)
    subprocess.run(["git", "-C", str(repo), "clean", "-fdq"], check=True)
    assert diff, "fixture produced an empty diff"
    return diff


def _seal(tmp: Path, diff: bytes, base: str, verdict: str = "PASS") -> Path:
    run = tmp / "runs" / "issue"
    ev = tmp / "evals" / "issue"
    run.mkdir(parents=True)
    ev.mkdir(parents=True)
    files = {
        "trajectory.json": b"{}\n",
        "config.yaml": b"fixture: true\n",
        "agent_result.json": json.dumps({
            "base_sha": base, "final_sha": None, "agent_status": "SUBMITTED",
        }).encode(),
        "final.diff": diff,
        "fault.json": b"{}\n",
        "agent_stdout.log": b"",
    }
    for name, data in files.items():
        (run / name).write_bytes(data)
    report = {
        "lc0_verdict": verdict,
        "decision": verdict,
        "delivery_verdict": verdict,
        "base_sha": base,
    }
    (run / "report.json").write_text(json.dumps(report) + "\n")
    (run / "report.md").write_text(f"verdict {verdict}\n")
    for name in ("baseline.json", "eval_1.json", "eval_2.json"):
        (ev / name).write_text("{}\n")

    def file_sha(path: Path) -> str:
        return _sha(path.read_bytes())

    manifest = {
        "run_id": "issue",
        "inputs": {f"run/{name}": file_sha(run / name) for name in files},
        "outputs": {
            "run/report.json": file_sha(run / "report.json"),
            "run/report.md": file_sha(run / "report.md"),
            "evals/baseline.json": file_sha(ev / "baseline.json"),
            "evals/eval_1.json": file_sha(ev / "eval_1.json"),
            "evals/eval_2.json": file_sha(ev / "eval_2.json"),
        },
        "base_sha": base,
        "git_diff_base_final_sha256": _sha(diff),
    }
    path = run / "evidence_manifest.json"
    path.write_text(json.dumps(manifest) + "\n")
    return path


def _write_task(path: Path, base: str, body: str = BODY, key: str | None = None) -> None:
    path.write_text(json.dumps({
        "owner": OWNER,
        "repo": REPO_NAME,
        "issue_number": NUMBER,
        "title": "Add sku_count",
        "body": body,
        "base_sha": base,
        "base_ref": "main",
        "task_key": key if key is not None else _task_key(body),
    }))


def _run(tmp, repo, base, diff: bytes, manifest: Path, capsys, task_key=None):
    from broker.gate import main

    diff_path = tmp / "agent.diff"
    diff_path.write_bytes(diff)
    task = tmp / "task.json"
    _write_task(task, base, key=task_key)
    receipt = tmp / "receipt.json"
    rc = main([
        "verify",
        "--task", str(task),
        "--diff", str(diff_path),
        "--evidence", str(manifest),
        "--repo", str(repo),
        "--policy", str(POLICY),
        "--receipt", str(receipt),
    ])
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    return rc, data, receipt, captured.err


def _good_diff(repo: Path) -> bytes:
    def mutate(path: Path):
        cart = path / "cart" / "cart.py"
        cart.write_text(cart.read_text() + "\n    def sku_count(self) -> int:\n        return len(self._items)\n")
    return _capture(repo, mutate)


def test_github_workflows_refused_even_if_verdict_passes(product, tmp_path, capsys):
    repo, base = product
    diff = _capture(repo, lambda p: (p / ".github" / "workflows").mkdir(parents=True) or (p / ".github" / "workflows" / "evil.yml").write_text("name: evil\n"))
    rc, data, receipt, _ = _run(tmp_path, repo, base, diff, _seal(tmp_path, diff, base, "PASS"), capsys)
    assert rc != 0 and data["ok"] is False and data["reason"] == "PROTECTED_PATH"
    assert not receipt.exists()


def test_codeowners_refused(product, tmp_path, capsys):
    repo, base = product
    diff = _capture(repo, lambda p: (p / "CODEOWNERS").write_text("* @attacker\n"))
    rc, data, _, _ = _run(tmp_path, repo, base, diff, _seal(tmp_path, diff, base), capsys)
    assert rc != 0 and data["reason"] == "PROTECTED_PATH"


def test_hidden_tests_refused(product, tmp_path, capsys):
    repo, base = product
    diff = _capture(repo, lambda p: (p / "task" / "hidden_tests").mkdir(parents=True) or (p / "task" / "hidden_tests" / "pwn.py").write_text("x = 1\n"))
    rc, data, _, _ = _run(tmp_path, repo, base, diff, _seal(tmp_path, diff, base), capsys)
    assert rc != 0 and data["reason"] == "HIDDEN_TEST"


def test_existing_test_edit_refused_despite_pass_verdict(product, tmp_path, capsys):
    repo, base = product
    def mutate(p: Path):
        t = p / "tests" / "test_cart.py"
        t.write_text(t.read_text().replace("assert c.item_count() == 0", "assert True"))
    diff = _capture(repo, mutate)
    rc, data, _, _ = _run(tmp_path, repo, base, diff, _seal(tmp_path, diff, base, "PASS"), capsys)
    assert rc != 0 and data["reason"] == "EXISTING_TEST"


def test_symlink_refused(product, tmp_path, capsys):
    repo, base = product
    diff = _capture(repo, lambda p: os.symlink("cart.py", p / "cart" / "link"))
    assert b"120000" in diff
    rc, data, _, _ = _run(tmp_path, repo, base, diff, _seal(tmp_path, diff, base), capsys)
    assert rc != 0 and data["reason"] == "SYMLINK"


def test_binary_refused(product, tmp_path, capsys):
    repo, base = product
    diff = _capture(repo, lambda p: (p / "cart" / "blob.bin").write_bytes(b"\x00\x01\x02"))
    rc, data, _, _ = _run(tmp_path, repo, base, diff, _seal(tmp_path, diff, base), capsys)
    assert rc != 0 and data["reason"] == "BINARY_FILE"


def test_oversized_diff_refused(product, tmp_path, capsys):
    from broker.gate import MAX_DIFF_BYTES

    repo, base = product
    diff = b"x" * (MAX_DIFF_BYTES + 1)
    rc, data, _, _ = _run(tmp_path, repo, base, diff, _seal(tmp_path, diff, base), capsys)
    assert rc != 0 and data["reason"] == "DIFF_TOO_LARGE"


def test_out_of_scope_refused(product, tmp_path, capsys):
    repo, base = product
    diff = _capture(repo, lambda p: (p / "README.md").write_text((p / "README.md").read_text() + "\nTamper\n"))
    rc, data, _, _ = _run(tmp_path, repo, base, diff, _seal(tmp_path, diff, base, "PASS"), capsys)
    assert rc != 0 and data["reason"] == "OUT_OF_SCOPE"


def test_stale_base_refused(product, tmp_path, capsys):
    repo, base = product
    diff = _good_diff(repo)
    manifest = _seal(tmp_path, diff, base)
    _git(repo, "commit", "-q", "--allow-empty", "-m", "main moved")
    tip = _git(repo, "rev-parse", "HEAD").stdout.strip()
    assert tip != base
    rc, data, _, _ = _run(tmp_path, repo, base, diff, manifest, capsys)
    assert rc != 0 and data["reason"] == "STALE_BASE"


def test_diff_hash_must_match_sealed_evidence(product, tmp_path, capsys):
    repo, base = product
    diff = _good_diff(repo)
    manifest = _seal(tmp_path, diff, base)
    flipped = bytearray(diff)
    flipped[-2] = flipped[-2] ^ 0x01
    rc, data, _, _ = _run(tmp_path, repo, base, bytes(flipped), manifest, capsys)
    assert rc != 0 and data["reason"] == "DIFF_HASH"


def test_evidence_file_hash_must_verify(product, tmp_path, capsys):
    repo, base = product
    diff = _good_diff(repo)
    manifest = _seal(tmp_path, diff, base)
    traj = manifest.parent / "trajectory.json"
    traj.write_text('{"tampered": true}\n')
    rc, data, _, _ = _run(tmp_path, repo, base, diff, manifest, capsys)
    assert rc != 0 and data["reason"] == "EVIDENCE_HASH"


def test_verdict_must_be_pass(product, tmp_path, capsys):
    repo, base = product
    diff = _good_diff(repo)
    rc, data, _, _ = _run(tmp_path, repo, base, diff, _seal(tmp_path, diff, base, "FAIL"), capsys)
    assert rc != 0 and data["reason"] == "VERDICT"


def test_malformed_diff_refused(product, tmp_path, capsys):
    repo, base = product
    diff = b"this is not a unified diff\n"
    rc, data, _, _ = _run(tmp_path, repo, base, diff, _seal(tmp_path, diff, base, "PASS"), capsys)
    assert rc != 0 and data["reason"] == "MALFORMED_DIFF"


def test_apply_check_failure_is_refused(product, tmp_path, capsys):
    repo, base = product
    diff = (
        b"diff --git a/cart/cart.py b/cart/cart.py\n"
        b"index 1111111..2222222 100644\n"
        b"--- a/cart/cart.py\n"
        b"+++ b/cart/cart.py\n"
        b"@@ -1,3 +1,4 @@\n"
        b" this context is not in the file\n"
        b"+added\n"
    )
    rc, data, _, _ = _run(tmp_path, repo, base, diff, _seal(tmp_path, diff, base, "PASS"), capsys)
    assert rc != 0 and data["reason"] == "MALFORMED_DIFF"


def test_happy_path_emits_receipt_and_does_not_publish(product, tmp_path, capsys):
    repo, base = product
    diff = _good_diff(repo)
    rc, data, receipt, err = _run(tmp_path, repo, base, diff, _seal(tmp_path, diff, base, "PASS"), capsys)
    assert rc == 0, data
    assert data["ok"] is True
    assert data["diff_sha256"] == _sha(diff)
    assert data["base_sha"] == base
    assert data["task_key"] == _task_key()
    assert data["verdict"] == "PASS"
    assert data["published"] is False
    assert "pr_url" not in data or data["pr_url"] is None
    on_disk = json.loads(receipt.read_text())
    assert on_disk == data
    blob = err + receipt.read_text() + json.dumps(data)
    assert "ghs_" not in blob and "BEGIN PRIVATE KEY" not in blob
    tip = _git(repo, "rev-parse", "HEAD").stdout.strip()
    assert tip == base  # the gate must not move the target branch


def test_task_key_mismatch_refused(product, tmp_path, capsys):
    repo, base = product
    diff = _good_diff(repo)
    rc, data, _, _ = _run(
        tmp_path, repo, base, diff, _seal(tmp_path, diff, base), capsys, task_key="acme/widget#7:" + "ab" * 32,
    )
    assert rc != 0 and data["reason"] == "TASK_INVALID"


def test_publisher_interface_has_no_token_path():
    import broker.publish as publish

    src = Path(publish.__file__).read_text().lower()
    for banned in ("jwt", "pyjwt", "access_token", "github_app", "authorization", "urllib", "requests"):
        assert banned not in src
    with pytest.raises(NotImplementedError):
        publish.Publisher().open_draft({"ok": True})


def test_gate_module_does_not_touch_the_network():
    src = (ROOT / "broker" / "gate.py").read_text().lower()
    for banned in ("urllib", "http.client", "socket", "requests", "jwt", "access_token", "authorization"):
        assert banned not in src
