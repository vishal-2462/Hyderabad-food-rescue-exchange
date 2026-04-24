from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from app import models


class UserStore:
    def __init__(self, users: list[models.User] | None = None) -> None:
        self.users: dict[str, models.User] = {}
        self.users_by_email: dict[str, models.User] = {}
        for user in users or []:
            self.add_user(user)

    def add_user(self, user: models.User) -> models.User:
        normalized_email = user.email.strip().lower()
        user.email = normalized_email
        self.users[user.id] = user
        self.users_by_email[normalized_email] = user
        return user

    def get_by_email(self, email: str) -> models.User | None:
        return self.users_by_email.get(email.strip().lower())

    def get_by_id(self, user_id: str) -> models.User | None:
        return self.users.get(user_id)

    def create_user(self, *, email: str, password_hash: str, role: models.UserRole, profile_id: str | None) -> models.User:
        user = models.User(
            id=f"user-{uuid4().hex[:8]}",
            email=email.strip().lower(),
            password_hash=password_hash,
            role=role,
            profile_id=profile_id,
            created_at=datetime.now(timezone.utc),
        )
        return self.add_user(user)

    def seed_demo_users(self) -> None:
        if self.users:
            return

        from app.security import hash_password

        self.create_user(
            email="donor@example.com",
            password_hash=hash_password("password123"),
            role=models.UserRole.DONOR,
            profile_id="donor-ameerpet-kitchen",
        )
        self.create_user(
            email="ngo@example.com",
            password_hash=hash_password("password123"),
            role=models.UserRole.NGO,
            profile_id="ngo-seva-meals",
        )


_user_store: UserStore | None = None


def get_user_store() -> UserStore:
    global _user_store
    if _user_store is None:
        _user_store = UserStore()
        _user_store.seed_demo_users()
    return _user_store
