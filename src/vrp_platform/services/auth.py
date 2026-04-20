"""Single-tenant auth and RBAC."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from vrp_platform.domain.enums import Role


@dataclass(slots=True)
class UserContext:
    username: str
    role: Role


class AuthService:
    """Minimal RBAC for single-tenant deployments."""

    def __init__(self) -> None:
        self._users = {
            "dispatcher": (self._hash_password("dispatcher123"), Role.DISPATCHER),
            "customer": (self._hash_password("customer123"), Role.CUSTOMER),
            "driver": (self._hash_password("driver123"), Role.DRIVER),
            "admin": (self._hash_password("admin123"), Role.ADMIN),
        }

    def login(self, username: str, password: str) -> UserContext:
        if username not in self._users:
            raise ValueError("Unknown user")
        password_hash, role = self._users[username]
        if password_hash != self._hash_password(password):
            raise ValueError("Invalid password")
        return UserContext(username=username, role=role)

    def require_role(self, user: UserContext, allowed: set[Role]) -> None:
        if user.role not in allowed:
            raise PermissionError(f"{user.role} cannot access this action")

    def _hash_password(self, password: str) -> str:
        return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), b"vrp-platform", 120000).hex()

