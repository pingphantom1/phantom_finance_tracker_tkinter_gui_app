"""
auth/auth.py
Password hashing and verification using stdlib hashlib + secrets.
Uses PBKDF2-HMAC-SHA256 with a per-user salt — no external dependencies.
"""

import hashlib
import secrets

# Number of PBKDF2 iterations (NIST recommends >= 310,000 for SHA-256 as of 2023)
_ITERATIONS = 390_000
_HASH_ALG = "sha256"
_SALT_BYTES = 32  # 256-bit salt


def hash_password(password: str) -> str:
    """
    Hash a plaintext password and return a storable string in the format:
        <hex_salt>$<hex_hash>
    """
    salt = secrets.token_bytes(_SALT_BYTES)
    key = hashlib.pbkdf2_hmac(
        _HASH_ALG,
        password.encode("utf-8"),
        salt,
        _ITERATIONS,
    )
    return f"{salt.hex()}${key.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """
    Verify a plaintext password against a stored hash string produced by
    hash_password(). Returns True if they match, False otherwise.
    Uses a constant-time comparison to prevent timing attacks.
    """
    try:
        salt_hex, key_hex = stored_hash.split("$", 1)
    except ValueError:
        return False

    salt = bytes.fromhex(salt_hex)
    expected_key = bytes.fromhex(key_hex)

    candidate_key = hashlib.pbkdf2_hmac(
        _HASH_ALG,
        password.encode("utf-8"),
        salt,
        _ITERATIONS,
    )
    return secrets.compare_digest(candidate_key, expected_key)
