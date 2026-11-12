"""One SANDBOXED OpenHands (SDK 1.62.0 agent-server, Docker) run on one instance.
Sandbox: agent-server image + mounted sanitized /testbed copy + instance conda env (ro); --network none.
Control channel: host TCP -> docker exec stdio relay -> container loopback:8000. LLM egress: container loopback:4000 -> UNIX socket
-> host proxy (gemini-2.5-flash only, real key injected host-side, cost metered + capped). usage: oh_run.py <iid> <outdir> <cost_cap> <max_iter>"""
import json, os, sys, subprocess, time, socket, shutil, uuid
sys.path.insert(0, "/workspace/lc1a0/lib")
import agent as A
iid, out, cap, max_iter = sys.argv[1], os.path.abspath(sys.argv[2]), float(sys.argv[3]), int(sys.argv[4])
WALL = int(sys.argv[5]) if len(sys.argv) > 5 else 1200
ROOT = "/workspace/lc1a0"; OH = f"{ROOT}/oh"; SERVER = "ghcr.io/openhands/agent-server:1.62.0-python"
S = {x["instance_id"]: x for x in json.load(open(f"{ROOT}/sample_v2.json"))["instances"]} if os.path.exists(f"{ROOT}/sample_v2.json") else {}
img = S[iid]["docker_image"] if iid in S else json.load(open(f"{ROOT}/work/inst/{iid}/meta.json"))["image"]
issue = open(f"{ROOT}/work/inst/{iid}/issue.md").read()
os.makedirs(out, exist_ok=True); ws = f"{out}/ws"; conda = f"{out}/conda"; sockd = f"{out}/sock"
sh = lambda *a, **k: subprocess.run(a, capture_output=True, text=True, **k)
t0 = time.time()
base = A.prep_ws(img, ws)
if not os.path.exists(conda):
    cid = sh("docker", "create", img).stdout.strip(); r = sh("docker", "cp", f"{cid}:/opt/conda", conda); sh("docker", "rm", "-f", cid)
    assert r.returncode == 0, r.stderr
os.makedirs(sockd, exist_ok=True); os.chmod(sockd, 0o777)
ledger = f"{out}/llm_ledger.json"
proxy = subprocess.Popen([f"{ROOT}/.venv/bin/python", f"{OH}/llm_proxy.py", f"{sockd}/llm.sock", ledger, str(cap)])
name = f"lc1a0_oh_{uuid.uuid4().hex[:8]}"
PATH = "/opt/conda/envs/testbed/bin:/opt/conda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
run = ["docker", "run", "-d", "--name", name, "--network", "none", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
       "--memory", "2g", "--cpus", "1", "--pids-limit", "512", "--label", "lc1a0.oh=1",
       "-v", f"{ws}:/testbed", "-v", f"{conda}:/opt/conda:ro", "-v", f"{OH}:/lc_oh:ro", "-v", f"{sockd}:/lc_sock",
       "-e", f"PATH={PATH}", "-e", "CONDA_DEFAULT_ENV=testbed", "-e", "OH_ENABLE_VSCODE=false", "-e", "OH_ENABLE_VNC=false",
       SERVER, "--port", "8000"]
