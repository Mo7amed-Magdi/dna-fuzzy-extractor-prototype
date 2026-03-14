"""Fuzzy extractor Rep() – reconstruction."""

from __future__ import annotations

from dna_proto.fuzzy_extractor.secure_sketch import (
    CODEWORD_BYTES,
    rep3_decode,
    sketch_xor,
)
from dna_proto.kdf_keys.kdf import hkdf_derive
from dna_proto.kdf_keys.x25519_keys import (
    X25519PrivateKey,
    derive_x25519_keypair,
    public_key_to_bytes,
)

_KEY_LABEL = b"dna-proto-main-key-v1"
_VERIFY_LABEL = b"dna-proto-verifier-v1"


def rep(
    biometric_new: bytes,
    helper_data: dict,
) -> tuple[bytes | None, X25519PrivateKey | None, bool]:
    """Attempt to reconstruct the secret from a new biometric measurement.

    Args:
        biometric_new: 96-byte biometric vector from a fresh DNA sample.
        helper_data:   dict produced by gen() at enrollment time.

    Returns:
        (key, private_key, success):
          - key:         32-byte reconstructed HKDF key (or None on failure).
          - private_key: reconstructed X25519 private key (or None on failure).
          - success:     True if reconstruction verified successfully.

    Algorithm:
        1. Recover noisy codeword = new_biometric XOR sketch.
        2. Majority-vote decode to candidate secret s'.
        3. Re-derive key R' = HKDF(s', salt, key_label).
        4. Re-derive verifier' = HKDF(R', salt, verify_label)[:16].
        5. Compare verifier' against stored verifier (constant-time).
        6. If match: reconstruct X25519 keypair and return (R', private_key, True).
           Else: return (None, None, False).
    """
    if len(biometric_new) != CODEWORD_BYTES:
        raise ValueError(
            f"Biometric must be {CODEWORD_BYTES} bytes, got {len(biometric_new)}"
        )

    sketch = bytes.fromhex(helper_data["sketch"])
    salt = bytes.fromhex(helper_data["salt"])
    stored_verifier = bytes.fromhex(helper_data["verifier"])
    key_salt = bytes.fromhex(helper_data["key_salt"])

    # Step 1: recover noisy codeword
    noisy_codeword = sketch_xor(biometric_new, sketch)

    # Step 2: majority-vote decode → candidate secret
    candidate_secret = rep3_decode(noisy_codeword)

    # Step 3–4: re-derive key and verifier
    candidate_key = hkdf_derive(candidate_secret, salt, _KEY_LABEL)
    candidate_verifier = hkdf_derive(candidate_key, salt, _VERIFY_LABEL, length=16)

    # Step 5: constant-time comparison
    import hmac
    if not hmac.compare_digest(candidate_verifier, stored_verifier):
        return None, None, False

    # Step 6: reconstruct keypair
    private_key, _pub = derive_x25519_keypair(candidate_key, key_salt)
    return candidate_key, private_key, True
