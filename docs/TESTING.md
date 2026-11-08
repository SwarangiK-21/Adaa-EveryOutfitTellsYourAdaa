# Adaa: testing

## Automated tests (backend)

Run from `backend/` with the virtual environment active:

```powershell
python -m pytest
```

Expected result: **258 passed**. Each test runs against a fresh temporary database and photo folder, so your real wardrobe is never touched.

| File | Tests | What it covers |
|---|---|---|
| `test_items.py` | 10 | Add, list, search, filter, edit (with and without a new photo), delete; rejects fake images, oversized photos and invalid details; 64 simultaneous photo requests |
| `test_recommendations.py` | 19 | Only real items are used and outfits are distinct; pairing rules; empty wardrobe; occasion tags; honest relaxed mode; building around a piece; colour, comfort and style preferences; consistent metals; saree blouse; minimal jewellery for casual looks; colour parsing; API validation |
| `test_parser.py` | 38 | Occasion words (sangeet, diwali, interview…); style, comfort and colour mood; *"Style my black crop top for a party"*; name vs type matching; typos; asking when ambiguous; reporting pieces you don't own; missing occasion |
| `test_looks.py` | 13 | Save, list, rename, delete looks; no duplicates; numbered names; swap options stay wearable and tagged pieces rank first; evaluation cautions; swaps inside saved looks; wear history; history survives deleting a look; no future dates; deleting a wardrobe item keeps the look and flags it |
| `test_look_photos.py` | 7 | Verified photo upload and serving; photo becomes outdated after a swap or a deleted piece; replacing/removing/deleting cleans up files; rejects non-images |
| `test_cutouts.py` | 8 | Saving, serving and deleting garment cut-outs; method version stored; new photo clears the cut-out; model download route and unknown models |
| `test_planner.py` | 12 | Shop Smart: missing bottoms and shoes suggested, things you own skipped (denim = blue), bags ranked after clothes, empty wardrobe; Trip Planner: no garment ever worn twice (shoes reused), a plan found where day-by-day picking would fail, an empty day instead of a repeat, only real items, API validation |
| `test_festivals.py` | 8 | Republic Day prefers saffron, white and green and says so; a colour request shows only outfits in it (untagged pieces in colour allowed, with a caution); whole-outfit-in-colour ranks first; nothing in the colour is explained; Makar Sankranti prefers black or yellow; missing festival colours explained; today's / next festival by date; API validation |
| `test_events.py` | 6 | Full wedding follows each dress code with no garment repeated; jewellery and shoes reused; missing colour explained; no all-white at the wedding; jeans a last resort at a reception; API |
| `test_weather_wear.py` | 9 | Hot day: light pieces, no jacket; cold day: sweater, jeans, boots; rain caution; no weather = no change; weather validated; wear stats (not worn, most worn, cost per wear, totals); prices saved/cleared/validated; wearing an unsaved outfit counts |
| `test_server.py` | 9 | The backend serves the built app: index page, hashed files cached for a year, `.wasm` and manifest types, other addresses open the app, unknown `/api` stays a JSON 404, nothing outside the build folder; without a build `/` just says the API runs. Backups hold the database and every photo, keep only the newest 7 (other files untouched); restore needs `--force`, keeps the replaced data, rejects other archives |
| `test_style_profile.py` | 36 | Profile empty until saved; save/read back (repeats removed, colour names tidied); only sent fields change; skipping is fine; validation (height, shape, fit, undertone, gender, avoid, unknown/too many colours); needs login; private per account; deleted with the account; database CHECKs; reading a piece's cut (palazzo, skin fit, bodycon, crop, anarkali, high waist, cami; a sling *bag* isn't sleeveless); no profile = no change; pear prefers flowing bottoms; preferred fit; avoided styles rank lower with a caution but are never hidden; undertone only adds notes; loved/avoided colours; petite and tall notes; jewellery metal; swaps explain too; the API uses the saved profile; Shop Smart and gender |
| `test_ratelimit.py` | 14 | Sign-ups, log-ins (across emails) and reset requests limited per address; limits are per address; normal use isn't limited; can be switched off; which rule applies to which address |
| `test_verify_email.py` | 7 | Sign-up emails a link; it confirms once (without login); expires; resend limited to 3/h; nothing sent once confirmed; resend needs login; bad tokens |
| `test_security.py` | 6 | Changes from another website blocked (403); from Adaa itself or its public address allowed; reading never blocked; app page has a CSP without Google Fonts; model download needs login |
| `test_offsite.py` | 6 | Request signing matches Amazon's published example; upload is a signed PUT; refused upload raises; backup command copies off-site, fails loudly (keeping the local copy) when it can't, says so when not set up |
| `test_image_meta.py` | 5 | JPEG loses EXIF/GPS, XMP and comments but keeps the picture and colour profile; PNG loses text/EXIF chunks; WebP loses EXIF/XMP and stays valid; unreadable files left alone; uploaded photos are saved and served without location |
| `test_errors.py` | 3 | Unexpected errors: calm message, no internals, logged; browser crash reports logged; size-limited |
| `test_account.py` | 18 | Sign-up needs privacy consent and records it; change password (wrong current password refused, other devices signed out); forgot password: email with link, reset, link works once, expires, same reply for unknown emails, max 3 emails an hour, signs out everywhere, cancelled by a later change; delete account erases items, photos, looks, history, sessions (and only yours), needs the password, email can sign up again; piece, look and account limits; Secure cookie setting |
| `test_auth.py` | 23 | Sign-up keeps name, email and phone and gives a first name; bad name/email/phone/password rejected; duplicate email; log out and back in; wrong password; 5 failures pause logging in; passwords stored hashed; change name and phone; every data route needs logging in, public ones don't; two accounts never see each other's items, looks, history or photo; the first account receives the old wardrobe |
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

