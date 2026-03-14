"""Rate-1/3 repetition code used as the secure-sketch (Option B simulation).

Each bit of the secret is repeated 3 times in the codeword:
    secret bit 0  → codeword bits 0, 1, 2
    secret bit 1  → codeword bits 3, 4, 5
    ...

This allows correcting 1 error per 3-bit group (majority vote).

For a 256-bit secret → 768-bit codeword (= 96 bytes), which matches the
biometric vector length.
"""

from __future__ import annotations

REP_FACTOR: int = 3
SECRET_BITS: int = 256   # 32 bytes
SECRET_BYTES: int = SECRET_BITS // 8   # 32
CODEWORD_BITS: int = SECRET_BITS * REP_FACTOR   # 768
CODEWORD_BYTES: int = CODEWORD_BITS // 8   # 96


def _get_bit(data: bytes, pos: int) -> int:
    """Return the bit at position pos (MSB-first within each byte)."""
    return (data[pos >> 3] >> (7 - (pos & 7))) & 1


def _set_bit(buf: bytearray, pos: int) -> None:
    """Set the bit at position pos (MSB-first within each byte)."""
    buf[pos >> 3] |= 1 << (7 - (pos & 7))


def rep3_encode(secret: bytes) -> bytes:
    """Encode a SECRET_BYTES-byte secret to a CODEWORD_BYTES-byte codeword.

    Each bit of the secret is repeated REP_FACTOR times.
    """
    if len(secret) != SECRET_BYTES:
        raise ValueError(f"Secret must be {SECRET_BYTES} bytes, got {len(secret)}")
    codeword = bytearray(CODEWORD_BYTES)
    for i in range(SECRET_BITS):
        bit = _get_bit(secret, i)
        if bit:
            for k in range(REP_FACTOR):
                _set_bit(codeword, REP_FACTOR * i + k)
    return bytes(codeword)


def rep3_decode(noisy_codeword: bytes) -> bytes:
    """Majority-vote decode a CODEWORD_BYTES-byte noisy codeword to a secret.

    Returns the SECRET_BYTES-byte recovered secret.
    Each group of REP_FACTOR bits is decoded by majority vote.
    """
    if len(noisy_codeword) != CODEWORD_BYTES:
        raise ValueError(
            f"Noisy codeword must be {CODEWORD_BYTES} bytes, got {len(noisy_codeword)}"
        )
    secret = bytearray(SECRET_BYTES)
    for i in range(SECRET_BITS):
        votes = sum(
            _get_bit(noisy_codeword, REP_FACTOR * i + k) for k in range(REP_FACTOR)
        )
        if votes > REP_FACTOR // 2:
            _set_bit(secret, i)
    return bytes(secret)


def sketch_xor(biometric: bytes, codeword: bytes) -> bytes:
    """Compute helper data: sketch = biometric XOR codeword."""
    if len(biometric) != CODEWORD_BYTES or len(codeword) != CODEWORD_BYTES:
        raise ValueError(
            f"Both biometric and codeword must be {CODEWORD_BYTES} bytes"
        )
    return bytes(a ^ b for a, b in zip(biometric, codeword))
