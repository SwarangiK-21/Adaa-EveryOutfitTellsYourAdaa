# Adaa

**Your wardrobe. Your world. Your Adaa.**

Adaa is a personal AI wardrobe stylist. It recommends outfits using only the clothes and accessories you have registered in your own wardrobe.

Status: **Phase 1, the local starter prototype.** The UI uses illustrative demo items. Nothing is uploaded or saved yet.

## Requirements

- Node.js LTS (tested with Node 24, npm 11)
- Python 3.11 or newer (tested with Python 3.15)

## Project layout

```
Adaa/
├─ backend/            FastAPI app (Python)
│  ├─ main.py          API entry point: /, /api/health, /docs
│  └─ requirements.txt
└─ frontend/           React + Vite app
   ├─ index.html       HTML shell and page title
   ├─ vite.config.js
   └─ src/
      ├─ main.jsx      React entry point
      ├─ App.jsx       Pages: Overview, My Wardrobe, AI Stylist, Saved Looks, Preferences
      └─ styles.css
```

## Run on Windows (VS Code terminal, PowerShell)

Open the `Adaa` folder in VS Code. Use two terminals (Terminal → New Terminal, then the split button).

### Terminal 1: backend

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn main:app --reload
```

You only need `python -m venv` and `pip install` the first time. After that, just activate and run `uvicorn`.

If PowerShell says *"running scripts is disabled on this system"*, run this once and then activate again:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Check these URLs in a browser:
- http://127.0.0.1:8000/api/health returns `{"status":"ok","project":"Adaa",...}`
- http://127.0.0.1:8000/docs shows the interactive API docs

### Terminal 2: frontend

```powershell
cd frontend
npm install
npm run dev
```

Open the URL Vite prints, usually http://localhost:5173.

Stop either server with `Ctrl + C`.

## Wardrobe API (Phase 2, backend)

Your data is stored in `backend/data/`: `adaa.db` (SQLite) and `uploads/` (photos). Git ignores this folder.

| Method | URL | What it does |
|---|---|---|
| GET | `/api/options` | Allowed categories, styles, occasions, type suggestions |
| GET | `/api/items?search=&category=` | List or search items |
| GET | `/api/items/{id}` | One item |
| GET | `/api/items/{id}/photo` | The item's photo |
| POST | `/api/items` | Add an item (form fields + `photo`) |
| PUT | `/api/items/{id}` | Edit an item (photo optional) |
| DELETE | `/api/items/{id}` | Delete the item and its photo |
| POST | `/api/recommendations` | Suggest up to 4 outfits (Phase 3, see below) |

Photos: JPEG, PNG or WebP, up to 5 MB. The real file type is checked, not just the name.

### Run the backend tests

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pytest
```

## Outfit recommendations (Phase 3, backend)

`POST /api/recommendations` with JSON, for example:

```json
{ "occasion": "Festive", "style": "Traditional", "colour": "green",
  "colour_mood": "Pastels", "comfort": "Comfort first", "anchor_item_id": 3 }
```

Only `occasion` is required. The engine (`backend/recommender/`) is rule-based and uses **only items in your wardrobe**:

1. Classifies each item by its type (top, bottom, saree, earrings, footwear...).
2. Builds outfit bases: one-pieces, or tops + bottoms that suit each other (kurta + salwar, top + jeans...).
3. Scores them on occasion tags, style, colour harmony and your preferences.
4. Adds footwear, jewellery, a bag and an accessory that are **tagged for the occasion** and match.
5. Returns up to 4 distinct outfits with reasons, plus notes on anything missing.

### Style me screen (Phase 3, frontend)

On **AI Stylist**, pick an occasion (plus optional style, colour, colour mood, comfort, or a piece to build around) and press **Style me**. Each look shows your real photos, why it works, and any cautions. On **My Wardrobe**, the ✦ button on a piece opens the stylist with that piece pre-selected.

### Ask in your own words (Phase 4)

Type a request in the box at the top of **AI Stylist**, e.g. *"Style my black crop top for a party"*, *"something comfy for college"* or *"what should I wear to my cousin's sangeet?"*. Adaa shows what it understood, fills in the form and styles you. Follow-ups like *"make it more comfortable"* keep the occasion and change only what you mention.

How it works: `backend/recommender/parser.py` (`POST /api/stylist/parse`) is rule-based and runs locally, with no AI service and no internet. It recognises occasion words (wedding, sangeet, diwali, interview, college...), styles, comfort and colour words, and matches "my ..." against **your** wardrobe items (with small typo tolerance). If you mention a piece you don't own, it says so instead of pretending; if two pieces match equally, it asks which one.

## Saved looks, swaps and history (Phase 5)

- **Save look** on any outfit stores it in the database (`looks`, `look_items` tables). Duplicate looks are refused; duplicate names are numbered.
- **Swap** (⇄ on any piece) lists other pieces from your wardrobe that keep the outfit wearable (a new top must still go with the bottom), tagged-for-the-occasion pieces first. The outfit's reasons are recalculated after a swap. Works on stylist results and on saved looks.
- **Wore it today** on a saved look adds it to **Outfit history** (`wear_log` table). History keeps the look's name even if the saved look is deleted later.
- **Data integrity:** deleting a wardrobe item removes it from saved looks, and the look shows "1 piece was deleted from your wardrobe". Foreign keys are enforced, so a look can never point at a missing item.

| Method | URL | What it does |
|---|---|---|
| POST | `/api/outfits/evaluate` | Reasons/cautions for a set of pieces |
| POST | `/api/outfits/alternatives` | Swap options for one piece |
| GET / POST | `/api/looks` | List / save looks |
| PUT / DELETE | `/api/looks/{id}` | Rename or change pieces / delete |
| POST | `/api/looks/{id}/wear` | Record that you wore it (today by default) |
| GET | `/api/history` | Outfit history, newest first |
| DELETE | `/api/history/{id}` | Remove a history entry |

Existing databases are upgraded automatically on startup (new tables are added; wardrobe data is untouched).

## Phase 1 scope

Responsive UI navigation, demo wardrobe cards with search, a demo stylist chat, session-only preferences, and a FastAPI health endpoint.

## My Wardrobe page (Phase 2, frontend)

Add pieces with a photo and details, browse them as a photo grid, search, filter by category, edit and delete. The page talks to the backend through Vite's `/api` proxy (see `frontend/vite.config.js`), so **both servers must be running**.

## Not implemented yet
- Phase 6: end-to-end testing pass, documentation and a mentor-demo workflow
- Later ideas: makeup suggestions, body-type-aware styling, optional local language model
- Out of scope for now: accounts, cloud hosting, virtual try-on
