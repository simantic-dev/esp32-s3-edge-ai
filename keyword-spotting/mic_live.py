"""Live I2S microphone for the micro_speech demo: the Mac's default input, captured by ffmpeg at
16 kHz mono, fed to the S3's I2S0 data line. Run the sim with --real-time so it asks for samples
at the pace the microphone makes them.
MIC_CMD overrides the capture command (anything writing s16le 16 kHz mono to stdout).
MIC_GAIN scales the samples (default 1.0); output is clipped to int16 because the example's
>>14 would wrap a louder word."""
import array, os, shlex, subprocess, sys, threading

CMD = os.environ.get("MIC_CMD", "ffmpeg -loglevel error -f avfoundation -i :default -ar 16000 -ac 1 -f s16le -")
GAIN = float(os.environ.get("MIC_GAIN", "1"))
MAX_BACKLOG = 16000 * 2 // 4   # bytes: keep at most 250 ms queued so the sim never lags the room


class Peer:
    def __init__(self, ctx):
        self.buf = bytearray()
        self.lock = threading.Lock()
        self.proc = subprocess.Popen(shlex.split(CMD), stdout=subprocess.PIPE)
        threading.Thread(target=self.pump, daemon=True).start()

    def pump(self):
        while chunk := self.proc.stdout.read(640):   # 20 ms
            with self.lock:
                self.buf += chunk
                del self.buf[:max(0, len(self.buf) - MAX_BACKLOG) & ~1]

    def sd_bytes(self, n):
        frames = n // 8
        with self.lock:
            raw = bytes(self.buf[:frames * 2]); del self.buf[:frames * 2]
        a = array.array("h", raw)
        if sys.byteorder != "little":
            a.byteswap()
        out = bytearray(n)   # frames the mic has not produced yet stay silent
        for f, s in enumerate(a):
            s = max(-32768, min(32767, int(s * GAIN)))
            out[8 * f:8 * f + 4] = ((s << 14) & 0xFFFFFFFF).to_bytes(4, "big")
        return bytes(out)
