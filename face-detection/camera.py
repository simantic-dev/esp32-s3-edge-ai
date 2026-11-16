"""Webcam on the S3's UART0 for the face detector (app_main.cpp has the protocol).
ffmpeg captures 640x480; each "F" from the chip gets the newest frame shrunk to 160x120 RGB888.
The ffplay window is split: on the left the live camera, on the right the last frame the chip
was sent, as the chip got it (160x120, scaled up), with the boxes it answered for that frame.
The right side lags by design: it changes only when the chip answers.
CAM_CMD overrides the capture command (anything writing 640x480 rgb24 to stdout)."""
import os, shlex, subprocess, threading, time

W, H, S = 640, 480, 4          # capture size; the chip gets W/S x H/S
CMD = os.environ.get("CAM_CMD",
    "ffmpeg -loglevel error -f avfoundation -framerate 30 -video_size 1280x720 -pixel_format nv12 -i 0:none "
    f"-vf crop=ih*4/3:ih,scale={W}:{H},hflip -pix_fmt rgb24 -f rawvideo -")
VIEW = (f"ffplay -loglevel error -autoexit -window_title esp32-s3-face-detect -f rawvideo "
        f"-pixel_format rgb24 -video_size {2 * W}x{H} -i -")
GREEN = b"\x00\xff\x00"


def shrink(frame):
    out = bytearray(W // S * H // S * 3)
    row = W // S * 3
    for y in range(H // S):
        src = frame[y * S * W * 3:(y * S + 1) * W * 3]
        for c in range(3):
            out[y * row + c:(y + 1) * row:3] = src[c::S * 3]
    return bytes(out)


def enlarge(small):
    """160x120 back to 640x480, each pixel a 4x4 block: what the chip saw, at screen size."""
    out = bytearray(W * H * 3)
    for y in range(H // S):
        src = small[y * W // S * 3:(y + 1) * W // S * 3]
        row = b"".join(src[i:i + 3] * S for i in range(0, len(src), 3))
        for r in range(S):
            out[(y * S + r) * W * 3:(y * S + r + 1) * W * 3] = row
    return out


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
        self.latest, self.n = None, 0   # newest camera frame and its number
        self.sent = None                  # the frame the chip is working on, as it got it
        self.right = bytes(W * H * 3)     # that frame with its boxes, once answered
        self.pending = []
        self.frames, self.t0 = 0, time.time()
        self.cam = subprocess.Popen(shlex.split(CMD), stdout=subprocess.PIPE)
        self.view = subprocess.Popen(shlex.split(VIEW), stdin=subprocess.PIPE)
        threading.Thread(target=self.grab, daemon=True).start()
        threading.Thread(target=self.show, daemon=True).start()

    def grab(self):
        # Read the camera as fast as it delivers and keep only the newest frame, so a slow
        # display drops frames instead of queueing them (a queue is lag that keeps growing).
        while len(f := self.cam.stdout.read(W * H * 3)) == W * H * 3:
            self.latest, self.n = f, self.n + 1

    def show(self):
        shown = 0
        while True:
            f, n = self.latest, self.n
            if f is None or n == shown:
                time.sleep(0.005)
                continue
            right, row = self.right, W * 3
            out = b"".join(f[y * row:(y + 1) * row] + right[y * row:(y + 1) * row] for y in range(H))
            try:
                self.view.stdin.write(out)
                shown = n
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
            self.sent = shrink(self.latest)
            self.ctx.send(self.sent)
        elif line[:1] == ["B"] and len(line) == 6:
            self.pending.append(tuple(int(v) * S for v in line[1:5]))
        elif line[:1] == ["E"]:
            boxes, self.pending = self.pending, []
            if self.sent is not None:
                right = enlarge(self.sent)
                draw(right, boxes)
                self.right = bytes(right)
            self.frames += 1
            fps = self.frames / (time.time() - self.t0)
            print(f"chip: {len(boxes)} face(s), inference {line[1]} ms, {fps:.1f} results/s", flush=True)
