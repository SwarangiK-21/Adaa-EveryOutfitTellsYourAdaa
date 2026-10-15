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

Photos: JPEG, PNG or WebP, up to 5 MB. The real file type is checked, not just the name.

### Run the backend tests

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pytest
```

## Phase 1 scope

Responsive UI navigation, demo wardrobe cards with search, a demo stylist chat, session-only preferences, and a FastAPI health endpoint.

## Not implemented yet

- Wardrobe page connected to the API (Phase 2, frontend)
- Rule-based outfit recommendations from your real wardrobe (Phase 3)
- Stylist chat connected to the engine (Phase 4)
- Saved looks, swaps and outfit history (Phase 5)
- Out of scope for now: accounts, cloud hosting, virtual try-on
