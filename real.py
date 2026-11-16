"""Runs a demo's scripted peer against a real ESP32-S3 instead of the simulator: the same Peer
class, with its bytes on a serial port (the board's COM / USB-UART port, wired to UART0).
Everything the board sends is also printed, as the simulator prints UART0; with a log port (the
native USB port of a board whose log is there), that port's text is printed instead.
Usage: python3 real.py <port> <baud> <peer.py> <seconds> [log port]   (needs pyserial)"""
import importlib.util, os, sys, threading, time
import serial

port_name, baud, peer_file, seconds = sys.argv[1], int(sys.argv[2]), sys.argv[3], float(sys.argv[4])
spec = importlib.util.spec_from_file_location("peer", peer_file)
mod = importlib.util.module_from_spec(spec)
sys.path.insert(0, os.path.dirname(os.path.abspath(peer_file)))
spec.loader.exec_module(mod)


class Ctx:
    config = None

    def __init__(self, port):
        self.port = port

    def send(self, data):
        self.port.write(data)


port = serial.Serial(None, baud, timeout=0.1)
port.port = port_name
port.dtr = port.rts = False   # on a DevKit DTR/RTS drive GPIO0 and EN: open without touching them
port.open()
peer = mod.Peer(Ctx(port))
port.rts = True               # then reset the chip, so it boots while we listen
time.sleep(0.1)
port.rts = False

def echo(name):
    # The native USB port drops off the bus while the chip resets: reopen until it is back.
    while True:
        try:
            with serial.Serial(name, 115200, timeout=0.1) as p:
                while True:
                    sys.stdout.write(p.read(max(1, p.in_waiting)).decode(errors="replace"))
                    sys.stdout.flush()
        except (OSError, serial.SerialException):
            time.sleep(0.2)


log = len(sys.argv) > 5
if log:
    threading.Thread(target=echo, args=(sys.argv[5],), daemon=True).start()

end = time.time() + seconds
while time.time() < end:
    data = port.read(max(1, port.in_waiting))
    if not log:
        sys.stdout.write(data.decode(errors="replace"))
        sys.stdout.flush()
    for b in data:
        peer.on_byte(b)
