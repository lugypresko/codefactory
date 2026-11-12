#!/usr/bin/env bash
# evaluate.sh <SHA> [out.json] — independent evaluator (SWE-bench style FAIL_TO_PASS / PASS_TO_PASS).
#
# Exports EXACTLY <SHA> from the canonical repo ($LC0_WORK/repo) and runs the hidden FAIL_TO_PASS tests
# and the locked PASS_TO_PASS tests against it in fresh, network-less, read-only containers.
# Tests live in task/ (never mounted into the agent sandbox), are mounted read-only at /eval, and run with
# --noconftest and the evaluator's own pytest config, so repo-level pytest config cannot alter them.
#
# Decisions / exit codes (a JSON report is ALWAYS written, including on unexpected errors):
#   0 PASS      every expected test id (task/manifest.json) present and passed in both suites
#   1 FAIL      suites ran; product is wrong: failed/missing/extra/skipped tests, or the product breaks
#               test collection/import
#   3 ERROR     infrastructure / evaluation problem — says nothing about the product, never PASS:
#               missing SHA or repo, docker unavailable, image missing, docker run failure, missing or
#               invalid JUnit XML, pytest internal/usage error, test-hash mismatch (before or after),
#               any unexpected script error (trap)
#   4 ESCALATE  tests passed, but the artifact adds/changes test-harness-sensitive files
#               (conftest.py, pytest.ini, sitecustomize.py, ...) or violates task/diff_policy.json
#               (protected paths, deleted pre-existing tests, dependency changes, changes outside scope):
#               needs human review
#   2 usage error
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"; export ROOT
source "$ROOT/lib/common.sh"
[[ $# -ge 1 && -n "${1:-}" ]] || { echo "usage: $0 <SHA> [out.json]" >&2; exit 2; }
REQ_SHA=$1; OUT=${2:--}
WORK=""; STATE="/nonexistent/state.json"; T0=$(date +%s)
U() { python3 "$LC0_UTIL" "$@"; }
put() { U put "$STATE" "$1" "$2"; }

finish() { # $1 decision $2 reason — writes the report and exits with the documented code
  trap - ERR
  U finish "$STATE" "$OUT" "$1" "$2" "$REQ_SHA" "$(date -Iseconds)" "$(( $(date +%s) - T0 ))" || true
  [[ -n "$WORK" ]] && rm -rf "$WORK"
  case $1 in PASS) exit 0;; FAIL) exit 1;; ESCALATE) exit 4;; *) exit 3;; esac
}
trap 'finish ERROR "unexpected_script_error: line $LINENO: $BASH_COMMAND"' ERR
WORK=$(mktemp -d "${TMPDIR:-/tmp}/lc0-eval-XXXXXX")
STATE="$WORK/state.json"; echo '{}' > "$STATE"

# 1. pinned test integrity BEFORE
put hidden_tests_sha256 "\"$(hidden_hash)\""; put p2p_tests_sha256 "\"$(p2p_hash)\""
verify_test_hashes || finish ERROR "test_hash_mismatch_before (task/ differs from task/manifest.json)"
put test_hashes_verified_before true
# 2. infrastructure
docker_ok || finish ERROR "docker_unavailable ($LC0_DOCKER)"
image_ok || finish ERROR "image_missing ($LC0_IMAGE)"
put image "\"$LC0_IMAGE\""; put image_id "\"$("$LC0_DOCKER" image inspect "$LC0_IMAGE" --format '{{.Id}}')\""
# 3. artifact: exactly this commit
[[ -d "$LC0_REPO/.git" ]] || finish ERROR "repo_missing ($LC0_REPO; run bootstrap.sh)"
SHA=$(git -C "$LC0_REPO" rev-parse --verify -q "${REQ_SHA}^{commit}") || finish ERROR "sha_not_found ($REQ_SHA)"
put sha "\"$SHA\""
mkdir -p "$WORK/src" "$WORK/eval/f2p" "$WORK/eval/p2p" "$WORK/out"
git -C "$LC0_REPO" archive "$SHA" | tar -x -C "$WORK/src"
cp "$LC0_HIDDEN"/*.py "$WORK/eval/f2p/"; cp "$LC0_P2P"/*.py "$WORK/eval/p2p/"
printf '[pytest]\naddopts =\n' > "$WORK/eval/pytest.ini"
chmod -R a+rX "$WORK"; chmod a+rwx "$WORK/out"
# harness-sensitive files anywhere in the artifact
PROTECTED=$(python3 -c "import json;print(' '.join(json.load(open('$LC0_MANIFEST'))['protected_basenames']))")
SUSPECT=""; for b in $PROTECTED; do SUSPECT+="$(cd "$WORK/src" && find . -name "$b" -o -name '*.pth' | sort -u | tr '\n' ' ')"; done
SUSPECT=$(echo "$SUSPECT" | tr ' ' '\n' | sort -u | grep -v '^$' | tr '\n' ' ' || true)
put harness_sensitive_files "$(python3 -c "import json,sys;print(json.dumps(sys.argv[1].split()))" "$SUSPECT")"

# change-boundary policy (task/diff_policy.json) on base..SHA; base = merge-base with main (override: LC0_BASE)
BASE_SHA=${LC0_BASE:-$(git -C "$LC0_REPO" merge-base main "$SHA")}
put base_sha "\"$BASE_SHA\""
put diff_policy "$(U diff-policy "$LC0_REPO" "$BASE_SHA" "$SHA" "$ROOT/task/diff_policy.json" "${LC0_EVAL_TRAJ:-}")"
DP=$(python3 -c "import json;print(json.load(open('$STATE'))['diff_policy']['result'])")

run_suite() { # $1 = f2p|p2p → prints status
  local s=$1 rc=0
  "$LC0_DOCKER" run --rm --network none --read-only --tmpfs /tmp --user "$(id -u):$(id -g)" \
    --cap-drop ALL --security-opt no-new-privileges -e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPATH=/repo \
    -v "$WORK/src:/repo:ro" -v "$WORK/eval:/eval:ro" -v "$WORK/out:/out" -w /eval "$LC0_IMAGE" \
    python -m pytest -q -p no:cacheprovider --noconftest -c /eval/pytest.ini --rootdir /eval \
      "/eval/$s" --junitxml="/out/$s.xml" > "$WORK/out/$s.log" 2>&1 || rc=$?
  U parse-suite "$STATE" "$s" "$rc" "$WORK/out/$s.xml" "$WORK/out/$s.log" "$LC0_MANIFEST"
}
F=$(run_suite f2p); P=$(run_suite p2p)
# 4. pinned test integrity AFTER
verify_test_hashes || finish ERROR "test_hash_mismatch_after"
put test_hashes_verified_after true
# 5. decision
[[ $F == error || $P == error ]] && finish ERROR "suite_error (f2p=$F, p2p=$P)"
if [[ $F == passed && $P == passed ]]; then
  [[ -n "$SUSPECT" ]] && finish ESCALATE "tests passed but harness-sensitive files present: $SUSPECT"
  [[ $DP != OK ]] && finish ESCALATE "tests passed but diff policy violated (see diff_policy.violations)"
  finish PASS "all expected tests present and passed"
fi
finish FAIL "f2p=$F, p2p=$P"
