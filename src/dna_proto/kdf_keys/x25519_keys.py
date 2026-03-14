"""Deterministic X25519 keypair derivation from a symmetric key material."""

from __future__ import annotations

from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from dna_proto.kdf_keys.kdf import hkdf_derive

_PRIVATE_KEY_INFO = b"dna-proto-x25519-private-key-v1"
_KEY_SALT_INFO = b"dna-proto-key-salt-v1"


def derive_x25519_keypair(
    key_material: bytes,
    salt: bytes,
) -> tuple[X25519PrivateKey, X25519PublicKey]:
    """Derive a deterministic X25519 keypair from key_material and salt.

    The same (key_material, salt) pair always produces the same keypair.
    key_material is the HKDF-derived key from the fuzzy extractor.

    Returns:
        (private_key, public_key)
    """
    private_seed = hkdf_derive(
        ikm=key_material,
        salt=salt,
        info=_PRIVATE_KEY_INFO,
        length=32,
    )
    private_key = X25519PrivateKey.from_private_bytes(private_seed)
    public_key = private_key.public_key()
    return private_key, public_key


def public_key_to_bytes(public_key: X25519PublicKey) -> bytes:
    """Serialize an X25519 public key to 32 raw bytes."""
    return public_key.public_bytes(encoding=Encoding.Raw, format=PublicFormat.Raw)


def public_key_from_bytes(data: bytes) -> X25519PublicKey:
    """Deserialize 32 raw bytes into an X25519 public key."""
    return X25519PublicKey.from_public_bytes(data)
