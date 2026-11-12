# Peheraav brand

**Peheraav AI — Your wardrobe, styled by AI.** A plum ribbon "P": a slanted ribbon stem with a curled foot, and a bowl that drapes across the stem like the end of a dupatta. Peheraav (पेहराव) is Marathi for attire, the way you dress.

## Files

| File | Use |
|---|---|
| `peheraav-logo.svg` / `png/peheraav-logo.png` | Main logo (stacked), transparent background |
| `peheraav-logo-cream.svg` | Main logo on cream |
| `peheraav-logo-dark.svg` | Main logo on plum (cream lettering, gold tagline) |
| `peheraav-logo-horizontal.svg`, `-dark.svg` | Headers, website, email signature |
| `peheraav-mark.svg` | The ribbon P alone (small spaces, watermark) |
| `peheraav-app-icon.svg`, `-light.svg` | App icon / favicon / WhatsApp & Instagram profile picture |
| `peheraav-app-icon-maskable.svg` | Phone home-screen icon (the P sits inside the safe circle phones crop to) |

SVGs are vectors: they stay sharp at any size and open in browsers, Canva, Figma and Illustrator. The lettering is already turned into shapes, so no fonts need to be installed. The `png/` folder has high-resolution PNGs (about 1000 px) for places that don't take SVG.

## Colours

| Name | Hex | Use |
|---|---|---|
| Plum | `#5B1F3F` | Logo, headings, primary buttons |
| Soft plum | `#7A3A5C` | Tagline, secondary text |
| Gold | `#C9A45C` | Thin accents only (the line under the name) |
| Cream | `#F4ECE8` | Backgrounds |

## Fonts (free, SIL Open Font License)

- **Great Vibes**: the name *Peheraav*
- **Cormorant Garamond Italic** (medium): the small gold *AI* and the tagline *your wardrobe, styled by AI*

## Do

- Keep clear space around the logo of at least the height of the "a".
- Use the plum logo on light backgrounds and the dark version on plum or photos.

## Don't

- Stretch, rotate, outline or recolour it outside the palette.
- Use the script name in ALL CAPS (it becomes hard to read).

## Rebuilding

`build_logo.py` makes every SVG from the drawing and the two fonts (it needs `fonttools`):
`python build_logo.py <folder with GreatVibes-Regular.ttf and CormorantGaramond-Italic.ttf> .` (the second is the variable font `CormorantGaramond-Italic[wght].ttf` from Google Fonts, renamed)
