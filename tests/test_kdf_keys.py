"""Tests for KDF and X25519 key derivation."""

from __future__ import annotations

import os

import pytest

from dna_proto.kdf_keys.kdf import hkdf_derive, hkdf_expand
from dna_proto.kdf_keys.x25519_keys import (
    derive_x25519_keypair,
    public_key_from_bytes,
    public_key_to_bytes,
)


class TestHKDF:
    def test_output_length_default(self):
        out = hkdf_derive(b"secret", b"salt", b"info")
        assert len(out) == 32

    def test_output_length_custom(self):
        out = hkdf_derive(b"secret", b"salt", b"info", length=64)
        assert len(out) == 64

    def test_deterministic(self):
        k1 = hkdf_derive(b"ikm", b"salt", b"info")
        k2 = hkdf_derive(b"ikm", b"salt", b"info")
        assert k1 == k2

    def test_different_salt_gives_different_output(self):
        k1 = hkdf_derive(b"ikm", b"salt1", b"info")
        k2 = hkdf_derive(b"ikm", b"salt2", b"info")
        assert k1 != k2

    def test_different_ikm_gives_different_output(self):
        k1 = hkdf_derive(b"ikm1", b"salt", b"info")
        k2 = hkdf_derive(b"ikm2", b"salt", b"info")
        assert k1 != k2

    def test_different_info_gives_different_output(self):
        k1 = hkdf_derive(b"ikm", b"salt", b"info1")
        k2 = hkdf_derive(b"ikm", b"salt", b"info2")
        assert k1 != k2

    def test_expand_deterministic(self):
        prk = hkdf_derive(b"ikm", b"salt", b"extract")
        e1 = hkdf_expand(prk, b"label", length=32)
        e2 = hkdf_expand(prk, b"label", length=32)
        assert e1 == e2


class TestX25519Keys:
    def test_keypair_deterministic(self):
        km = os.urandom(32)
        salt = os.urandom(16)
        priv1, pub1 = derive_x25519_keypair(km, salt)
        priv2, pub2 = derive_x25519_keypair(km, salt)
        assert public_key_to_bytes(pub1) == public_key_to_bytes(pub2)

    def test_keypair_different_km(self):
        km1 = os.urandom(32)
        km2 = os.urandom(32)
        salt = os.urandom(16)
        _, pub1 = derive_x25519_keypair(km1, salt)
        _, pub2 = derive_x25519_keypair(km2, salt)
        assert public_key_to_bytes(pub1) != public_key_to_bytes(pub2)

    def test_public_key_roundtrip(self):
        km = os.urandom(32)
        salt = os.urandom(16)
        _, pub = derive_x25519_keypair(km, salt)
        pub_bytes = public_key_to_bytes(pub)
        assert len(pub_bytes) == 32
        pub_restored = public_key_from_bytes(pub_bytes)
        assert public_key_to_bytes(pub_restored) == pub_bytes

    def test_dh_exchange_works(self):
        """Verify that DH between two keypairs produces the same shared secret."""
        km_a = os.urandom(32)
        km_b = os.urandom(32)
        salt = os.urandom(16)
        priv_a, pub_a = derive_x25519_keypair(km_a, salt)
        priv_b, pub_b = derive_x25519_keypair(km_b, salt)
        shared_ab = priv_a.exchange(pub_b)
        shared_ba = priv_b.exchange(pub_a)
        assert shared_ab == shared_ba
