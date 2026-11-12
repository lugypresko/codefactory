# runs INSIDE the sandbox (network none): TCP 127.0.0.1:4000 -> UNIX socket /lc_sock/llm.sock (host LLM proxy)
import socket, threading, os
def pipe(a, b):
    try:
        while (d := a.recv(65536)): b.sendall(d)
    except OSError: pass
    finally:
        for s in (a, b):
            try: s.shutdown(socket.SHUT_RDWR)
            except OSError: pass
srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); srv.bind(("127.0.0.1", 4000)); srv.listen(64)
while True:
    c, _ = srv.accept(); u = socket.socket(socket.AF_UNIX); u.connect("/lc_sock/llm.sock")
    threading.Thread(target=pipe, args=(c, u), daemon=True).start(); threading.Thread(target=pipe, args=(u, c), daemon=True).start()
