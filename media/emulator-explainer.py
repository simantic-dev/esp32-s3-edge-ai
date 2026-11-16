#!/usr/bin/env python3
"""Renders media/emulator-explainer.mp4: 15 s, 1920x1080, 30 fps, in the style of Simantic's
explainer videos (light dot-grid page, outlined cards, caption block, step tracker).

    python3 media/emulator-explainer.py            # render the video
    python3 media/emulator-explainer.py 1 4 7      # write still-<t>.png beside the video instead

Needs Pillow and ffmpeg. Fonts: Source Sans 3 and IBM Plex Mono, read from TeX Live (set FONT_DIR
to a folder holding the same .otf files otherwise). The wordmark is the site's
public/simantic_logo_4_full_transparent.png (LOGO overrides the path). Drawn at 2x, scaled down.
"""
import os, random, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

W, H, FPS, SECONDS, S = 1920, 1080, 30, 15, 2
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "emulator-explainer.mp4")
LOGO = os.environ.get("LOGO", os.path.expanduser("~/dev/simantic/simantic/public/simantic_logo_4_full_transparent.png"))
BAUD = "2,000,000"

BG, GRID, CARD, INK, MUTED, FAINT, RULE = "#f9faf5", "#e4e5e0", "#ffffff", "#111111", "#4a6275", "#aab7ba", "#d6d9d2"
TEAL, AMBER, CODE = "#337c78", "#a47632", "#f3f4ef"

TEXLIVE = "/usr/local/texlive/2026/texmf-dist/fonts/opentype"
FONT_FILES = {
    "sans": "adobe/sourcesans/SourceSans3-Regular.otf", "semi": "adobe/sourcesans/SourceSans3-Semibold.otf",
    "mono": "ibm/plex/IBMPlexMono-Regular.otf", "monom": "ibm/plex/IBMPlexMono-Medium.otf",
}
_fonts = {}


def font(name, size):
    if (name, size) not in _fonts:
        d = os.environ.get("FONT_DIR")
        path = os.path.join(d, os.path.basename(FONT_FILES[name])) if d else os.path.join(TEXLIVE, FONT_FILES[name])
        _fonts[name, size] = ImageFont.truetype(path, size * S)
    return _fonts[name, size]


def rgba(c, a=1.0):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) + (int(255 * max(0.0, min(1.0, a))),)


def sc(*v):
    return [x * S for x in v]


def text(d, x, y, s, f="sans", size=24, fill=INK, a=1.0, anchor="la"):
    if a > 0.01:
        d.text((x * S, y * S), s, font=font(f, size), fill=rgba(fill, a), anchor=anchor)


def width(s, f, size):
    return font(f, size).getlength(s) / S


def box(d, x0, y0, x1, y1, r=0, fill=None, outline=None, w=1, a=1.0):
    if a > 0.01:
        d.rounded_rectangle(sc(x0, y0, x1, y1), r * S, fill=fill and rgba(fill, a),
                            outline=outline and rgba(outline, a), width=max(1, int(w * S)))


def line(d, pts, fill, w=1, a=1.0):
    if a > 0.01:
        d.line(sc(*pts), fill=rgba(fill, a), width=max(1, int(w * S)))


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def ramp(t, t0, t1):
    return ease((t - t0) / (t1 - t0))


def span(t, t0, t1, d=0.3):
    """1 between t0 and t1, fading over d seconds at each end."""
    return ramp(t, t0, t0 + d) * (1 - ramp(t, t1 - d, t1))


