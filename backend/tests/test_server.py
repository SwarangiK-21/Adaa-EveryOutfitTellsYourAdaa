"""Running on a server: the backend serves the built app, and backups / restores work."""
import os
import sqlite3
import tarfile

import pytest

import backup
import config

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


def add_item(client, name="Green saree"):
    data = {"name": name, "category": "Clothing", "item_type": "Saree", "colour": "Green",
            "style": "Traditional", "occasions": ["Festive"]}
    res = client.post("/api/items", data=data, files={"photo": ("p.png", PNG, "image/png")})
    assert res.status_code == 201, res.text
    return res.json()


# ---------- one server ----------

@pytest.fixture()
def built_app(tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><div id=root></div>")
    (dist / "assets" / "index-abc123.js").write_text("console.log('adaa')")
    (dist / "assets" / "ort.wasm").write_bytes(b"\0asm")
    (dist / "manifest.webmanifest").write_text('{"name":"Adaa"}')
    (tmp_path / "secret.txt").write_text("not for the web")
    monkeypatch.setattr(config, "FRONTEND_DIR", dist)
    return dist


def test_serves_the_app_and_its_files(anon, built_app):
    page = anon.get("/")
    assert page.status_code == 200 and "id=root" in page.text and page.headers["cache-control"] == "no-cache"
    js = anon.get("/assets/index-abc123.js")
    assert js.status_code == 200 and "immutable" in js.headers["cache-control"]
    assert anon.get("/assets/ort.wasm").headers["content-type"] == "application/wasm"
    assert anon.get("/manifest.webmanifest").headers["content-type"].startswith("application/manifest+json")


def test_other_addresses_open_the_app(anon, built_app):
    res = anon.get("/wardrobe/anything")
    assert res.status_code == 200 and "id=root" in res.text


def test_api_still_answers_and_unknown_api_is_404(anon, built_app):
    assert anon.get("/api/health").json()["status"] == "ok"
    res = anon.get("/api/no-such-thing")
    assert res.status_code == 404 and res.json() == {"detail": "Not Found"}


def test_files_outside_the_app_folder_are_not_served(anon, built_app):
    res = anon.get("/%2e%2e/secret.txt")
    assert "not for the web" not in res.text


def test_without_a_build_the_root_just_says_running(anon, tmp_path, monkeypatch):
    monkeypatch.setattr(config, "FRONTEND_DIR", tmp_path / "no-build")
    assert anon.get("/").json()["message"] == "Adaa API is running."
    assert anon.get("/wardrobe").status_code == 404


# ---------- backups ----------

def test_backup_holds_the_database_and_photos(client, tmp_path):
    add_item(client)
    photos = sorted(p.name for p in config.UPLOAD_DIR.iterdir())
    path = backup.make_backup(tmp_path / "backups")
    assert backup.NAME.match(path.name)
    with tarfile.open(path) as tar:
        names = tar.getnames()
        assert "adaa.db" in names
        assert sorted(n.removeprefix("uploads/") for n in names if n.startswith("uploads/")) == photos
        tar.extract("adaa.db", tmp_path / "check", filter="data")
    db = sqlite3.connect(tmp_path / "check" / "adaa.db")
    assert db.execute("SELECT name FROM wardrobe_items").fetchall() == [("Green saree",)]
    db.close()


def test_only_the_newest_backups_are_kept(client, tmp_path):
    dest = tmp_path / "backups"
    dest.mkdir()
    for day in range(1, 10):                      # nine older backups...
        old = dest / f"adaa-202610{day:02d}-030000.tar.gz"
        old.write_bytes(b"old")
        os.utime(old, (day * 1000, day * 1000))
    (dest / "notes.txt").write_text("not a backup")
    newest = backup.make_backup(dest, keep=7)
    kept = sorted(p.name for p in dest.iterdir() if backup.NAME.match(p.name))
    assert len(kept) == 7 and newest.name in kept
    assert "adaa-20261001-030000.tar.gz" not in kept     # the oldest went first
    assert (dest / "notes.txt").exists()                  # other files are left alone


def test_restore_puts_a_backup_back(client, tmp_path):
    add_item(client, "Kept in the backup")
    archive = backup.make_backup(tmp_path / "backups")
    add_item(client, "Added after the backup")

    with pytest.raises(SystemExit):
        backup.restore_backup(archive)            # won't overwrite without --force
    backup.restore_backup(archive, force=True)
    names = [i["name"] for i in client.get("/api/items").json()]
    assert names == ["Kept in the backup"]
    assert (config.DATA_DIR / "test.db.before-restore").exists()   # the replaced database is kept


def test_restore_rejects_other_archives(tmp_path, data_dir):
    bad = tmp_path / "other.tar.gz"
    with tarfile.open(bad, "w:gz") as tar:
        (tmp_path / "x.txt").write_text("hi")
        tar.add(tmp_path / "x.txt", arcname="x.txt")
    with pytest.raises(SystemExit):
        backup.restore_backup(bad)
