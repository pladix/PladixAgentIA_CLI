"""
DeepSeek Proof of Work (PoW) Solver - DeepSeekHashV1
Optimized with Numba JIT (LLVM) for millisecond performance.

Desenvolvido por PladixOficial
Telegram: t.me/pladixoficial
"""

import time
import struct
import numpy as np

# Round constants for Keccak-f[1600]
RC = np.array([
    0x0000000000000001, 0x0000000000008082, 0x800000000000808A,
    0x8000000080008000, 0x000000000000808B, 0x0000000080000001,
    0x8000000080008081, 0x8000000000008009, 0x000000000000008A,
    0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
    0x000000008000808B, 0x800000000000008B, 0x8000000000008089,
    0x8000000000008003, 0x8000000000008002, 0x8000000000000080,
    0x000000000000800A, 0x800000008000000A, 0x8000000080008081,
    0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
], dtype=np.uint64)

try:
    import numba
    
    @numba.njit(inline='always')
    def _rotl64(x, n):
        return (x << np.uint64(n)) | (x >> np.uint64(64 - n))

    @numba.njit(fastmath=True)
    def _solve_kernel(base_bytes, t0, t1, t2, t3, max_nonce):
        base_len = len(base_bytes)
        rate = 136  # Keccak rate in bytes
        
        blk = np.zeros(rate, dtype=np.uint8)
        for i in range(base_len):
            blk[i] = base_bytes[i]
        blk[rate - 1] = 0x80

        digits = np.zeros(20, dtype=np.uint8)

        for nonce in range(max_nonce):
            # Convert nonce integer to ASCII decimal bytes
            n = nonce
            dlen = 0
            if n == 0:
                digits[0] = 48
                dlen = 1
            else:
                while n > 0:
                    digits[dlen] = 48 + (n % 10)
                    n //= 10
                    dlen += 1
                for k in range(dlen // 2):
                    tmp = digits[k]
                    digits[k] = digits[dlen - 1 - k]
                    digits[dlen - 1 - k] = tmp

            # Place nonce into block
            for k in range(dlen):
                blk[base_len + k] = digits[k]
            blk[base_len + dlen] = 0x06
            for k in range(base_len + dlen + 1, rate - 1):
                blk[k] = 0

            # Load into 25 uint64 state words
            A = np.zeros(25, dtype=np.uint64)
            for j in range(rate // 8):
                v = np.uint64(0)
                for b in range(8):
                    v |= np.uint64(blk[j * 8 + b]) << np.uint64(b * 8)
                A[j] = v

            # Keccak-f 23-round permutation (rounds 1 through 23)
            C = np.zeros(5, dtype=np.uint64)
            D = np.zeros(5, dtype=np.uint64)
            B = np.zeros(25, dtype=np.uint64)

            for r in range(1, 24):
                C[0] = A[0] ^ A[5] ^ A[10] ^ A[15] ^ A[20]
                C[1] = A[1] ^ A[6] ^ A[11] ^ A[16] ^ A[21]
                C[2] = A[2] ^ A[7] ^ A[12] ^ A[17] ^ A[22]
                C[3] = A[3] ^ A[8] ^ A[13] ^ A[18] ^ A[23]
                C[4] = A[4] ^ A[9] ^ A[14] ^ A[19] ^ A[24]

                D[0] = C[4] ^ _rotl64(C[1], 1)
                D[1] = C[0] ^ _rotl64(C[2], 1)
                D[2] = C[1] ^ _rotl64(C[3], 1)
                D[3] = C[2] ^ _rotl64(C[4], 1)
                D[4] = C[3] ^ _rotl64(C[0], 1)

                for j in range(25):
                    A[j] ^= D[j % 5]

                B[0] = A[0]
                B[1] = _rotl64(A[6], 44)
                B[2] = _rotl64(A[12], 43)
                B[3] = _rotl64(A[18], 21)
                B[4] = _rotl64(A[24], 14)
                B[5] = _rotl64(A[3], 28)
                B[6] = _rotl64(A[9], 20)
                B[7] = _rotl64(A[10], 3)
                B[8] = _rotl64(A[16], 45)
                B[9] = _rotl64(A[22], 61)
                B[10] = _rotl64(A[1], 1)
                B[11] = _rotl64(A[7], 6)
                B[12] = _rotl64(A[13], 25)
                B[13] = _rotl64(A[19], 8)
                B[14] = _rotl64(A[20], 18)
                B[15] = _rotl64(A[4], 27)
                B[16] = _rotl64(A[5], 36)
                B[17] = _rotl64(A[11], 10)
                B[18] = _rotl64(A[17], 15)
                B[19] = _rotl64(A[23], 56)
                B[20] = _rotl64(A[2], 62)
                B[21] = _rotl64(A[8], 55)
                B[22] = _rotl64(A[14], 39)
                B[23] = _rotl64(A[15], 41)
                B[24] = _rotl64(A[21], 2)

                A[0] = B[0] ^ ((~B[1]) & B[2])
                A[1] = B[1] ^ ((~B[2]) & B[3])
                A[2] = B[2] ^ ((~B[3]) & B[4])
                A[3] = B[3] ^ ((~B[4]) & B[0])
                A[4] = B[4] ^ ((~B[0]) & B[1])

                A[5] = B[5] ^ ((~B[6]) & B[7])
                A[6] = B[6] ^ ((~B[7]) & B[8])
                A[7] = B[7] ^ ((~B[8]) & B[9])
                A[8] = B[8] ^ ((~B[9]) & B[5])
                A[9] = B[9] ^ ((~B[5]) & B[6])

                A[10] = B[10] ^ ((~B[11]) & B[12])
                A[11] = B[11] ^ ((~B[12]) & B[13])
                A[12] = B[12] ^ ((~B[13]) & B[14])
                A[13] = B[13] ^ ((~B[14]) & B[10])
                A[14] = B[14] ^ ((~B[10]) & B[11])

                A[15] = B[15] ^ ((~B[16]) & B[17])
                A[16] = B[16] ^ ((~B[17]) & B[18])
                A[17] = B[17] ^ ((~B[18]) & B[19])
                A[18] = B[18] ^ ((~B[19]) & B[15])
                A[19] = B[19] ^ ((~B[15]) & B[16])

                A[20] = B[20] ^ ((~B[21]) & B[22])
                A[21] = B[21] ^ ((~B[22]) & B[23])
                A[22] = B[22] ^ ((~B[23]) & B[24])
                A[23] = B[23] ^ ((~B[24]) & B[20])
                A[24] = B[24] ^ ((~B[20]) & B[21])

                A[0] ^= RC[r]

            if A[0] == t0 and A[1] == t1 and A[2] == t2 and A[3] == t3:
                return nonce

        return -1

    # Pre-compile the JIT kernel on import
    _dummy_base = np.array([48], dtype=np.uint8)
    _solve_kernel(_dummy_base, np.uint64(0), np.uint64(0), np.uint64(0), np.uint64(0), 1)
    _NUMBA_READY = True

except Exception as _e:
    _NUMBA_READY = False
    _solve_kernel = None


def solve_pow(salt: str, expire_at: int | str, challenge_hex: str, difficulty: int = 144000) -> int:
    """
    Solves DeepSeekHashV1 challenge using native JIT acceleration.
    
    Args:
        salt: Server-issued salt string
        expire_at: Expiration timestamp
        challenge_hex: Target 64-char hex string (32 bytes)
        difficulty: Maximum iterations (typically 144000)
    
    Returns:
        The matching nonce, or -1 if not found.
    """
    base_str = f"{salt}_{expire_at}_"
    base_bytes = np.frombuffer(base_str.encode("utf-8"), dtype=np.uint8)
    
    raw_target = bytes.fromhex(challenge_hex)
    t0, t1, t2, t3 = struct.unpack("<4Q", raw_target)
    
    if _NUMBA_READY and _solve_kernel is not None:
        return int(_solve_kernel(
            base_bytes,
            np.uint64(t0),
            np.uint64(t1),
            np.uint64(t2),
            np.uint64(t3),
            int(difficulty) + 1
        ))
    
    raise RuntimeError("Numba JIT solver not ready.")


if __name__ == "__main__":
    # Self-test
    test_salt = "3fce1228ec40c770feee"
    test_exp = 1790529867829
    test_challenge = "74b21d88d19a993f4e98d81b22f191d89409cb854158fb40fe556e2727f345d7"
    expected_ans = 107747
    
    t0 = time.perf_counter()
    ans = solve_pow(test_salt, test_exp, test_challenge, 144000)
    t1 = time.perf_counter()
    
    print(f"Self-test: found {ans} in {(t1-t0)*1000:.2f}ms (expected {expected_ans}) -> {'SUCCESS' if ans == expected_ans else 'FAIL'}")
