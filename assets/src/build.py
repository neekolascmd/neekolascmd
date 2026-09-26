#!/usr/bin/env python3
"""Builds the neobrutalist README graphics into assets/ (light + dark variants).

SVGs loaded through <img> can't fetch web fonts, so every string is converted
to vector outlines with CoreText (glyphs.swift). Needs macOS + Xcode tools:

    python3 assets/src/build.py
"""
import json
import math
import pathlib
import subprocess
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent

DISPLAY = "Arial-Black"
BODY = "HelveticaNeue-Medium"
BOLD = "HelveticaNeue-Bold"
MONO = "Menlo-Bold"

INK = "#0A0A0A"
CREAM = "#FFF6E5"
WHITE = "#FFFFFF"
YELLOW = "#FFD23F"
PINK = "#FF8FC7"
BLUE = "#7FD8FF"
LIME = "#B9F26B"
ORANGE = "#FF8A4C"
VIOLET = "#C3B1FF"

W = 880  # viewBox width of full-width graphics
SW = 4  # border width


class Theme:
    def __init__(self, name, fg, shadow):
        self.name, self.fg, self.shadow = name, fg, shadow


THEMES = [Theme("light", INK, INK), Theme("dark", "#F2EDE3", "#F2EDE3")]


class Glyphs:
    def __init__(self):
        binary = pathlib.Path(tempfile.mkdtemp()) / "glyphs"
        subprocess.run(["swiftc", "-O", str(HERE / "glyphs.swift"), "-o", str(binary)], check=True)
        self.proc = subprocess.Popen([str(binary)], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        self.cache = {}

    def get(self, text, font, size, tracking=0):
        key = (text, font, size, tracking)
        if key not in self.cache:
            req = {"text": text, "font": font, "size": size, "tracking": tracking}
            self.proc.stdin.write(json.dumps(req) + "\n")
            self.proc.stdin.flush()
            self.cache[key] = json.loads(self.proc.stdout.readline())
        return self.cache[key]


G = Glyphs()


def tw(s, font, size, tracking=0):
    return G.get(s, font, size, tracking)["w"]


def text(s, font, size, x, y, fill, anchor="start", tracking=0):
    g = G.get(s, font, size, tracking)
    if anchor == "middle":
        x -= g["w"] / 2
    elif anchor == "end":
        x -= g["w"]
    return f'<path transform="translate({x:.1f} {y:.1f})" fill="{fill}" d="{g["d"]}"/>'


def box(x, y, w, h, fill, t, shadow=8, r=6, sw=SW):
    s = ""
    if shadow:
        s += f'<rect x="{x - sw / 2 + shadow:g}" y="{y - sw / 2 + shadow:g}" width="{w + sw:g}" height="{h + sw:g}" rx="{r + sw / 2:g}" fill="{t.shadow}"/>'
    s += f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{r:g}" fill="{fill}" stroke="{INK}" stroke-width="{sw}"/>'
    return s


def chip(label, x, y, fill, t, font=MONO, size=14, padx=14, h=34, shadow=4, fg=INK, tracking=0.5):
    w = tw(label, font, size, tracking) + 2 * padx
    s = box(x, y, w, h, fill, t, shadow=shadow, r=4, sw=3)
    cap = G.get(label, font, size, tracking)["capH"]
    s += text(label, font, size, x + padx, y + h / 2 + cap / 2, fg, tracking=tracking)
    return s, w


def rotate(svg, deg, cx, cy):
    return f'<g transform="rotate({deg} {cx:.1f} {cy:.1f})">{svg}</g>'


def wrap(src, font, size, maxw):
    """Greedy word wrap. ==marked== words get a highlighter stripe."""
    words, hl = [], False
    for raw in src.split():
        start = raw.startswith("==")
        end = raw.endswith("==") and len(raw) > 2
        word = raw.strip("=")
        words.append((word, hl or start))
        hl = (hl or start) and not end
    space = tw("n n", font, size) - tw("nn", font, size)
    lines, line, x = [], [], 0
    for word, marked in words:
        ww = tw(word, font, size)
        if line and x + space + ww > maxw:
            lines.append(line)
            line, x = [], 0
        if line:
            x += space
        line.append((word, marked, x, ww))
        x += ww
    if line:
        lines.append(line)
    return lines


def para(src, font, size, x, y, maxw, lh, fill=INK, mark=YELLOW):
    """Returns (svg, height). y is the first baseline."""
    lines = wrap(src, font, size, maxw)
    marks, words = "", ""
    for i, line in enumerate(lines):
        base = y + i * lh
        run = None
        for word, marked, wx, ww in line + [("", False, 0, 0)]:
            if marked:
                run = (run[0], wx + ww) if run else (wx, wx + ww)
            elif run:
                marks += f'<rect x="{x + run[0] - 4:.1f}" y="{base - size * 0.72:.1f}" width="{run[1] - run[0] + 8:.1f}" height="{size * 0.86:.1f}" fill="{mark}"/>'
                run = None
            if word:
                words += text(word, font, size, x + wx, base, fill)
    return marks + words, (len(lines) - 1) * lh


def star(cx, cy, r1, r2, n):
    pts = []
    for i in range(n * 2):
        r = r1 if i % 2 == 0 else r2
        a = math.pi * i / n - math.pi / 2
        pts.append(f"{cx + r * math.cos(a):.1f},{cy + r * math.sin(a):.1f}")
    return " ".join(pts)


def header(num, title, color, t, y=6):
    """Section label: ink number block + colored title block, then a rule."""
    h = 52
    num_w = 60
    title_w = tw(title, DISPLAY, 24) + 40
    s = box(6, y, num_w + title_w, h, color, t, shadow=6, r=4)
    s += f'<rect x="6" y="{y}" width="{num_w}" height="{h}" rx="4" fill="{INK}"/>'
    s += f'<rect x="{6 + num_w - 6}" y="{y}" width="6" height="{h}" fill="{INK}"/>'
    s += text(num, MONO, 18, 6 + num_w / 2, y + h / 2 + 6.5, color, anchor="middle")
    s += text(title, DISPLAY, 24, 6 + num_w + 20, y + h / 2 + 8.5, INK)
    rule_x = 6 + num_w + title_w + 24
    s += f'<rect x="{rule_x:.1f}" y="{y + h / 2 - 2}" width="{W - 30 - rule_x:.1f}" height="4" fill="{t.fg}"/>'
    s += f'<rect x="{W - 22}" y="{y + h / 2 - 8}" width="16" height="16" fill="{color}" stroke="{t.fg}" stroke-width="3" transform="rotate(45 {W - 14} {y + h / 2})"/>'
    return s, y + h + 6


MOTION = """<style>
@keyframes spin{to{transform:rotate(360deg)}}
@keyframes blink{50%{opacity:0}}
@keyframes slide{to{transform:translateX(var(--d))}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
</style>"""


def svg(w, h, body, style=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:g}" height="{h:g}" viewBox="0 0 {w:g} {h:g}" fill="none">'
        f"{style}{body}</svg>\n"
    )


