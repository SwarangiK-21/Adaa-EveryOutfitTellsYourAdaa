"""SQLite connection, table setup and wardrobe item queries.

Every wardrobe item, look and history entry belongs to one account (user_id): queries take the
signed-in user's id (uid) and only ever see that user's rows.
"""
import json
import sqlite3
from datetime import datetime, timezone

import config
from schemas import ItemFields

SCHEMA = """
CREATE TABLE IF NOT EXISTS wardrobe_items (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT NOT NULL,
    category       TEXT NOT NULL,
    item_type      TEXT NOT NULL,
    colour         TEXT NOT NULL,
    style          TEXT NOT NULL,
    occasions      TEXT NOT NULL,          -- JSON list, e.g. ["Festive", "Wedding"]
    notes          TEXT NOT NULL DEFAULT '',
    image_filename TEXT NOT NULL,
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL
);

-- Saved looks (Phase 5). Which pieces are in a look lives in look_items.
CREATE TABLE IF NOT EXISTS looks (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    name           TEXT NOT NULL,
    prefs          TEXT NOT NULL,          -- JSON: occasion + preferences the look was made for
    missing_pieces INTEGER NOT NULL DEFAULT 0,  -- pieces later deleted from the wardrobe
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS look_items (
    look_id   INTEGER NOT NULL REFERENCES looks(id) ON DELETE CASCADE,
    item_id   INTEGER NOT NULL REFERENCES wardrobe_items(id),
    position  INTEGER NOT NULL,
    PRIMARY KEY (look_id, item_id)
);

-- Outfit history: each time a saved look was worn. Keeps the look's name
-- so history survives even if the saved look is deleted later.
CREATE TABLE IF NOT EXISTS wear_log (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    look_id    INTEGER REFERENCES looks(id) ON DELETE SET NULL,
    look_name  TEXT NOT NULL,
    occasion   TEXT NOT NULL,
    worn_on    TEXT NOT NULL,              -- date, e.g. 2026-10-15
    created_at TEXT NOT NULL
);

-- Which pieces were worn in each history entry (for wear stats). No foreign key to the item,
-- so history stays even if a piece is deleted later.
CREATE TABLE IF NOT EXISTS wear_items (
    wear_id  INTEGER NOT NULL REFERENCES wear_log(id) ON DELETE CASCADE,
    item_id  INTEGER NOT NULL,
    PRIMARY KEY (wear_id, item_id)
);

-- Verified previews: the user's own photo wearing a saved look (one per look).
-- item_ids remembers the look's pieces when the photo was taken, so we can tell
-- when the look has changed since and the photo no longer matches.
CREATE TABLE IF NOT EXISTS look_photos (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    look_id        INTEGER NOT NULL UNIQUE REFERENCES looks(id) ON DELETE CASCADE,
    image_filename TEXT NOT NULL,
    item_ids       TEXT NOT NULL,          -- JSON list of item ids
    created_at     TEXT NOT NULL
);

-- Accounts. Passwords are stored only as salted scrypt hashes (see auth.py).
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,     -- lower case
    phone         TEXT NOT NULL,
    password_hash TEXT NOT NULL,
    created_at    TEXT NOT NULL
);

-- Signed-in browsers. Only a hash of the session token is stored.
CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

-- "Forgot password" links: one use, 30 minutes. Only a hash of the link's token is stored.
CREATE TABLE IF NOT EXISTS password_resets (
    token_hash TEXT PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    used_at    TEXT
);

"""
OWNED_TABLES = ("wardrobe_items", "looks", "wear_log")   # each row belongs to one user


def connect() -> sqlite3.Connection:
    # FastAPI may open the connection on one worker thread and use it on another.
    # Each request gets its own connection and uses it one step at a time, so this is safe.
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")  # never let a look point at a missing item
    return conn


