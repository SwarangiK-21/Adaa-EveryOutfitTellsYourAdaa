from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Adaa API",
    description="Local-first backend for Adaa, the personal wardrobe stylist.",
    version="0.1.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "project": "Adaa",
        "phase": 1,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }

@app.get("/")
def root():
    return {"message": "Adaa API is running.", "docs": "/docs", "health": "/api/health"}
