"""Off-site backup copies: correct request signing, the upload itself, and what backup.py reports."""
from datetime import datetime, timezone

import httpx
import pytest

import backup
import config
import offsite


def test_signature_matches_the_aws_published_example():
    # "GET Object" example from the Amazon S3 Signature Version 4 documentation.
    headers = {"Host": "examplebucket.s3.amazonaws.com", "Range": "bytes=0-9",
               "x-amz-content-sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
               "x-amz-date": "20130524T000000Z"}
    auth = offsite.sign("GET", "https://examplebucket.s3.amazonaws.com/test.txt", headers,
                        headers["x-amz-content-sha256"], datetime(2013, 5, 24, tzinfo=timezone.utc),
                        "AKIAIOSFODNN7EXAMPLE", "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY", "us-east-1")
    assert auth == ("AWS4-HMAC-SHA256 Credential=AKIAIOSFODNN7EXAMPLE/20130524/us-east-1/s3/aws4_request, "
                    "SignedHeaders=host;range;x-amz-content-sha256;x-amz-date, "
                    "Signature=f0e8bdb87c964420e857bd35b5d6ed310bd44f0170aba48dd91039c6036bdb41")


@pytest.fixture()
def r2(monkeypatch):
    monkeypatch.setattr(config, "S3_ENDPOINT", "https://acct123.r2.cloudflarestorage.com")
    monkeypatch.setattr(config, "S3_BUCKET", "peheraav-backups")
    monkeypatch.setattr(config, "S3_KEY_ID", "key-id")
    monkeypatch.setattr(config, "S3_SECRET", "secret")
    monkeypatch.setattr(config, "S3_REGION", "auto")


def test_upload_sends_a_signed_put(tmp_path, r2):
    seen = {}

    def handler(request: httpx.Request):
        seen.update(method=request.method, url=str(request.url), headers=dict(request.headers), body=request.content)
        return httpx.Response(200)

    archive = tmp_path / "peheraav-20261106-033000.tar.gz"
    archive.write_bytes(b"backup bytes")
    url = offsite.upload(archive, transport=httpx.MockTransport(handler))
    assert url == "https://acct123.r2.cloudflarestorage.com/peheraav-backups/peheraav-20261106-033000.tar.gz"
    assert seen["method"] == "PUT" and seen["url"] == url and seen["body"] == b"backup bytes"
    assert seen["headers"]["authorization"].startswith("AWS4-HMAC-SHA256 Credential=key-id/")
    assert "/auto/s3/aws4_request" in seen["headers"]["authorization"]


def test_refused_upload_raises(tmp_path, r2):
    archive = tmp_path / "peheraav-20261106-033000.tar.gz"
    archive.write_bytes(b"x")
    with pytest.raises(offsite.OffsiteError, match="403"):
        offsite.upload(archive, transport=httpx.MockTransport(lambda r: httpx.Response(403, text="AccessDenied")))


def test_backup_command_copies_off_site(client, tmp_path, monkeypatch, r2, capsys):
    monkeypatch.setattr(config, "BACKUP_DIR", tmp_path / "backups")
    sent = []
    monkeypatch.setattr(offsite, "upload", lambda path: sent.append(path) or f"r2://{path.name}")
    assert backup.main([]) == 0
    assert len(sent) == 1 and sent[0].exists()
    assert "Copied off-site" in capsys.readouterr().out


def test_backup_command_fails_loudly_when_off_site_fails(client, tmp_path, monkeypatch, r2, capsys):
    monkeypatch.setattr(config, "BACKUP_DIR", tmp_path / "backups")

    def broken(path):
        raise offsite.OffsiteError("network down")

    monkeypatch.setattr(offsite, "upload", broken)
    assert backup.main([]) == 1
    assert "FAILED" in capsys.readouterr().err
    assert len(list((tmp_path / "backups").iterdir())) == 1      # the local backup is still kept


def test_without_settings_backups_stay_local(client, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(config, "BACKUP_DIR", tmp_path / "backups")
    monkeypatch.setattr(config, "S3_ENDPOINT", "")
    assert backup.main([]) == 0
    assert "not set up" in capsys.readouterr().out
