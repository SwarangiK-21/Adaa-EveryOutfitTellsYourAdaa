"""Uploaded photos lose hidden metadata (EXIF / GPS, XMP, comments) but keep the picture and colour profile."""
import struct
import zlib

import config
from image_meta import strip_metadata


def seg(marker: int, payload: bytes) -> bytes:
    return bytes([0xFF, marker]) + struct.pack(">H", len(payload) + 2) + payload


JFIF = seg(0xE0, b"JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00")
EXIF = seg(0xE1, b"Exif\x00\x00" + b"GPSLatitude 18.52N GPSLongitude 73.85E")
XMP = seg(0xE1, b"http://ns.adobe.com/xap/1.0/\x00<x:xmpmeta>secret</x:xmpmeta>")
ICC = seg(0xE2, b"ICC_PROFILE\x00\x01\x01colour")
COMMENT = seg(0xFE, b"taken at home")
QUANT = seg(0xDB, b"\x00" + bytes(64))
SCAN = b"\xff\xda" + struct.pack(">H", 8) + b"\x01\x01\x00\x00\x3f\x00" + b"\x12\x34\xff\x00\x56" + b"\xff\xd9"
JPEG = b"\xff\xd8" + JFIF + EXIF + XMP + ICC + COMMENT + QUANT + SCAN


def png_chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload))


PNG = (b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
       + png_chunk(b"eXIf", b"MM\x00*GPS") + png_chunk(b"tEXt", b"Comment\x00secret")
       + png_chunk(b"IDAT", zlib.compress(b"\x00\x00\x00\x00\x00")) + png_chunk(b"IEND", b""))


def riff_chunk(kind: bytes, payload: bytes) -> bytes:
    return kind + struct.pack("<I", len(payload)) + payload + (b"\x00" if len(payload) % 2 else b"")


def webp(*chunks: bytes) -> bytes:
    body = b"".join(chunks)
    return b"RIFF" + struct.pack("<I", 4 + len(body)) + b"WEBP" + body


VP8X = riff_chunk(b"VP8X", bytes([0x0C, 0, 0, 0]) + bytes(6))   # flags say: has EXIF and XMP
WEBP = webp(VP8X, riff_chunk(b"VP8 ", b"picturedata"), riff_chunk(b"EXIF", b"GPS 18.52N"), riff_chunk(b"XMP ", b"<xmp/>"))


def test_jpeg_loses_exif_xmp_and_comments_but_keeps_the_picture():
    clean = strip_metadata(JPEG)
    assert b"GPS" not in clean and b"xmpmeta" not in clean and b"taken at home" not in clean
    assert clean.startswith(b"\xff\xd8" + JFIF)
    assert ICC in clean and QUANT in clean and clean.endswith(SCAN)


def test_png_loses_text_and_exif_chunks():
    clean = strip_metadata(PNG)
    assert b"eXIf" not in clean and b"secret" not in clean
    assert b"IHDR" in clean and b"IDAT" in clean and clean.endswith(png_chunk(b"IEND", b""))


def test_webp_loses_exif_and_xmp_and_stays_a_valid_file():
    clean = strip_metadata(WEBP)
    assert b"GPS" not in clean and b"<xmp/>" not in clean and b"picturedata" in clean
    assert struct.unpack("<I", clean[4:8])[0] == len(clean) - 8          # RIFF size is updated
    assert clean[20] & 0x0C == 0                                          # VP8X flags cleared


def test_files_it_cannot_read_are_left_alone():
    broken = b"\xff\xd8" + b"\x00" * 20
    assert strip_metadata(broken) == broken
    assert strip_metadata(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)            # no crash on a stub file


def test_uploaded_photos_are_saved_without_location(client):
    data = {"name": "Green saree", "category": "Clothing", "item_type": "Saree", "colour": "Green",
            "style": "Traditional", "occasions": ["Festive"]}
    res = client.post("/api/items", data=data, files={"photo": ("p.jpg", JPEG, "image/jpeg")})
    assert res.status_code == 201, res.text
    saved = next(config.UPLOAD_DIR.iterdir()).read_bytes()
    assert b"GPS" not in saved and saved.endswith(SCAN)
    served = client.get(res.json()["image_url"]).content
    assert b"GPS" not in served
