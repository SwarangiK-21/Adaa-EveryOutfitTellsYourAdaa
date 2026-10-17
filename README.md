# Adaa

**Your wardrobe. Your world. Your Adaa.**

Adaa is a personal wardrobe stylist. You photograph and register your own clothes, jewellery, footwear and bags; Adaa then suggests complete, coordinated outfits for an occasion, using **only pieces you actually own**. It supports Indian traditional, Western and Indo-Western styling.

It runs entirely on your own computer with free, open-source tools: no paid APIs, no cloud, no account.

## What it does

| Feature | Where |
|---|---|
| Add pieces with a photo and details (category, type, colour, style, occasions), then search, filter, edit and delete them | **My Wardrobe** |
| Ask in plain words, e.g. *"Style my green kurta for a traditional family function"*, or pick occasion, style, colour, colour mood and comfort | **AI Stylist** |
| Get up to 4 distinct outfits made from your real photos, each with reasons and honest cautions | **AI Stylist** |
| Swap any piece for another one from your wardrobe that still works | Outfit cards |
| Save looks, rename them, mark "Wore it today", and see your outfit history | **Saved Looks** |
| Save your usual style, comfort and colour preferences | **Preferences** |

**The core rule:** Adaa never invents a piece. If something is missing (no bag, nothing tagged for a wedding, "my green kurta" when you don't have one), it says so and shows the best real combination instead.

## Project status

| Phase | What | Status |
|---|---|---|
| 1 | Starter project runs; renamed to Adaa | Done |
| 2 | Wardrobe: photo upload, details, search, edit, delete, SQLite storage | Done |
| 3 | Rule-based outfit engine and **Style me** screen | Done |
| 4 | Plain-language requests (local, rule-based) | Done |
| 5 | Saved looks, piece swaps, outfit history | Done |
| 6 | End-to-end testing, documentation, mentor demo | Done |

61 automated backend tests pass. A full manual browser pass is recorded in [docs/TESTING.md](docs/TESTING.md).

## Tech

- **Frontend:** React 18 + Vite, plain CSS, Lucide icons
- **Backend:** Python + FastAPI
- **Database:** SQLite (one file)
- **Photos:** stored on the local disk
- **Recommendations and request parsing:** rule-based Python; no AI service

How it fits together: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Requirements

- Node.js LTS (tested with Node 24, npm 11)
- Python 3.11 or newer (tested with Python 3.15)

## Run on Windows (VS Code terminal, PowerShell)

Open the `Adaa` folder in VS Code and use two terminals.

### Terminal 1: backend

```powershell
cd backend
python -m venv .venv                         # first time only
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt    # first time, or after requirements change
uvicorn main:app --reload
```

Success looks like `Application startup complete.` Check http://127.0.0.1:8000/api/health; it should show `"status":"ok"`.

### Terminal 2: frontend

```powershell
cd frontend
npm install      # first time only
npm run dev
```

Open http://localhost:5173. **Both servers must be running.**

Stop either one with `Ctrl + C`.

### Troubleshooting

| Problem | Fix |
|---|---|
| *"running scripts is disabled on this system"* | Run `Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned` once, then activate again |
| App says *"Can't reach the Adaa server"* | The backend isn't running; start Terminal 1 |
| Backend says *port 8000 is already in use* (e.g. another FastAPI project is running) | Run the backend on another port: `uvicorn main:app --reload --port 8001`, and start the frontend with `$env:ADAA_API_URL="http://127.0.0.1:8001"; npm run dev` |
| iPhone photo refused | HEIC isn't supported; export or share the photo as JPEG |

## Your data

Everything lives in `backend/data/`:
- `adaa.db`: the SQLite database (wardrobe, saved looks, history)
- `uploads/`: your photos

Git ignores this folder, so your photos are never pushed to GitHub. To **back up**, copy the whole `backend/data` folder somewhere safe while the backend is stopped. Preferences are saved in your browser.

## Tests

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt   # first time only
python -m pytest
```

Expected: `61 passed`. Tests use a temporary folder, so they never touch your real wardrobe.

## API

Interactive docs: http://127.0.0.1:8000/docs (while the backend is running).

| Method | URL | What it does |
|---|---|---|
| GET | `/api/health` | Server status |
| GET | `/api/options` | Allowed categories, styles, occasions, moods, comfort levels |
| GET / POST | `/api/items` | List or search (`?search=&category=`) / add (form fields + `photo`) |
| GET / PUT / DELETE | `/api/items/{id}` | One item / edit (photo optional) / delete |
| GET | `/api/items/{id}/photo` | The item's photo |
| POST | `/api/stylist/parse` | Read a typed request into filters |
| POST | `/api/recommendations` | Up to 4 outfits for an occasion and preferences |
| POST | `/api/outfits/evaluate` | Reasons and cautions for a given set of pieces |
| POST | `/api/outfits/alternatives` | Swap options for one piece |
| GET / POST | `/api/looks` | List / save looks |
| PUT / DELETE | `/api/looks/{id}` | Rename or change pieces / delete |
| POST | `/api/looks/{id}/wear` | Record that you wore it (today by default) |
| GET | `/api/history`, DELETE `/api/history/{id}` | Outfit history / remove an entry |

## Project layout

```
Adaa/
├─ backend/
│  ├─ main.py               App setup: CORS, routers, startup (creates tables and folders)
│  ├─ config.py             Data folder, database path, 5 MB photo limit
│  ├─ wardrobe_options.py   Categories, styles, occasions, moods, comfort levels
│  ├─ schemas.py            Request/response shapes and validation (Pydantic)
│  ├─ database.py           SQLite connection, tables, wardrobe item queries
│  ├─ looks_db.py           Saved looks and outfit history queries
│  ├─ storage.py            Photo checks (real file type, size) and saving/deleting
│  ├─ routes/               API routes: items, recommendations (+ parse), looks
│  ├─ recommender/          colours.py, garments.py, engine.py, parser.py
│  └─ tests/                61 pytest tests
├─ frontend/
│  ├─ vite.config.js        Dev server; forwards /api to the backend
│  └─ src/
│     ├─ App.jsx            Layout, navigation, Overview, Preferences
│     ├─ api.js             All calls to the backend
│     ├─ preferences.js     Saved preferences (browser storage)
│     ├─ pages/             Wardrobe, Stylist, SavedLooks
│     ├─ components/        ItemForm, OutfitCard, SwapPanel, AskBox, Heading
│     └─ styles.css
└─ docs/                    ARCHITECTURE.md, TESTING.md, DEMO.md
```

## Limitations and future ideas

- Single user, on one computer; no accounts or cloud sync (by design for now).
- Recommendations follow hand-written rules. They're explainable and predictable, but not "learning".
- Requests are understood by keyword rules: clear sentences work best; unusual phrasing may only be partly understood (Adaa shows what it understood).
- Item details are entered by hand; there's no automatic garment recognition from photos.
- Later ideas: makeup suggestions, body-type-aware styling, an optional free local language model for richer chat, using wear history to suggest less-worn pieces.
- Out of scope: virtual try-on, cloud hosting, accounts.

## Mentor demo

A step-by-step demo script with talking points: [docs/DEMO.md](docs/DEMO.md).