# Real disassembly of face-detection/flash.bin (xtensa-esp32s3-elf-objdump -D -b binary), file offsets.
DISASM = [l.split(" ", 3) for l in """\
120b60: 0417dc ee.src.q.qup q0, q1, q2
120b63: d0e0e3 rur.sar_byte a14
120b66: f2cff0 addi a15, a15, -16
120b69: 548cad ee.ld.128.usar.xp q5, a5, a12
120b6c: caff add.n a15, a15, a12
120b6e: 34c7ec ee.src.q.qup q3, q4, q5
120b71: c4031a ee.vmulas.s8.accx q3, q0
120b74: 164c04 beqz a12, 0x120bbc
120b77: 5480a3 ee.vld.128.ip q5, a5, 0
120b7a: 34c3ec ee.src.q q3, q4, q5
120b7d: f40091 ee.ld.128.usar.ip q2, a15, 0
120b80: e00df3 wur.sar_byte a14
120b83: 0413dc ee.src.q q0, q1, q2
120b86: 0cf7 movi.n a7, 15
120b88: c077c0 sub a7, a7, a12
120b8b: 0c0e movi.n a14, 0
120b8d: 740e96 ee.slcxxp.2q q2, q0, a7, a14
120b90: 74bea6 ee.slcxxp.2q q5, q3, a7, a14
120b93: c4031a ee.vmulas.s8.accx q3, q0
120b96: 860800 j 0x120bbc
120b99: 540cad ee.ld.128.usar.xp q4, a5, a12
120b9c: 5480a3 ee.vld.128.ip q5, a5, 0
120b9f: 34c3ec ee.src.q q3, q4, q5
120ba2: f48c8d ee.ld.128.usar.xp q1, a15, a12
120ba5: f40093 ee.vld.128.ip q2, a15, 0
120ba8: 0413dc ee.src.q q0, q1, q2
120bab: 0cf7 movi.n a7, 15
120bad: c077c0 sub a7, a7, a12
120bb0: e2a000 movi a14, 0
120bb3: 740e96 ee.slcxxp.2q q2, q0, a7, a14
120bb6: 74bea6 ee.slcxxp.2q q5, q3, a7, a14
120bb9: c4031a ee.vmulas.s8.accx q3, q0
120bbc: aaff add.n a15, a15, a10
120bbe: 963605 bltz a6, 0x120c15
120bc1: f48181 ee.ld.128.usar.ip q1, a15, 16
120bc4: 5401a1 ee.ld.128.usar.ip q4, a5, 16
120bc7: f40191 ee.ld.128.usar.ip q2, a15, 16
120bca: 76a60e loopgtz a6, 0x120bdc
120bcd: 0417dc ee.src.q.qup q0, q1, q2
120bd0: 5481a1 ee.ld.128.usar.ip q5, a5, 16
120bd3: 34c7ec ee.src.q.qup q3, q4, q5
120bd6: f40191 ee.ld.128.usar.ip q2, a15, 16
120bd9: c4031a ee.vmulas.s8.accx q3, q0
120bdc: 0417dc ee.src.q.qup q0, q1, q2
120bdf: d0e0e3 rur.sar_byte a14
120be2: f2cff0 addi a15, a15, -16
120be5: 548cad ee.ld.128.usar.xp q5, a5, a12
120be8: caff add.n a15, a15, a12
120bea: 34c7ec ee.src.q.qup q3, q4, q5
120bed: c4031a ee.vmulas.s8.accx q3, q0
120bf0: 164c04 beqz a12, 0x120c38
120bf3: 5480a3 ee.vld.128.ip q5, a5, 0
120bf6: 34c3ec ee.src.q q3, q4, q5
120bf9: f40091 ee.ld.128.usar.ip q2, a15, 0
120bfc: e00df3 wur.sar_byte a14
120bff: 0413dc ee.src.q q0, q1, q2
120c02: 0cf7 movi.n a7, 15
120c04: c077c0 sub a7, a7, a12
120c07: 0c0e movi.n a14, 0
120c09: 740e96 ee.slcxxp.2q q2, q0, a7, a14
120c0c: 74bea6 ee.slcxxp.2q q5, q3, a7, a14
120c0f: c4031a ee.vmulas.s8.accx q3, q0
120c12: 860800 j 0x120c38
120c15: 540cad ee.ld.128.usar.xp q4, a5, a12
120c18: 5480a3 ee.vld.128.ip q5, a5, 0
120c1b: 34c3ec ee.src.q q3, q4, q5
120c1e: f48c8d ee.ld.128.usar.xp q1, a15, a12
120c21: f40093 ee.vld.128.ip q2, a15, 0
120c24: 0413dc ee.src.q q0, q1, q2
120c27: 0cf7 movi.n a7, 15""".splitlines()]

