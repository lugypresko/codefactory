#!/usr/bin/env bash
# selftest.sh — offline negative/positive tests of the verdict logic (no LLM calls, cost $0).
# Needs a bootstrapped package (Docker image + work/repo) and, for the end-to-end cases, the run A-control
# (LC0_SELFTEST_RUN, default A-control) in work/. Runs everything in a throw-away copy; prints one line per case.
# Exit 0 if every case gives the expected result, 1 otherwise.
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"; export ROOT
source "$ROOT/lib/common.sh"
exec python3 "$ROOT/lib/selftest.py" "$ROOT"
