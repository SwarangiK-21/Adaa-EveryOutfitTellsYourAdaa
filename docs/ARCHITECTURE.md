# Adaa: how it works

This explains how Adaa is put together and why it was built this way. For setup, see the [README](../README.md).

## The big picture

```
 Browser (React + Vite, port 5173)
   │   pages: My Wardrobe · AI Stylist · Saved Looks · Preferences
   │   all calls go through src/api.js  →  /api/...
   ▼
 Vite dev server  ── forwards /api/* ──►  FastAPI backend (port 8000)
                                            │
                     routes/items.py ───────┤  add / list / edit / delete items, photos
                     routes/recommendations.py  parse requests, recommend outfits
                     routes/looks.py ───────┤  swaps, saved looks, history
                                            │
                        recommender/ ───────┤  rule-based engine (pure Python)
                        storage.py ─────────┤  photo checks + files on disk
                        database.py, looks_db.py  SQLite queries
                                            ▼
                         backend/data/adaa.db   +   backend/data/uploads/*.jpg|png|webp
```

Each part has one job:

| Concern | Where |
|---|---|
| Screens and interaction | `frontend/src/pages`, `frontend/src/components` |
| Talking to the server | `frontend/src/api.js` (the only file that knows URLs) |
| HTTP routes, status codes, error messages | `backend/routes/` |
| Input validation | `backend/schemas.py` (Pydantic) |
| Database queries | `backend/database.py`, `backend/looks_db.py` |
| Photo handling | `backend/storage.py` |
| Styling logic | `backend/recommender/` (no web or database code inside) |

Because the recommender is plain Python that takes a list of items and returns outfits, it's easy to test on its own: most engine tests never start a server.

## Data model (SQLite)

```
wardrobe_items              looks                       wear_log
──────────────              ─────                       ────────
id                          id                          id
name                        name                        look_id → looks (SET NULL on delete; NULL
category                    prefs (JSON: occasion,                for outfits worn without saving)
item_type                          style, colour,       look_name   (kept even if look is deleted)
colour                             weather...)          occasion
style                       missing_pieces              worn_on     (date)
occasions (JSON list)       created_at, updated_at      created_at
notes
price (optional)            look_items                  wear_items
cutout_filename/_version    ──────────                  ──────────
image_filename              look_id → looks (CASCADE)   wear_id → wear_log (CASCADE)
created_at, updated_at      item_id → wardrobe_items    item_id (no FK: history outlives items)
                            position
```

- Foreign keys are switched on for every connection, so a saved look can never point at an item that doesn't exist.
- Deleting a wardrobe item runs in one transaction: it removes the item from any saved looks, adds 1 to each look's `missing_pieces` (so the look can say "1 piece was deleted"), then deletes the item and its photo.
- History stores the look's name and occasion, and `wear_items` stores the exact pieces worn that day, so history (and wear stats) survive later swaps or deleting the look. Older history is filled in from the saved look's pieces on startup.
- Tables are created with `CREATE TABLE IF NOT EXISTS` on startup, so older databases gain new tables automatically without losing data.

## Photos

`storage.py`:
1. Reads at most 5 MB + 1 byte, and rejects anything bigger.
2. Checks the file's **first bytes** (its "magic number") to confirm it's really JPEG, PNG or WebP. A renamed text file is rejected even if it ends in `.jpg`.
3. Saves it under a **random name** (e.g. `3f9c…e1.jpg`), never the user's file name, which avoids clashes and path tricks.
4. Photos are only served through `/api/items/{id}/photo`, which looks the file up from the database. The URL includes `?v=…`, so browsers show the new photo straight after it changes.

The browser also checks type, size, and that the image can actually be displayed before uploading, so users get instant feedback.

## The recommendation engine (`backend/recommender/`)

| File | Job |
|---|---|
| `colours.py` | Understands free-text colours (*"Sage green"*, *"daimond"*) and rates how two colours go together |
| `garments.py` | Works out what part of an outfit each item is (top, bottom, saree, dupatta, earrings, footwear…) and which tops and bottoms pair |
| `engine.py` | Builds, scores and picks outfits; evaluates a given outfit; suggests swaps |
| `parser.py` | Turns a typed request into the same filters the form uses |

### How outfits are built