# (start, end, step label, headline, detail): the caption block, one per beat.
BEATS = [
    (0.0, 2.2, "WEBCAM", "It looks like the laptop is running the AI.", ""),
    (2.2, 5.4, "FRAMES IN", "It isn't. The laptop only sends camera frames.",
     f"160×120 RGB into the chip's UART0 at {BAUD} baud, as a real board's USB-serial port gets it."),
    (5.4, 10.0, "EXECUTE", "The detector runs inside an emulated ESP32-S3.",
     "Real compiled firmware: about 97,000 Xtensa vector (PIE) instructions, each charged its cycles."),
    (10.0, 12.4, "ANSWER", "The chip answers in text. The laptop only draws the box.",
     "One line per face, B x1 y1 x2 y2 score, then E <ms>, back over the same UART."),
    (12.4, 14.2, "COMPARE", "The same file on a real ESP32-S3 gives the same answer.",
     "Inference runs on an emulated ESP32-S3. Not the laptop."),
]
STEPS = ["Webcam", "Frames in", "Execute", "Answer", "Compare with the chip"]
SUBJECT = "Face detection on a simulated ESP32-S3"
CONTENT_X0, CONTENT_X1 = 80, 1840


def background():
    img = Image.new("RGB", (W * S, H * S), BG)
    d = ImageDraw.Draw(img)
    for y in range(7, H, 14):                                                     # the dot grid
        for x in range(7, W, 14):
            d.rectangle(sc(x, y, x + 1, y + 1), fill=GRID)
    return img


def wordmark(h, color=INK):
    """The site's wordmark, recoloured for a light page: mark and letters in `color`, its dot white."""
    src = Image.open(LOGO).convert("RGBA")
    src = src.resize((round(src.width * h * S / src.height), h * S), Image.LANCZOS)
    out = Image.new("RGBA", src.size)
    ink = rgba(color)[:3]
    px, po = src.load(), out.load()
    for y in range(src.height):
        for x in range(src.width):
            r, g, b, a = px[x, y]
            po[x, y] = (255, 255, 255, a) if r + g + b < 384 else ink + (a,)   # dark dot -> white, white -> ink
    return out


def card(d, x0, y0, x1, y1, title=None, dot=None, label=None, a=1.0):
    """White card, 1px ink border, with the second outline offset behind it; optional header row."""
    box(d, x0 + 5, y0 + 5, x1 + 5, y1 + 5, 4, fill=CARD, outline=INK, a=a)
    box(d, x0, y0, x1, y1, 4, fill=CARD, outline=INK, a=a)
    if title:
        d.ellipse(sc(x0 + 22, y0 + 26, x0 + 32, y0 + 36), fill=rgba(dot or INK, a))
        text(d, x0 + 44, y0 + 31, title, "semi", 22, INK, a, "lm")
    if label:
        text(d, x1 - 22, y0 + 31, label, "mono", 17, MUTED, a, "rm")


def chrome(img, d, t, logo):
    img.alpha_composite(logo, (80 * S, 42 * S)) if img.mode == "RGBA" else img.paste(logo, (80 * S, 42 * S), logo)
    text(d, CONTENT_X1, 64, SUBJECT, "sans", 21, MUTED, anchor="rm")
    line(d, (CONTENT_X0, 112, CONTENT_X1, 112), INK, 1)
    cur = max(i for i, b in enumerate(BEATS) if t >= b[0] or i == 0)
    n = len(STEPS)
    xs = [CONTENT_X0 + (CONTENT_X1 - CONTENT_X0) * i / (n - 1) for i in range(n)]
    for i, (x, s) in enumerate(zip(xs, STEPS)):
        c = INK if i <= cur else FAINT
        anchor = "rm" if i == n - 1 else "lm"
        tx = x if i < n - 1 else CONTENT_X1
        lw = width(s, "semi" if i == cur else "sans", 21)
        dx = tx - lw - 16 if i == n - 1 else tx
        d.ellipse(sc(dx - 1, 1015, dx + 9, 1025), fill=rgba(c))
        text(d, dx + 18, 1020, s, "semi" if i == cur else "sans", 21, c, anchor="lm")
        if i < n - 1:                                                              # the track to the next step
            nx = xs[i + 1] - (width(STEPS[i + 1], "sans", 21) + 16 if i + 1 == n - 1 else 0)
            line(d, (dx + 30 + lw, 1020, nx - 14, 1020), RULE if i >= cur else "#9aa4a8", 1)
    for t0, t1, label, head, sub in BEATS:
        a = span(t, t0, t1, 0.25) if t0 else 1 - ramp(t, t1 - 0.25, t1)
        text(d, CONTENT_X0, 870, label, "monom", 19, "#555b5e", a, "lm")
        text(d, 258, 868, head, "semi", 46, INK, a, "lm")
        text(d, 258, 922, sub, "sans", 28, MUTED, a, "lm")