def init_db() -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = connect()
    try:
        conn.executescript(SCHEMA)
        # Added after the first release: older databases get the column on startup.
        columns = {r["name"] for r in conn.execute("PRAGMA table_info(wardrobe_items)")}
        if "cutout_filename" not in columns:
            conn.execute("ALTER TABLE wardrobe_items ADD COLUMN cutout_filename TEXT")
        if "cutout_version" not in columns:
            # Which cut-out method made it ("2" = automatic v2, "2m" = framed by the user...)
            conn.execute("ALTER TABLE wardrobe_items ADD COLUMN cutout_version TEXT")
        if "price" not in columns:
            conn.execute("ALTER TABLE wardrobe_items ADD COLUMN price REAL")
        user_columns = {r["name"] for r in conn.execute("PRAGMA table_info(users)")}
        if "privacy_accepted_at" not in user_columns:   # when they agreed to the privacy note (sign-up)
            conn.execute("ALTER TABLE users ADD COLUMN privacy_accepted_at TEXT")
        for table in OWNED_TABLES:   # accounts: older rows get an owner when the first user signs up
            if "user_id" not in {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER REFERENCES users(id)")
            conn.execute(f"CREATE INDEX IF NOT EXISTS idx_{table}_user ON {table}(user_id)")
        # History from before wear_items existed: use the saved look's pieces (best we know).
        conn.execute(
            "INSERT OR IGNORE INTO wear_items (wear_id, item_id)"
            " SELECT w.id, li.item_id FROM wear_log w JOIN look_items li ON li.look_id = w.look_id"
            " WHERE NOT EXISTS (SELECT 1 FROM wear_items wi WHERE wi.wear_id = w.id)")
        conn.commit()
    finally:
        conn.close()


def get_db():
    """FastAPI dependency: one connection per request, always closed."""
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def row_to_dict(row: sqlite3.Row) -> dict:
    item = dict(row)
    item["occasions"] = json.loads(item["occasions"])
    return item


def list_items(conn, uid: int, search: str = "", category: str | None = None) -> list[dict]:
    sql = "SELECT * FROM wardrobe_items WHERE user_id = ?"
    params: list = [uid]
    if category:
        sql += " AND category = ?"
        params.append(category)
    if search.strip():
        # instr() does a plain substring match, so % and _ in the search are not wildcards.
        sql += (
            " AND instr(lower(name || ' ' || item_type || ' ' || colour || ' ' ||"
            " category || ' ' || style || ' ' || occasions || ' ' || notes), lower(?)) > 0"
        )
        params.append(search.strip())
    sql += " ORDER BY created_at DESC, id DESC"
    return [row_to_dict(r) for r in conn.execute(sql, params)]


def get_item(conn, item_id: int, uid: int | None = None) -> dict | None:
    """One item; with uid, only if it belongs to that user (otherwise None, as if it didn't exist)."""
    if uid is None:
        row = conn.execute("SELECT * FROM wardrobe_items WHERE id = ?", (item_id,)).fetchone()
    else:
        row = conn.execute("SELECT * FROM wardrobe_items WHERE id = ? AND user_id = ?", (item_id, uid)).fetchone()
    return row_to_dict(row) if row else None


def create_item(conn, uid: int, fields: ItemFields, image_filename: str) -> dict:
    now = _now()
    cur = conn.execute(
        """INSERT INTO wardrobe_items
           (user_id, name, category, item_type, colour, style, occasions, notes, price,
            image_filename, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            uid, fields.name, fields.category, fields.item_type, fields.colour, fields.style,
            json.dumps(fields.occasions), fields.notes, fields.price, image_filename, now, now,
        ),
    )
    conn.commit()
    return get_item(conn, cur.lastrowid)


def update_item(conn, item_id: int, fields: ItemFields, image_filename: str) -> dict:
    conn.execute(
        """UPDATE wardrobe_items
           SET name = ?, category = ?, item_type = ?, colour = ?, style = ?,
               occasions = ?, notes = ?, price = ?, image_filename = ?, updated_at = ?
           WHERE id = ?""",
        (
            fields.name, fields.category, fields.item_type, fields.colour, fields.style,
            json.dumps(fields.occasions), fields.notes, fields.price, image_filename, _now(), item_id,
        ),
    )
    conn.commit()
    return get_item(conn, item_id)


def delete_item(conn, item_id: int) -> None:
    """Delete an item. Saved looks that used it keep the rest and note the missing piece."""
    with conn:  # one transaction: all of this happens, or none of it
        conn.execute(
            "UPDATE looks SET missing_pieces = missing_pieces + 1, updated_at = ?"
            " WHERE id IN (SELECT look_id FROM look_items WHERE item_id = ?)",
            (_now(), item_id),
        )
        conn.execute("DELETE FROM look_items WHERE item_id = ?", (item_id,))
        conn.execute("DELETE FROM wardrobe_items WHERE id = ?", (item_id,))


# ---------- accounts ----------

def create_user(conn, name: str, email: str, phone: str, password_hash: str) -> dict:
    now = _now()
    with conn:
        cur = conn.execute(
            "INSERT INTO users (name, email, phone, password_hash, created_at, privacy_accepted_at)"
            " VALUES (?, ?, ?, ?, ?, ?)", (name, email, phone, password_hash, now, now))
    return get_user(conn, cur.lastrowid)


def count_users(conn) -> int:
    return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]


def count_owned(conn, table: str, uid: int) -> int:
    assert table in OWNED_TABLES
    return conn.execute(f"SELECT COUNT(*) FROM {table} WHERE user_id = ?", (uid,)).fetchone()[0]


def set_password(conn, uid: int, password_hash: str) -> None:
    """New password: every signed-in browser and every unused reset link stops working."""
    with conn:
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, uid))
        conn.execute("DELETE FROM sessions WHERE user_id = ?", (uid,))
        conn.execute("DELETE FROM password_resets WHERE user_id = ?", (uid,))


def delete_user(conn, uid: int) -> list[str]:
    """Erase an account and everything in it, in one transaction.
    Returns the photo files to delete from disk (after the database change succeeded)."""
    files = [r[0] for r in conn.execute(
        "SELECT image_filename FROM wardrobe_items WHERE user_id = ?"
        " UNION ALL SELECT cutout_filename FROM wardrobe_items WHERE user_id = ? AND cutout_filename IS NOT NULL"
        " UNION ALL SELECT p.image_filename FROM look_photos p JOIN looks l ON l.id = p.look_id WHERE l.user_id = ?",
        (uid, uid, uid))]
    with conn:
        conn.execute("DELETE FROM looks WHERE user_id = ?", (uid,))            # look items and photos go with them
        conn.execute("DELETE FROM wear_log WHERE user_id = ?", (uid,))         # and the pieces worn each day
        conn.execute("DELETE FROM look_items WHERE item_id IN (SELECT id FROM wardrobe_items WHERE user_id = ?)", (uid,))
        conn.execute("DELETE FROM wardrobe_items WHERE user_id = ?", (uid,))
        conn.execute("DELETE FROM users WHERE id = ?", (uid,))                 # sessions and reset links cascade
    return files


def get_user(conn, uid: int) -> dict | None:
    row = conn.execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    return dict(row) if row else None


def find_user_by_email(conn, email: str) -> dict | None:
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    return dict(row) if row else None


def update_user(conn, uid: int, name: str, phone: str) -> dict:
    with conn:
        conn.execute("UPDATE users SET name = ?, phone = ? WHERE id = ?", (name, phone, uid))
    return get_user(conn, uid)


def claim_unowned(conn, uid: int) -> int:
    """Give everything made before accounts existed to this user (the first to sign up).
    Returns how many wardrobe items were moved into the account."""
    with conn:
        moved = conn.execute("UPDATE wardrobe_items SET user_id = ? WHERE user_id IS NULL", (uid,)).rowcount
        for table in ("looks", "wear_log"):
            conn.execute(f"UPDATE {table} SET user_id = ? WHERE user_id IS NULL", (uid,))
    return moved


# ---------- garment cut-outs (the garment with its background removed) ----------

def set_cutout(conn, item_id: int, filename: str | None, version: str | None = None) -> str | None:
    """Store (or clear, with None) an item's cut-out. Returns the previous file name, if any."""
    row = conn.execute("SELECT cutout_filename FROM wardrobe_items WHERE id = ?", (item_id,)).fetchone()
    old = row["cutout_filename"] if row else None
    with conn:
        conn.execute("UPDATE wardrobe_items SET cutout_filename = ?, cutout_version = ? WHERE id = ?",
                     (filename, version if filename else None, item_id))
    return old