1. **Classify** every item from its type (or name), with small typo tolerance: *Kurta → Top*, *Churidar → Bottom*, *Gown → Outfit*, *Jhumkas → Earrings*.
2. **Build bases:** every one-piece (gown, saree, dress…), and every top + bottom pair that makes sense. A kurta goes with a salwar, palazzo or jeans; a crop top never goes with a churidar.
3. **Score each base:**
   - occasion tag: strongly preferred
   - requested style: Traditional and Western clash; Indo-Western bridges both
   - colour harmony: neutrals, tonal, analogous, complementary, or a clash
   - favourite colour and colour mood
4. **Complete each base:**
   - Add a blouse for a saree, and a dupatta for a kurta if one suits.
   - Add the best footwear, earrings, necklace, bangles/bracelet, bag and accessory.
   - Only add pieces **tagged for that occasion**.
   - Keep jewellery metals consistent, use at most 2 pieces for casual/college/office looks, and prefer flats for "Comfort first".
5. **Pick up to 4 different outfits:** each new pick is penalised for reusing garments or accessories already chosen, so the looks really differ.
6. **Explain:** every outfit gets reasons (*"A classic kurta and churidar pairing"*) and cautions (*"Not Traditional: you don't have a Traditional option"*). The response also includes notes about anything missing.

If nothing is tagged for the occasion, it relaxes that rule, says so clearly, and shows the closest matches.

### Why rule-based instead of an AI model?

- **Honest by construction:** it can only ever pick from your items, so it can't "hallucinate" a piece you don't own.
- **Explainable:** every suggestion comes with the actual reasons it was chosen.
- **Free and local:** no API keys, no internet, no costs, works on any laptop.
- **Testable:** the same input always gives the same output, so behaviour is pinned down by 79 automated tests.

An optional free local language model could later make the chat friendlier, but it would only *read* requests and *write* explanations. The rules would still choose the clothes.

### Understanding typed requests (`parser.py`)

- **Occasions:** phrases are matched longest-first: *"family function"* → Traditional function, *"sangeet"* → Wedding, *"interview"* → Formal, *"movie"* → Casual.
- **Other preferences:** style, comfort and colour-mood words are matched the same way.
- **"My …":** matched against **your** item names and types. A match on the name beats a match on the type only. A colour word alone never picks an item, and typo tolerance is strict enough that *kurta* ≠ *kurti*.
- **Unknown pieces:** if you name a kind of piece you don't own (*"my green kurta"*), it reports it as not found.
- **Ties:** if two pieces match equally (*"my bracelet"*), it asks which one you meant.
- **Follow-ups:** a message without an occasion (*"make it more comfortable"*) keeps the current occasion and changes only what you mention.

## Outfit previews

`frontend/src/components/OutfitPreview.jsx` shows a large full-body preview at the top of every outfit card. It uses the best kind available:

| Priority | Kind | Status in Adaa |
|---|---|---|
| 1 | **Verified:** the user's own photo wearing a saved look | Shown only while the look's pieces still match the photo (stored in `look_photos`). |
| 2 | **Outfit board** ("Your pieces"): the user's own garment cut-outs, arranged as if worn | **The default.** Instant, offline, exact pieces (see *Outfit board* below). |
| 3 | **AI try-on** on the user's own photo | Optional: only when the Colab server is connected and the user presses **Try on me (AI)** (see *Virtual try-on*). |

*Earlier versions, dropped after testing with the real wardrobe:*
- *Photos cut into garment shapes on a mannequin:* photo backgrounds and models' legs showed through.
- *A drawn female model in colours read from the photos:* it looked generic, not like the actual pieces.
- *Automatic AI try-on for every look:* too slow on a free GPU, and inaccurate (wrong shapes, smudged shoes).

**Verified photos and staleness:**
- `POST /api/looks/{id}/photo` saves the photo (with the same file checks as item photos) together with the look's `item_ids`.
- `GET /api/looks` reports `photo.matches_current`, which turns false once a piece is swapped or deleted, plus `changed_pieces`. The UI then shows the outfit board with *"Your photo of this look is outdated (now includes …)"* and a **View old photo** option labelled *Outdated photo*.

**Swaps that can't be re-checked:** if the evaluate request fails after a swap on the Stylist page, the chosen piece is kept (preview, product cards and Save look all use it), and the card says the reasons may be outdated.

## Outfit board (default preview)

The default preview is a "ghost mannequin" board built from the user's own photos, without AI image generation.

