# host: TCP 127.0.0.1:<port> -> per-connection `docker exec -i <cid> python3 /lc_oh/stdio_relay.py`
import socket, subprocess, sys, threading
cid, port = sys.argv[1], int(sys.argv[2])
def handle(c):
    p = subprocess.Popen(["docker", "exec", "-i", cid, "python3", "/lc_oh/stdio_relay.py"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, bufsize=0)
    def up():
        try:
            while (d := c.recv(65536)): p.stdin.write(d)
        except OSError: pass
        try: p.stdin.close()
        except OSError: pass
    threading.Thread(target=up, daemon=True).start()
    try:
        while (d := p.stdout.read1(65536) if hasattr(p.stdout, "read1") else p.stdout.read(65536)): c.sendall(d)
    except OSError: pass
    c.close(); p.kill()
srv = socket.socket(); srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); srv.bind(("127.0.0.1", port)); srv.listen(64)
while True:
    c, _ = srv.accept(); threading.Thread(target=handle, args=(c,), daemon=True).start()
