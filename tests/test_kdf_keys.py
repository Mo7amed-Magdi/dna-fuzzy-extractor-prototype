"""Tests for KDF and X25519 key derivation."""

from __future__ import annotations

import pytest


class TestHKDF:
    def test_deterministic(self):
        from dna_proto.kdf_keys import hkdf_derive
        ikm = b"\x01" * 32
        salt = b"\x02" * 32
        k1 = hkdf_derive(ikm, salt, info=b"test")
        k2 = hkdf_derive(ikm, salt, info=b"test")
        assert k1 == k2

    def test_different_info_different_output(self):
        from dna_proto.kdf_keys import hkdf_derive
        ikm = b"\x01" * 32
        salt = b"\x02" * 32
        k1 = hkdf_derive(ikm, salt, info=b"domain-a")
        k2 = hkdf_derive(ikm, salt, info=b"domain-b")
        assert k1 != k2

    def test_length(self):
        from dna_proto.kdf_keys import hkdf_derive
        for length in (16, 32, 64):
            k = hkdf_derive(b"ikm", b"salt", length=length)
            assert len(k) == length


class TestX25519:
    def test_derive_keypair_deterministic(self, enrollment_001):
        from dna_proto.kdf_keys import derive_x25519_keypair, public_key_bytes
        key_material, enrollment = enrollment_001
        salt = bytes.fromhex(enrollment["salt"])
        priv1, pub1 = derive_x25519_keypair(key_material, salt)
        priv2, pub2 = derive_x25519_keypair(key_material, salt)
        assert public_key_bytes(pub1) == public_key_bytes(pub2)

    def test_different_key_material_different_keypair(self, enrollment_001):
        from dna_proto.kdf_keys import derive_x25519_keypair, public_key_bytes
        key_material, enrollment = enrollment_001
        salt = bytes.fromhex(enrollment["salt"])
        _, pub1 = derive_x25519_keypair(key_material, salt)
        _, pub2 = derive_x25519_keypair(b"\x00" * 32, salt)
        assert public_key_bytes(pub1) != public_key_bytes(pub2)

    def test_keypair_length(self, enrollment_001):
        from dna_proto.kdf_keys import derive_x25519_keypair, public_key_bytes, private_key_bytes
        key_material, enrollment = enrollment_001
        salt = bytes.fromhex(enrollment["salt"])
        priv, pub = derive_x25519_keypair(key_material, salt)
        assert len(public_key_bytes(pub)) == 32
        assert len(private_key_bytes(priv)) == 32
