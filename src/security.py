from __future__ import annotations

import base64
import hashlib
import hmac
import os

PBKDF2_ALGORITHM = "sha256"
PBKDF2_ITERATIONS = 600_000
SALT_BYTES = 16
DKLEN = 32


def _b64e(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64d(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def hash_password(password: str) -> str:
    """Return a password hash using only Python's standard library.

    Format:
    pbkdf2_sha256$iterations$salt_b64$hash_b64
    """
    if not isinstance(password, str) or not password:
        raise ValueError("Senha inválida.")
    salt = os.urandom(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac(
        PBKDF2_ALGORITHM,
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
        dklen=DKLEN,
    )
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${_b64e(salt)}${_b64e(digest)}"


def verify_password(stored_hash: str, password: str) -> bool:
    if not stored_hash or not isinstance(stored_hash, str):
        return False

    # Backward-compatible placeholder for older Argon2 hashes. The new build no
    # longer depends on argon2-cffi to avoid installation issues on Windows.
    if stored_hash.startswith("$argon2"):
        try:
            from argon2 import PasswordHasher  # type: ignore
            from argon2.exceptions import VerificationError, VerifyMismatchError  # type: ignore

            try:
                PasswordHasher().verify(stored_hash, password or "")
                return True
            except (VerificationError, VerifyMismatchError):
                return False
        except Exception:
            raise RuntimeError(
                "Este usuário foi criado com hash Argon2, mas o pacote argon2-cffi não está instalado. "
                "Crie um novo usuário nesta versão ou instale argon2-cffi temporariamente."
            )

    try:
        scheme, iterations_s, salt_b64, expected_b64 = stored_hash.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        iterations = int(iterations_s)
        salt = _b64d(salt_b64)
        expected = _b64d(expected_b64)
        actual = hashlib.pbkdf2_hmac(
            PBKDF2_ALGORITHM,
            (password or "").encode("utf-8"),
            salt,
            iterations,
            dklen=len(expected),
        )
        return hmac.compare_digest(actual, expected)
    except Exception:
        return False


def needs_rehash(stored_hash: str) -> bool:
    try:
        scheme, iterations_s, *_ = stored_hash.split("$", 3)
        return scheme != "pbkdf2_sha256" or int(iterations_s) < PBKDF2_ITERATIONS
    except Exception:
        return True
