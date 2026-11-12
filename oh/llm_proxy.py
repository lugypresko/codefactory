"""Host-side LLM egress proxy on a UNIX socket. Only forwards POST /v1beta/models/<gemini-2.5-flash>:generateContent|streamGenerateContent
to generativelanguage.googleapis.com, injects the real API key (container only ever sees a dummy), meters cost, enforces a cap."""
import json, os, socketserver, sys, threading, urllib.request, urllib.error, re, time
from http.server import BaseHTTPRequestHandler
SOCK, LEDGER, CAP = sys.argv[1], sys.argv[2], float(sys.argv[3])
KEY = os.environ["GEMINI_API_KEY"]
PIN, PCACHE, POUT = 0.30e-6, 0.03e-6, 2.50e-6  # pinned = litellm model_cost["gemini/gemini-2.5-flash"]
lock = threading.Lock(); state = {"cost": 0.0, "calls": 0, "in": 0, "out": 0}
ALLOWED = re.compile(r"^(?:/v1beta)?/models/gemini-2\.5-flash:(generateContent|streamGenerateContent)(\?.*)?$")
class H(BaseHTTPRequestHandler):
    def address_string(self): return "unix"
    def log_message(self, *a): pass
    def _send(self, code, body, ctype="application/json"):
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
    def do_GET(self): self._send(403, b'{"error":"forbidden"}')
    def do_POST(self):
        path = re.sub(r"([?&])key=[^&]*", r"\1", self.path).replace("?&", "?").rstrip("?&")
        open(LEDGER + ".paths", "a").write(path.split("?")[0] + "\n")
        if not ALLOWED.match(path): return self._send(403, b'{"error":"forbidden path"}')
        with lock:
            if state["cost"] >= CAP: return self._send(429, json.dumps({"error": {"code": 429, "message": "lc1a0 cost cap reached", "status": "RESOURCE_EXHAUSTED"}}).encode())
        body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        url = "https://generativelanguage.googleapis.com" + (path if path.startswith("/v1beta/") else "/v1beta" + path)
        req = urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": "application/json", "x-goog-api-key": KEY})
        try:
            with urllib.request.urlopen(req, timeout=300) as r: code, data = r.status, r.read()
        except urllib.error.HTTPError as e: code, data = e.code, e.read()
        except Exception as e: code, data = 502, json.dumps({"error": str(e)}).encode()
        try:
            um = None
            try: um = json.loads(data).get("usageMetadata")
            except Exception:
                for line in data.decode(errors="replace").splitlines():
                    line = line.strip().removeprefix("data:").strip()
                    if line.startswith("{"):
                        try: um = json.loads(line).get("usageMetadata") or um
                        except Exception: pass
            if um:
                i = um.get("promptTokenCount", 0); ca = um.get("cachedContentTokenCount", 0); o = um.get("candidatesTokenCount", 0) + um.get("thoughtsTokenCount", 0)
                with lock:
                    state["calls"] += 1; state["in"] += i; state["cached"] = state.get("cached", 0) + ca; state["out"] += o
                    state["cost"] += (i - ca) * PIN + ca * PCACHE + o * POUT
                    json.dump(dict(state, ts=time.strftime("%FT%T%z"), price_table="gemini-2.5-flash: $0.30/M uncached input, $0.03/M cached input, $2.50/M output incl. thinking (litellm model_cost)"), open(LEDGER, "w"))
            else:
                with lock: state["unmetered_responses"] = state.get("unmetered_responses", 0) + 1
        except Exception: pass
        self._send(code, data, self.headers.get("Accept", "application/json") if False else "application/json")
class S(socketserver.ThreadingMixIn, socketserver.UnixStreamServer): daemon_threads = True
if os.path.exists(SOCK): os.unlink(SOCK)
srv = S(SOCK, H); os.chmod(SOCK, 0o777); srv.serve_forever()
