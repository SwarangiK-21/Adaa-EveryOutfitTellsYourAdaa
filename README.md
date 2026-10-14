# AI Wardrobe Stylist — Phase 1

## Requirements
Install Node.js (LTS) and Python 3.11+.

## Start frontend
Open a terminal in `frontend`:
```bash
npm install
npm run dev
```
Open the localhost URL shown by Vite, usually http://localhost:5173.

## Start backend
Open a second terminal in `backend`:
```bash
python -m venv .venv
```
Activate:
- Windows PowerShell: `.venv\\Scripts\\Activate.ps1`
- Windows CMD: `.venv\\Scripts\\activate.bat`
- macOS/Linux: `source .venv/bin/activate`

Then run:
```bash
python -m pip install -r requirements.txt
uvicorn main:app --reload
```
Health check: http://127.0.0.1:8000/api/health
API docs: http://127.0.0.1:8000/docs

## Phase 1 scope
Working responsive UI navigation, demo wardrobe cards, local demo chat interaction, preferences, and FastAPI health endpoint.
Demo wardrobe pieces are illustrations, not your personal uploaded items.

## Not implemented yet
Photo uploads and persistent database (Phase 2); real wardrobe-based outfit ranking (Phase 3); real LLM integration, accounts, cloud hosting, virtual try-on.
