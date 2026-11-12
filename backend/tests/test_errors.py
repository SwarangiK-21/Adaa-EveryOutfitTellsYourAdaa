"""Unexpected errors give a calm message (and are logged); browser crash reports are logged."""
import logging

from fastapi.testclient import TestClient

import database
from main import app


def test_unexpected_error_is_logged_and_friendly(client, monkeypatch, caplog):
    def broken(*args, **kwargs):
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(database, "list_items", broken)
    with TestClient(app, raise_server_exceptions=False) as c:
        c.cookies = client.cookies
        with caplog.at_level(logging.ERROR, logger="peheraav"):
            res = c.get("/api/items")
    assert res.status_code == 500
    assert res.json() == {"detail": "Something went wrong on our side. Please try again in a moment."}
    assert "disk on fire" not in res.text                       # no internals shown to people
    assert any("Unexpected error on GET /api/items" in r.getMessage() for r in caplog.records)


def test_browser_crash_reports_are_logged(anon, caplog):
    with caplog.at_level(logging.WARNING, logger="peheraav"):
        res = anon.post("/api/client-error", json={"message": "x is undefined", "where": "at Wardrobe", "page": "/"})
    assert res.status_code == 204
    assert any("x is undefined" in r.getMessage() for r in caplog.records)


def test_crash_reports_are_size_limited(anon):
    assert anon.post("/api/client-error", json={"message": "x" * 600}).status_code == 422
