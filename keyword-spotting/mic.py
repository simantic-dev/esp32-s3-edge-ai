"""I2S MEMS microphone (an ICS-43434 class part with L/R tied low) on ESP32-S3 I2S0 for Espressif's
micro_speech example. The firmware is the bus master: 16 kHz, 64 BCK per frame. The mic answers in
the left slot, MSB first, and leaves the right slot undriven (reads low).

It plays the clips the example itself ships in test_data/ (16 kHz, 16-bit mono, from TFLM's
micro_speech test set): the "silence" clip on repeat, with "yes" and "no" laid over it at the
TIMELINE offsets (ms of audio since the firmware started the receiver).

Why those offsets: the stock example classifies back-to-back windows of about a second, not a
sliding one. Each loop() pulls up to 49 new 20 ms slices from its ring buffer and blocks until the
microphone has delivered them, so a word is heard only when it sits inside one window. The windows
end near 1000, 2000 and 2950 ms; "yes" at 1000 ms and "no" at 2000 ms fill one each, as the two
clips do in TFLM's own test. The quiet in the clips themselves (about 550 ms between the two
words) is the pause; a "no" laid across two windows is reported twice or not at all.

Level: a clip sample s goes out as the 32-bit slot word s << 14, a quarter of the slot's full scale.
The example's ESP32-S3 path shifts each word right by 14 to get its int16, so the firmware works on
the clip's own samples; a louder mic would wrap in that shift on the "yes" clip (peak 31238)."""
import array
import os
import sys
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
TIMELINE = [(1000, "yes"), (2000, "no")]


def clip(name):
    with wave.open(os.path.join(HERE, name + "_1000ms.wav")) as w:
        assert (w.getnchannels(), w.getsampwidth(), w.getframerate()) == (1, 2, 16000), name
        a = array.array("h", w.readframes(w.getnframes()))
    if sys.byteorder != "little":
        a.byteswap()
    return a


class Peer:
    def __init__(self, ctx):
        self.silence = clip("silence")
        self.clips = [(ms * 16, clip(name)) for ms, name in TIMELINE]
        self.i = 0

    def sample(self, k):
        for start, data in self.clips:
            if start <= k < start + len(data):
                return data[k - start]
        return self.silence[k % len(self.silence)]

    def sd_bytes(self, n):
        out = bytearray(n)  # 8 bytes a frame: left slot, then the right slot left at zero
        for f in range(n // 8):
            out[8 * f:8 * f + 4] = ((self.sample(self.i + f) << 14) & 0xFFFFFFFF).to_bytes(4, "big")
        self.i += n // 8
        return bytes(out)
