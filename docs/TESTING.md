# Adaa: testing

## Automated tests (backend)

Run from `backend/` with the virtual environment active:

```powershell
python -m pytest
```

Expected result: **93 passed**. Each test runs against a fresh temporary database and photo folder, so your real wardrobe is never touched.

| File | Tests | What it covers |
|---|---|---|
| `test_items.py` | 10 | Add, list, search, filter, edit (with and without a new photo), delete; rejects fake images, oversized photos and invalid details; 64 simultaneous photo requests |
| `test_recommendations.py` | 19 | Only real items are used and outfits are distinct; pairing rules; empty wardrobe; occasion tags; honest relaxed mode; building around a piece; colour, comfort and style preferences; consistent metals; saree blouse; minimal jewellery for casual looks; colour parsing; API validation |
| `test_parser.py` | 18 | Occasion words (sangeet, diwali, interview…); style, comfort and colour mood; *"Style my black crop top for a party"*; name vs type matching; typos; asking when ambiguous; reporting pieces you don't own; missing occasion |
| `test_looks.py` | 13 | Save, list, rename, delete looks; no duplicates; numbered names; swap options stay wearable and tagged pieces rank first; evaluation cautions; swaps inside saved looks; wear history; history survives deleting a look; no future dates; deleting a wardrobe item keeps the look and flags it |
| `test_look_photos.py` | 7 | Verified photo upload and serving; photo becomes outdated after a swap or a deleted piece; replacing/removing/deleting cleans up files; rejects non-images |
| `test_tryon.py` | 11 | Your photo and server settings; status check; bottom-then-top order; dress in one pass; skipped accessories; caching and new image after a swap; new photo clears old try-ons; clear errors (nothing to try on, server offline, not set up, no photo); safe image names; link-only change keeps the token |
| `test_workflow.py` | 1 | The whole journey: empty wardrobe → add 10 pieces → *"Style my green kurta for a traditional family function"* → outfits → swap → save → wear → history → delete a worn piece |

## Manual end-to-end pass (browser)

Done on 15 Oct 2026, starting from an **empty** data folder, using the real forms in the browser. Desktop (1280px), tablet (768px) and phone (375px) widths.

| Area | Check | Result |
|---|---|---|
| First run | Overview shows 0 pieces / 0 looks; Wardrobe, Stylist and Saved Looks show helpful empty states with a next step | ✅ |
| Add piece | No photo → "Please add a photo" | ✅ |
| | Text file → "Please choose a JPEG, PNG or WebP photo" | ✅ |
| | 6 MB file → "larger than 5 MB" | ✅ |
| | Renamed fake `.jpg` → "doesn't look like a real photo" (no broken preview) | ✅ *(fixed during this pass)* |
| | No occasion → "Please pick at least one occasion" | ✅ |
| | 11 real pieces added through the form; all photos display | ✅ |
| Edit | Adding several occasions with quick taps keeps all of them | ✅ *(fixed during this pass)* |
| Stylist | *"Style my green kurta for a traditional family function"* → kurta + churidar + dupatta + juttis + jhumkas + potli, with reasons; honest "only 1 outfit possible" note | ✅ |
| | Pieces not tagged for the occasion are left out, or clearly flagged when it has to relax | ✅ |
| Swap | Footwear swap shows real alternatives labelled "Not tagged for Traditional function" | ✅ |
| Saved looks | Save, Wore it today, history entry with photos, Overview count | ✅ |
| Preferences | Saved choices survive a reload and pre-fill the Stylist form | ✅ *(made functional during this pass)* |
| Server down | Every page shows "Can't reach the Adaa server. Is the backend running?" with Try again; Overview shows "–" | ✅ *(Overview count fixed during this pass)* |
| Layout | No page is wider than the screen at 375, 768 or 1280px | ✅ |
| Console | No errors except the expected ones while the server was deliberately stopped | ✅ |

## Quick checklist before a demo

1. `python -m pytest` → `93 passed`
2. Backend running: http://127.0.0.1:8000/api/health → `"status":"ok"`
3. Frontend running: http://localhost:5173 → Overview shows your piece count
4. AI Stylist → ask for one of your demo requests → outfits with photos appear

## Outfit preview pass (17 Oct 2026)

Fresh test wardrobe of 20 pieces; desktop (1280px) and phone (375px).

| Check | Result |
|---|---|
| Traditional look (kurta + churidar + dupatta + juttis + jhumkas + bangles + potli) drawn on the model, labelled *Illustration* | ✅ |
| Western look (crop top + jeans + heels + chain + tote + watch) | ✅ |
| Saree + blouse look | ✅ |
| Swap jeans → skirt: preview and product cards update immediately | ✅ |
| Swap when re-checking fails: chosen piece kept, "reasons may be outdated" notice, Save look saves the new piece | ✅ |
| Missing item photo: colour swatch with "photo unavailable" in both preview and product card | ✅ |
| Add own photo to a saved look → *Verified · your photo* | ✅ |
| Swap a piece in that look → *Illustration* + "photo is outdated (now includes White sneakers)" + *View old photo* labelled *Outdated photo* | ✅ |
| Phone: preview 314 × 523 px, no sideways scrolling; desktop: preview and details side by side | ✅ |
| Fixed during the pass: caption cut off; necklace charm covering the top; a new message being hidden early by an older one | ✅ |

### Illustrated model, on a copy of the real wardrobe (17 Oct 2026)

