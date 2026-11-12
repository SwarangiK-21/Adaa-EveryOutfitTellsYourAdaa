"""Build the Peheraav AI logo files and the opening-animation SVG.

The lettering is turned into vector outlines, so the logos look the same everywhere (no fonts needed).
Usage: python build_logo.py <folder with GreatVibes-Regular.ttf and CormorantGaramond-Italic.ttf> <output folder> [splash.svg]
"""
import pathlib
import sys

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

FONTS = pathlib.Path(sys.argv[1])
OUT = pathlib.Path(sys.argv[2])
SPLASH = pathlib.Path(sys.argv[3]) if len(sys.argv) > 3 else None

PLUM, PLUM_SOFT, GOLD, CREAM, GOLD_SOFT = "#5B1F3F", "#7A3A5C", "#C9A45C", "#F4ECE8", "#E8CFA0"
NAME, TAGLINE = "Peheraav", "your wardrobe, styled by AI"
TITLE = "Peheraav AI — Your wardrobe, styled by AI"

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


def measure(font, text, size, spacing=0.0):
    return outline(font, text, size, 0, 0, spacing, anchor="start")[1]


# The ribbon P: a slanted ribbon stem with a curled foot, and a bowl that drapes across the stem
# like the end of a dupatta. 200 x 200 box.
MARK = ('<path d="M92 30 C90 16 110 8 118 20 L94 140 C108 148 106 174 90 176 C80 177 72 170 72 162 L76 142 Z"/>'
        '<path d="M114 18 C162 6 190 40 174 78 C160 106 116 116 50 114 C104 100 148 88 151 64 C153 42 134 30 114 34 Z"/>')
FOLDS = ('<path d="M84 142 L94 162" stroke="#000" stroke-width="3.2" stroke-linecap="round"/>'
         '<path d="M98 98 L104 112" stroke="#000" stroke-width="3" stroke-linecap="round"/>')
MARK_CX, MARK_CY = 118, 94   # visual centre of the ribbon P


def mark(colour, transform="", mid=""):
    """The ribbon P; the folds are real cut-outs, so any background shows through."""
    return (f'<mask id="fold{mid}" maskUnits="userSpaceOnUse" x="0" y="0" width="200" height="200">'
            f'<rect width="200" height="200" fill="#fff"/>{FOLDS}</mask>'
            f'<g transform="{transform}" fill="{colour}" stroke="{colour}" stroke-width="0" mask="url(#fold{mid})">{MARK}</g>')


def svg(view, body, title=TITLE, bg=None, radius=0, extra=""):
    w, h = view
    back = f'<rect width="{w}" height="{h}" rx="{radius}" fill="{bg}"/>' if bg else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}"{extra}>'
            f'<title>{title}</title>{back}{body}</svg>\n')


def wordmark(x_centre, baseline, size, anchor="middle"):
    """'Peheraav' in script with a small 'AI' after it. Returns (name path, ai path, total width)."""
    ai_size = size * 0.38
    name_w = measure(script, NAME, size)
    ai_w = measure(serif, "AI", ai_size, spacing=ai_size * 0.08)
    gap = size * 0.03
    total = name_w + gap + ai_w
    left = x_centre - total / 2 if anchor == "middle" else x_centre
    name, _ = outline(script, NAME, size, left, baseline, anchor="start")
    ai, _ = outline(serif, "AI", ai_size, left + name_w + gap, baseline - size * 0.30, spacing=ai_size * 0.08, anchor="start")
    return name, ai, total


def stacked(fg, sub, line, bg=None):
    name, ai, _ = wordmark(200, 272, 74)
    tag, _ = outline(serif, TAGLINE, 21, 200, 330, spacing=0.5)
    body = (mark(fg, f"translate({200 - MARK_CX * 0.9:.1f} 22) scale(0.9)") +
            f'<path d="{name}" fill="{fg}"/><path d="{ai}" fill="{line}"/>'
            f'<line x1="138" y1="300" x2="262" y2="300" stroke="{line}" stroke-width="1"/>'
            f'<circle cx="200" cy="300" r="2.6" fill="{line}"/>'
            f'<path d="{tag}" fill="{sub}"/>')
    return svg((400, 380), body, bg=bg)


