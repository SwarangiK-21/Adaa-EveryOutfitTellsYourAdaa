"""Sign up, log in, log out, your account details, passwords, and deleting your account."""
import sqlite3
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response

import auth
import config
import database
import mailer
import storage
from schemas import (
    AboutOut, AccountFields, DeleteAccountIn, ForgotIn, LoginIn, PasswordChange, ResetIn, SignupIn, UserOut, VerifyIn,
    user_out,
)

router = APIRouter(prefix="/api/auth", tags=["account"])
Db = Annotated[sqlite3.Connection, Depends(database.get_db)]

FORGOT_REPLY = {"detail": "If an account uses that email, we've sent it a link to choose a new password. It works for 30 minutes."}


@router.get("/about", response_model=AboutOut)
def about():
    """Public facts for the sign-up screen and privacy note."""
    return AboutOut(contact_email=config.CONTACT_EMAIL, max_items=config.MAX_ITEMS_PER_USER,
                    max_looks=config.MAX_LOOKS_PER_USER)


def _send_verification(db, user: dict, tasks: BackgroundTasks) -> None:
    token = auth.new_verify_token(db, user["id"])
    first = user["name"].split()[0]
    link = f"{config.PUBLIC_URL}/#verify={token}"   # after "#": never reaches the server's access logs
    tasks.add_task(
        mailer.send_email, user["email"], "Confirm your email for Adaa",
        f"Hi {first},\n\nWelcome to Adaa! Please confirm this is your email address:\n\n{link}\n\n"
        f"The link works for {auth.VERIFY_HOURS} hours. If you didn't sign up for Adaa, ignore this email.\n\nAdaa\n")


@router.post("/signup", response_model=UserOut, status_code=201)
def signup(body: SignupIn, db: Db, response: Response, tasks: BackgroundTasks):
    """Create an account and sign in. The very first account also receives the wardrobe made
    before accounts existed."""
    if database.find_user_by_email(db, body.email):
        raise HTTPException(status_code=409, detail="An account with this email already exists. Please log in.")
    users = database.count_users(db)
    if config.MAX_USERS and users >= config.MAX_USERS:
        raise HTTPException(status_code=403, detail="Adaa isn't taking new accounts right now. Please try again later.")
    user = database.create_user(db, body.name, body.email, body.phone, auth.hash_password(body.password))
    moved = database.claim_unowned(db, user["id"]) if users == 0 else 0
    auth.start_session(db, response, user["id"])
    auth.may_send_email(user["email"], "verify")      # counts towards the 3-an-hour limit
    _send_verification(db, user, tasks)
    return user_out(user, moved)

@router.post("/verify", status_code=204)
def verify_email(body: VerifyIn, db: Db):
    """Confirm an email address from the emailed link (works without being logged in)."""
    uid = auth.use_verify_token(db, body.token)
    if uid is None:
        raise HTTPException(status_code=400, detail="This confirmation link has expired or was already used. "
                            "Log in and ask for a new one from the banner at the top.")
    database.mark_email_verified(db, uid)


@router.post("/verify/resend", status_code=202)
def resend_verification(user: auth.User, db: Db, tasks: BackgroundTasks):
    """Email a new confirmation link (at most 3 an hour)."""
    if user.get("email_verified_at"):
        return {"detail": "Your email is already confirmed."}
    if not auth.may_send_email(user["email"], "verify"):
        raise HTTPException(status_code=429, detail="We've sent a few links already. Please check your inbox "
                            "(and spam), or try again in an hour.")
    _send_verification(db, user, tasks)
    return {"detail": f"We've sent a new link to {user['email']}. It works for {auth.VERIFY_HOURS} hours."}


@router.post("/login", response_model=UserOut)
def login(body: LoginIn, db: Db, response: Response):
    if auth.too_many_failures(body.email):
        raise HTTPException(status_code=429, detail="Too many wrong passwords. Please wait 15 minutes and try again.")
    user = database.find_user_by_email(db, body.email)
    if not user or not auth.check_password(body.password, user["password_hash"]):
        auth.record_failure(body.email)
        raise HTTPException(status_code=401, detail="That email and password don't match.")
    auth.clear_failures(body.email)
    auth.start_session(db, response, user["id"])
    return user_out(user)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Db):
    auth.end_session(db, request, response)


@router.get("/me", response_model=UserOut)
def me(user: auth.User):
    return user_out(user)


@router.put("/me", response_model=UserOut)
def update_me(body: AccountFields, user: auth.User, db: Db):
    """Change your name or phone number (your email is your sign-in, so it stays)."""
    return user_out(database.update_user(db, user["id"], body.name, body.phone))


def _check_own_password(user: dict, password: str) -> None:
    """Re-asking for the password protects big changes on a browser someone left signed in."""
    if auth.too_many_failures(user["email"]):
        raise HTTPException(status_code=429, detail="Too many wrong passwords. Please wait 15 minutes and try again.")
    if not auth.check_password(password, user["password_hash"]):
        auth.record_failure(user["email"])
        raise HTTPException(status_code=400, detail="That isn't your current password.")
    auth.clear_failures(user["email"])


@router.put("/password", status_code=204)
def change_password(body: PasswordChange, user: auth.User, db: Db, response: Response):
    """Choose a new password. Other browsers signed in to this account are signed out."""
    _check_own_password(user, body.current_password)
    database.set_password(db, user["id"], auth.hash_password(body.new_password))
    auth.start_session(db, response, user["id"])   # keep this browser signed in


@router.post("/forgot", status_code=202)
def forgot_password(body: ForgotIn, db: Db, tasks: BackgroundTasks):
    """Email a link to choose a new password. The reply is the same whether or not the email has an
    account (so nobody can find out who uses Adaa), and the email is sent after replying."""
    user = database.find_user_by_email(db, body.email)
    if user and auth.may_send_reset(body.email):
        token = auth.new_reset_token(db, user["id"])
        # After "#", so browsers never send the token to the server and it can't end up in access logs.
        link = f"{config.PUBLIC_URL}/#reset={token}"
        first = user["name"].split()[0]
        tasks.add_task(
            mailer.send_email, user["email"], "Choose a new password for Adaa",
            f"Hi {first},\n\nSomeone (hopefully you) asked to reset your Adaa password. Open this link to choose a new one:\n\n"
            f"{link}\n\nIt works once, for {auth.RESET_MINUTES} minutes. If you didn't ask for this, ignore this email: "
            f"your password stays the same.\n\nAdaa\n")
    return FORGOT_REPLY


@router.post("/reset", status_code=204)
def reset_password(body: ResetIn, db: Db):
    """Set a new password from an emailed link. Every browser signed in to the account is signed out."""
    uid = auth.use_reset_token(db, body.token)
    if uid is None:
        raise HTTPException(status_code=400, detail="This link has expired or was already used. Please ask for a new one.")
    database.set_password(db, uid, auth.hash_password(body.password))
    user = database.get_user(db, uid)
    auth.clear_failures(user["email"])


@router.delete("/me", status_code=204)
def delete_account(body: DeleteAccountIn, user: auth.User, db: Db, request: Request, response: Response):
    """Erase your account and everything in it: pieces, photos, looks, history. This can't be undone."""
    _check_own_password(user, body.password)
    files = database.delete_user(db, user["id"])
    for name in files:
        storage.delete_image(name)
    response.delete_cookie(auth.COOKIE, path="/", secure=config.SECURE_COOKIES, httponly=True, samesite="lax")
