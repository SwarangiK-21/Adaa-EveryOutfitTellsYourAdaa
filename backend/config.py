"""Paths and limits shared by the backend.

Other modules read these as `config.NAME` (not `from config import NAME`)
so tests can point them at a temporary folder.
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Everything the app writes (database + photos) lives in one folder.
# Set ADAA_DATA_DIR to use a different location.
DATA_DIR = Path(os.environ.get("ADAA_DATA_DIR", BASE_DIR / "data"))
DB_PATH = DATA_DIR / "adaa.db"
UPLOAD_DIR = DATA_DIR / "uploads"

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB per photo
