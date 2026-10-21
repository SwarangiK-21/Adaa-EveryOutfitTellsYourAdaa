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

# The built app (npm run build). When it exists, the backend serves it too, so a server runs one program.
FRONTEND_DIR = Path(os.environ.get("ADAA_FRONTEND_DIR", BASE_DIR.parent / "frontend" / "dist"))

# Daily copies of the database and photos (backup.py). The newest BACKUP_KEEP are kept.
BACKUP_DIR = Path(os.environ.get("ADAA_BACKUP_DIR", BASE_DIR / "backups"))

# ---------- Running Adaa for other people (all optional; the defaults suit your own laptop) ----------

def _int(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


# The address people open Adaa at; used in "reset your password" emails.
PUBLIC_URL = os.environ.get("ADAA_PUBLIC_URL", "http://localhost:5173").rstrip("/")
# Shown in the privacy note so people know whom to ask about their data.
CONTACT_EMAIL = os.environ.get("ADAA_CONTACT_EMAIL", "")
# Set to 1 when Adaa is served over https, so the sign-in cookie is only ever sent encrypted.
SECURE_COOKIES = os.environ.get("ADAA_SECURE_COOKIES") == "1"

# Per-person limits, so one account can't fill the server. ADAA_MAX_USERS=0 means no cap on accounts.
MAX_ITEMS_PER_USER = _int("ADAA_MAX_ITEMS", 300)
MAX_LOOKS_PER_USER = _int("ADAA_MAX_LOOKS", 200)
MAX_USERS = _int("ADAA_MAX_USERS", 0)
BACKUP_KEEP = _int("ADAA_BACKUP_KEEP", 7)

# Email for "forgot password" (any SMTP service: Gmail with an app password, Brevo, ...).
# Without SMTP_HOST, the reset link is printed in the backend terminal instead.
SMTP_HOST = os.environ.get("ADAA_SMTP_HOST", "")
SMTP_PORT = _int("ADAA_SMTP_PORT", 587)
SMTP_USER = os.environ.get("ADAA_SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("ADAA_SMTP_PASSWORD", "")
MAIL_FROM = os.environ.get("ADAA_MAIL_FROM", "") or SMTP_USER
