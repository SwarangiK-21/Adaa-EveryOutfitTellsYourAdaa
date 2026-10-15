from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import database
import storage
from routes import items


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create the data folder, database table and photo folder on startup.
    database.init_db()
    storage.ensure_upload_dir()
    yield


app = FastAPI(
    title="Adaa API",
    description="Local-first backend for Adaa, the personal wardrobe stylist.",
    version="0.2.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(items.router)


@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "project": "Adaa",
        "phase": 2,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/")
def root():
    return {"message": "Adaa API is running.", "docs": "/docs", "health": "/api/health"}