def horizontal(fg, sub, line, bg=None):
    name, ai, w = wordmark(104, 72, 54, anchor="start")
    tag, tw = outline(serif, TAGLINE, 15, 108, 102, spacing=0.4, anchor="start")
    width = round(max(104 + w, 108 + tw) + 10)
    body = (mark(fg, "translate(0 10) scale(0.5)") + f'<path d="{name}" fill="{fg}"/><path d="{ai}" fill="{line}"/>'
            f'<path d="{tag}" fill="{sub}"/>')
    return svg((width, 120), body, bg=bg)


def icon(fg, bg, size=512, maskable=False):
    # The P is about 168 units tall: fill two thirds of the icon (half for "maskable" phone icons,
    # which phones crop to a circle or squircle, so the mark must sit inside the safe zone).
    s = size * (0.5 if maskable else 0.66) / 168
    ox, oy = size / 2 - MARK_CX * s, size / 2 - MARK_CY * s
    return svg((size, size), mark(fg, f"translate({ox:.1f} {oy:.1f}) scale({s:.4f})"),
               title="Peheraav AI", bg=bg, radius=0 if maskable else round(size * 0.22))


def splash():
    """The opening animation (classes are animated in frontend/src/styles.css, see .splash)."""
    t = f"translate({200 - MARK_CX * 0.9:.1f} 22) scale(0.9)"
    name, ai, _ = wordmark(200, 272, 74)
    tag, _ = outline(serif, TAGLINE, 21, 200, 330, spacing=0.5)
    shine = "".join(f'<path transform="{t}" d="{d}"/>' for d in
                    [p.split('d="')[1].split('"')[0] for p in MARK.split("<path ")[1:]])
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 380" class="splash-logo" aria-hidden="true" focusable="false">'
            '<defs><mask id="splash-fold" maskUnits="userSpaceOnUse" x="0" y="0" width="200" height="200">'
            f'<rect width="200" height="200" fill="#fff"/>{FOLDS}</mask>'
            f'<clipPath id="splash-shine-clip">{shine}</clipPath>'
            '<linearGradient id="splash-shine-grad" x1="0" x2="1"><stop offset="0" stop-color="#FFF4DA" stop-opacity="0"/>'
            '<stop offset=".5" stop-color="#FFF4DA" stop-opacity=".8"/><stop offset="1" stop-color="#FFF4DA" stop-opacity="0"/></linearGradient></defs>'
            f'<g class="s-mark"><g transform="{t}" fill="{CREAM}" stroke="{CREAM}" stroke-width="0" mask="url(#splash-fold)">{MARK}</g></g>'
            '<g clip-path="url(#splash-shine-clip)"><rect class="s-shine" x="40" y="0" width="60" height="200" fill="url(#splash-shine-grad)"/></g>'
            f'<g class="s-name"><path d="{name}" fill="{CREAM}"/><path d="{ai}" fill="{GOLD}"/></g>'
            f'<line class="s-thread" x1="138" y1="300" x2="262" y2="300" stroke="{GOLD}" stroke-width="1"/>'
            f'<circle class="s-dot" cx="200" cy="300" r="2.6" fill="{GOLD}"/>'
            f'<g class="s-tag"><path d="{tag}" fill="{GOLD_SOFT}"/></g></svg>\n')


files = {
    "peheraav-logo.svg": stacked(PLUM, PLUM_SOFT, GOLD),
    "peheraav-logo-cream.svg": stacked(PLUM, PLUM_SOFT, GOLD, bg=CREAM),
    "peheraav-logo-dark.svg": stacked(CREAM, GOLD_SOFT, GOLD, bg=PLUM),
    "peheraav-logo-horizontal.svg": horizontal(PLUM, PLUM_SOFT, GOLD),
    "peheraav-logo-horizontal-dark.svg": horizontal(CREAM, GOLD_SOFT, GOLD, bg=PLUM),
    "peheraav-mark.svg": svg((200, 200), mark(PLUM), title="Peheraav AI"),
    "peheraav-app-icon.svg": icon(CREAM, PLUM),
    "peheraav-app-icon-light.svg": icon(PLUM, CREAM),
    "peheraav-app-icon-maskable.svg": icon(CREAM, PLUM, maskable=True),
}
OUT.mkdir(parents=True, exist_ok=True)
for name, text in files.items():
    (OUT / name).write_text(text, encoding="utf-8")
    print(name, len(text), "bytes")
if SPLASH:
    SPLASH.write_text(splash(), encoding="utf-8")
    print(SPLASH.name, SPLASH.stat().st_size, "bytes")
