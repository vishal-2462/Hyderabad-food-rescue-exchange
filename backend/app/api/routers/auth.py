from __future__ import annotations

from re import sub
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app import models, schemas
from app.auth_store import get_user_store
from app.security import (
    authenticate_user,
    clear_auth_cookie,
    create_access_token,
    get_current_user,
    hash_password,
    set_auth_cookie,
    to_auth_user,
)
from app.store import get_store

router = APIRouter(prefix="/auth", tags=["auth"])


def _display_name_from_email(email: str) -> str:
    local_part = email.split("@", 1)[0]
    cleaned = sub(r"[._-]+", " ", local_part).strip()
    return cleaned.title() or "New Partner"


def _create_profile_for_role(role: models.UserRole, email: str) -> str:
    store = get_store()
    display_name = _display_name_from_email(email)

    if role == models.UserRole.DONOR:
        donor = models.Donor(
            id=store.new_id("donor"),
            name=f"{display_name} Donor",
            phone="Pending setup",
            donor_type="registered_partner",
            reliability=75,
            preferred_radius_km=12,
            location=models.Location(
                area="Hyderabad",
                address="Pending donor address setup",
                city="Hyderabad",
                lat=17.3850,
                lng=78.4867,
            ),
        )
        store.add_donor(donor)
        return donor.id

    ngo = models.NGO(
        id=store.new_id("ngo"),
        name=f"{display_name} NGO",
        contact_name=display_name,
        phone="Pending setup",
        reliability=75,
        max_daily_capacity=120,
        current_load=0,
        focus_areas=["prepared_food"],
        location=models.Location(
            area="Hyderabad",
            address="Pending NGO address setup",
            city="Hyderabad",
            lat=17.3850,
            lng=78.4867,
        ),
    )
    store.add_ngo(ngo)
    return ngo.id


@router.post("/register", response_model=schemas.AuthSession, status_code=status.HTTP_201_CREATED)
def register(payload: schemas.AuthRegisterRequest, response: Response) -> schemas.AuthSession:
    user_store = get_user_store()
    if user_store.get_by_email(payload.email) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with that email already exists")

    profile_id = _create_profile_for_role(payload.role, payload.email)
    user = user_store.create_user(
        email=payload.email,
        password_hash=hash_password(payload.password),
        role=payload.role,
        profile_id=profile_id,
    )
    token = create_access_token(user)
    set_auth_cookie(response, token)
    return schemas.AuthSession(token=token, user=to_auth_user(user))


@router.post("/login", response_model=schemas.AuthSession)
def login(payload: schemas.AuthLoginRequest, response: Response) -> schemas.AuthSession:
    user = authenticate_user(payload.email, payload.password, payload.role)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email, password, or role")

    token = create_access_token(user)
    set_auth_cookie(response, token)
    return schemas.AuthSession(token=token, user=to_auth_user(user))


@router.post("/logout", response_model=schemas.LogoutResponse)
def logout(response: Response) -> schemas.LogoutResponse:
    clear_auth_cookie(response)
    return schemas.LogoutResponse(success=True)


@router.get("/me", response_model=schemas.AuthUser)
def get_me(current_user: Annotated[models.User, Depends(get_current_user)]) -> schemas.AuthUser:
    return to_auth_user(current_user)
