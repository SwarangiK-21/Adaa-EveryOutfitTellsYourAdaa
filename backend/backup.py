"""Back up (or restore) Adaa's database and photos.

    python backup.py                  make a backup, keep the newest 7 (ADAA_BACKUP_KEEP), copy it off-site if set up
    python backup.py --restore FILE   put a backup back (stop the backend first)

A backup is one file, adaa-YYYYMMDD-HHMMSS.tar.gz, in ADAA_BACKUP_DIR (backend/backups on your
laptop). It holds a consistent copy of the database (made with SQLite's own backup, so it's safe
while Adaa is running) and every photo. The AI models aren't included: they download again by
themselves. On a server, a daily timer runs this (see docs/DEPLOY.md).
"""
import argparse
import re
import shutil
import sqlite3
import sys
import tarfile
import tempfile
from datetime import datetime
from pathlib import Path

import config
import offsite

NAME = re.compile(r"^adaa-\d{8}-\d{6}(-\d+)?\.tar\.gz$")


def make_backup(dest: Path | None = None, keep: int | None = None) -> Path:
    dest = Path(dest or config.BACKUP_DIR)
    keep = config.BACKUP_KEEP if keep is None else keep
    dest.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    target, n = dest / f"adaa-{stamp}.tar.gz", 2
    while target.exists():                       # two backups in the same second
        target, n = dest / f"adaa-{stamp}-{n}.tar.gz", n + 1

    with tempfile.TemporaryDirectory() as tmp:
        db_copy = Path(tmp) / "adaa.db"
        if config.DB_PATH.exists():
            src = sqlite3.connect(config.DB_PATH)
            out = sqlite3.connect(db_copy)
            try:
                src.backup(out)                  # consistent even while the app is writing
            finally:
                out.close()
                src.close()
        part = target.with_name(target.name + ".part")
        with tarfile.open(part, "w:gz") as tar:
            if db_copy.exists():
                tar.add(db_copy, arcname="adaa.db")
            if config.UPLOAD_DIR.exists():
                tar.add(config.UPLOAD_DIR, arcname="uploads")
        part.replace(target)                     # a half-written backup never looks finished

    for old in sorted((p for p in dest.iterdir() if NAME.match(p.name)), key=lambda p: p.stat().st_mtime)[:-keep or None]:
        old.unlink()
    return target


def restore_backup(archive: Path, force: bool = False) -> None:
    """Replace the current database and photos with a backup's. The current ones are kept beside
    them as adaa.db.before-restore / uploads.before-restore, in case you change your mind."""
    archive = Path(archive)
    with tarfile.open(archive, "r:gz") as tar:
        names = tar.getnames()
        if "adaa.db" not in names:
            raise SystemExit(f"{archive} doesn't look like an Adaa backup (no adaa.db inside).")
        if config.DB_PATH.exists() and not force:
            raise SystemExit("There is already a database here. Stop the backend, then run again with --force "
                             "(the current one is kept as adaa.db.before-restore).")
        config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        # The -wal/-shm side files belong to the old database: move them aside too, never mix them with the new one.
        wal, shm = (config.DB_PATH.with_name(config.DB_PATH.name + s) for s in ("-wal", "-shm"))
        for current in (config.DB_PATH, wal, shm, config.UPLOAD_DIR):
            if current.exists():
                kept = current.with_name(current.name + ".before-restore")
                if kept.is_dir():
                    shutil.rmtree(kept)
                elif kept.exists():
                    kept.unlink()
                current.rename(kept)
        with tempfile.TemporaryDirectory() as tmp:
            tar.extractall(tmp, filter="data")   # "data": refuses paths outside the folder, links, devices
            shutil.move(Path(tmp) / "adaa.db", config.DB_PATH)
            if (Path(tmp) / "uploads").exists():
                shutil.move(Path(tmp) / "uploads", config.UPLOAD_DIR)
            else:
                config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description="Back up or restore Adaa's database and photos.")
    parser.add_argument("--restore", metavar="FILE", help="put this backup back (stop the backend first)")
    parser.add_argument("--force", action="store_true", help="with --restore: replace the current data")
    args = parser.parse_args(argv)
    if args.restore:
        restore_backup(Path(args.restore), force=args.force)
        print(f"Restored {args.restore} into {config.DATA_DIR}. Start the backend again.")
    else:
        path = make_backup()
        print(f"Backup saved: {path} ({path.stat().st_size / 1_048_576:.1f} MB)")
        if offsite.enabled():
            try:
                print(f"Copied off-site: {offsite.upload(path)}")
            except offsite.OffsiteError as exc:
                # The local backup is still there; failing loudly makes the systemd timer show "failed".
                print(f"Off-site copy FAILED: {exc}", file=sys.stderr)
                return 1
        else:
            print("Off-site copy: not set up (see docs/DEPLOY.md). Only this server has the backup.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
