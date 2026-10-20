# Adaa brand

**Adaa — Every outfit tells your Adaa.** A plum ribbon "A": fabric folding like a dupatta or saree pleat, drawn as one continuous ribbon with a fine line for the left side.

## Files

| File | Use |
|---|---|
| `adaa-logo.svg` / `png/adaa-logo.png` | Main logo (stacked), transparent background |
| `adaa-logo-cream.svg` | Main logo on cream |
| `adaa-logo-dark.svg` | Main logo on plum (cream lettering, gold tagline) |
| `adaa-logo-horizontal.svg`, `-dark.svg` | Headers, website, email signature |
| `adaa-mark.svg` | The ribbon A alone (small spaces, watermark) |
| `adaa-app-icon.svg`, `-light.svg` | App icon / favicon / WhatsApp & Instagram profile picture |

SVGs are vectors: they stay sharp at any size and open in browsers, Canva, Figma and Illustrator. The lettering is already turned into shapes, so no fonts need to be installed. The `png/` folder has high-resolution PNGs (about 1000 px) for places that don't take SVG.

## Colours

| Name | Hex | Use |
|---|---|---|
| Plum | `#5B1F3F` | Logo, headings, primary buttons |
| Soft plum | `#7A3A5C` | Tagline, secondary text |
| Gold | `#C9A45C` | Thin accents only (the line under the name) |
| Cream | `#F4ECE8` | Backgrounds |

## Fonts (free, SIL Open Font License)

- **Great Vibes**: the name *Adaa*
- **Cormorant Garamond Italic** (medium): the tagline *every outfit tells your adaa*

## Do

- Keep clear space around the logo of at least the height of the "a".
- Use the plum logo on light backgrounds and the dark version on plum or photos.

## Don't

- Stretch, rotate, outline or recolour it outside the palette.
- Use the script name in ALL CAPS (it becomes hard to read).

## Rebuilding

`build_logo.py` makes every SVG from the drawing and the two fonts (it needs `fonttools`):
`python build_logo.py <folder with GreatVibes-Regular.ttf and CormorantGaramond-Italic.ttf> .` (the second is the variable font `CormorantGaramond-Italic[wght].ttf` from Google Fonts, renamed)