| Check | Result |
|---|---|
| "white fancy" (white ruffle top photographed on an orange wooden backdrop with a hanger) is drawn **white** with ruffle lines | ✅ |
| "black baggy jeans" (photo on a model) → wide-leg black trousers | ✅ |
| Crop top + mini skirt, pencil/bodycon skirt, gown, short frock, long one-piece | ✅ *(bodycon was A-line at first: fixed)* |
| Kurta + churidar + dupatta + juttis + jhumkas + potli; saree + blouse with pallu and border | ✅ |
| Sling, handbag, potli; earrings, necklace, bangles, bracelet, watch | ✅ |
| Skin tone from Preferences (Light, Medium, Tan, Deep) | ✅ |
| Phone: 314 × 523 px preview, no sideways scrolling | ✅ |

## Virtual try-on pass (17 Oct 2026)

Run with a **stand-in try-on server**: same API, link and token as the Colab notebook, but it returns a coloured test image after 2 s instead of running the AI model. It used a copy of the real wardrobe. **The real CatVTON model has not been run in this environment** (no NVIDIA GPU); run `tryon/Adaa_TryOn_Colab.ipynb` on Colab to try it.

| Check | Result |
|---|---|
| First open: Welcome step asks for a full-length photo; upload saves it; Skip works | ✅ |
| Preferences: wrong token → "The token was rejected…"; right token → "Connected: …" | ✅ |
| AI Stylist: 4 looks start as Illustration + "Putting this look on you…", then become *AI try-on · approximation* **one at a time** | ✅ |
| Caption lists pieces not shown on you (shoes, earrings, chain, bag, watch) | ✅ |
| Swap the top → previous try-on faded with "Updating for your swap…" → new image | ✅ |
| Swap back → original image instantly from cache (no new GPU work) | ✅ |
| Server stopped → swap kept, Illustration + "Can't reach your try-on server… Colab…" + Try again | ✅ |
| Server restarted → Try again works immediately | ✅ *(fixed: it was blocked for 30 s by the offline pause)* |
| Saved Looks → "Show it on me" → try-on | ✅ |
| Phone: no sideways scrolling; try-on label no longer shows above the open menu | ✅ *(fixed during this pass)* |

## Outfit board pass (18 Oct 2026)

Run on a **copy of the real wardrobe** (23 items).

| Check | Result |
|---|---|
| Background removal runs in the browser (IS-Net + onnxruntime-web), in a Web Worker | ✅ about 20–45 s per garment, once each, page stays responsive |
| Background queue makes all missing cut-outs on its own after the app opens; boards update as each one finishes | ✅ 23 of 23 |
| Clean results: skirts, jeans, shoes, earrings, watch, chain, bags | ✅ |
| "white fancy" photographed on orange wood with a hanger | ✅ wood removed; hanger needs **Frame just the garment** |
| Jeans photographed on a model | ✅ with framing (waist to hem) |
| Outfit board: top over bottom, shoes below, jewellery and bag around; badge *Your pieces*; instant | ✅ |
| Phone layout | ✅ |
| Fixed during the pass: pale haze around garments (mask contrast), coloured fringe (1-px edge shave), beige boxes from the product-card image style, WebGPU and multi-threaded modes hanging (now single-threaded worker), slow-down in hidden tabs (moved to a worker) | ✅ |
| Not done in this environment | Running in a normal visible Chrome tab, where it should be faster |

## Outfit board accuracy pass (18 Oct 2026)

Run on a **copy of the real wardrobe** after adding the clothes parser and the proportional layout.

| Check | Result |
|---|---|
| Top photographed **on a model** ("fancy top") | ✅ face, hair, arms and the model's jeans removed; only the top remains, clean edge |
| Jeans photographed on a model ("black baggy jeans") | ✅ hands and the model's top removed without framing. ⚠️ The white sneakers stay (the parser reads them as part of the jeans in this very small photo); **Frame just the garment** above the shoes fixes it |
| Flat lays and product photos (skirts, crop tops) | ✅ unchanged quality |
| Top on a **hanger** ("white fancy") | ⚠️ the hanger stays (the parser counted it as part of the top, so it is not used for hanger photos). **Frame just the garment** trims the hook; a photo without the hanger is best |
| Older cut-outs redone automatically with the new method | ✅ (`cutout_version`) |
| Board: top sized to the bottom, top hem over the waistband, shoes under the hem, accessories in two columns | ✅ |
| Necklace placement | ✅ moved to the side column: chain product photos are long diagonal lines that looked like a hanger wire over the top |
| *Try on me (AI)* button | ✅ moved to a small corner chip so it no longer covers the shoes |
| Fixed during the pass: overlapping jobs made the parser fail ("Session already started") and a weaker picture was saved silently; now jobs run one at a time and a failure is retried. The parser cut part of a white bag photographed alone; now it is only used when someone wears the garment. Faint floating specks removed. Tall tops (shot on a model) drawn no taller than wide | ✅ |
| Midi skirt worn by a model ("black bodycon skirt"): the parser called most of it "dress" and the crop top "hat"/"face", so keeping only "skirt" pixels shredded it | ✅ fixed by switching to a **subtractive** method: keep what background removal sees, cut away only what is clearly the person, shoes, bag or the other garment. Re-checked 10 worn photos (skirts, jeans, gowns, dresses, tops): all whole and clean |
| Backend tests | ✅ 93 passed |
