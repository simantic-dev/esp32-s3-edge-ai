"""Webcam on the S3's UART1 for the face detector (app_main.cpp has the protocol).
ffmpeg captures 640x480; each "F" from the chip gets the newest frame shrunk to 160x120 RGB888.
The boxes the chip sends back are drawn on the live video in an ffplay window, so the video
stays at camera rate and the boxes update at whatever rate the simulated chip manages.
CAM_CMD overrides the capture command (anything writing 640x480 rgb24 to stdout)."""
import os, shlex, subprocess, threading, time

W, H, S = 640, 480, 4          # capture size; the chip gets W/S x H/S
CMD = os.environ.get("CAM_CMD",
    "ffmpeg -loglevel error -f avfoundation -framerate 30 -video_size 1280x720 -i 0:none "
    f"-vf crop=ih*4/3:ih,scale={W}:{H},hflip -pix_fmt rgb24 -f rawvideo -")
VIEW = (f"ffplay -loglevel error -autoexit -window_title esp32-s3-face-detect -f rawvideo "
        f"-pixel_format rgb24 -video_size {W}x{H} -i -")
GREEN = b"\x00\xff\x00"


def shrink(frame):
    out = bytearray(W // S * H // S * 3)
    row = W // S * 3
    for y in range(H // S):
        src = frame[y * S * W * 3:(y * S + 1) * W * 3]
        for c in range(3):
            out[y * row + c:(y + 1) * row:3] = src[c::S * 3]
    return bytes(out)


def draw(frame, boxes, t=3):
    for x1, y1, x2, y2 in boxes:
        x1, x2 = max(0, x1), min(W - 1, x2)
        y1, y2 = max(0, y1), min(H - 1, y2)
        if x2 <= x1 or y2 <= y1:
            continue
        for y in range(y1, y2 + 1):
            o = y * W * 3
            if y < y1 + t or y > y2 - t:
                frame[o + x1 * 3:o + (x2 + 1) * 3] = GREEN * (x2 - x1 + 1)
            else:
                frame[o + x1 * 3:o + (x1 + t) * 3] = GREEN * t
                frame[o + (x2 - t + 1) * 3:o + (x2 + 1) * 3] = GREEN * t


class Peer:
    def __init__(self, ctx):
        self.ctx = ctx
        self.line = b""
        self.latest = None
        self.boxes, self.pending = [], []
        self.frames, self.t0 = 0, time.time()
        self.cam = subprocess.Popen(shlex.split(CMD), stdout=subprocess.PIPE)
        self.view = subprocess.Popen(shlex.split(VIEW), stdin=subprocess.PIPE)
        threading.Thread(target=self.pump, daemon=True).start()

    def pump(self):
        while len(f := self.cam.stdout.read(W * H * 3)) == W * H * 3:
            self.latest = f
            shown = bytearray(f)
            draw(shown, self.boxes)
            try:
                self.view.stdin.write(shown)
            except BrokenPipeError:   # viewer window closed
                os._exit(0)

    def on_byte(self, b):
        if b != 0x0A:
            self.line += bytes([b])
            return
        line, self.line = self.line.decode(errors="replace").split(), b""
        if line == ["F"]:
            while self.latest is None:
                time.sleep(0.01)
            self.ctx.send(shrink(self.latest))
        elif line[:1] == ["B"] and len(line) == 6:
            self.pending.append(tuple(int(v) * S for v in line[1:5]))
        elif line[:1] == ["E"]:
            self.boxes, self.pending = self.pending, []
            self.frames += 1
            fps = self.frames / (time.time() - self.t0)
            print(f"chip: {len(self.boxes)} face(s), inference {line[1]} ms, {fps:.1f} results/s", flush=True)
