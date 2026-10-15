"""Database queries for saved looks and outfit history."""
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
    return look


def list_looks(conn) -> list[dict]:
    rows = conn.execute("SELECT * FROM looks ORDER BY created_at DESC, id DESC").fetchall()
    return [_look_row(conn, r) for r in rows]


def get_look(conn, look_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM looks WHERE id = ?", (look_id,)).fetchone()
    return _look_row(conn, row) if row else None


def find_same_look(conn, item_ids: list[int], occasion: str) -> int | None:
    """Id of an existing saved look with exactly these pieces for this occasion, if any."""
    wanted = sorted(item_ids)
    for look in list_looks(conn):
        if sorted(look["item_ids"]) == wanted and look["prefs"]["occasion"] == occasion:
            return look["id"]
    return None


def _set_items(conn, look_id: int, item_ids: list[int]) -> None:
    conn.execute("DELETE FROM look_items WHERE look_id = ?", (look_id,))
    conn.executemany(
        "INSERT INTO look_items (look_id, item_id, position) VALUES (?, ?, ?)",
        [(look_id, item_id, pos) for pos, item_id in enumerate(item_ids)],
    )


def create_look(conn, name: str, prefs: dict, item_ids: list[int]) -> dict:
    now = _now()
    with conn:
        cur = conn.execute(
            "INSERT INTO looks (name, prefs, created_at, updated_at) VALUES (?, ?, ?, ?)",
            (name, json.dumps(prefs), now, now),
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


def delete_look(conn, look_id: int) -> None:
    with conn:
        conn.execute("DELETE FROM looks WHERE id = ?", (look_id,))


def log_wear(conn, look: dict, worn_on: date) -> dict:
    with conn:
        cur = conn.execute(
            "INSERT INTO wear_log (look_id, look_name, occasion, worn_on, created_at)"
            " VALUES (?, ?, ?, ?, ?)",
            (look["id"], look["name"], look["prefs"]["occasion"], worn_on.isoformat(), _now()),
        )
    return get_wear(conn, cur.lastrowid)


def get_wear(conn, wear_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM wear_log WHERE id = ?", (wear_id,)).fetchone()
    return dict(row) if row else None


def list_history(conn) -> list[dict]:
    rows = conn.execute("SELECT * FROM wear_log ORDER BY worn_on DESC, id DESC").fetchall()
    return [dict(r) for r in rows]


def delete_wear(conn, wear_id: int) -> None:
    with conn:
        conn.execute("DELETE FROM wear_log WHERE id = ?", (wear_id,))
