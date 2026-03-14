"""Tests for the fuzzy extractor (Gen and Rep)."""

from __future__ import annotations

import pytest

from dna_proto.fuzzy_extractor.gen import gen
from dna_proto.fuzzy_extractor.rep import rep
from dna_proto.fuzzy_extractor.secure_sketch import (
    CODEWORD_BYTES,
    SECRET_BYTES,
    rep3_decode,
    rep3_encode,
    sketch_xor,
)
from dna_proto.fuzzing.mutators import mutate_bit_flip


# ---------------------------------------------------------------------------
# Secure sketch (rep-3 code)
# ---------------------------------------------------------------------------

class TestSecureSketch:
    def test_encode_decode_exact(self):
        import os
        for _ in range(5):
            secret = os.urandom(SECRET_BYTES)
            codeword = rep3_encode(secret)
            assert len(codeword) == CODEWORD_BYTES
            recovered = rep3_decode(codeword)
            assert recovered == secret

    def test_encode_wrong_length_raises(self):
        with pytest.raises(ValueError):
            rep3_encode(b"\x00" * 16)

    def test_decode_wrong_length_raises(self):
        with pytest.raises(ValueError):
            rep3_decode(b"\x00" * 32)

    def test_sketch_xor_roundtrip(self):
        import os
        bio = os.urandom(CODEWORD_BYTES)
        codeword = os.urandom(CODEWORD_BYTES)
        sketch = sketch_xor(bio, codeword)
        # XOR is its own inverse
        assert sketch_xor(sketch, codeword) == bio

    def test_single_bit_error_correction(self):
        """Rep-3 code should correct 1 error per 3-bit group."""
        import os
        import random
        rng = random.Random(0)
        secret = os.urandom(SECRET_BYTES)
        codeword = rep3_encode(secret)
        # Flip one bit in each group independently (should still decode correctly)
        noisy = bytearray(codeword)
        for group in range(0, CODEWORD_BYTES * 8, 3):
            # flip only the first bit of each group
            pos = group
            noisy[pos >> 3] ^= 1 << (7 - (pos & 7))
        recovered = rep3_decode(bytes(noisy))
        assert recovered == secret

    def test_two_errors_in_group_causes_failure(self):
        """2 errors out of 3 in the same group should flip the majority."""
        import os
        secret = bytes([0xFF] * SECRET_BYTES)  # all ones
        codeword = rep3_encode(secret)
        # Flip 2 bits in the first group (positions 0 and 1)
        noisy = bytearray(codeword)
        noisy[0] ^= 0b11000000  # flip bits 0 and 1 (MSB side)
        recovered = rep3_decode(bytes(noisy))
        # The first secret bit (bit 0) should be flipped (was 1, now 0)
        assert recovered != secret


# ---------------------------------------------------------------------------
# Gen / Rep integration
# ---------------------------------------------------------------------------

class TestGenRep:
    def test_exact_reconstruction(self, sample_biometric):
        """Rep with the exact enrollment biometric must succeed."""
        _secret, helper = gen(sample_biometric)
        key, priv, success = rep(sample_biometric, helper)
        assert success
        assert key is not None
        assert priv is not None

    def test_deterministic_key(self, sample_biometric):
        """Two Rep calls with identical input must produce the same key."""
        _secret, helper = gen(sample_biometric)
        key1, _, ok1 = rep(sample_biometric, helper)
        key2, _, ok2 = rep(sample_biometric, helper)
        assert ok1 and ok2
        assert key1 == key2

    def test_deterministic_public_key(self, sample_biometric):
        """Two Rep calls must produce the same X25519 public key."""
        from dna_proto.kdf_keys.x25519_keys import public_key_to_bytes
        _secret, helper = gen(sample_biometric)
        _, priv1, ok1 = rep(sample_biometric, helper)
        _, priv2, ok2 = rep(sample_biometric, helper)
        assert ok1 and ok2
        pk1 = public_key_to_bytes(priv1.public_key())
        pk2 = public_key_to_bytes(priv2.public_key())
        assert pk1 == pk2

    def test_small_mutation_succeeds(self, sample_biometric):
        """A biometric with a few bit flips should still reconstruct (within capacity)."""
        import random
        _secret, helper = gen(sample_biometric)
        # Flip 1 bit per 3-bit group = maximum correctable without exceeding threshold
        rng = random.Random(42)
        noisy = mutate_bit_flip(sample_biometric, n_flips=10, rng=rng)
        _key, _priv, success = rep(noisy, helper)
        # With only 10 bit flips spread across 768 bits (avg < 1 per group), should succeed
        assert success

    def test_heavy_mutation_fails(self, sample_biometric):
        """A heavily mutated biometric should fail reconstruction."""
        import random
        _secret, helper = gen(sample_biometric)
        # Flip ~40% of bits: well beyond rep-3 correction capacity
        rng = random.Random(1)
        noisy = mutate_bit_flip(sample_biometric, n_flips=300, rng=rng)
        _key, _priv, success = rep(noisy, helper)
        assert not success

    def test_wrong_biometric_fails(self, markers_and_profiles):
        """An entirely different biometric must not reconstruct."""
        from dna_proto.dna_input.schema import validate_profile
        from dna_proto.preprocess.vectorize import vectorize
        _, profiles = markers_and_profiles
        bio0 = vectorize(validate_profile(profiles[0]))
        bio1 = vectorize(validate_profile(profiles[1]))
        _secret, helper = gen(bio0)
        _key, _priv, success = rep(bio1, helper)
        assert not success

    def test_helper_data_has_required_keys(self, sample_biometric):
        _secret, helper = gen(sample_biometric)
        for key in ("sketch", "salt", "verifier", "public_key", "key_salt"):
            assert key in helper

    def test_helper_public_key_matches_rep(self, sample_biometric):
        """Public key in helper_data must match the one reconstructed by Rep."""
        from dna_proto.kdf_keys.x25519_keys import public_key_to_bytes
        _secret, helper = gen(sample_biometric)
        _, priv, success = rep(sample_biometric, helper)
        assert success
        rep_pub = public_key_to_bytes(priv.public_key())
        assert rep_pub.hex() == helper["public_key"]