1. `python -m pytest` → `258 passed`
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

*Try-on was removed on 20 Oct 2026 (slow and inaccurate); this pass is kept as a record.*

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

## Outfit board polish pass (19 Oct 2026)

Run on a **copy of the real wardrobe** (28 items).

| Check | Result |
|---|---|
| Shoes sized to the hem (about half the bottom's width), never oversized next to skinny jeans | ✅ |
| Top kept in balance with the bottom (at most ~1.35× its width); slim fits given a little more room | ✅ |
| Accessories stacked in neat columns close beside the outfit, no large empty gaps | ✅ |
| Leftover fringes trimmed: skin at the bodycon skirt's slit, white sneaker edge at the straight jeans' hem | ✅ |
| *Erase bits* brush (My Wardrobe → Edit → Outfit picture): erased the hanger hook on "white fancy", Undo, Save; board and preview update; saved as `7m` | ✅ |
| Hand-made pictures (framed or erased) are not replaced when the method version changes | ✅ |
| Backend tests | ✅ 93 passed |

## Sharing and photo tips pass (19 Oct 2026)

| Check | Result |
|---|---|
| Shoes under short skirts: full size, just below the hem (they were shrunk by a height limit meant for long outfits) | ✅ |
| *Add a piece* shows photo tips under the photo box (desktop and phone width, no sideways scroll) | ✅ |
| **Download image** under the board saves `adaa-<look>.png`, 900×1500, cream background, shadows, capitalised look name | ✅ (checked by capturing the image in the test browser) |
| Backend tests | ✅ 93 passed |

## Planning and auto-fill pass (19 Oct 2026)

Run on a **copy of the real wardrobe** (28 items).

| Check | Result |
|---|---|
| Shop Smart: 41 outfits today; top ideas are beige trousers / white palazzo / white kurta (+6 to +7 outfits each, with "goes with your..." photos); gold juttis for the festive gowns that have no shoes; note "No complete outfit is tagged for Wedding yet" | ✅ |
| Shop Smart doesn't suggest what you own (your blue straight jeans count as "blue jeans") and lists bag/jewellery ideas after clothes and shoes | ✅ (fixed during the pass) |
| Trip Planner, 5 days (Travel, Casual, College, Party, Date): an outfit every day, no repeats, **9 pieces** to pack, packing checklist, a board for each day | ✅ |
| Trip API rejects 0 days, more than 14, or an unknown occasion | ✅ |
| Auto-fill on 28 photos: category right for all clothes, shoes and bags; jewellery and the watch correctly left blank; type right for about 20 of 22; colour right for about 17 of 22 | ✅ suggestions only. Misses: a maroon top read as a dress, a purple frock as a navy skirt, brown checks as grey, white under warm light as beige |
| Add a piece with the straight-jeans photo: Name "Denim jeans", Clothing, Jeans, Denim, Western filled in; note asks to check | ✅ |
| Backend tests (11 new for planning) | ✅ 104 passed |

## Trip Planner: no repeated clothes (19 Oct 2026)

Reported: a 5-day trip wore the white top on 3 days and the short skirt on 2. Now **no garment is worn twice on a trip**; shoes, bags and jewellery may be reused.

| Check | Result |
|---|---|
| Your 5-day trip (Casual, Party, Office, Date, Party) on the real wardrobe | ✅ 5 different outfits, every garment worn once, 0.2 s |
| 14-day stress test | ✅ 8 different outfits (the most your clothes allow without repeats), one combined note naming the empty days and what to add, 0.6 s |
| A scarce Party outfit isn't used up on a Casual day (search instead of day-by-day picking) | ✅ test |
| Not enough clothes: the day is left empty with a note, never a repeat | ✅ test |
| Backend tests | ✅ 105 passed |

## Weather and wear stats pass (19 Oct 2026)

Run on a **copy of the real wardrobe** (31 items).

| Check | Result |
|---|---|
| Preferences → city search "Pune" (Open-Meteo geocoding) → Pune, Maharashtra, India | ✅ |
| Today's forecast shown: "34°C, drizzle in Pune" (the laptop's own weather showed 33°C) | ✅ |
| AI Stylist: weather chip "Styling for light, breezy pieces and rain-friendly shoes", with a *Use* switch | ✅ |
| College outfits at 34°C: "Light, breezy pieces for a 34°C day"; the full-sleeve top held back; "Rain is expected: your black shoes may not love puddles" on the outfit with heels | ✅ |
| *Wore it today* on a stylist outfit → "Worn today"; counted in Wear Stats | ✅ |
| Wear Stats: 9 of 31 pieces worn in 30 days (old saved-look history filled in), 22 not worn with *Style it*, most worn list | ✅ |
| Price ₹1,200 on "crop top" (Edit piece) → cost per wear ₹1,200 (worn once), total spent and average | ✅ |
| Overview nudge: "22 pieces not worn in 30 days … give them a day out" with photos, opens Wear Stats | ✅ |
| History keeps the pieces worn even after deleting the saved look (test updated) | ✅ |
| Backend tests | ✅ 114 passed |

