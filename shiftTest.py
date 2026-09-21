"""
Standalone tests for BigInt.l_shift(self, n) and BigInt.r_shift(self, n).
No pytest required -- just run: python test_bigint_shift.py

Assumptions (adjust if your implementation differs):
  - l_shift(n): shifts left by n bits (magnitude * 2**n) if n >= 0.
                if n < 0, shifts right by abs(n) instead.
  - r_shift(n): shifts right by n bits (magnitude // 2**n, truncating toward
                zero -- since this is sign-magnitude, not two's complement)
                if n >= 0. if n < 0, shifts left by abs(n) instead.
  - Sign is maintained: shifting a negative value keeps it negative, UNLESS
    the magnitude becomes 0 (via right shift), in which case is_negative
    should become False (no negative zero).
  - Both methods return a NEW BigInt (don't mutate self). If they mutate
    in place instead, adjust the calls below (they'll still work since we
    only ever read the return value or re-fetch `.values`/`.is_negative`,
    but you may want extra tests asserting the original is untouched).
  - values is little-endian (values[0] = least significant limb), base 2^16.

Because this is sign-magnitude (not two's complement), right-shifting a
negative number is expected to TRUNCATE TOWARD ZERO, unlike Python's native
`>>` on negative ints which floors toward -infinity. The `expected_rshift`
helper below implements truncate-toward-zero explicitly for cross-checks.
"""

import random
import traceback

from fixedint import UInt16
from integer import BigInt  # adjust import to your module



RADIX = BigInt.RADIX
RADIX_SHIFT = BigInt.RADIX_SHIFT
MASK = RADIX - 1


def mk(*limbs, neg=False):
    """Helper to build a BigInt from little-endian limbs."""
    return BigInt([UInt16(x) for x in limbs], is_negative=neg)


def to_int(b: BigInt) -> int:
    """Reference conversion for comparing results, independent of internal repr."""
    val = 0
    for i, limb in enumerate(int(x) for x in b.values):
        val += limb << (RADIX_SHIFT * i)
    return -val if b.is_negative and val != 0 else val


def from_int(n: int) -> BigInt:
    neg = n < 0
    n = abs(n)
    if n == 0:
        return BigInt([UInt16(0)], is_negative=False)
    limbs = []
    while n:
        limbs.append(UInt16(n & MASK))
        n >>= 16
    return BigInt(limbs, is_negative=neg)


def assert_equal_value(result: BigInt, expected_int: int):
    actual = to_int(result)
    assert actual == expected_int, (
        f"expected {expected_int}, got {actual} "
        f"(values={result.values}, is_negative={result.is_negative})"
    )

RADIX = 1 << 16


def expected_lshift(x: int, n: int) -> int:
    if n >= 0:
        return x << n
    return expected_rshift(x, -n)


def expected_rshift(x: int, n: int) -> int:
    if n < 0:
        return expected_lshift(x, -n)
    # truncate toward zero, sign-magnitude style
    sign = -1 if x < 0 else 1
    mag = abs(x) >> n
    return sign * mag


# ---------------------------------------------------------------------------
# Left shift
# ---------------------------------------------------------------------------

def test_lshift_by_zero():
    a = mk(1234)
    assert_equal_value(a.l_shift(0), 1234)


def test_lshift_positive_small():
    a = mk(1)
    assert_equal_value(a.l_shift(4), 16)


def test_lshift_positive_across_limb():
    # 1 << 16 overflows into a second limb
    a = mk(1)
    assert_equal_value(a.l_shift(16), 1 << 16)


def test_lshift_positive_across_multiple_limbs():
    a = mk(1)
    assert_equal_value(a.l_shift(50), 1 << 50)


def test_lshift_negative_maintains_sign():
    a = mk(3, neg=True)
    assert_equal_value(a.l_shift(4), -48)


def test_lshift_zero_stays_zero():
    a = mk(0)
    result = a.l_shift(10)
    assert_equal_value(result, 0)
    assert result.is_negative is False


def test_lshift_by_partial_limb_amount():
    # shift not a multiple of 16, exercises bit-level carry between limbs
    a = mk(0xFFFF, 0x0001)  # 0x1_FFFF
    assert_equal_value(a.l_shift(5), to_int(a) << 5)


def test_lshift_negative_n_shifts_right():
    # n < 0 should behave like a right shift by abs(n)
    a = mk(256)
    assert_equal_value(a.l_shift(-4), 16)


def test_lshift_negative_n_negative_value():
    a = mk(256, neg=True)
    assert_equal_value(a.l_shift(-4), -16)


# ---------------------------------------------------------------------------
# Right shift
# ---------------------------------------------------------------------------

def test_rshift_by_zero():
    a = mk(1234)
    assert_equal_value(a.r_shift(0), 1234)


def test_rshift_positive_small():
    a = mk(16)
    assert_equal_value(a.r_shift(4), 1)


def test_rshift_positive_across_limb():
    a = mk(0, 1)  # 65536
    assert_equal_value(a.r_shift(16), 1)


def test_rshift_positive_across_multiple_limbs():
    a = from_int(1 << 50)
    assert_equal_value(a.r_shift(50), 1)


def test_rshift_negative_maintains_sign():
    a = mk(48, neg=True)
    assert_equal_value(a.r_shift(4), -3)


def test_rshift_truncates_toward_zero_for_negative():
    # -7 >> 1 should truncate to -3 (not floor to -4)
    a = mk(7, neg=True)
    assert_equal_value(a.r_shift(1), -3)


def test_rshift_positive_truncates_remainder():
    # 7 >> 1 == 3, remainder dropped
    a = mk(7)
    assert_equal_value(a.r_shift(1), 3)


