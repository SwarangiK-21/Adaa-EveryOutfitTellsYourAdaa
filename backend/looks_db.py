"""Database queries for saved looks and outfit history (each row belongs to one user: uid)."""
import json
from datetime import date

from database import _now


def _look_row(conn, row) -> dict:
    look = dict(row)
    look["prefs"] = json.loads(look["prefs"])
    look["item_ids"] = [r["item_id"] for r in conn.execute(
        "SELECT item_id FROM look_items WHERE look_id = ? ORDER BY position", (look["id"],))]
    wear = conn.execute(
        "SELECT COUNT(*) AS n, MAX(worn_on) AS last FROM wear_log WHERE look_id = ?", (look["id"],)
    ).fetchone()
    look["wear_count"], look["last_worn_on"] = wear["n"], wear["last"]
    look["photo"] = get_photo(conn, look["id"])
    return look


def list_looks(conn, uid: int) -> list[dict]:
    rows = conn.execute("SELECT * FROM looks WHERE user_id = ? ORDER BY created_at DESC, id DESC", (uid,)).fetchall()
    return [_look_row(conn, r) for r in rows]


def get_look(conn, look_id: int, uid: int | None = None) -> dict | None:
    """One look; with uid, only if it belongs to that user."""
    if uid is None:
        row = conn.execute("SELECT * FROM looks WHERE id = ?", (look_id,)).fetchone()
    else:
        row = conn.execute("SELECT * FROM looks WHERE id = ? AND user_id = ?", (look_id, uid)).fetchone()
    return _look_row(conn, row) if row else None


def find_same_look(conn, uid: int, item_ids: list[int], occasion: str) -> int | None:
    """Id of an existing saved look with exactly these pieces for this occasion, if any."""
    wanted = sorted(item_ids)
    for look in list_looks(conn, uid):
        if sorted(look["item_ids"]) == wanted and look["prefs"]["occasion"] == occasion:
            return look["id"]
    return None


def _set_items(conn, look_id: int, item_ids: list[int]) -> None:
    conn.execute("DELETE FROM look_items WHERE look_id = ?", (look_id,))
    conn.executemany(
        "INSERT INTO look_items (look_id, item_id, position) VALUES (?, ?, ?)",
        [(look_id, item_id, pos) for pos, item_id in enumerate(item_ids)],
    )


def create_look(conn, uid: int, name: str, prefs: dict, item_ids: list[int]) -> dict:
    now = _now()
    with conn:
        cur = conn.execute(
            "INSERT INTO looks (user_id, name, prefs, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (uid, name, json.dumps(prefs), now, now),
        )
        _set_items(conn, cur.lastrowid, item_ids)
    return get_look(conn, cur.lastrowid)


def update_look(conn, look_id: int, name: str | None, item_ids: list[int] | None) -> dict:
    with conn:
        if name is not None:
            conn.execute("UPDATE looks SET name = ?, updated_at = ? WHERE id = ?", (name, _now(), look_id))
        if item_ids is not None:
            _set_items(conn, look_id, item_ids)
            conn.execute("UPDATE looks SET updated_at = ? WHERE id = ?", (_now(), look_id))
    return get_look(conn, look_id)


def delete_look(conn, look_id: int) -> str | None:
    """Delete a look. Returns its photo file name (if any) so the caller can remove the file."""
    photo = get_photo(conn, look_id)
    with conn:
        conn.execute("DELETE FROM looks WHERE id = ?", (look_id,))
    return photo["image_filename"] if photo else None


# ---------- verified photos ----------

def get_photo(conn, look_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM look_photos WHERE look_id = ?", (look_id,)).fetchone()
    if not row:
        return None
    photo = dict(row)
    photo["item_ids"] = json.loads(photo["item_ids"])
    return photo


def set_photo(conn, look_id: int, image_filename: str, item_ids: list[int]) -> str | None:
    """Attach a photo to a look, replacing any earlier one. Returns the old file name, if any."""
    old = get_photo(conn, look_id)
    with conn:
        conn.execute("DELETE FROM look_photos WHERE look_id = ?", (look_id,))
        conn.execute(
            "INSERT INTO look_photos (look_id, image_filename, item_ids, created_at) VALUES (?, ?, ?, ?)",
            (look_id, image_filename, json.dumps(item_ids), _now()),
        )
    return old["image_filename"] if old else None


def delete_photo(conn, look_id: int) -> str | None:
    old = get_photo(conn, look_id)
    with conn:
        conn.execute("DELETE FROM look_photos WHERE look_id = ?", (look_id,))
    return old["image_filename"] if old else None


def log_wear(conn, uid: int, look: dict, worn_on: date) -> dict:
    """A saved look was worn: remember the look and exactly which pieces it had that day."""
    return log_outfit_wear(conn, uid, look["item_ids"], look["name"], look["prefs"]["occasion"], worn_on, look["id"])


def log_outfit_wear(conn, uid: int, item_ids: list[int], name: str, occasion: str, worn_on: date,
                    look_id: int | None = None) -> dict:
    with conn:
        cur = conn.execute(
            "INSERT INTO wear_log (user_id, look_id, look_name, occasion, worn_on, created_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (uid, look_id, name, occasion, worn_on.isoformat(), _now()),
        )
        conn.executemany("INSERT OR IGNORE INTO wear_items (wear_id, item_id) VALUES (?, ?)",
                         [(cur.lastrowid, i) for i in item_ids])
    return get_wear(conn, cur.lastrowid)


def worn_item_ids(conn, wear_id: int) -> list[int]:
    return [r["item_id"] for r in conn.execute(
        "SELECT item_id FROM wear_items WHERE wear_id = ? ORDER BY rowid", (wear_id,))]


def item_wear(conn, uid: int) -> dict[int, tuple[int, str]]:
    """item id -> (times worn, last date worn), from this user's outfit history."""
    rows = conn.execute(
        "SELECT wi.item_id, COUNT(DISTINCT w.id) AS n, MAX(w.worn_on) AS last"
        " FROM wear_items wi JOIN wear_log w ON w.id = wi.wear_id WHERE w.user_id = ? GROUP BY wi.item_id", (uid,))
    return {r["item_id"]: (r["n"], r["last"]) for r in rows}


def get_wear(conn, wear_id: int, uid: int | None = None) -> dict | None:
    if uid is None:
        row = conn.execute("SELECT * FROM wear_log WHERE id = ?", (wear_id,)).fetchone()
    else:
        row = conn.execute("SELECT * FROM wear_log WHERE id = ? AND user_id = ?", (wear_id, uid)).fetchone()
    return dict(row) if row else None


def list_history(conn, uid: int) -> list[dict]:
    rows = conn.execute("SELECT * FROM wear_log WHERE user_id = ? ORDER BY worn_on DESC, id DESC", (uid,)).fetchall()
    return [dict(r) for r in rows]


def delete_wear(conn, wear_id: int) -> None:
    with conn:
        conn.execute("DELETE FROM wear_log WHERE id = ?", (wear_id,))
