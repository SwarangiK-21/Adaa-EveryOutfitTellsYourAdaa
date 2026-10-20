"""Accounts: password hashing, sign-in sessions and the "who is signed in?" check.

- Passwords are never stored: only a salted scrypt hash (Python's standard library, no extra
  packages), compared in constant time.
- Signing in creates a random session token, sent to the browser as an HttpOnly cookie (page
  scripts can't read it). The database stores only a SHA-256 hash of the token, so a copied
  database can't be used to sign in. Sessions last 30 days, or until you log out.
- After 5 wrong passwords for an email within 15 minutes, further tries wait (429).
"""
import base64
import hashlib
import hmac
import secrets
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, Request, Response

import database

COOKIE = "adaa_session"
SESSION_DAYS = 30
_SCRYPT = {"n": 2 ** 14, "r": 8, "p": 1}
MAX_FAILURES, FAILURE_WINDOW = 5, 15 * 60

_failures: dict[str, list[float]] = {}
_failures_lock = threading.Lock()


# ---------- passwords ----------

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, dklen=32, **_SCRYPT)
    return "scrypt${n}${r}${p}${salt}${hash}".format(
        **_SCRYPT, salt=base64.b64encode(salt).decode(), hash=base64.b64encode(digest).decode())


def check_password(password: str, stored: str) -> bool:
    try:
        _, n, r, p, salt, digest = stored.split("$")
        expected = base64.b64decode(digest)
        actual = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt), dklen=len(expected),
                                n=int(n), r=int(r), p=int(p))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(actual, expected)


# ---------- too many wrong passwords ----------

def too_many_failures(email: str) -> bool:
    now = time.monotonic()
    with _failures_lock:
        recent = [t for t in _failures.get(email, []) if now - t < FAILURE_WINDOW]
        _failures[email] = recent
        return len(recent) >= MAX_FAILURES


def record_failure(email: str) -> None:
    with _failures_lock:
        _failures.setdefault(email, []).append(time.monotonic())


def clear_failures(email: str) -> None:
    with _failures_lock:
        _failures.pop(email, None)


# ---------- sessions ----------

def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def start_session(conn: sqlite3.Connection, response: Response, uid: int) -> None:
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    with conn:
        conn.execute("DELETE FROM sessions WHERE expires_at < ?", (now.isoformat(),))   # tidy up old ones
        conn.execute("INSERT INTO sessions (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
                     (_token_hash(token), uid, now.isoformat(), (now + timedelta(days=SESSION_DAYS)).isoformat()))
    # Secure is off because the local app runs on plain http://localhost; turn it on behind https.
    response.set_cookie(COOKIE, token, max_age=SESSION_DAYS * 24 * 3600, httponly=True, samesite="lax", path="/")


def end_session(conn: sqlite3.Connection, request: Request, response: Response) -> None:
    token = request.cookies.get(COOKIE)
    if token:
        with conn:
            conn.execute("DELETE FROM sessions WHERE token_hash = ?", (_token_hash(token),))
    response.delete_cookie(COOKIE, path="/")


def current_user(request: Request, db: Annotated[sqlite3.Connection, Depends(database.get_db)]) -> dict:
    """FastAPI dependency: the signed-in user, or 401 if nobody is signed in."""
    token = request.cookies.get(COOKIE)
    if token:
        row = db.execute(
            "SELECT u.* FROM sessions s JOIN users u ON u.id = s.user_id WHERE s.token_hash = ? AND s.expires_at > ?",
            (_token_hash(token), datetime.now(timezone.utc).isoformat())).fetchone()
        if row:
            return dict(row)
    raise HTTPException(status_code=401, detail="Please log in to continue.")


User = Annotated[dict, Depends(current_user)]