## Wedding planner, festivals, Hinglish and voice (19 Oct 2026)

Run on a **copy of the real wardrobe** (32 items).

| Check | Result |
|---|---|
| Overview festival card on 19 Oct 2026: "Navratri Day 9: Peacock Green · Maa Siddhidatri" | ✅ |
| *Style me in peacock green* → stylist preset to Festive + Traditional + peacock green; first look: Bottle green saree ("Features your preferred colour, peacock green") | ✅ |
| Wedding Planner, full wedding: Mehendi → long gown (green), Wedding → Red Saree, Reception → party top + bodycon skirt; Haldi and Sangeet honestly flagged "nothing in yellow / pink… so this is the closest match"; 12 pieces, no garment repeated | ✅ |
| Reception used to pick baggy jeans; casual pieces are now a last resort at dressy functions | ✅ fixed during the pass |
| Hinglish: "Aaj college ke liye kuch comfy aur neela" → College, Comfort first, blue; 8 more Hinglish phrases in tests | ✅ |
| Voice button shown in the ask box (Chrome); Hinglish example in "Try saying" | ✅ shown. Speaking itself needs a real microphone, so it wasn't tested here |
| Backend tests | ✅ 128 passed |

## Festival requests (19 Oct 2026)

| Check | Result |
|---|---|
| "Style me for republic day" → Festival: Republic Day (saffron, white and green), Festive; top look: green long gown | ✅ |
| "style me for ganesh chaturti" (typo) → Ganesh Chaturthi (yellow, red, orange and green), Traditional; Red Saree, Bottle green saree | ✅ |
| "style me for makar sankranti" → Makar Sankranti (black, yellow and green), Traditional; black gown ("Black, yellow and green for Makar Sankranti: your gown"), green saree | ✅ |
| "Diwali party look" → party with Diwali colours; "Diwali puja outfit" → Diwali; "kuch for 15 august" → Independence Day; "sankranthi ke liye kuch kaala" → Sankranti + black | ✅ tests |
| Festival chip on the stylist form, removable with × | ✅ |
| Overview card now comes from the backend table (one source of truth) | ✅ |
| Backend tests | ✅ 145 passed |

## Colour-first fix (19 Oct 2026)

Reported: "Rakhi pe kuch gulabi", "15th aug" and "26th jan" gave black and grey outfits. Cause: occasion tags beat colour. The pink pieces weren't tagged Festive, so they were never considered, and colour was only a small bonus. Also "15th aug" / "26th jan" (short month names) weren't recognised.

| Request (real wardrobe, read-only) | Looks after the fix |
|---|---|
| Rakhi pe kuch gulabi | pink navari; pink party crop top with 3 bottoms (only pink looks; the crop top flagged as not tagged Festive) |
| style me for 15th aug / 26th jan / republic day | green long gown; bottle green saree; white fancy + black jeans / skirt |
| style me for ganesh chaturti | Red Saree; bottle green saree; green gown; yellow ruffle top + skirt |
| style me for makar sankranti | black gown; bottle green saree; all-black crop top + skirt; green gown |
| Backend tests | ✅ 148 passed |