# ---------------------------------------------------------------- hero


def hero(t):
    cx, cy, cw, ch = 10, 12, 836, 356
    s = box(cx, cy, cw, ch, YELLOW, t, shadow=12, r=8)
    # window chrome
    s += f'<path d="M{cx} {cy + 8}a8 8 0 0 1 8-8h{cw - 16}a8 8 0 0 1 8 8v40h-{cw}z" fill="{WHITE}" stroke="{INK}" stroke-width="{SW}"/>'
    for i, c in enumerate([ORANGE, YELLOW, LIME]):
        s += f'<circle cx="{cx + 28 + i * 28}" cy="{cy + 24}" r="8" fill="{c}" stroke="{INK}" stroke-width="3"/>'
    s += text("~/neekolascmd/README.md", MONO, 14, cx + cw - 24, cy + 29, INK, anchor="end")

    left = cx + 36
    pill, pw = chip("DEVELOPER & REVERSE ENGINEER", left, cy + 72, INK, t, size=13, h=32, shadow=0, fg=YELLOW, tracking=1)
    s += pill
    s += text("HEY, I'M", DISPLAY, 70, left - 3, cy + 176, INK)
    nick_w = tw("NICK.", DISPLAY, 70)
    s += rotate(f'<rect x="{left - 10}" y="{cy + 196}" width="{nick_w + 20:.1f}" height="66" fill="{PINK}" stroke="{INK}" stroke-width="{SW}"/>', -2, left + nick_w / 2, cy + 229)
    s += text("NICK.", DISPLAY, 70, left - 3, cy + 254, INK)
    s += f'<rect class="cursor" x="{left + nick_w + 22:.1f}" y="{cy + 204}" width="16" height="50" fill="{INK}" style="animation:blink 1.1s steps(1) infinite"/>'
    s += text("Building local-first software for hardware you own.", BOLD, 21, left, cy + 298, INK)

    x = left
    for label, color in [("REVERSE ENGINEERING", WHITE), ("WEARABLE INTEROP", BLUE), ("ON-DEVICE ANALYTICS", LIME)]:
        c, w = chip(label, x, cy + 314, color, t, size=12, h=28, padx=12, shadow=3)
        s += c
        x += w + 14

    # starburst sticker
    sx, sy = 700, cy + 160
    burst = f'<polygon points="{star(sx + 7, sy + 7, 104, 84, 18)}" fill="{INK}"/>'
    burst += f'<polygon points="{star(sx, sy, 104, 84, 18)}" fill="{PINK}" stroke="{INK}" stroke-width="{SW}" stroke-linejoin="round"/>'
    s += f'<g style="transform-origin:{sx}px {sy}px;animation:spin 40s linear infinite">{burst}</g>'
    s += f'<circle cx="{sx}" cy="{sy}" r="70" fill="{WHITE}" stroke="{INK}" stroke-width="3"/>'
    label = text("100%", DISPLAY, 38, sx, sy + 2, INK, anchor="middle")
    label += text("LOCAL-FIRST", DISPLAY, 13, sx, sy + 26, INK, anchor="middle", tracking=0.5)
    label += text("NO CLOUD", MONO, 11, sx, sy - 36, INK, anchor="middle", tracking=1.5)
    s += rotate(label, -10, sx, sy)

    # BLE tape
    tape, tw_ = chip("BLUETOOTH LE ✱ SWIFT ✱ KOTLIN", 0, 0, BLUE, t, size=12, h=30, padx=12, shadow=4, tracking=0.5)
    s += f'<g transform="translate({W - tw_ - 14:.1f} {cy + ch - 50}) rotate(-3 {tw_ / 2:.1f} 15)">{tape}</g>'
    # sparkle
    s += f'<g transform="translate(820 {cy + 76}) rotate(12)"><polygon points="{star(0, 0, 22, 7, 4)}" fill="{YELLOW}" stroke="{INK}" stroke-width="3" stroke-linejoin="round"/></g>'
    return svg(W, cy + ch + 24, s, MOTION)


