"""The webcam demo on a real ESP32-S3 DevKit running board.bin: camera.py's Peer, on the board's
COM (USB-UART) port instead of the simulator's UART1. The chip's log is on its other, native USB port.
Usage: python3 board.py /dev/cu.usbserial-0001   (needs pyserial)"""
import sys
import serial
from camera import Peer


class Ctx:
    def __init__(self, port):
        self.port = port

    def send(self, data):
        self.port.write(data)


port = serial.Serial(None, 921600, timeout=1)   # board.bin's CAM_BAUD
port.port = sys.argv[1]
port.dtr = port.rts = False   # on a DevKit these drive EN and GPIO0: leave the chip running
port.open()
peer = Peer(Ctx(port))   # no handshake: the chip asks again after 2 s if it missed us
while True:
    for b in port.read(max(1, port.in_waiting)):
        peer.on_byte(b)
