# Adaa: how it works

This explains how Adaa is put together and why it was built this way. For setup, see the [README](../README.md).

## The big picture

```
 Browser (React + Vite, port 5173)
   │   pages: Overview · My Wardrobe · AI Stylist · Saved Looks · Wedding Planner
   │          Trip Planner · Wear Stats · Shop Smart · Preferences
   │   all calls go through src/api.js  →  /api/...
   ▼
 Vite dev server  ── forwards /api/* ──►  FastAPI backend (port 8000)
 (on the live server there is no Vite: the backend serves the built app itself, see "Running on a server")
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

## Accounts (`auth.py`, `routes/auth.py`)

- **Consent:** sign-up requires `accept_privacy` ("I'm 18 or older and agree to the privacy note"); the time is stored in `users.privacy_accepted_at`. The note itself is `PrivacyNote.jsx`.
- **Forgot password:** `POST /api/auth/forgot` always gives the same reply (nobody can learn who has an account) and sends the email after replying, via `mailer.py` (any SMTP service; printed to the terminal when none is set). The link is `ADAA_PUBLIC_URL/#reset=<token>` (after `#`, so the token never reaches server logs), never built from request headers, so a forged request can't point it at another site. Tokens are random, stored only as SHA-256 in `password_resets`, work once, for 30 minutes; at most 3 emails per address per hour.
- **New password** (reset or change) ends every session and cancels unused reset links; changing it in Preferences keeps the current browser signed in. Both changing the password and deleting the account ask for the current password (wrong tries count towards the 5-try throttle).
- **Delete account:** one transaction removes looks (with their pieces and photos), history, wardrobe items, then the user (sessions and reset links cascade); the photo files are deleted from disk afterwards. The browser also forgets that account's saved preferences.
- **Limits:** `ADAA_MAX_ITEMS` (300) pieces and `ADAA_MAX_LOOKS` (200) looks per person (403 with a friendly message), and an optional `ADAA_MAX_USERS` cap on accounts. `ADAA_SECURE_COOKIES=1` adds `Secure` to the cookie behind https.
- **Sign-up** asks for name, email, phone and a password (8+ characters). Email is stored lower-case and must be unique; phone keeps only digits (10 to 15) and a leading `+`.
- **Passwords:** Python's built-in `hashlib.scrypt` (n=2^14, r=8, p=1) with a random 16-byte salt, checked with `hmac.compare_digest`. No extra packages needed.
- **Sessions:** a random token in an HttpOnly, SameSite=Lax cookie (`adaa_session`, 30 days). The database keeps only its SHA-256, so a copied database can't be used to log in.
- **Throttle:** 5 wrong passwords for one email within 15 minutes → 429 until the window passes.
- **Every data route** takes `user: auth.User` (a FastAPI dependency that returns 401 when logged out) and passes `user["id"]` to every query, so one account can never read or change another's items, looks, history or photos.
- **Upgrading:** `wardrobe_items`, `looks` and `wear_log` gain a `user_id` column on startup. The first account to sign up claims all rows without an owner.
- **Frontend:** `Root.jsx` asks `/api/auth/me`; logged out → `AuthScreen`, else the app inside a `UserContext`. `useUser()` gives `first` (first name), used in greetings, page titles, toasts, the stylist's replies and a personal line on each look. Browser storage keys get a per-account suffix (`adaa.preferences.u3`). Any 401 shows the log-in screen again.

## Data model (SQLite)