def face(d, cx, cy, s, a=1.0):
    """A plain drawn face: no real person's likeness."""
    d.ellipse(sc(cx - 72 * s, cy - 84 * s, cx + 72 * s, cy + 84 * s), fill=rgba("#eceee8", a), outline=rgba(INK, a), width=max(1, int(2 * S)))
    for ex in (-28, 28):
        d.ellipse(sc(cx + (ex - 7) * s, cy - 22 * s, cx + (ex + 7) * s, cy - 8 * s), fill=rgba(INK, a))
    d.arc(sc(cx - 34 * s, cy - 4 * s, cx + 34 * s, cy + 46 * s), 25, 155, fill=rgba(INK, a), width=max(1, int(2 * S)))


def laptop(d, x0, t, dim):
    """The laptop card: webcam view with the box the laptop draws."""
    x1, y0, y1 = x0 + 470, 150, 790
    card(d, x0, y0, x1, y1, "Laptop", INK, "webcam · ffplay")
    vx0, vy0, vx1, vy1 = x0 + 30, y0 + 70, x1 - 30, y0 + 410
    box(d, vx0, vy0, vx1, vy1, 3, fill=CODE, outline=RULE)
    cx, cy = (vx0 + vx1) / 2, vy0 + 160
    d.chord(sc(cx - 130, cy + 96, cx + 130, cy + 330), 202.6, 337.4, fill=rgba("#d9ddd5"))
    face(d, cx, cy, 1)
    a = max(1 - ramp(t, 2.0, 2.4), ramp(t, 11.2, 11.4))                           # the box the laptop draws
    grow = 10 * (1 - ramp(t, 11.2, 11.6)) if t > 5 else 0
    box(d, cx - 88 - grow, cy - 100 - grow, cx + 88 + grow, cy + 100 + grow, 2, outline=TEAL, w=4, a=a)
    rows = (("sends camera frames", False), ("draws the box", False), ("runs no model", True))
    for i, (s, key) in enumerate(rows):
        y = vy1 + 50 + i * 44
        ra = ramp(t, 2.3 + i * 0.15, 2.7 + i * 0.15)
        d.ellipse(sc(x0 + 34, y - 5, x0 + 44, y + 5), fill=rgba(TEAL if key else RULE, ra))
        text(d, x0 + 58, y, s, "semi" if key else "sans", 24, INK if key else MUTED, ra, "lm")
    box(d, x0 - 2, y0 - 2, x1 + 8, y1 + 8, 0, fill=BG, a=0.55 * dim)               # steps back while the chip works


def token(d, x, y, s, lo, hi, kind="byte"):
    """A token on the wire, centred on x, fading near the lane ends."""
    w = width(s, "mono", 17) + 24
    a = min(ramp(x - w / 2, lo - 30, lo + 10), 1 - ramp(x + w / 2, hi - 10, hi + 30))
    if kind == "ask":
        box(d, x - w / 2, y - 16, x + w / 2, y + 16, 3, fill=TEAL, a=a)
        text(d, x, y, s, "monom", 17, CARD, a, "mm")
    else:
        box(d, x - w / 2, y - 16, x + w / 2, y + 16, 3, fill=CARD, outline=TEAL if kind == "reply" else INK, a=a)
        text(d, x, y, s, "mono", 17, TEAL if kind == "reply" else INK, a, "mm")


