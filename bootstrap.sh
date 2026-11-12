#!/usr/bin/env bash
# bootstrap.sh — set up the LC-0 environment from scratch (idempotent; safe to re-run).
#   1. Python venv in $LC0_VENV with exact pins from requirements.lock
#   2. Docker present + daemon reachable
#   3. Build the code-env image ($LC0_IMAGE) from docker/Dockerfile (base pinned by digest)
#   4. Create the canonical task repo with a deterministic base commit (fixed author/date)
#   5. Write $LC0_WORK/environment.json (versions actually installed)
# Exit codes: 0 ok | 40 python missing/too old | 41 pip install failed | 42 docker missing/unreachable
#             43 image build failed | 44 task repo / base SHA problem | 45 test hash manifest mismatch
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"; export ROOT
source "$ROOT/lib/common.sh"
EXPECTED_BASE_SHA="$(sed -n 's/^base_commit_sha=//p' "$ROOT/VERSIONS")"

# ---- 1. Python + venv ------------------------------------------------------
PY="${LC0_PYTHON:-python3}"
command -v "$PY" >/dev/null || die 40 "python3 not found. Install Python >= 3.11 (tested: 3.13)."
"$PY" -c 'import sys; sys.exit(0 if sys.version_info >= (3,11) else 1)' || die 40 "Python >= 3.11 required (found $("$PY" -V))."
if [[ ! -x "$LC0_VENV/bin/python" ]]; then
  log "creating venv at $LC0_VENV"; "$PY" -m venv "$LC0_VENV" || die 40 "venv creation failed (Debian/Ubuntu: apt install python3-venv)"
fi
LOCK_HASH=$(sha256sum "$ROOT/requirements.lock" | cut -d' ' -f1)
STAMP="$LC0_VENV/.lc0-lock-hash"
if [[ "$(cat "$STAMP" 2>/dev/null || true)" != "$LOCK_HASH" ]]; then
  log "installing pinned requirements (requirements.lock)"
  "$LC0_VENV/bin/pip" install -q --upgrade pip >/dev/null || true
  "$LC0_VENV/bin/pip" install -q --no-deps -r "$ROOT/requirements.lock" || die 41 "pip install failed"
  "$LC0_VENV/bin/pip" check >/dev/null || die 41 "pip check failed (inconsistent deps)"
  echo "$LOCK_HASH" > "$STAMP"
else log "venv up to date"; fi
MSWEA_VER=$("$LC0_VENV/bin/python" -c 'import importlib.metadata as m; print(m.version("mini-swe-agent"))')
LITELLM_VER=$("$LC0_VENV/bin/python" -c 'import importlib.metadata as m; print(m.version("litellm"))')

# ---- 2. Docker -------------------------------------------------------------
if ! docker_ok; then
  cat >&2 <<'MSG'
Docker is required (tested: Docker Engine 27.3.1) and the daemon must be reachable by this user.
  Install:      https://docs.docker.com/engine/install/  (or: curl -fsSL https://get.docker.com | sh)
  Start daemon: sudo systemctl start docker
  Permissions:  sudo usermod -aG docker "$USER"  (then log out/in)  — or run as a docker-capable user
  Check:        docker run --rm hello-world
MSG
  die 42 "docker not available ($LC0_DOCKER)"
fi
DOCKER_VER=$("$LC0_DOCKER" version --format '{{.Server.Version}}')

# ---- 3. Image --------------------------------------------------------------
NET_ARGS=()
"$LC0_DOCKER" network inspect bridge >/dev/null 2>&1 || NET_ARGS=(--network host)  # daemons without bridge
log "building image $LC0_IMAGE (cached if unchanged)"
"$LC0_DOCKER" build -q "${NET_ARGS[@]}" -t "$LC0_IMAGE" -f "$ROOT/docker/Dockerfile" "$ROOT/docker" >/dev/null \
  || die 43 "docker build failed"
"$LC0_DOCKER" run --rm --network none "$LC0_IMAGE" python -m pytest --version >/dev/null 2>&1 \
  || die 43 "image smoke test failed (pytest not runnable in $LC0_IMAGE)"
IMAGE_ID=$("$LC0_DOCKER" image inspect "$LC0_IMAGE" --format '{{.Id}}')
BASE_DIGEST=$(sed -n 's/^FROM .*@\(sha256:[0-9a-f]*\).*/\1/p' "$ROOT/docker/Dockerfile")

# ---- 4. Task repo (deterministic base commit) -------------------------------
verify_test_hashes || die 45 "hidden/P2P tests do not match task/tests.sha256"
if [[ ! -d "$LC0_REPO/.git" ]]; then
  log "creating canonical task repo at $LC0_REPO"
  mkdir -p "$LC0_REPO"; cp -a "$ROOT/task/repo/." "$LC0_REPO/"
  (cd "$LC0_REPO" && git init -q -b main && git add -A &&
   GIT_AUTHOR_NAME=lc0 GIT_AUTHOR_EMAIL=lc0@local GIT_COMMITTER_NAME=lc0 GIT_COMMITTER_EMAIL=lc0@local \
   GIT_AUTHOR_DATE="2026-01-01T00:00:00+00:00" GIT_COMMITTER_DATE="2026-01-01T00:00:00+00:00" \
   git commit -q -m "base: cart library") || die 44 "git init/commit failed"
fi
BASE_SHA=$(git -C "$LC0_REPO" rev-parse main) || die 44 "no main branch in $LC0_REPO"
if [[ -n "$EXPECTED_BASE_SHA" && "$BASE_SHA" != "$EXPECTED_BASE_SHA" ]]; then
  die 44 "base SHA $BASE_SHA != expected $EXPECTED_BASE_SHA (VERSIONS). Delete $LC0_REPO and re-run, or check task/repo/ is unmodified."
fi

# ---- 5. Environment record --------------------------------------------------
mkdir -p "$LC0_WORK"
"$LC0_VENV/bin/python" - "$LC0_WORK/environment.json" <<PY
import json, sys, platform
json.dump({"python": platform.python_version(), "mini_swe_agent": "$MSWEA_VER", "litellm": "$LITELLM_VER",
  "docker_server": "$DOCKER_VER", "image_tag": "$LC0_IMAGE", "image_id": "$IMAGE_ID",
  "base_image_digest": "$BASE_DIGEST", "base_commit_sha": "$BASE_SHA",
  "hidden_tests_sha256": "$(hidden_hash)", "p2p_tests_sha256": "$(p2p_hash)",
  "os": platform.platform()}, open(sys.argv[1], "w"), indent=2)
PY
log "bootstrap OK: mini-swe-agent $MSWEA_VER, litellm $LITELLM_VER, docker $DOCKER_VER, image $IMAGE_ID, base $BASE_SHA"
