"""Confirming your email: link sent at sign-up, works once, expires, can be resent (limited)."""
from datetime import datetime, timedelta, timezone

import pytest

import database
import mailer
from tests.conftest import TEST_USER


@pytest.fixture()
def outbox(monkeypatch):
    sent = []
    monkeypatch.setattr(mailer, "send_email", lambda to, subject, body: sent.append({"to": to, "subject": subject, "body": body}))
    return sent


def token_from(email):
    return email["body"].split("#verify=")[1].split()[0]


def test_sign_up_sends_a_confirmation_link(anon, outbox):
    res = anon.post("/api/auth/signup", json=TEST_USER)
    assert res.status_code == 201 and res.json()["email_verified"] is False
    assert len(outbox) == 1 and outbox[0]["subject"] == "Confirm your email for Adaa"
    assert "Hi Test," in outbox[0]["body"] and "#verify=" in outbox[0]["body"]


def test_link_confirms_the_email_once(anon, outbox):
    anon.post("/api/auth/signup", json=TEST_USER)
    token = token_from(outbox[0])
    anon.post("/api/auth/logout")
    assert anon.post("/api/auth/verify", json={"token": token}).status_code == 204      # no login needed
    me = anon.post("/api/auth/login", json={"email": TEST_USER["email"], "password": TEST_USER["password"]}).json()
    assert me["email_verified"] is True
    again = anon.post("/api/auth/verify", json={"token": token})
    assert again.status_code == 400 and "expired or was already used" in again.json()["detail"]


def test_expired_link(anon, outbox):
    anon.post("/api/auth/signup", json=TEST_USER)
    with database.connect() as conn:
        conn.execute("UPDATE email_verifications SET expires_at = ?", ((datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),))
    assert anon.post("/api/auth/verify", json={"token": token_from(outbox[0])}).status_code == 400
    assert anon.get("/api/auth/me").json()["email_verified"] is False


def test_resend_is_limited(anon, outbox):
    anon.post("/api/auth/signup", json=TEST_USER)                  # 1st email
    assert anon.post("/api/auth/verify/resend").status_code == 202  # 2nd
    assert anon.post("/api/auth/verify/resend").status_code == 202  # 3rd
    res = anon.post("/api/auth/verify/resend")
    assert res.status_code == 429 and "check your inbox" in res.json()["detail"]
    assert len(outbox) == 3


def test_resend_after_confirming_does_nothing(anon, outbox):
    anon.post("/api/auth/signup", json=TEST_USER)
    anon.post("/api/auth/verify", json={"token": token_from(outbox[0])})
    res = anon.post("/api/auth/verify/resend")
    assert res.status_code == 202 and "already confirmed" in res.json()["detail"] and len(outbox) == 1


def test_resend_needs_login(anon):
    assert anon.post("/api/auth/verify/resend").status_code == 401


def test_bad_tokens_are_rejected(anon):
    assert anon.post("/api/auth/verify", json={"token": "x" * 40}).status_code == 400
    assert anon.post("/api/auth/verify", json={"token": "short"}).status_code == 422