```
users: id, name, email (unique), phone, password_hash, created_at, privacy_accepted_at, email_verified_at
email_verifications: token_hash, user_id → users (CASCADE), expires_at, used_at
style_profiles: user_id → users (CASCADE), height, body shape, fit, undertone... (see "Style profile")
password_resets: token_hash, user_id → users (CASCADE), expires_at, used_at
sessions: token_hash, user_id → users (CASCADE), expires_at

wardrobe_items              looks                       wear_log
──────────────              ─────                       ────────
id                          id                          id
user_id → users             user_id → users             user_id → users
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
- **Testable:** the same input always gives the same output, so behaviour is pinned down by automated tests (about half of the 258 backend tests cover styling: the engine, parser, planners, festivals, weather and style profile).

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

*Earlier versions, dropped after testing with the real wardrobe:*
- *Photos cut into garment shapes on a mannequin:* photo backgrounds and models' legs showed through.
- *A drawn female model in colours read from the photos:* it looked generic, not like the actual pieces.
- *AI try-on on the user's own photo (CatVTON on a free Colab GPU):* about a minute per look, needed the notebook running, and got shapes and shoes wrong. Removed on 20 Oct 2026; the code is in git history.

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

## Frontend notes

- `App.jsx` holds the layout and navigation. Each main page is its own file in `pages/`.
- **Wi-Fi sharing:** `npm run share` = `vite build && vite preview --host`. The preview server (port 4173) is reachable on the home network and forwards `/api` to the backend, which itself stays on 127.0.0.1:8000. The session cookie has no `Secure` flag, so login works over plain http on the LAN.
- **Installable app:** `public/manifest.webmanifest` (standalone, plum theme, 192/512 icons and a maskable 512 icon with the A inside the safe circle) and Apple meta tags in `index.html`. No service worker: every screen needs the backend anyway, so there's nothing useful to cache offline (an offline page is planned for the Play Store version).
- **Phones:** `cutoutQueue.js` skips automatic cut-outs on touch devices with a small screen (the IS-Net model is ~179 MB); the board shows the original photo until a computer makes the cut-out. `AskBox.jsx` hides the microphone when `window.isSecureContext` is false.
- **Opening animation (`Splash.jsx`):** `Root.jsx` shows it once per tab (`sessionStorage` `adaa.splashSeen`) while it checks who is logged in, always in the same place so it never restarts. `assets/adaa-splash.svg` is the plum logo with each part in its own group (`s-mark`, `s-shine`, `s-name`, `s-thread`, `s-dot`, `s-tag`), imported with `?raw` so CSS can animate the parts: focus-in (scale + blur), a gold glint clipped to the A, `clip-path` reveals for the name and tagline, the thread scaling out from the centre. After about 6 s (or a tap / key) it slides up in 0.9 s. With `prefers-reduced-motion` it's a still logo that fades out. Pure CSS, no libraries.
- The Style me form is the single source of truth: typed requests, the ✦ "Style this" button and saved preferences all just fill in the form, then call `/api/recommendations`.
- Swapping a piece calls `/api/outfits/alternatives`, then `/api/outfits/evaluate`, so the reasons always match the current pieces.
- Preferences are a per-browser convenience (`localStorage`, one set per account), used as the form's starting values.
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

## Running on a server (`deploy/`, `backup.py`, docs/DEPLOY.md)

```
browser ──https──► Caddy (Let's Encrypt, security headers, 12 MB body limit)
                     └──► uvicorn main:app on 127.0.0.1:8000 (systemd service "adaa", user "adaa", 1 worker)
                             ├─ /api/*        the API
                             └─ everything else: frontend/dist (index.html for app screens)
data: /var/lib/adaa (ADAA_DATA_DIR)      settings: /etc/adaa.env      backups: /var/backups/adaa (timer, 03:30)
```

- **One program:** when `frontend/dist/index.html` exists (`ADAA_FRONTEND_DIR`), `main.py`'s last route serves the build: real files directly (`assets/*` cached for a year because their names carry a content hash; everything else `no-cache`), any other non-API address gets `index.html`. Paths are resolved and must stay inside the build folder. In development the folder doesn't exist and Vite serves the app as before.
- **One worker on purpose:** SQLite and the in-memory login/reset throttles assume a single process. Plenty for friends and family.
- **Backups (`backup.py`):** SQLite's online backup API copies the database consistently while Adaa runs; it and `uploads/` go into one `adaa-YYYYMMDD-HHMMSS.tar.gz`, written as `.part` and renamed when complete; the newest `ADAA_BACKUP_KEEP` (7) are kept. Restore extracts with `tarfile`'s `data` filter (no paths outside the folder, no links), keeps the replaced data as `*.before-restore`, and refuses to overwrite without `--force`. The AI models aren't backed up; they download again.
- **Hardening:** the service may only write to its data and backup folders (`ProtectSystem=strict`), runs as its own user without a login shell, and the backend only listens on localhost. `install.sh` opens ports 80/443 in the server's own iptables (Oracle's Ubuntu images block them) and adds swap on 1 GB machines so the build fits.
- **Deploy files keep LF line endings** (`.gitattributes`), so scripts edited on Windows still run on Linux.

## Style profile (`recommender/profile_fit.py`, `routes/profile.py`)

- **Table `style_profiles`** (one row per user, deleted with the account): `height_cm` (CHECK 120–220), `body_shape` (hourglass, pear, apple, rectangle, inverted_triangle), `fit` (fitted, regular, relaxed), `undertone` (warm, cool, neutral), `gender` (woman, man, non_binary), JSON lists `avoid` (sleeveless, short_hemlines, bodycon, crop_tops), `love_colours`, `avoid_colours`, the Style me defaults (`style`, `comfort`, `colour_mood`) and `onboarded`. Every column is optional; CHECK constraints back up the Pydantic validation. Weight and clothing sizes are deliberately not collected.
- **API:** `GET /api/profile/style`, `PATCH /api/profile/style` (only sent fields change, so the Preferences page and the profile screen never overwrite each other). The profile is read from the database inside the routes, never taken from the request, so it can't be spoofed.
- **How it's used:** `profile_fit.traits()` reads each piece's cut from its type, name and notes (palazzo → flowy / wide-leg / long; "skin fit" → fitted; "crop" → cropped; "sleeveless", "mini"...). `apply()` adds small points with a reason to each base outfit before the engine picks (so it affects ranking), `apply_jewellery()` adds the metal note after jewellery is chosen. Reasons go to a separate `personal` list shown as **"Why it suits you, <name>"**. Rules: body shape and height only add bonuses; undertone only adds colour notes (never a caution); preferred fit adds a bonus (a small minus for bodycon when someone prefers relaxed); styles and colours the person said they avoid rank lower *with a caution* but are never hidden (if they're all the wardrobe has, they still appear). Shop Smart hides women-only ideas only if someone chose "man".
- **Sign-up flow:** after the first log-in, a 2-step card (skippable at any point) asks the questions; `onboarded` stops it reappearing. Preferences has the same form plus Clear all. The old per-browser Style me preferences now sync to the account (the account wins; a browser that has some uploads them once).

## Launch hardening (6 Nov 2026)

- **Photos:** the browser redraws every upload upright at ≤1600 px (`photo.js`: JPEG stays JPEG, others become WebP/PNG), which drops EXIF/GPS and makes files ~10× smaller; originals up to 25 MB can be chosen. The server still checks the type and strips metadata itself (`image_meta.py`, pure Python: JPEG APP1/APP13/COM, PNG eXIf/tEXt/zTXt/iTXt/tIME, WebP EXIF/XMP; ICC colour profiles kept). Photo URLs carry a version, so they're cached `private, max-age=30 days, immutable`.
- **Rate limits (`ratelimit.py`):** per address, in memory: sign-up 10/h, log-in 20/15 min (plus 5 wrong passwords per email), forgot 5/h, reset 10/h, verify 20/h, model download 10/h, uploads 300/h, crash reports 30/h, everything else 1500/min. 429 with `Retry-After`.
- **Cross-site requests (`security.py`):** POST/PUT/PATCH/DELETE to `/api/` with an `Origin` that isn't this site's host (or `ADAA_PUBLIC_URL`) get 403. **CSP** on the app page: `default-src 'self'`, `script-src 'self' 'wasm-unsafe-eval'` (the in-browser model), `worker-src 'self' blob:`, `connect-src` self + Open-Meteo, `frame-ancestors 'none'`, `object-src 'none'`. Fonts are self-hosted (`@fontsource`, OFL) so no request goes to Google.
- **Tokens never in logs:** reset and confirmation links use `#reset=` / `#verify=`; the part after `#` never reaches the server.
- **Email confirmation:** `email_verifications` (hashed, one use, 24 h, max 3 emails/h); `users.email_verified_at`. Nothing is blocked while unconfirmed; a banner offers a new link.
- **Errors:** unexpected exceptions are logged with the request path and answered with a calm 500 (no internals); a React error boundary shows "Something went wrong · Reload" instead of a blank page and reports the message (no personal data) to `POST /api/client-error`, which is logged.
- **Database:** WAL mode (readers don't wait for writers); restore also moves the old `-wal`/`-shm` files aside.
- **Backups off-site (`offsite.py`):** after each nightly backup the `.tar.gz` is PUT to S3-compatible storage (Backblaze B2 in production) with AWS Signature V4 (stdlib + httpx; checked against Amazon's published example). Old copies are removed by the bucket's lifecycle rule. A failed upload makes the backup service exit 1 (visible as "failed" in systemd) while keeping the local copy.
- **Supply chain:** `requirements.lock` pins exact versions (server installs with `-c`), `npm audit`: 0 vulnerabilities. Server logs are kept 30 days (journald), as the privacy note says.
