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

## Phase 1 scope

Responsive UI navigation, demo wardrobe cards with search, a demo stylist chat, session-only preferences, and a FastAPI health endpoint.

## My Wardrobe page (Phase 2, frontend)

Add pieces with a photo and details, browse them as a photo grid, search, filter by category, edit and delete. The page talks to the backend through Vite's `/api` proxy (see `frontend/vite.config.js`), so **both servers must be running**.

## Not implemented yet
- Rule-based outfit recommendations from your real wardrobe (Phase 3)
- Stylist chat connected to the engine (Phase 4)
- Saved looks, swaps and outfit history (Phase 5)
- Out of scope for now: accounts, cloud hosting, virtual try-on