## Brand and re-theme (20 Oct 2026)

| Check | Result |
|---|---|
| Logo files: 8 SVGs (lettering outlined, so no fonts needed) and high-res PNGs in `brand/`; centred; fold is a real cut-out (works on any background) | ✅ |
| Browser tab: app icon and title "Adaa — Every outfit tells your Adaa"; phone theme colour plum | ✅ |
| Sidebar: horizontal logo (desktop and phone menu) | ✅ |
| Re-theme: 105 browns/beiges shifted to plum/blush with the same lightness; accent exactly logo plum; small labels and italic headline words in gold; caution/error/success colours and garment swatches unchanged | ✅ checked Overview, AI Stylist, Wedding Planner, phone menu |
| Downloaded outfit image uses plum lettering and the gold credit line | ✅ |

## Accounts and "calls you by name" (20 Oct 2026)

On a copy of the real wardrobe (32 pieces), backend on 8011 and frontend on 5181.

| Check | Result |
|---|---|
| Sign up with name, email, phone, password | ✅ "Welcome to Adaa, Swarangi! Your 32 pieces are now safely in your account." |
| Name across the app: greeting, hero, sidebar (initials, name, email), header avatar, page titles ("Swarangi's wardrobe") | ✅ |
| AI Stylist: "Here's what I understood, Swarangi", a personal line on each look ("Swarangi, this one would look lovely on you."), save toast | ✅ |
| Log out → log-in screen; log back in → "Welcome back, Swarangi!", saved look still there | ✅ |
| Preferences: Your account (name, phone, read-only email, Save, Log out) | ✅ |
| Short laptop screens (768 px tall): sidebar scrolls and hides the tip card so the profile and log-out stay visible | ✅ (fixed during this pass) |
| Phone: log-in screen stacks (logo on top, form below); app greeting with name | ✅ |
| Backend tests | ✅ 171 passed (153 after removing try-on below) |

## Try-on removed (20 Oct 2026)

| Check | Result |
|---|---|
| Preferences shows only Your account, Your city and the style choices (no Your photo, no Try-on server) | ✅ |
| No first-run "add your photo" step; outfit cards show the outfit board with Download image | ✅ |
| *Verified · your photo* on saved looks still works (separate feature) | ✅ unchanged |
| Backend tests | ✅ 153 passed (17 try-on tests and one route check removed) |

## Opening animation (20 Oct 2026)

| Check | Result |
|---|---|
| Frames stepped at 0.3 / 0.8 / 1.15 / 1.7 / 2.2 s: A focuses in → *Adaa* writing → thread and dot → tagline → "Hi, Swarangi" | ✅ |
| Ends and shows the app underneath (Overview greeting) with no console errors | ✅ |
| Refresh in the same tab: no replay | ✅ |
| Key press skips it: gone within 0.8 s | ✅ |
| Slowed to about 6 s after trying it (A 0–1.6 s, glint 1.3–2.5 s, *Adaa* 1.8–3.6 s, thread 3.4–4.7 s, tagline 3.9–5.3 s, "Hi" 4.9–5.8 s, lift at 6.2 s) | ✅ frames checked |

## Wi-Fi sharing and home-screen app (20 Oct 2026)

`npm run share` on a test backend, opened through the laptop's network address (http://192.168.31.127), as a friend's phone would.

| Check | Result |
|---|---|
| `npm run share` builds and prints Local + Network addresses | ✅ |
| Over the network address (not secure, plain http): sign up a second person, stay logged in (cookie works), greeting uses her name | ✅ "Good evening, Riya." |
| Manifest loads (Adaa, standalone) and all 3 icons return 200; Apple full-screen tags present | ✅ |
| Phone size (375 px, touch): add a piece → no model download, no cut-out started | ✅ |
| Phone over Wi-Fi: microphone button hidden, ask box works | ✅ |
| Not tested here: a real phone on the Wi-Fi, the Windows firewall prompt, Add to Home Screen | ⏳ to try with friends |

## Public-ready accounts (20 Oct 2026)

On a fresh test database (ports 8011/5181), no email service set up.

| Check | Result |
|---|---|
| Sign-up without ticking "I'm 18 or older and agree to the privacy note" → friendly error; after ticking → signed in | ✅ |
| Privacy note opens from sign-up (6 short sections, contact falls back to "the person who runs this Adaa") | ✅ |
| Forgot password → same "if an account uses that email…" reply; the email with the link is printed in the backend terminal | ✅ |
| Opening the link → "Choose a new password" → saved, link removed from the address bar, back on log-in with a note; new password logs in | ✅ |
| Preferences → Change password: wrong current password refused; right one → "Password changed, Swarangi. Other devices are signed out." | ✅ |
| Preferences → Delete my account → asks for the password → erased, back on the sign-up screen, the old password no longer works, saved preferences for that account cleared | ✅ |
| Backend tests | ✅ 171 passed |

