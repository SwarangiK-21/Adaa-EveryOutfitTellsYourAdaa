"""Copies a backup to off-site storage (Cloudflare R2, or any S3-compatible service).

A server's own disk can fail or the server can be removed; the nightly backups then go with it.
After each backup, backup.py calls upload() to put a copy somewhere else. Old copies are removed
by the bucket's own lifecycle rule (set in the R2 dashboard, see docs/DEPLOY.md), so this only
needs permission to write. Requests are signed with AWS Signature V4 using only the standard
library and httpx (already installed).

Settings: ADAA_BACKUP_S3_ENDPOINT (e.g. https://<account-id>.r2.cloudflarestorage.com),
ADAA_BACKUP_S3_BUCKET, ADAA_BACKUP_S3_KEY_ID, ADAA_BACKUP_S3_SECRET, ADAA_BACKUP_S3_REGION ("auto").
"""
import hashlib
import hmac
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlsplit

import httpx

import config


class OffsiteError(Exception):
    pass


def enabled() -> bool:
    return bool(config.S3_ENDPOINT and config.S3_BUCKET and config.S3_KEY_ID and config.S3_SECRET)


def _hmac(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode(), hashlib.sha256).digest()


def sign(method: str, url: str, headers: dict[str, str], payload_hash: str, now: datetime,
         key_id: str, secret: str, region: str, service: str = "s3") -> str:
    """The Authorization header for a request (AWS Signature Version 4). `headers` must already
    contain every header to sign, including host, x-amz-date and x-amz-content-sha256."""
    parts = urlsplit(url)
    path = quote(parts.path or "/", safe="/~")
    query = "&".join(sorted(parts.query.split("&"))) if parts.query else ""
    names = sorted(h.lower() for h in headers)
    canonical_headers = "".join(f"{n}:{' '.join(str(headers[k]).split())}\n" for n in names
                                for k in headers if k.lower() == n)
    signed = ";".join(names)
    canonical = "\n".join([method, path, query, canonical_headers, signed, payload_hash])
    day = now.strftime("%Y%m%d")
    scope = f"{day}/{region}/{service}/aws4_request"
    to_sign = "\n".join(["AWS4-HMAC-SHA256", now.strftime("%Y%m%dT%H%M%SZ"), scope,
                         hashlib.sha256(canonical.encode()).hexdigest()])
    key = _hmac(_hmac(_hmac(_hmac(("AWS4" + secret).encode(), day), region), service), "aws4_request")
    signature = hmac.new(key, to_sign.encode(), hashlib.sha256).hexdigest()
    return f"AWS4-HMAC-SHA256 Credential={key_id}/{scope}, SignedHeaders={signed}, Signature={signature}"


def upload(path: Path, transport: httpx.BaseTransport | None = None) -> str:
    """Upload one backup file. Returns its address in the bucket; raises OffsiteError on failure."""
    data = Path(path).read_bytes()
    payload_hash = hashlib.sha256(data).hexdigest()
    url = f"{config.S3_ENDPOINT.rstrip('/')}/{config.S3_BUCKET}/{Path(path).name}"
    now = datetime.now(timezone.utc)
    headers = {
        "host": urlsplit(url).netloc,
        "x-amz-content-sha256": payload_hash,
        "x-amz-date": now.strftime("%Y%m%dT%H%M%SZ"),
        "content-type": "application/gzip",
    }
    headers["authorization"] = sign("PUT", url, headers, payload_hash, now,
                                    config.S3_KEY_ID, config.S3_SECRET, config.S3_REGION)
    try:
        with httpx.Client(transport=transport, timeout=300) as client:
            res = client.put(url, content=data, headers=headers)
    except httpx.HTTPError as exc:
        raise OffsiteError(f"Couldn't reach the backup storage: {exc}") from None
    if res.status_code >= 300:
        raise OffsiteError(f"The backup storage refused the upload ({res.status_code}): {res.text[:300]}")
    return url
