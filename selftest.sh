#!/usr/bin/env bash
# selftest.sh [--no-strict] [--unit-only] [--json out.json] — offline tests of the verdict logic (no LLM calls, $0).
# STRICT by default: every expected case must execute; any SKIP (e.g. no Docker image) => exit 1.
# Integration cases use committed fixtures (tests/fixtures), not work/runs. Prints a JSON summary
# {passed, failed, skipped, total_expected, strict}. Exit 0 only if nothing failed (and, strict, nothing skipped).
set -Eeuo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"; export ROOT
source "$ROOT/lib/common.sh"
exec python3 "$ROOT/lib/selftest.py" "$ROOT" "$@"
