"""scratch.py <iid> : create work/scratch/<iid> (sanitized copy of /testbed) for authoring wrong patches."""
import sys, json, os
sys.path.insert(0, os.path.dirname(__file__)); import agent
iid = sys.argv[1]; meta = json.load(open(f"work/inst/{iid}/meta.json"))
print(agent.prep_ws(meta["image"], os.path.abspath(f"work/scratch/{iid}")))
