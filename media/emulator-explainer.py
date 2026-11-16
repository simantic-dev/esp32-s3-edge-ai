#!/usr/bin/env python3
"""Renders media/emulator-explainer.mp4: 15 s, 1920x1080, 30 fps.

    python3 media/emulator-explainer.py            # render the video
    python3 media/emulator-explainer.py 1 4 7      # write still-<t>.png beside the video instead

Needs Pillow and ffmpeg. Fonts are the site's (IBM Plex Sans, JetBrains Mono), read from TeX Live;
set FONT_DIR to a folder holding the same .otf files if TeX Live is elsewhere.
Drawn at 2x and scaled down by ffmpeg for antialiasing.
"""
import os, random, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS, SECONDS, S = 1920, 1080, 30, 15, 2
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "emulator-explainer.mp4")
BAUD = "2,000,000"

# simantic.com palette (src/index.css, src/pages/LandingPage.css)
BG, TEXT, TEXT_H, BORDER, CODE_BG = "#ffffff", "#6b6375", "#08060d", "#e5e4e7", "#f4f3ec"
ACCENT, ACCENT_DARK = "#aa3bff", "#c084fc"
TERM, TERM_FG, TERM_DIM, CHIP_BG = "#1e1e2a", "#e6e6ea", "#8b949e", "#16171d"
BLUE, TEAL, AMBER, GREEN = "#6ec1ff", "#4ec9b0", "#f0b95d", "#28c840"