# ---------------------------------------------------------------- about

ABOUT = (
    "I'm a ==developer and reverse engineer== in South Carolina. I focus on useful hardware "
    "interoperability, privacy-minded applications, and turning ==undocumented protocols== into "
    "tools people can inspect and run themselves."
)


def about(t):
    s, y = header("01", "ABOUT", PINK, t)
    y += 18
    body, bh = para(ABOUT, BODY, 23, 40, y + 50, 770, 36)
    h = bh + 76
    s += box(10, y, 836, h, CREAM, t, shadow=10)
    s += body
    return svg(W, y + h + 16, s)


# ---------------------------------------------------------------- NOOP feature

NOOP_DESC = (
    "A local-first recovery and wearable analytics app for ==macOS, iOS, and Android.== "
    "NOOP works directly with WHOOP 4.0, 5.0, and MG hardware while keeping ==data and analytics on the device.=="
)
NOOP_FOCUS = [
    "WHOOP 4.0, 5.0, and MG Bluetooth LE interoperability",
    "Recovery, strain, HRV, and sleep analysis computed on-device",
    "Shared Swift and Kotlin analytics fixtures",
    "Hardware verification, release reliability, and cross-platform parity",
]


def noop(t):
    s, y = header("02", "NOW BUILDING", BLUE, t)
    y += 18
    cx, cw = 10, 836
    left = cx + 32
    inner = ""
    inner += text("NOOP", DISPLAY, 76, left - 3, y + 100, INK)
    x = cx + cw - 32
    for label in reversed(["MACOS", "IOS", "ANDROID"]):
        w = tw(label, MONO, 14, 1) + 28
        x -= w
        c, _ = chip(label, x, y + 50, WHITE, t, size=14, tracking=1)
        inner += c
        x -= 12
    body, bh = para(NOOP_DESC, BODY, 21, left, y + 150, 770, 32)
    inner += body
    ty = y + 150 + bh + 26
    x = left
    for label, color in [("OFFLINE BY DESIGN", YELLOW), ("ACCOUNT-FREE", PINK), ("WHOOP 4.0 · 5.0 · MG", WHITE)]:
        c, w = chip(label, x, ty, color, t, size=13, h=32)
        inner += c
        x += w + 14
    fy = ty + 70
    inner += text("CURRENT FOCUS", DISPLAY, 17, left, fy, INK, tracking=0.5)
    inner += f'<rect x="{left + tw("CURRENT FOCUS", DISPLAY, 17, 0.5) + 14:.1f}" y="{fy - 8}" width="{cx + cw - 32 - left - tw("CURRENT FOCUS", DISPLAY, 17, 0.5) - 14:.1f}" height="3" fill="{INK}"/>'
    gy = fy + 20
    colw = (cw - 64 - 24) / 2
    wrapped = [wrap(item, BOLD, 18, colw - 90) for item in NOOP_FOCUS]
    rowh = max(len(w) for w in wrapped) * 25 + 34
    for i, (item, lines) in enumerate(zip(NOOP_FOCUS, wrapped)):
        bx = left + (i % 2) * (colw + 24)
        by = gy + (i // 2) * (rowh + 20)
        inner += box(bx, by, colw, rowh, WHITE, t, shadow=5, r=4, sw=3)
        inner += f'<rect x="{bx + 14}" y="{by + rowh / 2 - 22}" width="44" height="44" rx="3" fill="{INK}"/>'
        inner += text(f"0{i + 1}", MONO, 17, bx + 36, by + rowh / 2 + 6, [YELLOW, PINK, LIME, ORANGE][i], anchor="middle")
        block, _ = para(item, BOLD, 18, bx + 74, by + rowh / 2 - (len(lines) - 1) * 12.5 + 6.5, colw - 90, 25)
        inner += block
    ch = gy + 2 * rowh + 20 + 28 - y
    s += box(cx, y, cw, ch, BLUE, t, shadow=10) + inner
    return svg(W, y + ch + 16, s)


def button(label, color, t):
    size, h, padx = 19, 56, 26
    w = tw(label, DISPLAY, size) + 2 * padx
    cap = G.get(label, DISPLAY, size)["capH"]
    s = box(4, 4, w, h, color, t, shadow=6, r=6)
    s += text(label, DISPLAY, size, 4 + padx, 4 + h / 2 + cap / 2, INK)
    return svg(w + 14, h + 14, s)


# ---------------------------------------------------------------- selected work

WORK = [
    ("noop", "PROJECT 01", ["NOOP"], LIME,
     "Offline, local-first wearable analytics across Apple platforms and Android.",
     ["SWIFT", "KOTLIN", "BLE"], True),
    ("ankermake", "PROJECT 02", ["ANKERMAKE M5", "PROTOCOL"], ORANGE,
     "Direct printer control, protocol tooling, slicer integration, and Home Assistant support for M5/M5C hardware.",
     ["PYTHON", "PROTOCOL", "HOME ASSISTANT"], False),
]


def work_card(item, height, t):
    _, tag, title, color, desc, tags, pulse = item
    x, y, w = 4, 4, 410
    inner = ""
    c, _ = chip(tag, x + 24, y + 24, INK, t, size=12, h=28, shadow=0, fg=color, tracking=1)
    inner += c
    ax, ay = x + w - 44, y + 38
    inner += f'<circle cx="{ax}" cy="{ay}" r="20" fill="{WHITE}" stroke="{INK}" stroke-width="3"/>'
    inner += f'<path d="M{ax - 7} {ay + 7}L{ax + 7} {ay - 7}M{ax - 4} {ay - 7}H{ax + 7}V{ay + 4}" stroke="{INK}" stroke-width="3.5" stroke-linecap="square" fill="none"/>'
    ty = y + 104
    for line in title:
        inner += text(line, DISPLAY, 30, x + 22, ty, INK)
        ty += 36
    body, bh = para(desc, BODY, 18, x + 24, ty + 8, w - 48, 26)
    inner += body
    if pulse:
        top, bottom = ty + bh + 20, y + height - 70
        py = (top + bottom) / 2
        amp = min(34, (bottom - top) / 2)
        pts = [(24, 0), (150, 0), (164, -0.45), (180, 0.6), (198, -1), (216, 0.75), (230, 0), (w - 24, 0)]
        d = "M" + " L".join(f"{x + px:.1f} {py + a * amp:.1f}" for px, a in pts)
        inner += f'<path d="{d}" stroke="{INK}" stroke-width="4" stroke-linejoin="round" stroke-linecap="round" fill="none"/>'
        inner += f'<circle cx="{x + w - 24}" cy="{py}" r="7" fill="{PINK}" stroke="{INK}" stroke-width="3"/>'
    cxp = x + 24
    for label in tags:
        c, cw = chip(label, cxp, y + height - 52, WHITE, t, size=11, h=28, padx=10, shadow=3)
        inner += c
        cxp += cw + 10
    return svg(x + w + 2 + 6 + 4, y + height + 2 + 6 + 4, box(x, y, w, height, color, t, shadow=8) + inner)


def work_height(item):
    _, _, title, _, desc, _, _ = item
    lines = wrap(desc, BODY, 18, 410 - 48)
    return 104 + 36 * len(title) + 8 + (len(lines) - 1) * 26 + 90


def section_header(num, title, color, t):
    s, y = header(num, title, color, t)
    return svg(W, y + 6, s)


# ---------------------------------------------------------------- toolbox

TOOLS = [("Swift", ORANGE), ("Kotlin", VIOLET), ("Python", YELLOW), ("TypeScript", BLUE),
         ("SwiftUI", PINK), ("Bluetooth LE", LIME), ("SQLite", WHITE), ("GitHub Actions", CREAM)]


def toolbox(t):
    s, y = header("04", "TOOLBOX", LIME, t)
    y += 26
    x, row_h, gap = 10, 58, 18
    tilts = [-2, 1.5, -1, 2, -1.5, 1, -2, 1.5]
    for i, (name, color) in enumerate(TOOLS):
        label = name.upper()
        w = tw(label, DISPLAY, 19) + 40
        if x + w > W - 20:
            x, y = 10, y + row_h + 22
        c = box(x, y, w, row_h - 8, color, t, shadow=6, r=5)
        c += text(label, DISPLAY, 19, x + 20, y + (row_h - 8) / 2 + 7, INK)
        s += rotate(c, tilts[i], x + w / 2, y + 25)
        x += w + gap
    return svg(W, y + row_h + 16, s)


# ---------------------------------------------------------------- principles

PRINCIPLES = [
    ("LOCAL", "FIRST", YELLOW, "The useful path should not depend on an account or a remote service."),
    ("EVIDENCE", "OVER GUESSES", PINK, "Protocol work should be reproducible and clearly separate verified behavior from experiments."),
    ("OWN YOUR", "HARDWARE", LIME, "People should be able to understand, maintain, and extend the devices they bought."),
]


def principles(t):
    s, y = header("05", "HOW I BUILD", YELLOW, t)
    y += 18
    gap = 22
    cw = (836 - 2 * gap) / 3
    lines = [wrap(p[3], BODY, 17, cw - 44) for p in PRINCIPLES]
    ch = 150 + max(len(l) for l in lines) * 25 + 10
    for i, (a, b, color, desc) in enumerate(PRINCIPLES):
        x = 10 + i * (cw + gap)
        s += box(x, y, cw, ch, color, t, shadow=8)
        s += text(f"0{i + 1}", DISPLAY, 46, x + cw - 20, y + 60, WHITE, anchor="end")
        s += f'<path transform="translate({x + cw - 20 - tw(f"0{i + 1}", DISPLAY, 46):.1f} {y + 60})" d="{G.get(f"0{i + 1}", DISPLAY, 46)["d"]}" fill="none" stroke="{INK}" stroke-width="2.5"/>'
        s += text(a, DISPLAY, 22, x + 22, y + 104, INK)
        s += text(b, DISPLAY, 22, x + 22, y + 132, INK)
        body, _ = para(desc, BODY, 17, x + 22, y + 168, cw - 44, 25)
        s += body
    return svg(W, y + ch + 18, s)


# ---------------------------------------------------------------- footer ticker

TICKER = "SOUTH CAROLINA, USA ✱ BUILDING IN PUBLIC ON GITHUB ✱ LOCAL-FIRST ✱ OWN YOUR HARDWARE ✱ "


def ticker_strip(y, angle, fill, fg, size, speed, reverse, t):
    unit = tw(TICKER, DISPLAY, size)
    reps = math.ceil((W + 200) / unit) + 1
    h = 46
    gid = "tk" + fill.lstrip("#")
    defs = f'<defs><path id="{gid}" fill="{fg}" d="{G.get(TICKER, DISPLAY, size)["d"]}"/></defs>'
    content = "".join(f'<use href="#{gid}" x="{-100 + i * unit:.1f}" y="{y + h / 2 + size * 0.36:.1f}"/>' for i in range(reps))
    d = -unit if not reverse else unit
    start = 0 if not reverse else -unit
    band = defs + f'<rect x="-100" y="{y + 6}" width="{W + 200}" height="{h}" fill="{t.shadow}"/>'
    band += f'<rect x="-100" y="{y}" width="{W + 200}" height="{h}" fill="{fill}" stroke="{INK}" stroke-width="{SW}"/>'
    band += (
        f'<g transform="translate({start:.1f} 0)"><g style="--d:{d:.1f}px;animation:slide {speed}s linear infinite">'
        f"{content}</g></g>"
    )
    return rotate(band, angle, W / 2, y + h / 2)


def footer(t):
    s = ticker_strip(62, 4, PINK, INK, 17, 34, True, t)
    s += ticker_strip(62, -3, INK, YELLOW, 17, 26, False, t)
    return svg(W, 176, s, MOTION)


# ---------------------------------------------------------------- write

def main():
    wh = {i[0]: work_height(i) for i in WORK}
    height = max(wh.values())
    for t in THEMES:
        files = {
            "hero": hero(t),
            "about": about(t),
            "noop": noop(t),
            "btn-explore": button("EXPLORE NOOP →", YELLOW, t),
            "btn-release": button("LATEST RELEASE →", PINK, t),
            "work-header": section_header("03", "SELECTED WORK", ORANGE, t),
            "toolbox": toolbox(t),
            "principles": principles(t),
            "footer": footer(t),
        }
        for item in WORK:
            files[f"work-{item[0]}"] = work_card(item, height, t)
        for name, content in files.items():
            (OUT / f"{name}-{t.name}.svg").write_text(content)
    print("wrote", len(list(OUT.glob("*.svg"))), "files")


if __name__ == "__main__":
    main()