```
add/edit item ──► cutoutQueue.js (one at a time) ──► cutout.worker.js (Web Worker)
                                                        │ fetch photo → IS-Net 1024×1024 (background)
                                                        │            → clothes parser 512×512 (which pixels are the garment)
                                                        │ background × garment mask → drop stray bits → trim
                                                        │ (onnxruntime-web, CPU, 1 thread)
                                                        ▼
                                PUT /api/items/{id}/cutout  (PNG, stored next to the photo)
OutfitBoard.jsx: sizes the pieces to each other using each cut-out's real proportions
  (top at most ~1.35× the bottom's width, top hem over the waistband, shoes ~half the hem width just under it,
   earrings/bangles/watch stacked on the left, necklace/bag/extra jewellery on the right, close beside the outfit)
```

- **Models:** downloaded once by `backend/cutout_model.py` into `backend/data/models/` and served at `/api/models/{name}` with long-lived caching:
  - `isnet`: IS-Net "isnet-general-use" (Apache 2.0) for the background.
  - `clothes`: SegFormer-B2 clothes parser (Xenova/segformer_b2_clothes, quantised ONNX, 18 ATR labels). **NVIDIA licence: non-commercial / research use only.** `partsFor()` in `cutoutQueue.js` picks the labels for each item (jeans → pants, crop top → upper clothes, sandals → shoes, bag → bag; jewellery and watches skip the parser).
- **Combining (subtractive):** the parser is used only when it finds a person (hair/face/arms/legs over 1 % of the picture) and the garment (over 2 %). Adaa keeps what IS-Net sees and only **cuts away what the parser clearly labels as something else**: the person (face, hair, arms, legs), hat/sunglasses, shoes, and the other garment (a top's jeans, a skirt's top). Look-alike labels are never cut (the parser often reads a skirt as "dress"), so uncertain parts of the garment stay instead of leaving holes. The cut-away area is grown by one cell, so thin fringes (skin, a sneaker edge, the top underneath) go too. The parser's garment area (grown by 3 cells) then only decides **which pieces to keep**: a piece must lie mostly on it, which drops chairs and curtains. Product photos, flat lays and hangers use IS-Net alone. If the parser fails, the cut-out fails and is retried later. The worker runs one job at a time. Pieces smaller than 15 % of the biggest are dropped, so pairs like two shoes or earrings stay; faint pixels survive only next to the kept garment.
- **Versions:** each cut-out stores `cutout_version` (`7` automatic, `7m` framed or touched up by the user). Bumping `CUTOUT_VERSION` redoes older automatic cut-outs in the background.
- **Why in the browser:** onnxruntime has no Python 3.15 build, so it can't run in the backend. WebGPU hung on Intel Iris Xe, and multi-threaded WASM hung too (nested threads), so it runs single-threaded in a **Web Worker**. That way it isn't throttled in background tabs and doesn't freeze the page.
- **Framing and erasing:** `CutoutEditor.jsx` lets the user drag a box around just the garment (only that part is processed), and `EraseCutout.jsx` is a brush that paints leftovers transparent on a canvas (undo, then trimmed and saved). Both save with an `m` version and are never redone automatically.
- **Lifecycle:** replacing an item's photo clears its cut-out (a new one is queued), and deleting an item deletes its cut-out file. Older databases get the `cutout_filename` column automatically on startup.
- **Fallback:** until a cut-out exists, the board shows the original photo in that position, and the caption says "Cleaning up photo backgrounds… (n of m)".
- **Download image:** `boardImage.js` redraws the board on a 900×1500 canvas from the pictures exactly where they appear on screen (same cream background and shadows), adds the look's name, and downloads it as `adaa-<look>.png`. All in the browser.
- **Photo tips:** `ItemForm.jsx` shows short tips for clean garment photos under the photo box, since the board is only as good as the photo.

## Planning (`recommender/planner.py`)

Both features reuse the stylist's own rules (roles, top/bottom fit, colour harmony, occasion tags), so their advice matches the outfits Adaa suggests.