TEXLIVE = "/usr/local/texlive/2026/texmf-dist/fonts/opentype"
FONT_FILES = {
    "light": "ibm/plex/IBMPlexSans-Light.otf", "sans": "ibm/plex/IBMPlexSans-Regular.otf",
    "medium": "ibm/plex/IBMPlexSans-Medium.otf", "mono": "SIL/jetbrainsmono-otf/JetBrainsMono-Regular.otf",
    "monob": "SIL/jetbrainsmono-otf/JetBrainsMono-SemiBold.otf",
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


def text(d, x, y, s, f="sans", size=24, fill=TEXT, a=1.0, anchor="la"):
    if a > 0.01:
        d.text((x * S, y * S), s, font=font(f, size), fill=rgba(fill, a), anchor=anchor)


def width(s, f, size):
    return font(f, size).getlength(s) / S


def box(d, x0, y0, x1, y1, r=0, fill=None, outline=None, w=1, a=1.0):
    if a > 0.01:
        d.rounded_rectangle(sc(x0, y0, x1, y1), r * S, fill=fill and rgba(fill, a),
                            outline=outline and rgba(outline, a), width=int(w * S))


def line(d, pts, fill, w=2, a=1.0):
    if a > 0.01:
        d.line(sc(*pts), fill=rgba(fill, a), width=int(w * S))


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

HEADLINES = [
    (0.0, 2.2, "It looks like the laptop is running the AI."),
    (2.2, 5.4, "It isn't. The laptop only sends camera frames."),
    (5.4, 10.0, "The detector runs inside an emulated ESP32-S3."),
    (10.0, 12.4, "The chip answers in text. The laptop only draws the box."),
]
FACTS = [
    (2.6, 5.4, f"160×120 RGB into the chip's UART0 at {BAUD} baud, exactly as a real board's USB-serial port would get it."),
    (5.4, 7.7, "Real compiled firmware: about 97,000 Xtensa vector (PIE/SIMD) instructions in the image."),
    (7.7, 10.0, "Each instruction is interpreted / JIT-compiled with cycle timing. Kernels like dl_tie728_s8_unaligned_conv2d_33cn."),
    (10.0, 12.4, "One line per face: B x1 y1 x2 y2 score, then E <ms>, back over the same UART."),
]
END = [
    ("light", 72, TEXT_H, 330, "Inference runs on an emulated ESP32-S3."),
    ("medium", 72, ACCENT, 426, "Not the laptop."),
    ("sans", 28, TEXT, 570, "The same firmware file on a real ESP32-S3 board gives the identical result:"),
    ("mono", 26, TEXT_H, 616, "score 0.893, box [98 57 198 194]"),
]
FACT_SIZE, FACT_MAX_W = 28, 1640


def background():
    """White page, the site's 90%-wide column borders, a faint accent aurora behind the header."""
    small = Image.new("RGB", (W // 8, H // 8), BG)
    d = ImageDraw.Draw(small, "RGBA")
    d.ellipse([40, -44, 150, 14], fill=rgba(ACCENT, 0.16))
    d.ellipse([120, -48, 215, 10], fill=rgba(BLUE, 0.14))
    img = small.filter(ImageFilter.GaussianBlur(9)).resize((W * S, H * S), Image.BICUBIC)
    borders(ImageDraw.Draw(img, "RGBA"))
    return img


def borders(d):
    for x in (96, 1824):
        line(d, (x, 0, x, H), BORDER, 1)


def laptop(d, ox, t):
    box(d, ox + 142, 306, ox + 562, 646, 16, fill="#000000", a=0.05)             # shadow
    box(d, ox + 136, 300, ox + 556, 640, 14, fill=BG, outline=BORDER, w=2)       # screen
    box(d, ox + 100, 640, ox + 592, 658, 8, fill="#f6f8fa", outline=BORDER, w=2)  # base
    text(d, ox + 346, 268, "LAPTOP", "medium", 18, TEXT, anchor="ma")
    x0, y0, x1, y1 = ox + 156, 320, ox + 536, 620                                # webcam view
    box(d, x0, y0, x1, y1, 6, fill=CODE_BG)
    cx, cy = ox + 346, 452
    d.chord(sc(cx - 130, cy + 96, cx + 130, cy + 330), 202.6, 337.4, fill=rgba("#d0d7de"))  # shoulders, cut at y1
    d.ellipse(sc(cx - 72, cy - 84, cx + 72, cy + 84), fill=rgba("#ebe9e3"), outline=rgba(TEXT_H), width=3 * S)
    for ex in (-28, 28):
        d.ellipse(sc(cx + ex - 7, cy - 22, cx + ex + 7, cy - 8), fill=rgba(TEXT_H))
    d.arc(sc(cx - 34, cy - 4, cx + 34, cy + 46), 25, 155, fill=rgba(TEXT_H), width=3 * S)
    box(d, x0 + 10, y0 + 10, x0 + 92, y0 + 36, 5, fill=TERM, a=0.8)
    text(d, x0 + 51, y0 + 23, "webcam", "mono", 14, TERM_FG, anchor="mm")
    a = max(1 - ramp(t, 2.0, 2.4), ramp(t, 11.2, 11.4))                           # the green box
    grow = 10 * (1 - ramp(t, 11.2, 11.6)) if t > 5 else 0
    box(d, cx - 88 - grow, cy - 100 - grow, cx + 88 + grow, cy + 100 + grow, 4, outline=GREEN, w=5, a=a)
    for i, (s, c) in enumerate((("sends camera frames", TEXT), ("draws the box", TEXT), ("runs no model", TEXT_H))):
        y = 708 + i * 42
        ra = ramp(t, 2.3 + i * 0.15, 2.7 + i * 0.15)                                # roles appear after the reveal
        d.ellipse(sc(ox + 196, y - 5, ox + 206, y + 5), fill=rgba(ACCENT if i == 2 else BORDER, ra))
        text(d, ox + 222, y, s, "medium" if i == 2 else "sans", 26, c, ra, "lm")


def pill(d, x, y, s, lo, hi, fill=TERM, fg=TERM_FG):
    """A token travelling along a lane, centred on x, fading out near the lane ends."""
    w = width(s, "mono", 17) + 22
    a = min(ramp(x - w / 2, lo - 30, lo + 10), 1 - ramp(x + w / 2, hi - 10, hi + 30))
    box(d, x - w / 2, y - 16, x + w / 2, y + 16, 7, fill=fill, a=a)
    text(d, x, y, s, "mono", 17, fg, a, "mm")


def channel(d, t):
    L, R, TOP, BOT = 600, 894, 500, 650
    text(d, 747, 372, "UART0", "medium", 30, TEXT_H, anchor="ma")
    text(d, 747, 414, f"{BAUD} baud", "mono", 18, TEXT, anchor="ma")
    line(d, (L + 76, TOP, R, TOP), BORDER, 3)
    d.polygon(sc(R + 4, TOP, R - 12, TOP - 9, R - 12, TOP + 9), fill=rgba(TEXT))
    line(d, (L, BOT, R, BOT), BORDER, 3)
    d.polygon(sc(L - 4, BOT, L + 12, BOT - 9, L + 12, BOT + 9), fill=rgba(TEXT))
    text(d, (L + 76 + R) / 2, 462, "57,600 bytes", "mono", 16, TEXT, anchor="mm")
    text(d, 747, 686, 'chip asks for a frame: "F"', "mono", 16, TEXT, span(t, 2.4, 9.9), "mm")
    text(d, 747, 686, "chip replies in text", "mono", 16, TEXT, ramp(t, 10.0, 10.3), "mm")
    # the frame shrinks from the webcam view to a 160x120 thumbnail at the head of the lane
    k = ramp(t, 3.0, 3.5)
    if t >= 3.0:
        src, dst = (156, 320, 536, 620), (L, TOP - 24, L + 64, TOP + 24)
        r = [s + (e - s) * k for s, e in zip(src, dst)]
        box(d, *r, 4, fill=CODE_BG if k == 1 else None, outline=ACCENT, w=3)
        if k == 1:
            for gx in range(1, 4):
                line(d, (L + gx * 16, TOP - 22, L + gx * 16, TOP + 22), BORDER, 1)
            for gy in range(1, 3):
                line(d, (L + 2, TOP - 24 + gy * 16, L + 62, TOP - 24 + gy * 16), BORDER, 1)
            text(d, L, TOP + 40, "160×120 RGB", "mono", 15, TEXT_H, anchor="lm")
    if 2.5 <= t < 3.2:                                                            # "F": chip -> laptop
        pill(d, R - (R - L) * (t - 2.5) / 0.7, BOT, "F", L, R, ACCENT, "#ffffff")
    for i in range(14):                                                           # frame bytes: laptop -> chip
        x = L + 76 + (t - 3.5 - i * 0.15) * 330
        if 3.5 + i * 0.15 <= t and x < R + 40:
            pill(d, x, TOP, f"{random.Random(i).randrange(256):02x}", L + 76, R)
    for s, t0 in (("B x1 y1 x2 y2 score", 10.1), ("E <ms>", 10.75)):              # result: chip -> laptop
        x = R + 110 - (t - t0) * 520
        if t >= t0 and x > L - 120:
            pill(d, x, BOT, s, L, R)


def sim_window(img, d, t):
    X0, Y0, X1, Y1 = 900, 250, 1784, 850
    box(d, X0 + 4, Y0 + 14, X1 + 4, Y1 + 14, 14, fill="#0f0c1e", a=0.12)
    box(d, X0, Y0, X1, Y1, 12, fill=TERM)
    box(d, X0, Y0, X1, Y0 + 38, 12, fill="#33333c")
    box(d, X0, Y0 + 20, X1, Y0 + 38, 0, fill="#2a2a32")
    for i, c in enumerate(("#ff5f57", "#febc2e", "#28c840")):
        d.ellipse(sc(X0 + 16 + i * 22, Y0 + 12, X0 + 30 + i * 22, Y0 + 26), fill=rgba(c))
    text(d, (X0 + X1) / 2, Y0 + 19, "sim — Simantic simulator", "sans", 16, "#ffffff", 0.6, "mm")
    cx0, cy0, cx1, cy1 = 950, 310, 1734, 826                                      # the chip
    for y in range(cy0 + 30, cy1 - 10, 40):
        for x in (cx0 - 14, cx1):
            box(d, x, y, x + 14, y + 14, 2, fill="#3c3c46")
    for y in (500, 650):                                                          # UART pins
        box(d, cx0 - 50, y - 2, cx0, y + 2, 0, fill=ACCENT_DARK, a=0.6)
    box(d, cx0, cy0, cx1, cy1, 10, fill=CHIP_BG, outline=ACCENT_DARK, w=2)
    text(d, cx0 + 24, cy0 + 16, "ESP32-S3 (emulated)", "medium", 30, "#f3f4f6")
    text(d, cx1 - 24, cy0 + 26, "ESP32-S3-WROOM-1-N8R2", "mono", 16, TERM_DIM, anchor="ra")
    text(d, cx0 + 24, cy0 + 62, "dual-core Xtensa LX7 · 240 MHz · 2 MB PSRAM", "mono", 17, TERM_DIM)
    text(d, cx0 + 24, cy0 + 90, "firmware: ESP-DL face detector · ESPDet-Pico · 224×224 · int8", "mono", 17, TEAL)
    text(d, cx1 - 24, cy0 + 90, "flash.bin", "mono", 17, TERM_DIM, anchor="ra")
    line(d, (cx0 + 24, cy0 + 124, cx1 - 24, cy0 + 124), "#2e303a", 1)

    # scrolling disassembly, program counter on the middle row
    pc = 4 + 8.6 * (ramp(t, 5.2, 6.0) * 0.4 + max(0, min(t, 10.0) - 5.6)) if t > 5.2 else 4.0
    pc = min(pc, len(DISASM) - 6)
    ROWS, PITCH, lw, lh = 9, 25, cx1 - cx0 - 48, 9 * 25
    lst = Image.new("RGB", (lw * S, lh * S), CHIP_BG)
    ld = ImageDraw.Draw(lst, "RGBA")
    running = 5.3 < t < 10.0
    for i in range(int(pc) - 5, int(pc) + 6):
        if not 0 <= i < len(DISASM):
            continue
        addr, raw, op, args = DISASM[i]
        y = (i - pc + ROWS // 2) * PITCH + PITCH / 2
        cur = i == int(pc + 0.5)
        if cur:
            box(ld, 0, y - 12, lw, y + 12, 4, fill=ACCENT_DARK, a=0.22 if running else 0.1)
        text(ld, 26, y, addr, "mono", 16, TERM_DIM, anchor="lm")
        text(ld, 110, y, raw, "mono", 16, "#59636e", anchor="lm")
        text(ld, 200, y, op, "monob" if "vmulas" in op else "mono", 16,
             AMBER if "vmulas" in op else TEAL if op.startswith("ee.") else TERM_FG, anchor="lm")
        text(ld, 420, y, args, "mono", 16, TERM_FG, anchor="lm")
        if cur:
            ld.polygon(sc(6, y - 7, 6, y + 7, 17, y), fill=rgba(ACCENT_DARK))
    for i in range(12):                                                           # soft top/bottom edges
        a = 1 - i / 12
        box(ld, 0, i * 2, lw, i * 2 + 2, 0, fill=CHIP_BG, a=a)
        box(ld, 0, lh - i * 2 - 2, lw, lh - i * 2, 0, fill=CHIP_BG, a=a)
    img.paste(lst, (int((cx0 + 24) * S), int((cy0 + 134) * S)))

    # the two int8 vectors of the latest ee.vmulas.s8.accx, and its accumulator
    done = [i for i in range(int(pc + 0.5) + 1) if "vmulas" in DISASM[i][2]]
    vr = random.Random(len(done))
    q3 = [vr.randrange(-128, 128) for _ in range(16)]
    q0 = [vr.randrange(-128, 128) for _ in range(16)]
    acc = 0
    for n in range(len(done) // 3 * 3, len(done) + 1):                             # accumulates, cleared every 3rd
        r = random.Random(n)
        a3 = [r.randrange(-128, 128) for _ in range(16)]
        acc += sum(x * y for x, y in zip(a3, [r.randrange(-128, 128) for _ in range(16)]))
    if not done:
        q3, q0, acc = [0] * 16, [0] * 16, 0
    flash = 1 - min(1, (pc + 0.5 - done[-1]) / 2.5) if done and running else 0
    y = cy0 + 372
    line(d, (cx0 + 24, y, cx1 - 24, y), "#2e303a", 1)
    for row, (name, vals) in enumerate((("q3", q3), ("q0", q0))):
        ry = y + 14 + row * 36
        text(d, cx0 + 24, ry + 15, name, "monob", 17, AMBER, anchor="lm")
        for i, v in enumerate(vals):
            x = cx0 + 66 + i * 43
            box(d, x, ry, x + 39, ry + 30, 4, fill="#2e303a")
            box(d, x, ry, x + 39, ry + 30, 4, fill=AMBER, a=0.35 * flash)
            text(d, x + 19.5, ry + 15, str(v), "mono", 13, TERM_FG, anchor="mm")
    text(d, cx0 + 24, y + 106, "ee.vmulas.s8.accx", "monob", 17, AMBER, anchor="lm")
    text(d, cx0 + 218, y + 106, f"ACCX += Σ q3[i] × q0[i]  =  {acc:,}", "mono", 17, TERM_FG, anchor="lm")
    text(d, cx1 - 24, y + 106, "16 × int8", "mono", 15, TERM_DIM, anchor="rm")


def logo(d, x, y, s):
    box(d, x, y, x + s, y + s, 0, fill="#000000")
    box(d, x + s * 0.205, y + s * 0.205, x + s * 0.795, y + s * 0.795, s * 0.05, fill="#ffffff")
    r = s * 0.045
    d.ellipse(sc(x + s * 0.28 - r, y + s * 0.72 - r, x + s * 0.28 + r, y + s * 0.72 + r), fill=rgba("#000000"))


def frame(n, bg):
    t = n / FPS
    img = bg.copy()
    d = ImageDraw.Draw(img, "RGBA")
    text(d, W / 2, 78, "FACE DETECTION ON A SIMULATED ESP32-S3", "mono", 18, ACCENT, anchor="ma")
    for t0, t1, s in HEADLINES:
        text(d, W / 2, 118, s, "light", 56, TEXT_H, span(t, t0, t1) if t0 else 1 - ramp(t, t1 - 0.3, t1), "ma")
    for t0, t1, s in FACTS:
        text(d, W / 2, 938, s, "sans", FACT_SIZE, TEXT, span(t, t0, t1), "mm")

    reveal = ramp(t, 1.9, 2.6)
    if reveal > 0:
        channel(d, t)
        sim_window(img, d, t)
        box(d, 560, 240, 1800, 880, 0, fill=BG, a=1 - reveal)
    laptop(d, 614 * (1 - ramp(t, 1.8, 2.5)), t)
    box(d, 98, 256, 596, 820, 0, fill=BG, a=0.55 * span(t, 5.4, 10.0, 0.4))           # laptop steps back

    end = ramp(t, 12.4, 12.8)
    if end > 0:
        img = Image.blend(img, bg, end)
        d = ImageDraw.Draw(img, "RGBA")
        text(d, W / 2, 78, "FACE DETECTION ON A SIMULATED ESP32-S3", "mono", 18, ACCENT, end, "ma")
        for i, (f, size, c, y, s) in enumerate(END):
            text(d, W / 2, y, s, f, size, c, ramp(t, 12.5 + i * 0.15, 12.9 + i * 0.15), "ma")
        a = ramp(t, 13.1, 13.5)
        w = width("simantic.com", "monob", 34)
        x = (W - (64 + 20 + w)) / 2
        if a > 0.01:
            logo(d, x, 728, 64)
            box(d, x - 1, 727, x + 65, 793, 0, fill=BG, a=1 - a)
        text(d, x + 84, 760, "simantic.com", "monob", 34, TEXT_H, a, "lm")
    return img


def check():
    for _, _, s in FACTS:
        assert width(s, "sans", FACT_SIZE) <= FACT_MAX_W, f"fact too wide: {s}"
    for _, _, s in HEADLINES:
        assert width(s, "light", 56) <= FACT_MAX_W, f"headline too wide: {s}"
    assert all(len(l) == 4 for l in DISASM) and len(DISASM) >= 50


if __name__ == "__main__":
    check()
    bg = background()
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            p = os.path.join(os.path.dirname(OUT), f"still-{arg}.png")
            frame(round(float(arg) * FPS), bg).resize((W, H), Image.LANCZOS).save(p)
            print(p)
        sys.exit()
    ff = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W * S}x{H * S}",
         "-r", str(FPS), "-i", "-", "-vf", f"scale={W}:{H}:flags=lanczos", "-c:v", "libx264", "-preset", "slow",
         "-crf", "16", "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
    for n in range(FPS * SECONDS):
        ff.stdin.write(frame(n, bg).tobytes())
    ff.stdin.close()
    sys.exit(ff.wait())
