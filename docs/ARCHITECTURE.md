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
name                        name                        look_id → looks (SET NULL on delete)
category                    prefs (JSON: occasion,      look_name   (kept even if look is deleted)
item_type                          style, colour...)    occasion
colour                      missing_pieces              worn_on     (date)
style                       created_at, updated_at      created_at
occasions (JSON list)
notes                       look_items
image_filename              ──────────
created_at, updated_at      look_id → looks (CASCADE)
                            item_id → wardrobe_items
                            position
```

- Foreign keys are switched on for every connection, so a saved look can never point at an item that doesn't exist.
- Deleting a wardrobe item runs in one transaction: it removes the item from any saved looks, adds 1 to each look's `missing_pieces` (so the look can say "1 piece was deleted"), then deletes the item and its photo.
- History stores the look's name and occasion, so it survives if the saved look is deleted.
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
- **Testable:** the same input always gives the same output, so behaviour is pinned down by 61 automated tests.

An optional free local language model could later make the chat friendlier, but it would only *read* requests and *write* explanations. The rules would still choose the clothes.

### Understanding typed requests (`parser.py`)

- **Occasions:** phrases are matched longest-first: *"family function"* → Traditional function, *"sangeet"* → Wedding, *"interview"* → Formal, *"movie"* → Casual.
- **Other preferences:** style, comfort and colour-mood words are matched the same way.
- **"My …":** matched against **your** item names and types. A match on the name beats a match on the type only. A colour word alone never picks an item, and typo tolerance is strict enough that *kurta* ≠ *kurti*.
- **Unknown pieces:** if you name a kind of piece you don't own (*"my green kurta"*), it reports it as not found.
- **Ties:** if two pieces match equally (*"my bracelet"*), it asks which one you meant.
- **Follow-ups:** a message without an occasion (*"make it more comfortable"*) keeps the current occasion and changes only what you mention.

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