def wire(d, t):
    L, R, TOP, BOT = 590, 888, 430, 600
    text(d, (L + R) / 2, 312, "UART0", "semi", 30, INK, anchor="ma")
    text(d, (L + R) / 2, 352, f"{BAUD} baud", "mono", 18, MUTED, anchor="ma")
    line(d, (L + 76, TOP, R, TOP), INK, 1)
    d.polygon(sc(R + 2, TOP, R - 10, TOP - 6, R - 10, TOP + 6), fill=rgba(INK))
    line(d, (L, BOT, R, BOT), INK, 1)
    d.polygon(sc(L - 2, BOT, L + 10, BOT - 6, L + 10, BOT + 6), fill=rgba(INK))
    text(d, (L + 76 + R) / 2, 396, "57,600 bytes a frame", "mono", 16, MUTED, anchor="mm")
    text(d, (L + R) / 2, 640, 'the chip asks: "F"', "mono", 16, MUTED, span(t, 2.4, 9.9), "mm")
    text(d, (L + R) / 2, 640, "the chip replies in text", "mono", 16, MUTED, ramp(t, 10.0, 10.3), "mm")
    k = ramp(t, 3.0, 3.5)                                                          # webcam view -> 160x120 frame
    if t >= 3.0:
        src, dst = (110, 220, 520, 560), (L, TOP - 24, L + 64, TOP + 24)
        r = [s + (e - s) * k for s, e in zip(src, dst)]
        box(d, *r, 2, fill=CODE if k == 1 else None, outline=TEAL, w=2)
        if k == 1:
            for gx in range(1, 4):
                line(d, (L + gx * 16, TOP - 22, L + gx * 16, TOP + 22), RULE, 1)
            for gy in range(1, 3):
                line(d, (L + 2, TOP - 24 + gy * 16, L + 62, TOP - 24 + gy * 16), RULE, 1)
            text(d, L, TOP + 42, "160×120 RGB", "mono", 15, INK, anchor="lm")
    if 2.5 <= t < 3.2:
        token(d, R - (R - L) * (t - 2.5) / 0.7, BOT, "F", L, R, "ask")
    for i in range(14):                                                           # frame bytes: laptop -> chip
        x = L + 76 + (t - 3.5 - i * 0.15) * 330
        if 3.5 + i * 0.15 <= t and x < R + 40:
            token(d, x, TOP, f"{random.Random(i).randrange(256):02x}", L + 76, R)
    for s, t0 in (("B x1 y1 x2 y2 score", 10.1), ("E <ms>", 10.75)):              # the answer: chip -> laptop
        x = R + 110 - (t - t0) * 520
        if t >= t0 and x > L - 120:
            token(d, x, BOT, s, L, R, "reply")


