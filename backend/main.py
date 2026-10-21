import mimetypes
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

import config
import database
import storage
from routes import auth as auth_routes, items, looks, planner, recommendations


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create the data folder, database table and photo folder on startup.
    database.init_db()
    storage.ensure_upload_dir()
    yield


app = FastAPI(
    title="Adaa API",
    description="Backend for Adaa, the personal wardrobe stylist. Also serves the built app when frontend/dist exists.",
    version="1.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_routes.router)
app.include_router(items.router)
app.include_router(recommendations.router)
app.include_router(looks.router)
app.include_router(planner.router)


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "project": "Adaa",
        "phase": 6,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


# ---------- one server: the built app (frontend/dist) is served from here too ----------
# In development Vite serves the app on :5173 instead, and "/" here just says the API is running.

mimetypes.add_type("application/wasm", ".wasm")                      # the in-browser cut-out model runtime
mimetypes.add_type("application/manifest+json", ".webmanifest")      # home-screen app details


@app.get("/{path:path}", include_in_schema=False)
def frontend(path: str):
    if path == "api" or path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not Found")      # unknown API address: a plain 404
    dist = config.FRONTEND_DIR.resolve()
    index = dist / "index.html"
    if not index.is_file():
        if path:
            raise HTTPException(status_code=404, detail="Not Found")
        return {"message": "Adaa API is running.", "docs": "/docs", "health": "/api/health"}
    file = (dist / path).resolve()
    if path and file.is_file() and file.is_relative_to(dist):
        # Built files have a content hash in their name, so browsers may keep them for a year.
        cache = "public, max-age=31536000, immutable" if path.startswith("assets/") else "no-cache"
        return FileResponse(file, headers={"Cache-Control": cache})
    # Any other address is a screen of the app: let the app show it.
    return FileResponse(index, headers={"Cache-Control": "no-cache"})
