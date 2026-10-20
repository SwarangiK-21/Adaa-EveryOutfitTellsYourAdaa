"""Sign up, log in, log out, and your account details."""
import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response

import auth
import database
from schemas import AccountFields, LoginIn, SignupIn, UserOut, user_out

router = APIRouter(prefix="/api/auth", tags=["account"])
Db = Annotated[sqlite3.Connection, Depends(database.get_db)]


@router.post("/signup", response_model=UserOut, status_code=201)
def signup(body: SignupIn, db: Db, response: Response):
    """Create an account and sign in. The very first account also receives the wardrobe made
    before accounts existed."""
    if database.find_user_by_email(db, body.email):
        raise HTTPException(status_code=409, detail="An account with this email already exists. Please log in.")
    first = db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0
    user = database.create_user(db, body.name, body.email, body.phone, auth.hash_password(body.password))
    moved = database.claim_unowned(db, user["id"]) if first else 0
    auth.start_session(db, response, user["id"])
    return user_out(user, moved)


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