def simulator(img, d, t):
    X0, Y0, X1, Y1 = 930, 150, 1840, 790
    card(d, X0, Y0, X1, Y1, "Pyrite simulator", TEAL, "ESP32-S3-WROOM-1-N8R2 model")
    text(d, X0 + 30, Y0 + 82, "ESP32-S3 (emulated)", "semi", 28, TEAL, anchor="lm")
    text(d, X1 - 30, Y0 + 82, "flash.bin", "mono", 17, MUTED, anchor="rm")
    text(d, X0 + 30, Y0 + 116, "dual-core Xtensa LX7 · 240 MHz · 2 MB PSRAM", "mono", 17, MUTED, anchor="lm")
    text(d, X0 + 30, Y0 + 142, "ESP-DL face detector · ESPDet-Pico · 224×224 · int8", "mono", 17, MUTED, anchor="lm")

    # inner-loop listing, the instruction now running highlighted, as in the inner-loop card
    LX0, LY0, LX1 = X0 + 30, Y0 + 172, X1 - 30
    card(d, LX0, LY0, LX1, LY0 + 262, "Inner loop of the detector", TEAL, "Xtensa + PIE")
    pc = 4 + 8.6 * (ramp(t, 5.2, 6.0) * 0.4 + max(0, min(t, 10.0) - 5.6)) if t > 5.2 else 4.0
    pc = min(pc, len(DISASM) - 4)
    running = 5.3 < t < 10.0
    ROWS, PITCH = 7, 27
    ly = LY0 + 64
    lst = Image.new("RGB", (int((LX1 - LX0 - 30) * S), ROWS * PITCH * S), CARD)
    ld = ImageDraw.Draw(lst, "RGBA")
    top = max(0, int(pc + 0.5) - ROWS // 2)                                       # whole rows; the highlight steps
    for i in range(top, top + ROWS):
        if i >= len(DISASM):
            continue
        addr, _, op, args = DISASM[i]
        y = (i - top) * PITCH + PITCH / 2
        cur = i == int(pc + 0.5)
        if cur:
            box(ld, 0, y - 13, LX1 - LX0 - 30, y + 13, 2, fill=TEAL, a=1 if running else 0.15)
        fg = CARD if cur and running else INK
        text(ld, 12, y, addr[2:-1], "mono", 18, CARD if cur and running else MUTED, anchor="lm")
        text(ld, 110, y, op, "monom" if "vmulas" in op else "mono", 18, fg if cur and running else (TEAL if "vmulas" in op else INK), anchor="lm")
        text(ld, 450, y, args, "mono", 18, fg, anchor="lm")
    img.paste(lst, (int((LX0 + 15) * S), int(ly * S)))

    # the latest ee.vmulas.s8.accx: two 16-lane int8 vectors and the accumulator they feed
    done = [i for i in range(int(pc + 0.5) + 1) if "vmulas" in DISASM[i][2]]
    vr = random.Random(len(done))
    q3 = [vr.randrange(-128, 128) for _ in range(16)]
    q0 = [vr.randrange(-128, 128) for _ in range(16)]
    acc = 0
    for n in range(len(done) // 3 * 3, len(done) + 1):
        r = random.Random(n)
        a3 = [r.randrange(-128, 128) for _ in range(16)]
        acc += sum(x * y for x, y in zip(a3, [r.randrange(-128, 128) for _ in range(16)]))
    if not done:
        q3, q0, acc = [0] * 16, [0] * 16, 0
    flash = 1 - min(1, (pc + 0.5 - done[-1]) / 2.5) if done and running else 0
    vy = LY0 + 296
    text(d, LX0, vy - 8, "VECTOR LANES, LATEST MULTIPLY-ADD", "monom", 16, "#555b5e", anchor="lm")
    for row, (name, vals) in enumerate((("q3", q3), ("q0", q0))):
        ry = vy + 16 + row * 40
        text(d, LX0, ry + 16, name, "monom", 18, TEAL, anchor="lm")
        for i, v in enumerate(vals):
            x = LX0 + 44 + i * 49
            box(d, x, ry, x + 45, ry + 32, 2, fill=CARD, outline=INK)
            box(d, x, ry, x + 45, ry + 32, 2, fill=TEAL, a=0.18 * flash)
            text(d, x + 22.5, ry + 16, str(v), "mono", 14, INK, anchor="mm")
    text(d, LX0, vy + 124, "ee.vmulas.s8.accx", "monom", 19, TEAL, anchor="lm")
    text(d, LX0 + 214, vy + 124, f"ACCX += sum(q3[i] × q0[i])  =  {acc:,}", "mono", 19, INK, anchor="lm")
    text(d, LX1, vy + 124, "16 × int8", "mono", 16, MUTED, anchor="rm")


def board(d, x0, y0, x1, y1, color, sim, a):
    """A DevKit drawn in outline: solid ink for the real board, dashed teal for the model."""
    def edge(p0, p1):
        if not sim:
            line(d, (*p0, *p1), INK, 1.5, a)
            return
        (ax, ay), (bx, by) = p0, p1
        n = int(max(abs(bx - ax), abs(by - ay)) // 10)
        for k in range(0, n, 2):
            f0, f1 = k / n, min(1, (k + 1) / n)
            line(d, (ax + (bx - ax) * f0, ay + (by - ay) * f0, ax + (bx - ax) * f1, ay + (by - ay) * f1), TEAL, 1.5, a)
    if sim:
        box(d, x0, y0, x1, y1, 8, fill="#e8f0ee", a=a)
    for p0, p1 in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        edge(p0, p1)
    for x in range(int(x0) + 60, int(x1) - 20, 10):                               # header pins
        d.rectangle(sc(x, y0 + 12, x + 3, y0 + 15), fill=rgba(INK if not sim else TEAL, a))
        d.rectangle(sc(x, y1 - 15, x + 3, y1 - 12), fill=rgba(INK if not sim else TEAL, a))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    box(d, cx - 46, cy - 34, cx + 46, cy + 34, 3, fill=color, a=a)                 # the S3
    d.ellipse(sc(cx - 38, cy + 22, cx - 32, cy + 28), fill=rgba(CARD, a))
    for side in (x0 - 8, x1 - 2):                                                  # the two USB ports
        box(d, side, cy - 16, side + 10, cy + 16, 2, fill=CARD, outline=INK if not sim else TEAL, a=a)


def compare(d, t):
    a = ramp(t, 12.4, 12.8)
    rows = (("score", "0.893"), ("box", "[98 57 198 194]"), ("inference", None))
    for k, (x0, title, dot, label, sim, timing) in enumerate((
            (80, "Real board", AMBER, "ESP32-S3 · 2 MB PSRAM", False, "278 ms"),
            (980, "Pyrite simulator", TEAL, "ESP32-S3-WROOM-1-N8R2 model", True, "191 ms"))):
        ca = a * ramp(t, 12.4 + k * 0.2, 12.8 + k * 0.2)
        x1 = x0 + 860
        card(d, x0, 150, x1, 700, title, dot, label, ca)
        board(d, x0 + 150, 230, x1 - 150, 450, dot if not sim else TEAL, sim, ca)
        line(d, (x0, 490, x1, 490), RULE, 1, ca)
        for i, (name, val) in enumerate(rows):
            y = 540 + i * 50
            text(d, x0 + 40, y, name, "mono", 22, MUTED, ca, "lm")
            text(d, x0 + 220, y, val or timing, "monom", 22, INK, ca, "lm")
    text(d, 960, 760, "Identical answers. The simulator's time is 32% fast here: it does not yet charge PSRAM store misses.",
         "sans", 22, MUTED, ramp(t, 12.9, 13.3), "mm")


def frame(n, bg, logo, big_logo):
    t = n / FPS
    img = bg.copy()
    d = ImageDraw.Draw(img, "RGBA")
    if t < 14.2:
        if t < 12.4:
            reveal = ramp(t, 1.9, 2.6)
            if reveal > 0:
                wire(d, t)
                simulator(img, d, t)
                box(d, 560, 140, 1860, 800, 0, fill=BG, a=1 - reveal)
                d = ImageDraw.Draw(img, "RGBA")
            x0 = 80 + 645 * (1 - ramp(t, 1.8, 2.5))
            laptop(d, x0, t, span(t, 5.4, 10.0, 0.4))
            out = ramp(t, 12.1, 12.4)
            if out > 0:
                box(d, 60, 130, 1860, 800, 0, fill=BG, a=out)
        else:
            compare(d, t)
        chrome(img, d, t, logo)
    end = ramp(t, 14.1, 14.4)
    if end > 0:                                                                    # the closing wordmark
        img = Image.blend(img, bg, end)
        x, y = (W * S - big_logo.width) // 2, (H * S - big_logo.height) // 2 - 40 * S
        faded = big_logo.copy()
        faded.putalpha(faded.getchannel("A").point(lambda v: int(v * ramp(t, 14.3, 14.7))))
        img.paste(faded, (x, y), faded)
    return img


def check():
    for _, _, _, head, sub in BEATS:
        assert width(head, "semi", 46) <= CONTENT_X1 - 258, f"headline too wide: {head}"
        assert width(sub, "sans", 28) <= CONTENT_X1 - 258, f"detail too wide: {sub}"
    assert all(len(l) == 4 for l in DISASM) and len(DISASM) >= 50


if __name__ == "__main__":
    check()
    bg = background()
    logo, big_logo = wordmark(44), wordmark(150, "#555555")
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            p = os.path.join(HERE, f"still-{arg}.png")
            frame(round(float(arg) * FPS), bg, logo, big_logo).resize((W, H), Image.LANCZOS).save(p)
            print(p)
        sys.exit()
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W * S}x{H * S}",
         "-r", str(FPS), "-i", "-", "-vf", f"scale={W}:{H}:flags=lanczos", "-c:v", "libx264", "-preset", "slow",
         "-crf", "16", "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
    for n in range(FPS * SECONDS):
        ff.stdin.write(frame(n, bg, logo, big_logo).tobytes())
    ff.stdin.close()
    sys.exit(ff.wait())
