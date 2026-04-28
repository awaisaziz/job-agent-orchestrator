"""Credential generation, validation, and redaction helpers."""

from __future__ import annotations

import re
import secrets
import string
from dataclasses import dataclass

_USERNAME_ALPHABET = string.ascii_lowercase + string.digits
_PASSWORD_ALPHABET = string.ascii_letters + string.digits + "!@#$%^&*()-_=+[]{}:,.?"
_REFERENCE_PREFIXES = ("arn:", "sm://", "vault://", "gcp-sm://", "azure-kv://")
_ENCRYPTED_PREFIXES = ("enc:", "kms:", "age:", "sealed:")


@dataclass(slots=True)
class CredentialMaterial:
    """Generated username + password pair."""

    username: str
    password: str


@dataclass(slots=True)
class CredentialPolicyResult:
    """Password policy evaluation details."""

    valid: bool
    violations: list[str]


def generate_strong_username(prefix: str = "acct", random_length: int = 12) -> str:
    """Generate a random username suitable for throwaway application accounts."""

    suffix = "".join(secrets.choice(_USERNAME_ALPHABET) for _ in range(random_length))
    return f"{prefix}_{suffix}"


def generate_strong_password(length: int = 24) -> str:
    """Generate a strong password guaranteed to satisfy complexity requirements."""

    if length < 16:
        raise ValueError("Password length must be at least 16 characters")

    required = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
        secrets.choice("!@#$%^&*()-_=+[]{}:,.?"),
    ]
    remaining = [secrets.choice(_PASSWORD_ALPHABET) for _ in range(length - len(required))]
    chars = required + remaining
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


def generate_credential_material(prefix: str = "acct") -> CredentialMaterial:
    """Generate a username/password pair that meets baseline policy checks."""

    username = generate_strong_username(prefix=prefix)
    password = generate_strong_password()
    return CredentialMaterial(username=username, password=password)


def check_password_policy(password: str, minimum_length: int = 16) -> CredentialPolicyResult:
    """Validate password complexity requirements."""

    violations: list[str] = []
    if len(password) < minimum_length:
        violations.append(f"Password must be at least {minimum_length} characters long")
    if not re.search(r"[a-z]", password):
        violations.append("Password must include at least one lowercase character")
    if not re.search(r"[A-Z]", password):
        violations.append("Password must include at least one uppercase character")
    if not re.search(r"\d", password):
        violations.append("Password must include at least one numeric character")
    if not re.search(r"[^A-Za-z0-9]", password):
        violations.append("Password must include at least one special character")

    return CredentialPolicyResult(valid=not violations, violations=violations)


def is_secret_reference_or_encrypted(secret_value: str) -> bool:
    """Return true when the secret appears to be a manager reference or encrypted blob."""

    normalized = secret_value.strip().lower()
    return normalized.startswith(_REFERENCE_PREFIXES) or normalized.startswith(_ENCRYPTED_PREFIXES)


def assert_secret_is_safe_for_storage(secret_value: str) -> None:
    """Reject plaintext secret persistence for DB/log safety."""

    if not is_secret_reference_or_encrypted(secret_value):
        raise ValueError("Secret storage requires encrypted data or a secret-manager reference")


def redact_sensitive_values(message: str, sensitive_values: list[str | None]) -> str:
    """Redact known sensitive fields from log messages."""

    redacted = message
    for value in sensitive_values:
        if value:
            redacted = redacted.replace(value, "[REDACTED]")
    return redacted
