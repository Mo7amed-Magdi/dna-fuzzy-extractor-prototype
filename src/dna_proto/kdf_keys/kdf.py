"""HKDF-SHA256 key derivation function."""

from __future__ import annotations

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF, HKDFExpand


def hkdf_derive(
    ikm: bytes,
    salt: bytes,
    info: bytes,
    length: int = 32,
) -> bytes:
    """Derive key material using HKDF-SHA256.

    Args:
        ikm:    Input key material (e.g. recovered secret from fuzzy extractor).
        salt:   A per-enrollment random salt (non-secret).
        info:   Context/application-specific binding label.
        length: Output length in bytes (default 32).

    Returns:
        Derived key bytes of the requested length.
    """
    return HKDF(
        algorithm=hashes.SHA256(),
        length=length,
        salt=salt,
        info=info,
    ).derive(ikm)


def hkdf_expand(
    prk: bytes,
    info: bytes,
    length: int = 32,
) -> bytes:
    """Expand a pseudo-random key (PRK) to additional key material.

    Useful when the PRK has already been extracted via hkdf_derive.
    """
    return HKDFExpand(
        algorithm=hashes.SHA256(),
        length=length,
        info=info,
    ).derive(prk)