r = sh(*run); assert r.returncode == 0, r.stderr
port = A.__dict__.get("_p", None) or (lambda s: (s.bind(("127.0.0.1", 0)), s.getsockname()[1], s.close())[1])(socket.socket())
bridge = None; res = {"instance_id": iid, "engine": "OpenHands SDK agent-server 1.62.0 (Docker sandbox, --network none)", "container": name, "run_cmd": run}
try:
    sh("docker", "exec", "-d", name, "python3", "/lc_oh/relay_in_container.py")
    bridge = subprocess.Popen([sys.executable, f"{OH}/host_bridge.py", name, str(port)])
    host = f"http://127.0.0.1:{port}"
    import urllib.request
    for i in range(90):
        try:
            urllib.request.urlopen(f"{host}/health", timeout=5).read(); break
        except Exception: time.sleep(2)
    else: raise RuntimeError("agent server not healthy:\n" + sh("docker", "logs", "--tail", "50", name).stdout + sh("docker", "logs", "--tail", "50", name).stderr)
    from pydantic import SecretStr
    from openhands.sdk import LLM, Conversation
    from openhands.sdk.workspace import RemoteWorkspace
    from openhands.tools.preset.default import get_default_agent
    llm = LLM(model="gemini/gemini-2.5-flash", base_url="http://127.0.0.1:4000", api_key=SecretStr("LC_DUMMY_KEY"), usage_id="agent", num_retries=2)
    ag = get_default_agent(llm=llm, cli_mode=True)
    w = RemoteWorkspace(host=host, working_dir="/testbed")
    conv = Conversation(agent=ag, workspace=w, max_iteration_per_run=max_iter)
    conv.send_message("Please solve this GitHub issue in the repository at /testbed (Python; dependencies are installed; there is no network access). "
                      "Make the minimal source change that resolves the issue. When you are done, finish.\n\n<issue>\n" + issue + "\n</issue>")
    import threading
    def _run():
        try: conv.run()
        except Exception as e: res["run_error"] = repr(e)[:3000]
    th = threading.Thread(target=_run, daemon=True); th.start(); th.join(WALL)
    if th.is_alive():
        res["wall_timeout"] = True
        try: conv.pause()
        except Exception as e: res["pause_error"] = repr(e)
        th.join(60)
    st = conv.state
    res["execution_status"] = str(getattr(st, "execution_status", ""))
    try:
        evs = list(st.events); res["n_events"] = len(evs)
        json.dump([e.model_dump(mode="json") for e in evs], open(f"{out}/events.json", "w"), default=str)
    except Exception as e: res["events_error"] = str(e)
    try: conv.close()
    except Exception: pass
except Exception as e:
    res["error"] = repr(e)[:3000]
finally:
    open(f"{out}/server.log", "w").write(sh("docker", "logs", name).stdout[-200000:] + sh("docker", "logs", name).stderr[-200000:])
    sh("docker", "rm", "-f", name)
    if bridge: bridge.kill()
    proxy.kill()
g = lambda *a: sh("git", "-C", ws, "-c", "safe.directory=*", *a).stdout
g("add", "-A"); diff = g("diff", "--cached", base)
open(f"{out}/patch_raw.diff", "w").write(diff)
res["llm"] = json.load(open(ledger)) if os.path.exists(ledger) else None
acc = 0.0; final_msg = ""
try:
    import re as _re
    ev = open(f"{out}/events.json").read()
    accs = [float(x) for x in _re.findall(r'"accumulated_cost": ([0-9.eE-]+)', ev)]; acc = max(accs) if accs else 0.0
    evj = json.load(open(f"{out}/events.json"))
    for e in evj:
        t = json.dumps(e)
        if e.get("source") == "agent" and ("FinishAction" in t or e.get("kind") in ("MessageEvent",)): final_msg = t[:4000]
except Exception as e: res["final_msg_error"] = repr(e)
res["litellm_accumulated_cost"] = acc; res["proxy_metered_cost"] = (res["llm"] or {}).get("cost", 0.0)
res["base_sha"] = base; res["run_id"] = os.environ.get("LC_RUNID"); res["cost_usd"] = max(acc, res["proxy_metered_cost"]); res["final_message"] = final_msg; res["wall_seconds"] = round(time.time() - t0); res["diff_bytes"] = len(diff)
json.dump(res, open(f"{out}/oh_result.json", "w"), indent=2, default=str)
with open(A.LEDGER, "a") as f: f.write(json.dumps({"run_id": os.environ.get("LC_RUNID", f"oh-feasibility-{iid}"), "role": os.environ.get("LC_ROLE", "oh-feasibility"), "cost_usd": res["cost_usd"], "ts": time.strftime("%FT%T%z")}) + "\n")
print(json.dumps({k: res.get(k) for k in ("execution_status", "error", "cost_usd", "wall_seconds", "diff_bytes", "n_events")}))