**Shop Smart (`GET /api/insights/gaps`).** A fixed catalogue of 17 versatile pieces (white sneakers, black heels, nude flats, gold juttis, blue jeans, black/beige trousers, black skirt, white shirt, black top, white kurta, white palazzo, gold jhumkas, silver studs, black clutch, tan tote, gold potli), each with the occasions it's usually worn for. For each one you don't already own (same kind and colour family; denim counts as blue):
- *Clothes:* the wardrobe's outfit bases (top + bottom or a one-piece, tagged for the occasion, no colour clash) are counted with and without it. The difference is "new outfits".
- *Shoes / bag / earrings:* the outfits it would finish for occasions where you have none of that kind tagged.
Clothes and shoes are ranked first (they make outfits possible), then bags and jewellery; the best shoe idea always makes the list. It also notes occasions with no complete outfit and a lopsided top/bottom count. Ideas only: there are no shop links.

**Trip Planner (`POST /api/trips/plan`).** Rule: **no garment is worn twice on a trip** (shoes, bags and jewellery may be). For each day (1-14, an occasion each) it lists the 12 best outfit bases tagged for that occasion, plus the 6 best untagged ones at a cost. A search then picks one per day so that no garment appears twice, filling as many days as possible with the best total score. It starts with the days that have the fewest options, so a scarce Party outfit isn't used up on a Casual day; this is capped at 60,000 steps. A day that can't get fresh clothes is left empty with a note ("not enough different clothes for Party... add or tag more") instead of repeating. Shoes, earrings, necklace and bag prefer pieces already in the suitcase. The result lists each day's outfit, a packing list (the days each piece is used) and notes.

## Wedding planner (`recommender/events.py`)

Each function has occasions (tagged for any of them counts), a usual style and comfort, dress-code colours, colours to avoid, and a short dress code shown to the user:

| Function | Dress code |
|---|---|
| Haldi | Yellow, mustard, lemon or orange; comfort first |
| Mehendi | Greens; comfort first |
| Sangeet | Pink, magenta, purple, royal blue, gold or silver; Indo-Western |
| Cocktail | Black, navy, wine, emerald or metallics; Western, polished |
| Engagement / Roka | Pink, peach, lavender, rose, gold or blush |
| Wedding ceremony | Red, maroon, pink, magenta, gold, orange or wine; traditional; avoid white and black |
| Reception | Wine, navy, emerald, gold, silver or black; polished |
| Puja / Griha pravesh | Yellow, red, orange, cream, white or green; traditional |

It uses the trip planner's search (`planner.plan_days`, with a `DaySpec` per function), so **no garment is worn twice**. Each garment in a dress-code colour adds 3 points; each one in an avoided colour, or a casual piece (jeans, shorts, tees, hoodies) at the wedding, reception, engagement or cocktail, costs 4. Shoes, earrings, necklace, bangles and bag are reused across functions. Each look says why ("Fits the dress code: your Red Saree"), or cautions when nothing in the colours exists ("…so this is the closest match") or a piece is too casual.

## Festivals (`recommender/festivals.py`)

One table of about 30 festivals and national days: Republic and Independence Day, Gandhi Jayanti, Makar Sankranti, Pongal, Lohri, Bihu, Vasant Panchami, Maha Shivratri, Holi, Gudi Padwa / Ugadi, Baisakhi, Ram Navami, Eid, Raksha Bandhan, Teej, Janmashtami, Onam, Ganesh Chaturthi, Navratri, Durga Puja, Dussehra, Karva Chauth, Dhanteras, Diwali, Bhai Dooj, Chhath, Gurpurab, Christmas, New Year's Eve and Valentine's Day. For each one it stores:
- the ways people type it ("ganpati", "26 jan", "uttarayan", "bakri eid"…),
- the usual colours (e.g. Republic Day: saffron, white, green; Makar Sankranti: black, yellow, green),
- the usual occasion and style, and a short tip.

- **Typed requests:** the parser finds the festival first, tolerating small typos for longer names ("ganesh chaturti", "sankranthi"); short ones like Holi, Eid and Teej must be exact. It sets `festival`, the festival's occasion (unless another is named: "Diwali party" stays a party, while "Diwali puja" means Diwali) and its usual style (unless you ask for another). During Navratri it also sets **today's colour**.
- **Styling (colour first):** when a request names a colour ("gulabi" → pink) or a festival (its usual colours), Adaa shows **only outfits in those colours**. The typed colour wins over the festival's. Pieces in the right colour that aren't tagged for the occasion are allowed, with a caution ("…isn't tagged for Festive, but it's in pink"). Outfits are ranked by how much of the outfit is in colour (+12 × share), so a green saree beats a white top with black jeans for 15 August. If nothing matches, the closest looks are shown with a note ("Nothing in your wardrobe is yellow…"), and fewer than 4 matches gets "Only 2 outfits in pink… add more". Each piece in a festival colour also gets +1.5, and each look says *"Saffron, white and green for Republic Day: your …"*. The festival stays on the form as a chip (with ×) and carries over to swaps and saved looks.
- **Dates:** `DATES` lists Oct 2026 to Dec 2027, checked against several calendars, with Navratri's 9 day colours (2027 follows the usual weekday rule). `GET /api/festivals/now` gives today's festival or the next one within 3 weeks for the Overview card ("Navratri Day 9: Peacock Green · Maa Siddhidatri"). Its button opens the stylist preset to that festival and styles at once. Dates that weren't consistent across sources were left out, and the card notes that dates can differ by a day by region.