def test_rshift_to_zero_from_positive():
    a = mk(1)
    result = a.r_shift(5)
    assert_equal_value(result, 0)
    assert result.is_negative is False


def test_rshift_to_zero_from_negative_drops_sign():
    # magnitude shifts away to 0 -- should not be "negative zero"
    a = mk(1, neg=True)
    result = a.r_shift(5)
    assert_equal_value(result, 0)
    assert result.is_negative is False


def test_rshift_zero_stays_zero():
    a = mk(0)
    result = a.r_shift(10)
    assert_equal_value(result, 0)
    assert result.is_negative is False


def test_rshift_shift_amount_exceeds_bit_length():
    a = mk(0xFFFF, 0xFFFF)  # small-ish multi-limb value
    result = a.r_shift(100)
    assert_equal_value(result, 0)
    assert result.is_negative is False


def test_rshift_by_partial_limb_amount():
    a = mk(0x1234, 0x5678)
    assert_equal_value(a.r_shift(5), to_int(a) >> 5)


def test_rshift_negative_n_shifts_left():
    a = mk(1)
    assert_equal_value(a.r_shift(-4), 16)


def test_rshift_negative_n_negative_value():
    a = mk(1, neg=True)
    assert_equal_value(a.r_shift(-4), -16)


# ---------------------------------------------------------------------------
# Round-trip / consistency checks
# ---------------------------------------------------------------------------

def test_lshift_then_rshift_roundtrip_positive():
    a = mk(0x1234, 0x5678)
    shifted = a.l_shift(20)
    print(shifted.values)
    back = shifted.r_shift(20)
    print(back.values)
    assert_equal_value(back, to_int(a))


def test_lshift_then_rshift_roundtrip_negative():
    a = mk(0x1234, 0x5678, neg=True)
    shifted = a.l_shift(20)
    back = shifted.r_shift(20)
    assert_equal_value(back, to_int(a))


def test_rshift_is_inverse_of_lshift_negative_n():
    a = mk(0xABCD)
    assert_equal_value(a.r_shift(-3), to_int(a.l_shift(3)))


def test_lshift_is_inverse_of_rshift_negative_n():
    a = mk(0xABCD)
    assert_equal_value(a.l_shift(-3), to_int(a.r_shift(3)))


# ---------------------------------------------------------------------------
# Cross-check against Python semantics (truncate-toward-zero variant)
# ---------------------------------------------------------------------------

def test_lshift_large_random_cross_check():
    random.seed(11)
    for _ in range(50):
        x = random.randint(-(1 << 60), 1 << 60)
        n = random.randint(0, 40)
        result = from_int(x).l_shift(n)
        assert_equal_value(result, expected_lshift(x, n))


def test_rshift_large_random_cross_check():
    random.seed(23)
    for _ in range(50):
        x = random.randint(-(1 << 60), 1 << 60)
        n = random.randint(0, 40)
        result = from_int(x).r_shift(n)
        assert_equal_value(result, expected_rshift(x, n))


def test_shift_negative_n_random_cross_check():
    random.seed(77)
    for _ in range(30):
        x = random.randint(-(1 << 60), 1 << 60)
        n = random.randint(1, 20)
        l_res = from_int(x).l_shift(-n)
        r_res = from_int(x).r_shift(-n)
        assert_equal_value(l_res, expected_rshift(x, n))
        assert_equal_value(r_res, expected_lshift(x, n))


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

ALL_TESTS = [
    test_lshift_by_zero,
    test_lshift_positive_small,
    test_lshift_positive_across_limb,
    test_lshift_positive_across_multiple_limbs,
    test_lshift_negative_maintains_sign,
    test_lshift_zero_stays_zero,
    test_lshift_by_partial_limb_amount,
    test_lshift_negative_n_shifts_right,
    test_lshift_negative_n_negative_value,
    test_rshift_by_zero,
    test_rshift_positive_small,
    test_rshift_positive_across_limb,
    test_rshift_positive_across_multiple_limbs,
    test_rshift_negative_maintains_sign,
    test_rshift_truncates_toward_zero_for_negative,
    test_rshift_positive_truncates_remainder,
    test_rshift_to_zero_from_positive,
    test_rshift_to_zero_from_negative_drops_sign,
    test_rshift_zero_stays_zero,
    test_rshift_shift_amount_exceeds_bit_length,
    test_rshift_by_partial_limb_amount,
    test_rshift_negative_n_shifts_left,
    test_rshift_negative_n_negative_value,
    test_lshift_then_rshift_roundtrip_positive,
    test_lshift_then_rshift_roundtrip_negative,
    test_rshift_is_inverse_of_lshift_negative_n,
    test_lshift_is_inverse_of_rshift_negative_n,
    test_lshift_large_random_cross_check,
    test_rshift_large_random_cross_check,
    test_shift_negative_n_random_cross_check,
]


def run_all():
    passed = 0
    failed = 0
    failures = []

    for test_fn in ALL_TESTS:
        name = test_fn.__name__
        try:
            test_fn()
        except Exception as e:
            failed += 1
            failures.append((name, e, traceback.format_exc()))
            print(f"FAIL  {name}: {e}")
        else:
            passed += 1
            print(f"PASS  {name}")

    print()
    print(f"{passed} passed, {failed} failed out of {len(ALL_TESTS)} tests")

    if failures:
        print("\n--- Failure details ---")
        for name, e, tb in failures:
            print(f"\n{name}:")
            print(tb)

    return failed == 0


if __name__ == "__main__":
    import sys
    success = run_all()
    sys.exit(0 if success else 1)
