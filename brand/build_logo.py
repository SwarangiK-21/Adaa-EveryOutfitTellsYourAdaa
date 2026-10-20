"""Build the Adaa logo files: lettering turned into vector outlines, so they look the same everywhere."""
import pathlib
import sys

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

FONTS = pathlib.Path(sys.argv[1])
OUT = pathlib.Path(sys.argv[2])

PLUM, PLUM_SOFT, GOLD, CREAM = "#5B1F3F", "#7A3A5C", "#C9A45C", "#F4ECE8"

script = TTFont(FONTS / "GreatVibes-Regular.ttf")
serif = instancer.instantiateVariableFont(TTFont(FONTS / "CormorantGaramond-Italic.ttf"), {"wght": 500})


def outline(font, text, size, x, baseline, spacing=0.0, anchor="middle"):
    """SVG path data for text, placed like an SVG <text> (x is the centre with anchor='middle')."""
    cmap = font.getBestCmap()
    glyphs = font.getGlyphSet()
    scale = size / font["head"].unitsPerEm
    names = [cmap[ord(c)] for c in text]
    width = sum(glyphs[n].width for n in names) * scale + spacing * (len(names) - 1)
    pen_x = x - width / 2 if anchor == "middle" else x
    parts = []
    for n in names:
        pen = SVGPathPen(glyphs)
        glyphs[n].draw(TransformPen(pen, (scale, 0, 0, -scale, pen_x, baseline)))
        parts.append(pen.getCommands())
        pen_x += glyphs[n].width * scale + spacing
    return " ".join(p for p in parts if p), width


MARK = ('<path d="M95 31 C92 17 112 9 122 21 L161 117 C181 124 185 156 165 163 C153 167 144 162 141 156 L135 127 Z"/>'
        '<path d="M38 121 L138 126 L157 164 C118 160 72 145 38 121 Z"/>'
        '<path d="M103 32 L76 123" stroke-width="4.5" stroke-linecap="round" fill="none"/>')


MARK_CX, MARK_CY = 111.5, 88   # visual centre of the ribbon A (the curl makes it lopsided)


def mark(colour, transform="", mid=""):
    """The ribbon A (200 x 200 box); the fold is a real cut-out, so any background shows through."""
    return (f'<mask id="fold{mid}" maskUnits="userSpaceOnUse" x="0" y="0" width="200" height="200">'
            f'<rect width="200" height="200" fill="#fff"/>'
            f'<path d="M147 126 L159 154" stroke="#000" stroke-width="3.2" stroke-linecap="round"/></mask>'
            f'<g transform="{transform}" fill="{colour}" stroke="{colour}" stroke-width="0" mask="url(#fold{mid})">{MARK}</g>')


def svg(view, body, title="Adaa — Every outfit tells your Adaa", bg=None, radius=0):
    w, h = view
    back = f'<rect width="{w}" height="{h}" rx="{radius}" fill="{bg}"/>' if bg else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
            f'<title>{title}</title>{back}{body}</svg>\n')


def stacked(fg, sub, line, bg=None):
    name, _ = outline(script, "Adaa", 92, 200, 272)
    tag, _ = outline(serif, "every outfit tells your adaa", 21, 200, 330, spacing=0.5)
    body = (mark(fg, f"translate({200 - MARK_CX * 0.9:.1f} 22) scale(0.9)") +
            f'<path d="{name}" fill="{fg}"/>'
            f'<line x1="138" y1="300" x2="262" y2="300" stroke="{line}" stroke-width="1"/>'
            f'<circle cx="200" cy="300" r="2.6" fill="{line}"/>'
            f'<path d="{tag}" fill="{sub}"/>')
    return svg((400, 380), body, bg=bg)


def horizontal(fg, sub, bg=None):
    name, w = outline(script, "Adaa", 64, 112, 74, anchor="start")
    tag, _ = outline(serif, "every outfit tells your adaa", 15, 116, 104, spacing=0.4, anchor="start")
    body = mark(fg, "translate(4 10) scale(0.5)") + f'<path d="{name}" fill="{fg}"/><path d="{tag}" fill="{sub}"/>'
    return svg((290, 120), body, bg=bg)


def icon(fg, bg, size=512):
    s = size * 0.66 / 160          # the A is about 160 units tall: fill two thirds of the icon
    ox, oy = size / 2 - MARK_CX * s, size / 2 - MARK_CY * s
    return svg((size, size), mark(fg, f"translate({ox:.1f} {oy:.1f}) scale({s:.4f})"),
               title="Adaa", bg=bg, radius=round(size * 0.22))


files = {
    "adaa-logo.svg": stacked(PLUM, PLUM_SOFT, GOLD),
    "adaa-logo-cream.svg": stacked(PLUM, PLUM_SOFT, GOLD, bg=CREAM),
    "adaa-logo-dark.svg": stacked(CREAM, "#E8CFA0", GOLD, bg=PLUM),
    "adaa-logo-horizontal.svg": horizontal(PLUM, PLUM_SOFT),
    "adaa-logo-horizontal-dark.svg": horizontal(CREAM, "#E8CFA0", bg=PLUM),
    "adaa-mark.svg": svg((200, 200), mark(PLUM), title="Adaa"),
    "adaa-app-icon.svg": icon(CREAM, PLUM),
    "adaa-app-icon-light.svg": icon(PLUM, CREAM),
}
OUT.mkdir(parents=True, exist_ok=True)
for name, text in files.items():
    (OUT / name).write_text(text, encoding="utf-8")
    print(name, len(text), "bytes")
