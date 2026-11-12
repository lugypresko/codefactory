#!/usr/bin/env bash
# run_agent.sh <run_id> — one headless mini-SWE-agent run on a fresh clone of the canonical task repo.
#
# The agent loop (and the LLM API call) runs on the host; every shell command the agent issues runs in a
# Docker sandbox ($LC0_IMAGE) with --network none, non-root user, no capabilities, mem/cpu/pid limits.
# Only the clone ($LC0_WORK/runs/<id>/ws) is mounted; task/hidden_tests and task/locked_p2p never are.
# The agent uses mini-swe-agent's non-interactive DefaultAgent with stdin=/dev/null: no human channel.
#
# Output: $LC0_WORK/runs/<id>/{agent_result.json, trajectory.json, agent_stdout.log, final.diff, config.yaml}
# agent_result.json keeps the AGENT status separate from any product test result (see evaluate.sh).
#
# Fault injection: LC0_FAULT=none|<fault_id> (catalogue in lib/lc0util.py FAULTS); recorded in
# agent_result.json "fault" (fault_id, injected_at, fired_events).
#
# Exit codes (agent_status):
#   0  SUBMITTED        agent submitted and produced a non-empty diff → final_sha set (branch run/<id>)
#   10 LIMIT_EXCEEDED   cost or step limit hit (limit_hit = cost|steps)
#   11 WALL_TIMEOUT     wall-clock limit hit
#   12 NO_SUBMIT        agent stopped without submitting (e.g. RepeatedFormatError)
#   13 EMPTY_DIFF       agent submitted but changed nothing
#   20 AGENT_CRASH      mini exited abnormally / uncaught exception / no trajectory
#   30 INFRA_ERROR      precondition or harness failure (key, venv, docker, image, repo, test hashes, git)
#   2  usage
# Non-SUBMITTED runs: whatever the agent left is still committed for audit, on branch run/<id>-incomplete
# with agent_status in the commit message, recorded as workspace_sha — never as final_sha.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"; export ROOT
source "$ROOT/lib/common.sh"
[[ $# -eq 1 && "$1" =~ ^[A-Za-z0-9._-]+$ ]] || { echo "usage: $0 <run_id>  (alnum . _ -)" >&2; exit 2; }
RID=$1; RD="$LC0_WORK/runs/$RID"; RES="$RD/agent_result.json"
T0=$(date +%s); STARTED=$(date -Iseconds)
declare -A R=( [agent_status]=INFRA_ERROR [reason]="" [mini_exit_code]=null [exit_status]="" [base_sha]="" \
  [final_sha]="" [workspace_sha]="" [diff_files]=0 [diff_lines]=0 [limit_hit]="" )
CODE=30

write_result() {
  local k; for k in "${!R[@]}"; do export "LCR_$k=${R[$k]}"; done
  LCR_code=$CODE LCR_rid=$RID LCR_t0=$T0 LCR_started=$STARTED python3 - "$RES" "$RD" <<'PY' || log "WARNING: could not write $RES"
import json, sys, os, time
e = os.environ; g = lambda k: e.get("LCR_" + k) or None
rd = sys.argv[2]; tp = os.path.join(rd, "trajectory.json")
cost = calls = None; models = []
if os.path.exists(tp):
    try:
        t = json.load(open(tp)); s = t.get("info", {}).get("model_stats", {})
        cost, calls = s.get("instance_cost"), s.get("api_calls")
        models = sorted({m.get("extra", {}).get("response", {}).get("model") for m in t.get("messages", [])
                         if m.get("role") == "assistant" and m.get("extra", {}).get("response")} - {None})
    except Exception as ex:
        models = ["<trajectory unreadable: %s>" % ex]
num = lambda k: int(g(k)) if g(k) not in (None, "null") else None
r = {"run_id": g("rid"), "agent_status": g("agent_status"), "agent_exit_code": int(g("code")), "reason": g("reason"),
     "mini_exit_code": num("mini_exit_code"), "mini_exit_status": g("exit_status"), "limit_hit": g("limit_hit"),
     "base_sha": g("base_sha"), "final_sha": g("final_sha"), "workspace_sha": g("workspace_sha"),
     "diff_files": num("diff_files"), "diff_lines": num("diff_lines"),
     "model_requested": e["LC0_MODEL"], "models_returned_by_api": models,
     "cost_usd": cost, "api_calls": calls, "cost_limit_usd": float(e["LC0_COST_LIMIT"]), "step_limit": int(e["LC0_STEP_LIMIT"]),
     "wall_seconds": int(time.time()) - int(g("t0")), "started_at": g("started"),
     "ended_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "image": e["LC0_IMAGE"],
     "paths": {"run_dir": rd, "trajectory": tp if os.path.exists(tp) else None,
               "log": os.path.join(rd, "agent_stdout.log"), "diff": os.path.join(rd, "final.diff")}}
fp = os.path.join(rd, "fault.json")
if os.path.exists(fp):
    fj = json.load(open(fp)); fj.pop("extra_run_args", None)
    ev = fj.get("events_log")
    fj["fired_events"] = open(ev).read().split("\n")[:-1] if ev and os.path.exists(ev) else []
    fj.pop("events_log", None)
    r["fault"] = fj
else:
    r["fault"] = {"fault_id": e.get("LC0_FAULT", "none"), "note": "fault not set up (run ended before setup)"}
json.dump(r, open(sys.argv[1], "w"), indent=2)
PY
}
fail() { R[agent_status]=$2; R[reason]=$3; CODE=$1; trap - ERR; cleanup_containers; write_result; log "$2: $3"; exit "$1"; }
cleanup_containers() { "$LC0_DOCKER" ps -aq --filter "label=lc0.run=$RID" 2>/dev/null | xargs -r "$LC0_DOCKER" rm -f >/dev/null 2>&1 || true; }
trap 'fail 30 INFRA_ERROR "unexpected harness error: line $LINENO: $BASH_COMMAND"' ERR

rm -rf "$RD"; mkdir -p "$RD"
# ---- preconditions (all INFRA_ERROR) ----
[[ "$LC0_MODEL" != gemini/* || -n "${GEMINI_API_KEY:-}" ]] || fail 30 INFRA_ERROR "GEMINI_API_KEY not set"
[[ -x "$LC0_VENV/bin/mini" ]] || fail 30 INFRA_ERROR "mini not found in $LC0_VENV (run bootstrap.sh)"
docker_ok || fail 30 INFRA_ERROR "docker unavailable ($LC0_DOCKER)"
image_ok || fail 30 INFRA_ERROR "image missing ($LC0_IMAGE; run bootstrap.sh)"
[[ -d "$LC0_REPO/.git" ]] || fail 30 INFRA_ERROR "task repo missing ($LC0_REPO; run bootstrap.sh)"
verify_test_hashes || fail 30 INFRA_ERROR "hidden/P2P test hashes do not match manifest (before run)"

git clone -q "$LC0_REPO" "$RD/ws" || fail 30 INFRA_ERROR "git clone failed"
R[base_sha]=$(git -C "$RD/ws" rev-parse HEAD)
# ---- inject exactly one development-process fault (harness-side; not mentioned in the task text) ----
python3 "$LC0_UTIL" fault-setup "$LC0_FAULT" "$RD" "$RD/ws" "$LC0_CMD_TIMEOUT" > "$RD/fault.json" \
  || fail 30 INFRA_ERROR "fault setup failed: $(cat "$RD/fault.json")"
chmod -R a+rwX "$RD/ws"
WS_MODE=$(python3 -c "import json;print(':ro' if json.load(open('$RD/fault.json'))['ws_readonly'] else '')")
EXTRA_ARGS=$(python3 -c "import json;print(''.join(', '+json.dumps(x) for x in json.load(open('$RD/fault.json'))['extra_run_args']))")
cat > "$RD/config.yaml" <<YAML
agent:
  step_limit: $LC0_STEP_LIMIT
  cost_limit: $LC0_COST_LIMIT
  wall_time_limit_seconds: $LC0_WALL_TIMEOUT
environment:
  environment_class: docker
  image: $LC0_IMAGE
  executable: $LC0_DOCKER
  cwd: /repo
  timeout: $LC0_CMD_TIMEOUT
  forward_env: []
  env: {HOME: /tmp, PAGER: cat, MANPAGER: cat, PYTHONDONTWRITEBYTECODE: "1"}
  run_args: ["--rm", "--network", "none", "--user", "$(id -u):$(id -g)", "--cap-drop", "ALL",
             "--security-opt", "no-new-privileges", "--memory", "1g", "--cpus", "1", "--pids-limit", "256",
             "--label", "lc0.run=$RID", "-v", "$RD/ws:/repo$WS_MODE"$EXTRA_ARGS]
YAML

# ---- agent run ----
log "agent run $RID: fault=$LC0_FAULT model=$LC0_MODEL cost_limit=\$$LC0_COST_LIMIT step_limit=$LC0_STEP_LIMIT"
export MSWEA_CONFIGURED=true MSWEA_SILENT_STARTUP=1 MSWEA_GLOBAL_CONFIG_DIR="$LC0_WORK/.mswea"
RC=0
timeout --kill-after=30 "$(( LC0_WALL_TIMEOUT + 120 ))" "$LC0_VENV/bin/mini" --agent-class default \
  -m "$LC0_MODEL" -c "$ROOT/mini.yaml" -c "$RD/config.yaml" -t "$(cat "$ROOT/task/TASK.md")" \
  -o "$RD/trajectory.json" < /dev/null > "$RD/agent_stdout.log" 2>&1 || RC=$?
R[mini_exit_code]=$RC
cleanup_containers

# ---- classify the agent's stop reason (independent of product tests) ----
if [[ -f "$RD/trajectory.json" ]]; then
  R[exit_status]=$(python3 -c "import json;print(json.load(open('$RD/trajectory.json'))['info'].get('exit_status',''))" 2>/dev/null || echo "")
fi
case "$RC:${R[exit_status]}" in
  124:*|137:*|*:TimeExceeded) CODE=11; R[agent_status]=WALL_TIMEOUT ;;
  0:Submitted)                CODE=0;  R[agent_status]=SUBMITTED ;;
  *:LimitsExceeded)           CODE=10; R[agent_status]=LIMIT_EXCEEDED
     R[limit_hit]=$(python3 -c "
import json;s=json.load(open('$RD/trajectory.json'))['info']['model_stats']
print('cost' if s['instance_cost']>=$LC0_COST_LIMIT else 'steps')") ;;
  0:RepeatedFormatError|0:FormatError) CODE=12; R[agent_status]=NO_SUBMIT ;;
  *:)  CODE=20; R[agent_status]=AGENT_CRASH; R[reason]="mini exit $RC, no trajectory/exit_status"
       grep -qiE "docker|CalledProcessError" "$RD/agent_stdout.log" && { CODE=30; R[agent_status]=INFRA_ERROR; R[reason]="sandbox start failed (see agent_stdout.log)"; } ;;
  *)   CODE=20; R[agent_status]=AGENT_CRASH; R[reason]="mini exit $RC, exit_status=${R[exit_status]}" ;;
esac

# ---- freeze the artifact (harness commits, not the agent) ----
cd "$RD/ws"
git add -A
git diff --cached "${R[base_sha]}" > "$RD/final.diff"
R[diff_files]=$(git diff --cached --name-only "${R[base_sha]}" | wc -l)
R[diff_lines]=$(wc -l < "$RD/final.diff")
if [[ ${R[diff_files]} -eq 0 ]]; then
  [[ $CODE -eq 0 ]] && { CODE=13; R[agent_status]=EMPTY_DIFF; }
else
  BR="run/$RID"; [[ $CODE -eq 0 ]] || BR="run/$RID-incomplete"
  GIT_AUTHOR_NAME=lc0-harness GIT_AUTHOR_EMAIL=lc0@local GIT_COMMITTER_NAME=lc0-harness GIT_COMMITTER_EMAIL=lc0@local \
    git commit -q -m "agent run $RID: agent_status=${R[agent_status]} mini_exit_status=${R[exit_status]:-none}"
  SHA=$(git rev-parse HEAD)
  git -C "$LC0_REPO" fetch -q "$RD/ws" "+HEAD:refs/heads/$BR"
  if [[ $CODE -eq 0 ]]; then R[final_sha]=$SHA; else R[workspace_sha]=$SHA; fi
fi
cd "$ROOT"
verify_test_hashes || fail 30 INFRA_ERROR "hidden/P2P test hashes changed during run"
trap - ERR
write_result
log "agent_status=${R[agent_status]} (exit $CODE) final_sha=${R[final_sha]:-none}"
exit $CODE