## Hinglish and voice (`recommender/parser.py`, `AskBox.jsx`)

- **Hinglish:** the parser knows Hindi colour words (lal, peela, hara, neela, kaala, safed, gulabi, aasmani…, in `colours.HINDI`), occasion words (shaadi, sagai, tyohar, dussehra, safar, daftar, ghoomne…), comfort words (aaram, halka / bhaari, shandaar) and moods (rangeen, gehra). Filler words (aaj, ke liye, kuch, meri…) are ignored. Hindi colour words are translated before matching your pieces, so *"meri hari kurti"* finds your **green** kurti. Two-word colours like "sky blue" (from "aasmani") are recognised.
- **Voice:** a microphone button (Chrome / Edge) uses the browser's Web Speech API with Indian English (`en-IN`), which handles Hinglish. The words appear in the box as you speak and are sent when you stop. In Chrome the audio goes to Google's speech service; nothing is recorded by Adaa. The button is hidden where the browser doesn't support it.

## Weather (`recommender/weather.py`, `frontend/src/weather.js`)

- **Forecast:** the browser asks Open-Meteo (free, no key) for today's high, rain chance and weather code at the city saved in Preferences (geocoding by name, also Open-Meteo), cached for an hour. Rain = chance of at least 50 %, or a rain code.
- **Styling:** the request carries `weather: {temp_c, rain, label}` (the stylist chip has a *Use* switch). It's a gentle nudge, not a filter:
  - **Hot (high ≥ 30 °C):** light pieces +1 (crop tops, tees, shorts, skirts, dresses, kurtis, palazzos, sandals, or "linen/cotton/sleeveless" in the name). Warm pieces −1.5, layers −3 (so jackets aren't added).
  - **Cold (≤ 17 °C):** warm pieces +1, layers +2 (so one gets added). Shorts, skirts and sandals −1.5.
  - **Rain:** heels −1, light-coloured bottoms −0.5.
- **Explaining it:** each outfit gets a reason ("Light, breezy pieces for a 34°C day", "Your wool sweater keeps you warm at 9°C", "Rain-friendly…") or a caution ("Might feel warm at 34°C: your jacket", "Rain is expected: your heels may not love puddles"). With no city set, nothing changes.

## Wear stats (`GET /api/insights/wear?days=30`)

Counts come from `wear_items`: *Wore it today* on a saved look, or on any stylist outfit (`POST /api/history`). For each piece, Adaa works out times worn, last worn and days since. **Not worn** lists pieces never worn (oldest first), then those not worn for the longest. **Most worn** shows the top 5. **Cost per wear** = price ÷ max(wears, 1), shown for pieces with a price, best value first. The totals are spent, average cost per wear (spent ÷ total wears) and pieces worn in the window. The window can be 7–365 days (the page offers 30/60/90). The Overview shows a nudge when pieces haven't been worn in 30 days.

## Auto-fill from a photo (browser)

When a photo is chosen in *Add a piece*, `analysePhoto()` (in `cutout.js`) runs the clothes parser in its own Web Worker, so it never waits behind background cut-outs (about 3 s). Top, skirt and dress labels are grouped, and the kind is decided like this:
- If the parser clearly says top or skirt (70 %), that is used.
- Otherwise, when someone is wearing it, legs below mean skirt, arms beside mean top (dress if tall), and a "top" and "skirt" in the same colour mean one dress.
- Otherwise the shape decides: tall means dress; wide at the top means top; wider at the hem means skirt.

Trousers, shoes, bag, dupatta, belt, hat and sunglasses come straight from their labels, and blue trousers become jeans. The colour is the largest group of similar inner pixels (k-means in Lab), matched to the named colours the form suggests; for checks or prints, the most colourful sizeable group wins. Clothes must cover at least 10 % of the photo (6 % when worn), so jewellery isn't mistaken for clothing; then nothing is filled and the form says so. Only fields the user hasn't touched are filled, plus a name like "Denim jeans", and a note asks the user to check.

## Virtual try-on (optional)

```
Adaa frontend ──POST /api/tryon {item_ids}──► Adaa backend (tryon.py)
                                               │  1. plan: dress → "overall"; else bottom → "lower", then top → "upper"
                                               │  2. cache hit? → return saved image instantly
                                               │  3. else, one garment at a time (lock: one job on the GPU):
                                               ▼
                         https://xxxx.trycloudflare.com  (X-Adaa-Token header)
                                               │
                     Colab notebook: FastAPI → CatVTON (fp16, 768×1024, 30 steps) on a free T4 GPU
```

- **Your photo:** stored once in `user_profile` (single row). Replacing or removing it clears cached try-ons.
- **Server settings:** the link and token live in `backend/data/tryon_settings.json`. It's local and git-ignored, and an empty link switches try-on off.
- **Cache:** `backend/data/tryon/<sha1>.png`. The key is made from the exact photo files and cloth types, so a swap makes a new image, and swapping back reuses the old one.
- **Accuracy steps in the notebook:**
  - Garment photos are cleaned before try-on: if someone is wearing the garment, CatVTON's SCHP human parser keeps only that garment; otherwise `rembg` (isnet) removes the background. The garment is then centred on white.
  - After generation, everything outside the mask is copied back from the user's photo (`Image.composite`), so face, hair and background stay identical.
  - Quality is 50 steps ("high", default) or 30 steps ("standard").
- **Shoes (experimental):** a final `shoes` pass masks the feet using the parser's shoe labels (LIP 18/19, ATR 9/10), dilated. If the feet aren't found, the clothes result is kept and a note is returned (stored next to the cached image).
- **What can't be shown on you:** jewellery, watches, bags, dupattas and layers can't be rendered by the model. They're returned as `skipped`, and the caption names them.
- **Frontend (`tryon.js`):** a queue sends one request at a time. Results are remembered per piece combination. If the server is found offline, other cards stop waiting for 30 s, but **Try again** always retries.
- **Previews (`OutfitPreview.jsx`):** Stylist looks request try-on automatically; saved looks have a **Show it on me** button, to save GPU time.
  - While generating: the drawing is shown with *"Putting this look on you…"*.
  - After a swap: the previous try-on is shown faded with *"Updating for your swap…"*.
  - On failure: the drawing is shown with the reason and **Try again**.
- **Errors are actionable:** unreachable (Colab stopped or a new link), wrong token, person not detected in the photo, nothing to try on, or not set up yet. Each one tells the user what to do.
- **Licence:** CatVTON is CC BY-NC-SA 4.0, non-commercial. The original `runwayml/stable-diffusion-inpainting` base was removed from Hugging Face, so the notebook uses the mirror `booksforcharlie/stable-diffusion-inpainting`.

## Frontend notes

- `App.jsx` holds the layout and navigation. Each main page is its own file in `pages/`.
- The Style me form is the single source of truth: typed requests, the ✦ "Style this" button and saved preferences all just fill in the form, then call `/api/recommendations`.
- Swapping a piece calls `/api/outfits/alternatives`, then `/api/outfits/evaluate`, so the reasons always match the current pieces.
- Preferences are a per-browser convenience (`localStorage`), used as the form's starting values.
- Every page has loading, empty and "server unreachable" states.

## Notable bugs found and fixed during development

| Bug | Cause | Fix |
|---|---|---|
| Random 500 errors when many photos loaded at once | A SQLite connection opened on one worker thread was used on another | `check_same_thread=False` (each request still has its own connection), plus a 64-request test |
| Untagged accessories appeared in outfits | A style match outweighed a missing occasion tag | Accessories must be tagged for the occasion |
| *"Sage green"* read as green | Longest colour word won | The first colour word wins (*sage* green, *navy* blue) |
| *"my green kurta"* matched a kurti | Typo tolerance too loose | Stricter similarity threshold |
| Quick occasion taps lost selections | The form used a stale copy of its state | State updates read the latest value |
| Outfit card headings looked like the page's top bar | A global `header{}` style | Scoped reset for `.outfit header` |
