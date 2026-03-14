"""Hybrid encryption: ephemeral X25519 key agreement + ChaCha20-Poly1305.

Encrypt / decrypt arbitrary byte payloads using the recipient's X25519
public key.  The sender generates an ephemeral keypair; the shared secret is
derived via ECDH → HKDF-SHA256 → ChaCha20-Poly1305 AEAD.

Wire format (all fields concatenated, no external framing needed):
    [4 bytes: magic "DNAP"] [1 byte: version=1]
    [32 bytes: ephemeral_pub]
    [12 bytes: nonce]
    [N bytes: ciphertext + 16-byte Poly1305 tag]

Security properties:
- Forward secrecy via ephemeral sender key.
- Authenticated encryption (AEAD) prevents ciphertext tampering.
- Decryption requires reconstructing the same X25519 private key from DNA.
"""

from __future__ import annotations

import os
import struct

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey, X25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from ..kdf_keys.kdf import hkdf_derive

_MAGIC = b"DNAP"
_VERSION = 1
_HEADER = _MAGIC + bytes([_VERSION])  # 5 bytes


def encrypt(
    plaintext: bytes,
    recipient_pub: X25519PublicKey,
    *,
    associated_data: bytes = b"",
) -> bytes:
    """Encrypt ``plaintext`` for ``recipient_pub``.

    Parameters
    ----------
    plaintext:
        Arbitrary bytes to encrypt.
    recipient_pub:
        Recipient's X25519 public key (derived from DNA enrollment).
    associated_data:
        Optional additional data bound to the ciphertext (not encrypted).

    Returns
    -------
    Serialised ciphertext blob (see wire format above).
    """
    # Ephemeral sender keypair
    eph_priv = X25519PrivateKey.generate()
    eph_pub = eph_priv.public_key()
    eph_pub_bytes = eph_pub.public_bytes(Encoding.Raw, PublicFormat.Raw)

    # ECDH shared secret
    shared_secret = eph_priv.exchange(recipient_pub)

    # Derive AEAD key via HKDF
    aead_key = hkdf_derive(
        shared_secret,
        eph_pub_bytes,
        info=b"dna-proto-aead-chacha20",
        length=32,
    )

    # Encrypt
    nonce = os.urandom(12)
    chacha = ChaCha20Poly1305(aead_key)
    ciphertext = chacha.encrypt(nonce, plaintext, associated_data or None)

    return _HEADER + eph_pub_bytes + nonce + ciphertext


def decrypt(
    blob: bytes,
    recipient_priv: X25519PrivateKey,
    *,
    associated_data: bytes = b"",
) -> bytes:
    """Decrypt a ciphertext blob produced by ``encrypt``.

    Parameters
    ----------
    blob:
        Ciphertext blob as produced by ``encrypt``.
    recipient_priv:
        Recipient's X25519 private key (reconstructed from DNA via Rep).
    associated_data:
        Must match the value used during encryption.

    Returns
    -------
    Original plaintext bytes.

    Raises
    ------
    ValueError
        If the blob header is invalid.
    cryptography.exceptions.InvalidTag
        If AEAD authentication fails (wrong key or tampered ciphertext).
    """
    header_len = len(_HEADER)
    if len(blob) < header_len + 32 + 12 + 16:
        raise ValueError("Ciphertext blob is too short to be valid.")
    if blob[:header_len] != _HEADER:
        raise ValueError(
            f"Invalid magic/version header. Expected {_HEADER!r}, got {blob[:header_len]!r}."
        )

    offset = header_len
    eph_pub_bytes = blob[offset : offset + 32]
    offset += 32
    nonce = blob[offset : offset + 12]
    offset += 12
    ciphertext = blob[offset:]

    # Reconstruct ephemeral public key
    eph_pub = X25519PublicKey.from_public_bytes(eph_pub_bytes)

    # ECDH
    shared_secret = recipient_priv.exchange(eph_pub)

    # Re-derive AEAD key
    aead_key = hkdf_derive(
        shared_secret,
        eph_pub_bytes,
        info=b"dna-proto-aead-chacha20",
        length=32,
    )

    chacha = ChaCha20Poly1305(aead_key)
    return chacha.decrypt(nonce, ciphertext, associated_data or None)
