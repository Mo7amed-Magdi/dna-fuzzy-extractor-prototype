"""Deterministic X25519 keypair generation from key material.

The biometric key material (32 bytes) is expanded via HKDF to produce a
deterministic X25519 private key seed.  Identical DNA inputs → identical
private key → identical public key, without storing either.

Note: X25519 private keys require the low-order bits clamped per RFC 7748.
The ``cryptography`` library performs clamping automatically when loading from
raw bytes, so we just supply the 32-byte seed.
"""

from __future__ import annotations

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey

from .kdf import hkdf_derive


def derive_x25519_keypair(
    key_material: bytes,
    salt: bytes,
) -> tuple[X25519PrivateKey, X25519PublicKey]:
    """Derive a deterministic X25519 keypair from biometric key material.

    Parameters
    ----------
    key_material:
        32 bytes returned by Gen/Rep (HKDF output from the secret seed).
    salt:
        The same salt stored in the enrollment artifact (domain separation).

    Returns
    -------
    ``(private_key, public_key)`` – both are
    ``cryptography.hazmat.primitives.asymmetric.x25519`` objects.
    """
    # Second HKDF pass for keypair derivation (domain separation from the key)
    seed = hkdf_derive(
        key_material,
        salt,
        info=b"dna-proto-x25519",
        length=32,
    )
    private_key = X25519PrivateKey.from_private_bytes(seed)
    public_key = private_key.public_key()
    return private_key, public_key


def public_key_bytes(pub: X25519PublicKey) -> bytes:
    """Return the raw 32-byte representation of an X25519 public key."""
    from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

    return pub.public_bytes(Encoding.Raw, PublicFormat.Raw)


def private_key_bytes(priv: X25519PrivateKey) -> bytes:
    """Return the raw 32-byte representation of an X25519 private key."""
    from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption

    return priv.private_bytes(Encoding.Raw, PrivateFormat.Raw, NoEncryption())