## Server-ready: one program, backups (21 Oct 2026)

| Check | Result |
|---|---|
| `npm run build`, then only the backend (port 8011, no Vite): app opens, sign up, add a piece, photo loads, greeting by name | ✅ |
| Hashed JS cached for a year; `.wasm` served as `application/wasm`; manifest as `application/manifest+json`; a deep link like `/some/screen` opens the app | ✅ |
| `python backup.py` while the server runs → one `.tar.gz` with `adaa.db` and the photo | ✅ |
| Restore that backup into an empty folder ("new server"), start there, log in with the same password: piece and photo there | ✅ |
| `install.sh` / `update.sh` syntax check (`bash -n`) | ✅ (not yet run on a real server) |
| Backend tests | ✅ 180 passed |

## Launch pass (6 Nov 2026)

On a copy of the real wardrobe (backend 8011, Vite 5181), then the built app served by the backend alone (one-server mode, with the CSP on).

| Check | Result |
|---|---|
| Existing account: style-profile card appears once; height 152, pear, relaxed, warm, skips sleeveless, loves mustard → saved; mustard leaves the "avoid" list | ✅ |
| AI Stylist "something for college": every look has **Why it suits you, Swarangi** (e.g. "Black baggy jeans: a flowing cut past the hips balances a pear shape", "Yellow near your face tends to glow on warm undertones") | ✅ |
| Preferences → style profile shows the saved answers; feet/inches: 152 cm shows 5 ft 0 in, 5 ft 4 in → 163 cm | ✅ (rounding bug found and fixed) |
| New account on a phone (375 px): card fits, no sideways scroll; **Skip for now** → not shown again after reload | ✅ |
| Sign-up email printed in the backend log; opening `#verify=` link → "Your email is confirmed", banner gone, link removed from the address bar | ✅ |
| Forgot password → `#reset=` link → new password → logs in; access log (36 requests) contains no reset/verify token | ✅ |
| Upload through the app code: 3000×4000 JPEG → stored 1200×1600, 122 KB; cached privately; another account's photo → 404 | ✅ |
| One-server mode with CSP: page loads, fonts are self-hosted (0 requests to Google), weather API allowed, **in-browser cut-out made in ~38 s** (worker + WebAssembly + logged-in model download), no CSP violations in the console | ✅ |
| Basic accessibility on Overview, Preferences, AI Stylist: no unnamed buttons, unlabelled inputs or images without alt; one h1; `lang="en"` | ✅ (shape cards got labels during the pass) |
| Phone: email banner fits | ✅ (wording fixed for accounts created before confirmation existed) |
| `npm audit` | ✅ 0 vulnerabilities |
| Backend tests | ✅ 257 passed |
| Tested live on the Azure server: install.sh, https, Gmail email, Backblaze off-site backup, UptimeRobot check. Not yet: update.sh on the server, a full axe audit (loading outside scripts was blocked) | ✅ / ⏳ |

## Repository review (8 Nov 2026)

| Check | Result |
|---|---|
| Screenshots in `docs/screenshots/` are the author's own captures of the real app; the email under the name in the sidebar was covered and an old header label cropped out; the name is kept, nothing else edited | ✅ |
| "Prototype mode" label removed; sign-up and log-in fields start empty with neutral hints ("Type your name"…); no personal details in placeholders or test data | ✅ |
| MIT `LICENSE` added; README explains that downloaded AI models keep their own licences | ✅ |
| Every page loads after the review changes (Overview, My Wardrobe, AI Stylist, Saved Looks, Wedding Planner, Trip Planner, Wear Stats, Shop Smart, Preferences) | ✅ |
| Phone menu button now has an accessible name ("Open menu") | ✅ (fixed during this pass) |
| Privacy note named Cloudflare R2 for backups; production uses Backblaze B2 | ✅ (fixed during this pass) |
| README links, image paths and section links resolve; report images resolve | ✅ |
| `docs/ADAA_Project_Report.pdf` generated from `docs/report/ADAA_Project_Report.html` with headless Chrome | ✅ |
| No secrets, keys or personal contact details in tracked files or git history (pattern scan) | ✅ |
| `npm run build`, `npm audit --omit=dev` | ✅ built, 0 vulnerabilities |
| Backend tests | ✅ 258 passed |
