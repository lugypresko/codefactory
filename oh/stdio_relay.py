# runs INSIDE the sandbox via `docker exec -i`: bridges stdin/stdout <-> TCP 127.0.0.1:8000 (agent server)
import socket, sys, threading, os
s = socket.create_connection(("127.0.0.1", 8000))
def up():
    while (d := os.read(0, 65536)): s.sendall(d)
    s.shutdown(socket.SHUT_WR)
threading.Thread(target=up, daemon=True).start()
while (d := s.recv(65536)): os.write(1, d)
