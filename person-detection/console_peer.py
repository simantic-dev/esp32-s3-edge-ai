# Types at the example's UART0 console (console.board puts it on uart0):
# one `detect_image <n>` per `esp> ` prompt. The prompt only comes back when the previous command
# has returned, so inferences never overlap.
PROMPT = b"esp> "


class Peer:
    def __init__(self, ctx):
        self.ctx = ctx
        self.tail = b""
        self.images = list((getattr(ctx, "config", None) or {}).get("images", range(10)))

    def on_byte(self, b):
        self.tail = (self.tail + bytes([b]))[-len(PROMPT):]
        if self.tail == PROMPT and self.images:
            self.ctx.send(b"detect_image %d\n" % self.images.pop(0))
            self.tail = b""
