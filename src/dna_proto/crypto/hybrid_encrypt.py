"""Hybrid encryption: ephemeral X25519 DH + ChaCha20-Poly1305 AEAD.

Encryption:
    1. Caller reconstructs recipient X25519 public key from enrollment helper data.
    2. Generate ephemeral X25519 keypair.
    3. Perform DH: shared_secret = ephemeral_private × recipient_public.
    4. Derive AEAD key: k = HKDF(shared_secret, nonce, info="dna-proto-aead-v1").
    5. Encrypt plaintext with ChaCha20-Poly1305.
    6. Return: {ephemeral_public_hex, nonce_hex, ciphertext_hex, aad_hex}.

Decryption:
    1. Reconstruct recipient private key via Rep().
    2. Recover shared_secret = recipient_private × ephemeral_public.
    3. Re-derive AEAD key.
    4. Decrypt with ChaCha20-Poly1305 and verify authentication tag.
"""

from __future__ import annotations

import os

from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

from dna_proto.kdf_keys.kdf import hkdf_derive
from dna_proto.kdf_keys.x25519_keys import public_key_from_bytes, public_key_to_bytes

_AEAD_INFO = b"dna-proto-aead-v1"
_NONCE_BYTES = 12


def encrypt(
    recipient_public_key: X25519PublicKey,
    plaintext: bytes,
    aad: bytes = b"",
) -> dict:
    """Encrypt plaintext for a recipient identified by their X25519 public key.

    Returns a dict with all fields needed for decryption.
    """
    ephemeral_private = X25519PrivateKey.generate()
    ephemeral_public = ephemeral_private.public_key()

    shared_secret = ephemeral_private.exchange(recipient_public_key)

    nonce = os.urandom(_NONCE_BYTES)
    aead_key = hkdf_derive(shared_secret, nonce, _AEAD_INFO, length=32)

    chacha = ChaCha20Poly1305(aead_key)
    ciphertext = chacha.encrypt(nonce, plaintext, aad or None)

    return {
        "ephemeral_public": public_key_to_bytes(ephemeral_public).hex(),
        "nonce": nonce.hex(),
        "ciphertext": ciphertext.hex(),
        "aad": aad.hex(),
    }


def decrypt(
    recipient_private_key: X25519PrivateKey,
    packet: dict,
) -> bytes:
    """Decrypt a packet produced by encrypt().

    Raises cryptography.exceptions.InvalidTag if authentication fails.
    """
    ephemeral_public = public_key_from_bytes(bytes.fromhex(packet["ephemeral_public"]))
    nonce = bytes.fromhex(packet["nonce"])
    ciphertext = bytes.fromhex(packet["ciphertext"])
    aad_bytes = bytes.fromhex(packet["aad"]) or None

    shared_secret = recipient_private_key.exchange(ephemeral_public)

    aead_key = hkdf_derive(shared_secret, nonce, _AEAD_INFO, length=32)

    chacha = ChaCha20Poly1305(aead_key)
    return chacha.decrypt(nonce, ciphertext, aad_bytes)
