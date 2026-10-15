"""Saving, finding and deleting item photos on the local disk."""
import uuid
from pathlib import Path

from fastapi import UploadFile

import config

# The first bytes of a file reveal its real type, whatever its name says.
_SIGNATURES = [
    (b"\xff\xd8\xff", ".jpg"),
    (b"\x89PNG\r\n\x1a\n", ".png"),
]


class InvalidImage(ValueError):
    """The upload is not an accepted photo. The message is safe to show the user."""


def ensure_upload_dir() -> None:
    config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _detect_extension(data: bytes) -> str | None:
    for signature, ext in _SIGNATURES:
        if data.startswith(signature):
            return ext
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return ".webp"
    return None


def save_image(upload: UploadFile) -> str:
    """Validate and store an uploaded photo. Returns the new file name."""
    # Read one byte past the limit so we can tell if the file is too big.
    data = upload.file.read(config.MAX_UPLOAD_BYTES + 1)
    if not data:
        raise InvalidImage("The photo file is empty.")
    if len(data) > config.MAX_UPLOAD_BYTES:
        limit_mb = config.MAX_UPLOAD_BYTES // (1024 * 1024)
        raise InvalidImage(f"The photo is larger than {limit_mb} MB.")
    ext = _detect_extension(data)
    if ext is None:
        raise InvalidImage("Only JPEG, PNG or WebP photos are allowed.")

    # Never reuse the user's file name: a random name avoids clashes and path tricks.
    filename = f"{uuid.uuid4().hex}{ext}"
    ensure_upload_dir()
    (config.UPLOAD_DIR / filename).write_bytes(data)
    return filename


def image_path(filename: str) -> Path | None:
    """Full path of a stored photo, or None if it is missing or outside the upload folder."""
    upload_dir = config.UPLOAD_DIR.resolve()
    path = (upload_dir / filename).resolve()
    if path.parent != upload_dir or not path.is_file():
        return None
    return path


def delete_image(filename: str) -> None:
    path = image_path(filename)
    if path is not None:
        path.unlink(missing_ok=True)
