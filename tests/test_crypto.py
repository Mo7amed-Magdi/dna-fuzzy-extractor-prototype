"""Tests for hybrid encryption (X25519 + ChaCha20-Poly1305)."""

from __future__ import annotations

import pytest


class TestHybridEncrypt:
    def test_encrypt_decrypt_roundtrip(self, enrollment_001):
        from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
        from dna_proto.crypto import encrypt, decrypt
        from dna_proto.kdf_keys import derive_x25519_keypair
        key_material, enrollment = enrollment_001
        salt = bytes.fromhex(enrollment["salt"])
        priv, pub = derive_x25519_keypair(key_material, salt)

        plaintext = b"This is a secret medical record."
        ct = encrypt(plaintext, pub)
        pt = decrypt(ct, priv)
        assert pt == plaintext

    def test_encrypt_nondeterministic(self, enrollment_001):
        from dna_proto.crypto import encrypt
        from dna_proto.kdf_keys import derive_x25519_keypair
        key_material, enrollment = enrollment_001
        salt = bytes.fromhex(enrollment["salt"])
        _, pub = derive_x25519_keypair(key_material, salt)
        ct1 = encrypt(b"hello", pub)
        ct2 = encrypt(b"hello", pub)
        assert ct1 != ct2  # ephemeral keys differ

    def test_wrong_key_fails(self, enrollment_001):
        from cryptography.exceptions import InvalidTag
        from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
        from dna_proto.crypto import encrypt, decrypt
        from dna_proto.kdf_keys import derive_x25519_keypair
        key_material, enrollment = enrollment_001
        salt = bytes.fromhex(enrollment["salt"])
        _, pub = derive_x25519_keypair(key_material, salt)
        ct = encrypt(b"secret", pub)
        # Attempt decryption with a different (random) private key
        wrong_priv = X25519PrivateKey.generate()
        with pytest.raises(InvalidTag):
            decrypt(ct, wrong_priv)

    def test_tampered_ciphertext_fails(self, enrollment_001):
        from cryptography.exceptions import InvalidTag
        from dna_proto.crypto import encrypt, decrypt
        from dna_proto.kdf_keys import derive_x25519_keypair
        key_material, enrollment = enrollment_001
        salt = bytes.fromhex(enrollment["salt"])
        priv, pub = derive_x25519_keypair(key_material, salt)
        ct = bytearray(encrypt(b"data", pub))
        ct[-1] ^= 0xFF  # tamper last byte
        with pytest.raises(InvalidTag):
            decrypt(bytes(ct), priv)

    def test_invalid_header_raises(self, enrollment_001):
        from dna_proto.crypto import decrypt
        from dna_proto.kdf_keys import derive_x25519_keypair
        key_material, enrollment = enrollment_001
        salt = bytes.fromhex(enrollment["salt"])
        priv, _ = derive_x25519_keypair(key_material, salt)
        with pytest.raises(ValueError, match="Invalid magic"):
            decrypt(b"XXXX\x01" + b"\x00" * 60, priv)

    def test_encrypt_binary_data(self, enrollment_001):
        """Encrypt/decrypt arbitrary binary (image-like) data."""
        import os
        from dna_proto.crypto import encrypt, decrypt
        from dna_proto.kdf_keys import derive_x25519_keypair
        key_material, enrollment = enrollment_001
        salt = bytes.fromhex(enrollment["salt"])
        priv, pub = derive_x25519_keypair(key_material, salt)
        data = os.urandom(4096)
        ct = encrypt(data, pub)
        assert decrypt(ct, priv) == data

    def test_associated_data(self, enrollment_001):
        from cryptography.exceptions import InvalidTag
        from dna_proto.crypto import encrypt, decrypt
        from dna_proto.kdf_keys import derive_x25519_keypair
        key_material, enrollment = enrollment_001
        salt = bytes.fromhex(enrollment["salt"])
        priv, pub = derive_x25519_keypair(key_material, salt)
        aad = b"subject_001"
        ct = encrypt(b"data", pub, associated_data=aad)
        # Correct AAD
        assert decrypt(ct, priv, associated_data=aad) == b"data"
        # Wrong AAD
        with pytest.raises(InvalidTag):
            decrypt(ct, priv, associated_data=b"wrong")
