# Adaa: testing

## Automated tests (backend)

Run from `backend/` with the virtual environment active:

```powershell
python -m pytest
```

Expected result: **61 passed**. Each test runs against a fresh temporary database and photo folder, so your real wardrobe is never touched.

| File | Tests | What it covers |
|---|---|---|
| `test_items.py` | 10 | Add, list, search, filter, edit (with and without a new photo), delete; rejects fake images, oversized photos and invalid details; 64 simultaneous photo requests |
| `test_recommendations.py` | 19 | Only real items are used and outfits are distinct; pairing rules; empty wardrobe; occasion tags; honest relaxed mode; building around a piece; colour, comfort and style preferences; consistent metals; saree blouse; minimal jewellery for casual looks; colour parsing; API validation |
| `test_parser.py` | 18 | Occasion words (sangeet, diwali, interview…); style, comfort and colour mood; *"Style my black crop top for a party"*; name vs type matching; typos; asking when ambiguous; reporting pieces you don't own; missing occasion |
| `test_looks.py` | 13 | Save, list, rename, delete looks; no duplicates; numbered names; swap options stay wearable and tagged pieces rank first; evaluation cautions; swaps inside saved looks; wear history; history survives deleting a look; no future dates; deleting a wardrobe item keeps the look and flags it |
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

1. `python -m pytest` → `61 passed`
2. Backend running: http://127.0.0.1:8000/api/health → `"status":"ok"`
3. Frontend running: http://localhost:5173 → Overview shows your piece count
4. AI Stylist → ask for one of your demo requests → outfits with photos appear
