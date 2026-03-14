"""Fuzzy extractor Gen() – enrollment."""

from __future__ import annotations

import os

from dna_proto.fuzzy_extractor.secure_sketch import (
    CODEWORD_BYTES,
    rep3_encode,
    sketch_xor,
)
from dna_proto.kdf_keys.kdf import hkdf_derive
from dna_proto.kdf_keys.x25519_keys import derive_x25519_keypair, public_key_to_bytes

_KEY_LABEL = b"dna-proto-main-key-v1"
_VERIFY_LABEL = b"dna-proto-verifier-v1"
_KEY_PAIR_SALT_LABEL = b"dna-proto-keypair-salt-v1"


def gen(biometric: bytes) -> tuple[bytes, dict]:
    """Enroll a biometric and return (secret, helper_data).

    Args:
        biometric: 96-byte biometric vector from vectorize().

    Returns:
        secret:      32-byte uniformly random secret (do NOT store).
        helper_data: dict containing sketch, salt, verifier, public_key, key_salt.
                     This dict is safe to store; it does not contain the secret or
                     raw biometric.

    Algorithm (Option B secure-sketch simulation):
        1. Generate random 32-byte secret `s`.
        2. Encode to 768-bit codeword via rate-1/3 repetition code.
        3. Compute sketch = biometric XOR codeword.
        4. Derive main key R = HKDF(s, salt, key_label).
        5. Derive verifier tag = HKDF(R, salt, verify_label)[:16].
        6. Derive deterministic X25519 keypair from R.
        7. Return (s, {sketch, salt, verifier, public_key, key_salt}).
    """
    if len(biometric) != CODEWORD_BYTES:
        raise ValueError(
            f"Biometric must be {CODEWORD_BYTES} bytes, got {len(biometric)}"
        )

    # Step 1: random secret
    secret = os.urandom(32)

    # Step 2: encode secret → codeword
    codeword = rep3_encode(secret)

    # Step 3: helper data (sketch)
    sketch = sketch_xor(biometric, codeword)

    # Step 4–5: derive key and verifier
    salt = os.urandom(16)
    key = hkdf_derive(secret, salt, _KEY_LABEL)
    verifier = hkdf_derive(key, salt, _VERIFY_LABEL, length=16)

    # Step 6: deterministic X25519 keypair
    key_salt = os.urandom(16)
    _priv, pub = derive_x25519_keypair(key, key_salt)
    public_key_bytes = public_key_to_bytes(pub)

    helper_data = {
        "sketch": sketch.hex(),
        "salt": salt.hex(),
        "verifier": verifier.hex(),
        "public_key": public_key_bytes.hex(),
        "key_salt": key_salt.hex(),
        "params": {
            "rep_factor": 3,
            "secret_bits": 256,
            "biometric_bits": 768,
        },
    }
    return secret, helper_data
