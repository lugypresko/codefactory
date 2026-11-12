# LC-0 / FG-0 Feasibility Gate — report (2026-11-12, Asia/Jerusalem)

Model: gemini/gemini-3-flash-preview (via litellm) | Agent: mini-SWE-agent 2.4.6, yolo mode, headless
Toy repo: /workspace/lc0/toyrepo (base 2c6d9f4) | Task: TASK.md (remove_item + discount codes)

| # | FG-0 condition | Result | Evidence |
|---|---|---|---|
| 1 | Agent runs on isolated repo | PASS | Docker container lc0-env:1, only a fresh clone (runs/run1/ws) mounted at /repo; hidden tests never mounted |
| 2 | Budget definable + measured | PASS | step_limit=30, cost_limit=$0.50 set; actual: 18 API calls, $0.1068, 103 s wall |
| 3 | Permissions/network restricted | PASS | --network none, --user 1000:1000, --cap-drop ALL, no-new-privileges, 1 GB RAM, 1 CPU, 256 pids; API key not forwarded to container (forward_env=[]); LLM loop runs on host |
| 4 | Trace + final SHA saved | PASS | runs/run1/trajectory.json, agent_stdout.log, artifact.json (final SHA c05be0b), final.diff; branch run-run1 in toyrepo |
| 5 | External evaluator on artifact | PASS | evaluate.sh c05be0b → FAIL_TO_PASS 9/9, PASS_TO_PASS 5/5, decision PASS; run twice, identical. Base SHA → F2P 0/9 (tests are valid) |
| 6 | No full org infra needed | PASS | One Linux box, static Docker binaries, a pip venv, 2 bash scripts |

Notes: agent hit 2 format errors (no tool call) mid-run and recovered by itself; not counted as the planned injected-failure recovery.
Gaps: dockerd started manually without iptables/bridge (only --network none/host possible); not persistent across box restarts. Code-env network is cut entirely (LLM access is host-side, not via an egress proxy).
