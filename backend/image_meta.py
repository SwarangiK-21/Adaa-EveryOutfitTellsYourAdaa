"""Removes hidden metadata (camera details, GPS location, comments) from uploaded photos.

Phone photos often carry the exact place they were taken (EXIF GPS). The app already re-draws
photos in the browser before uploading, which drops all of this; this is the server-side safety
net for anything that arrives another way. Pure Python, no image library: it only removes
metadata blocks and never re-encodes the picture itself.

- JPEG: drops APP1 (EXIF, XMP), APP13 (IPTC/Photoshop) and COM (comment) segments.
- PNG:  drops eXIf, tEXt, zTXt, iTXt and tIME chunks.
- WebP: drops EXIF and XMP chunks and clears their flags in the VP8X header.
Colour profiles (ICC) are kept, so colours look the same. If a file can't be parsed, it's
returned unchanged (its type was already checked).
"""
import struct

_JPEG_DROP = {0xE1, 0xED, 0xFE}                              # APP1, APP13, COM
_PNG_DROP = {b"eXIf", b"tEXt", b"zTXt", b"iTXt", b"tIME"}
_WEBP_DROP = {b"EXIF", b"XMP "}


def strip_metadata(data: bytes) -> bytes:
    try:
        if data.startswith(b"\xff\xd8"):
            return _jpeg(data)
        if data.startswith(b"\x89PNG\r\n\x1a\n"):
            return _png(data)
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            return _webp(data)
    except (IndexError, struct.error, ValueError):
        pass
    return data


def _jpeg(data: bytes) -> bytes:
    out = bytearray(data[:2])
    i = 2
    while i < len(data):
        if data[i] != 0xFF:
            raise ValueError("not a marker")
        marker = data[i + 1]
        if marker == 0xFF:                       # fill byte
            i += 1
            continue
        if marker == 0xDA or marker == 0xD9:     # start of image data / end: copy the rest as it is
            out += data[i:]
            return bytes(out)
        if 0xD0 <= marker <= 0xD7 or marker == 0x01:   # markers without a length
            out += data[i:i + 2]
            i += 2
            continue
        length = struct.unpack(">H", data[i + 2:i + 4])[0]
        if length < 2 or i + 2 + length > len(data):
            raise ValueError("bad segment")
        if marker not in _JPEG_DROP:
            out += data[i:i + 2 + length]
        i += 2 + length
    raise ValueError("no image data")


def _png(data: bytes) -> bytes:
    out = bytearray(data[:8])
    i = 8
    while i < len(data):
        length = struct.unpack(">I", data[i:i + 4])[0]
        kind = data[i + 4:i + 8]
        end = i + 12 + length
        if end > len(data):
            raise ValueError("bad chunk")
        if kind not in _PNG_DROP:
            out += data[i:end]
        i = end
        if kind == b"IEND":
            break
    return bytes(out)


def _webp(data: bytes) -> bytes:
    chunks = bytearray()
    i = 12
    while i + 8 <= len(data):
        kind = data[i:i + 4]
        size = struct.unpack("<I", data[i + 4:i + 8])[0]
        end = i + 8 + size + (size & 1)          # chunks are padded to an even length
        if end > len(data) + 1:
            raise ValueError("bad chunk")
        chunk = bytearray(data[i:min(end, len(data))])
        if kind == b"VP8X" and len(chunk) >= 9:
            chunk[8] &= ~0x0C & 0xFF             # clear the "has EXIF" (0x08) and "has XMP" (0x04) flags
        if kind not in _WEBP_DROP:
            chunks += chunk
        i = end
    return b"RIFF" + struct.pack("<I", 4 + len(chunks)) + b"WEBP" + bytes(chunks)
