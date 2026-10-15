"""SQLite connection, table setup and wardrobe item queries."""
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
"""


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = connect()
    try:
        conn.executescript(SCHEMA)
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


def list_items(conn, search: str = "", category: str | None = None) -> list[dict]:
    sql = "SELECT * FROM wardrobe_items WHERE 1=1"
    params: list = []
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


def get_item(conn, item_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM wardrobe_items WHERE id = ?", (item_id,)).fetchone()
    return row_to_dict(row) if row else None


def create_item(conn, fields: ItemFields, image_filename: str) -> dict:
    now = _now()
    cur = conn.execute(
        """INSERT INTO wardrobe_items
           (name, category, item_type, colour, style, occasions, notes,
            image_filename, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            fields.name, fields.category, fields.item_type, fields.colour, fields.style,
            json.dumps(fields.occasions), fields.notes, image_filename, now, now,
        ),
    )
    conn.commit()
    return get_item(conn, cur.lastrowid)


def update_item(conn, item_id: int, fields: ItemFields, image_filename: str) -> dict:
    conn.execute(
        """UPDATE wardrobe_items
           SET name = ?, category = ?, item_type = ?, colour = ?, style = ?,
               occasions = ?, notes = ?, image_filename = ?, updated_at = ?
           WHERE id = ?""",
        (
            fields.name, fields.category, fields.item_type, fields.colour, fields.style,
            json.dumps(fields.occasions), fields.notes, image_filename, _now(), item_id,
        ),
    )
    conn.commit()
    return get_item(conn, item_id)


def delete_item(conn, item_id: int) -> None:
    conn.execute("DELETE FROM wardrobe_items WHERE id = ?", (item_id,))
    conn.commit()
