"""Token encryption helpers for secure OAuth credential storage."""

from __future__ import annotations

import base64

from cryptography.fernet import Fernet, InvalidToken


class TokenCipher:
    """Symmetric token envelope encryption using Fernet."""

    def __init__(self, key: str) -> None:
        self._fernet = Fernet(self._normalize_key(key))

    @staticmethod
    def _normalize_key(key: str) -> bytes:
        raw = key.encode("utf-8")
        try:
            Fernet(raw)
            return raw
        except Exception:
            return base64.urlsafe_b64encode(raw.ljust(32, b"0")[:32])

    def encrypt(self, value: str) -> bytes:
        return self._fernet.encrypt(value.encode("utf-8"))

    def decrypt(self, value: bytes) -> str:
        try:
            return self._fernet.decrypt(value).decode("utf-8")
        except InvalidToken as exc:
            raise ValueError("Invalid encrypted token payload") from exc
