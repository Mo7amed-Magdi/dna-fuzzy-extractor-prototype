"""HKDF-SHA256 key derivation."""

from __future__ import annotations

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


def hkdf_derive(
    ikm: bytes,
    salt: bytes,
    *,
    info: bytes = b"",
    length: int = 32,
) -> bytes:
    """Derive ``length`` bytes from input keying material using HKDF-SHA256.

    Parameters
    ----------
    ikm:
        Input keying material (e.g. reconstructed secret seed).
    salt:
        Non-secret random salt stored in enrollment artifacts.
    info:
        Context label to produce domain-separated outputs.
    length:
        Number of output bytes (default 32).

    Returns
    -------
    Derived key bytes.
    """
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=length,
        salt=salt,
        info=info,
    )
    return hkdf.derive(ikm)
