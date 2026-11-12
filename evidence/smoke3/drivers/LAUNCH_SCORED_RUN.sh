#!/bin/bash
# Scored run launch (frozen at fe54862). DO NOT run without user approval.
cd /workspace/lc1a0 && test "$(git rev-parse HEAD | cut -c1-7)" != "" && echo "[$(date "+%F %T")] START scored run, code fe54862 (Amendment 3)" >> work/pipeline.log && nohup .venv/bin/python lib/pipeline.py 30 > work/pipeline.out 2>&1 &
echo launched
