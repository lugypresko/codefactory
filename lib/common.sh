# Shared settings for LC-0 scripts. Source from a script after setting ROOT.
# Every value is overridable via environment variable (defaults documented in README.md).
: "${ROOT:?ROOT must be set}"
export LC0_WORK="${LC0_WORK:-$ROOT/work}"                 # generated state (git repo, runs)
export LC0_IMAGE="${LC0_IMAGE:-lc0-env:1}"                # code-env docker image tag
export LC0_DOCKER="${LC0_DOCKER:-docker}"                 # docker executable
export LC0_MODEL="${LC0_MODEL:-gemini/gemini-2.5-flash}"  # litellm model name
export LC0_COST_LIMIT="${LC0_COST_LIMIT:-0.50}"           # USD, hard stop (mini-swe-agent cost_limit)
export LC0_STEP_LIMIT="${LC0_STEP_LIMIT:-30}"             # max LLM calls (mini-swe-agent step_limit)
export LC0_CMD_TIMEOUT="${LC0_CMD_TIMEOUT:-60}"           # seconds per shell command in sandbox
export LC0_WALL_TIMEOUT="${LC0_WALL_TIMEOUT:-1800}"       # seconds, whole agent run (host-side timeout)
export LC0_FAULT="${LC0_FAULT:-none}"                    # one injected dev-process fault per run (see README)
export LC0_VENV="${LC0_VENV:-$ROOT/.venv}"
LC0_REPO="$LC0_WORK/repo"                                 # canonical git repo (base + run branches)
LC0_HIDDEN="$ROOT/task/hidden_tests"
LC0_P2P="$ROOT/task/locked_p2p"
LC0_MANIFEST="$ROOT/task/manifest.json"
LC0_UTIL="$ROOT/lib/lc0util.py"

log() { printf '[%s] %s\n' "$(date +%H:%M:%S)" "$*" >&2; }
die() { local code=$1; shift; log "ERROR: $*"; exit "$code"; }

# Verify hidden + locked P2P test files against the pinned sha256 in task/manifest.json. Returns 0/1.
verify_test_hashes() { python3 "$LC0_UTIL" verify-hashes "$ROOT/task" >/dev/null 2>&1; }

# Combined hash of hidden tests (for reports)
hidden_hash() { cat "$LC0_HIDDEN"/*.py | sha256sum | cut -d' ' -f1; }
p2p_hash() { cat "$LC0_P2P"/*.py | sha256sum | cut -d' ' -f1; }

docker_ok() { command -v "$LC0_DOCKER" >/dev/null 2>&1 && "$LC0_DOCKER" info >/dev/null 2>&1; }
image_ok() { "$LC0_DOCKER" image inspect "$LC0_IMAGE" >/dev/null 2>&1; }
