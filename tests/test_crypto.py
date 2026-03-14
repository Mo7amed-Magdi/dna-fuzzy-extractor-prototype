"""Tests for hybrid encryption (X25519 DH + ChaCha20-Poly1305)."""

from __future__ import annotations

import os

import pytest
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

from dna_proto.crypto.hybrid_encrypt import decrypt, encrypt
from dna_proto.kdf_keys.x25519_keys import derive_x25519_keypair, public_key_to_bytes


@pytest.fixture
def keypair():
    km = os.urandom(32)
    salt = os.urandom(16)
    return derive_x25519_keypair(km, salt)


class TestHybridEncrypt:
    def test_encrypt_decrypt_roundtrip(self, keypair):
        priv, pub = keypair
        plaintext = b"hello, DNA world!"
        packet = encrypt(pub, plaintext)
        recovered = decrypt(priv, packet)
        assert recovered == plaintext

    def test_encrypt_with_aad(self, keypair):
        priv, pub = keypair
        plaintext = b"sensitive record"
        aad = b"patient_id:12345"
        packet = encrypt(pub, plaintext, aad=aad)
        recovered = decrypt(priv, packet)
        assert recovered == plaintext

    def test_wrong_private_key_raises(self, keypair):
        _, pub = keypair
        wrong_priv, _ = derive_x25519_keypair(os.urandom(32), os.urandom(16))
        plaintext = b"test"
        packet = encrypt(pub, plaintext)
        with pytest.raises(InvalidTag):
            decrypt(wrong_priv, packet)

    def test_tampered_ciphertext_raises(self, keypair):
        priv, pub = keypair
        plaintext = b"test message"
        packet = encrypt(pub, plaintext)
        # Tamper with ciphertext
        ct = bytearray(bytes.fromhex(packet["ciphertext"]))
        ct[0] ^= 0xFF
        packet["ciphertext"] = bytes(ct).hex()
        with pytest.raises(InvalidTag):
            decrypt(priv, packet)

    def test_each_encrypt_produces_unique_ciphertext(self, keypair):
        _, pub = keypair
        plaintext = b"same message"
        p1 = encrypt(pub, plaintext)
        p2 = encrypt(pub, plaintext)
        # Each call uses a fresh ephemeral key + nonce
        assert p1["ciphertext"] != p2["ciphertext"]
        assert p1["ephemeral_public"] != p2["ephemeral_public"]

    def test_large_plaintext(self, keypair):
        priv, pub = keypair
        plaintext = os.urandom(64 * 1024)  # 64 KB
        packet = encrypt(pub, plaintext)
        recovered = decrypt(priv, packet)
        assert recovered == plaintext

    def test_encrypt_decrypt_with_dna_derived_keys(self, sample_biometric):
        """Full pipeline: enroll → encrypt → reconstruct → decrypt."""
        from dna_proto.fuzzy_extractor.gen import gen
        from dna_proto.fuzzy_extractor.rep import rep
        from dna_proto.kdf_keys.x25519_keys import public_key_from_bytes

        _secret, helper = gen(sample_biometric)
        pub = public_key_from_bytes(bytes.fromhex(helper["public_key"]))
        plaintext = b"medical record: blood type O+"
        packet = encrypt(pub, plaintext)

        _key, priv, success = rep(sample_biometric, helper)
        assert success
        recovered = decrypt(priv, packet)
        assert recovered == plaintext
