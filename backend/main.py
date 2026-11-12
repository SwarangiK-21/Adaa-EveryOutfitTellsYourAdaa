import logging
import mimetypes
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

import config
import database
import ratelimit
import security
import storage
from routes import auth as auth_routes, items, looks, planner, profile, recommendations


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create the data folder, database table and photo folder on startup.
    database.init_db()
    storage.ensure_upload_dir()
    yield


app = FastAPI(
    title="Peheraav API",
    description="Backend for Peheraav, the personal wardrobe stylist. Also serves the built app when frontend/dist exists.",
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
app.middleware("http")(ratelimit.middleware)
app.middleware("http")(security.origin_check)
app.include_router(auth_routes.router)
app.include_router(items.router)
app.include_router(recommendations.router)
app.include_router(looks.router)
app.include_router(planner.router)
app.include_router(profile.router)


log = logging.getLogger("peheraav")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@app.exception_handler(Exception)
async def unexpected_error(request: Request, exc: Exception):
    """Anything unexpected: log the full details for the admin, give the person a calm message."""
    log.exception("Unexpected error on %s %s", request.method, request.url.path)
    return JSONResponse({"detail": "Something went wrong on our side. Please try again in a moment."}, status_code=500)


class ClientError(BaseModel):
    message: str = Field(max_length=500)
    where: str = Field(default="", max_length=2000)
    page: str = Field(default="", max_length=200)


@app.post("/api/client-error", status_code=204, include_in_schema=False)
def client_error(report: ClientError):
    """A screen crashed in someone's browser: note it in the server log (no personal data is sent)."""
    where = " ".join(report.where.split())[:600]   # one line in the log
    log.warning("Browser error on %s: %s | %s", report.page, report.message, where)


@app.api_route("/api/health", methods=["GET", "HEAD"])  # HEAD: uptime monitors check with it
def health_check():
    return {
        "status": "ok",
        "project": "Peheraav",
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
        return {"message": "Peheraav API is running.", "docs": "/docs", "health": "/api/health"}
    file = (dist / path).resolve()
    if path and file.is_file() and file.is_relative_to(dist):
        # Built files have a content hash in their name, so browsers may keep them for a year.
        cache = "public, max-age=31536000, immutable" if path.startswith("assets/") else "no-cache"
        headers = {"Cache-Control": cache}
        if file.suffix == ".html":
            headers["Content-Security-Policy"] = security.CSP
        return FileResponse(file, headers=headers)
    # Any other address is a screen of the app: let the app show it.
    return FileResponse(index, headers={"Cache-Control": "no-cache", "Content-Security-Policy": security.CSP})
