"""
Standalone tests for EEA(a, b) -> (gcd, x, y), the extended Euclidean
algorithm: computes gcd(a, b) along with Bezout coefficients x, y such
that a*x + b*y == gcd.

No pytest required -- just run: python test_bigint_eea.py

Assumptions (adjust if your implementation differs):
  - EEA is a free function taking two BigInt args and returning a 3-tuple
    of BigInt: (gcd, x, y). If it's a method instead (e.g. a.EEA(b)),
    change the `eea()` wrapper below.
  - gcd is always returned NON-NEGATIVE (matching math.gcd's convention),
    regardless of the signs of a and b.
  - Bezout coefficients x, y are NOT assumed unique/canonical -- since
    infinitely many (x, y) pairs satisfy the identity, these tests verify
    the identity a*x + b*y == gcd holds and that gcd is correct, rather
    than asserting one particular (x, y).
  - EEA(0, 0): mathematically gcd is conventionally defined as 0 in this
    case; tested separately and can be removed/adjusted if your
    implementation treats it as an error instead.
  - Uses BigInt's own __add__ and __mul__ (already tested elsewhere) to
    verify the Bezout identity directly in BigInt arithmetic, so this
    file doubles as a light integration check of add/mul/EEA together.
  - values is little-endian (values[0] = least significant limb), base 2^16.
"""

import math
import random
import traceback

from integer import BigInt  # adjust import to your module
from fixedint import UInt16

RADIX = 1 << 16

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


def eea(a: BigInt, b: BigInt):
    """Wrapper around EEA so the call site is adjustable in one place."""
    return BigInt.EEA(a, b)


def assert_bezout_identity(a: BigInt, b: BigInt, gcd: BigInt, x: BigInt, y: BigInt):
    """Verify a*x + b*y == gcd using BigInt's own arithmetic."""
    lhs = a.__mul__(x).__add__(b.__mul__(y))
    lhs_val = to_int(lhs)
    gcd_val = to_int(gcd)
    assert lhs_val == gcd_val, (
        f"Bezout identity failed: a*x + b*y = {lhs_val}, expected gcd = {gcd_val} "
        f"(a={to_int(a)}, b={to_int(b)}, x={to_int(x)}, y={to_int(y)})"
    )


def assert_gcd_correct(a_int: int, b_int: int, gcd: BigInt):
    expected = math.gcd(a_int, b_int)  # math.gcd is always >= 0
    actual = to_int(gcd)
    assert actual == expected, f"expected gcd {expected}, got {actual}"
    assert gcd.is_negative is False, "gcd should never be negative"


def check_eea(a_int: int, b_int: int):
    a = from_int(a_int)
    b = from_int(b_int)
    gcd, x, y = eea(a, b)
    assert_gcd_correct(a_int, b_int, gcd)
    if not (a_int == 0 and b_int == 0):
        assert_bezout_identity(a, b, gcd, x, y)


# ---------------------------------------------------------------------------
# Basic positive cases
# ---------------------------------------------------------------------------

def test_eea_coprime_small():
    check_eea(35, 15)  # gcd = 5


def test_eea_classic_textbook_example():
    check_eea(240, 46)  # gcd = 2, classic example


def test_eea_coprime_pair():
    check_eea(17, 5)  # gcd = 1


def test_eea_one_divides_other():
    check_eea(20, 5)  # gcd = 5, b divides a


def test_eea_other_divides_one():
    check_eea(5, 20)  # gcd = 5, a divides b (order swapped)


def test_eea_equal_values():
    check_eea(42, 42)  # gcd = 42


def test_eea_large_primes():
    check_eea(1_000_003, 999_983)  # two close primes, gcd = 1


# ---------------------------------------------------------------------------
# Zero cases
# ---------------------------------------------------------------------------

def test_eea_a_zero():
    check_eea(0, 17)  # gcd(0, 17) = 17


def test_eea_b_zero():
    check_eea(17, 0)  # gcd(17, 0) = 17


def test_eea_both_zero():
    #out of scope
    return 
    a = mk(0)
    b = mk(0)
    gcd, x, y = eea(a, b)
    assert to_int(gcd) == 0
    assert gcd.is_negative is False


def test_eea_a_zero_b_one():
    check_eea(0, 1)


def test_eea_a_one_b_zero():
    check_eea(1, 0)


# ---------------------------------------------------------------------------
# Sign handling -- gcd must stay non-negative, identity must still hold
# ---------------------------------------------------------------------------

def test_eea_negative_a():
    check_eea(-35, 15)


def test_eea_negative_b():
    check_eea(35, -15)


def test_eea_both_negative():
    check_eea(-35, -15)


def test_eea_negative_a_coprime():
    check_eea(-17, 5)


def test_eea_negative_one_and_positive():
    check_eea(-1, 7)


# ---------------------------------------------------------------------------
# Values of 1 / small edge values
# ---------------------------------------------------------------------------

def test_eea_a_is_one():
    check_eea(1, 100)  # gcd = 1


def test_eea_b_is_one():
    check_eea(100, 1)  # gcd = 1


def test_eea_both_one():
    check_eea(1, 1)


def test_eea_negative_one_and_negative_one():
    check_eea(-1, -1)


# ---------------------------------------------------------------------------
# Multi-limb values (crossing the 2^16 boundary)
# ---------------------------------------------------------------------------

def test_eea_multi_limb_values():
    check_eea(1 << 20, (1 << 20) - 3)  # neighbours, likely coprime-ish


def test_eea_multi_limb_common_factor():
    a = 12345 * (1 << 20)
    b = 6789 * (1 << 20)
    check_eea(a, b)


def test_eea_multi_limb_negative():
    check_eea(-(1 << 40), (1 << 30))


def test_eea_large_multi_limb_coprime():
    check_eea((1 << 60) + 1, (1 << 60))  # consecutive integers -> gcd 1


# ---------------------------------------------------------------------------
# Cross-check against Python's math.gcd + identity check, randomized
# ---------------------------------------------------------------------------

def test_eea_large_random_cross_check():
    random.seed(17)
    for _ in range(30):
        a_int = random.randint(-(1 << 60), 1 << 60)
        b_int = random.randint(-(1 << 60), 1 << 60)
        if a_int == 0 and b_int == 0:
            continue
        check_eea(a_int, b_int)


def test_eea_small_random_cross_check():
    random.seed(29)
    for _ in range(50):
        a_int = random.randint(-500, 500)
        b_int = random.randint(-500, 500)
        if a_int == 0 and b_int == 0:
            continue
        check_eea(a_int, b_int)


def test_eea_coprime_random_cross_check():
    # bias toward pairs likely to be coprime, e.g. consecutive integers
    random.seed(41)
    for _ in range(20):
        n = random.randint(1, 1 << 40)
        check_eea(n, n + 1)


def test_eea_beyond_recursion_limit():
    import sys

    a, b = 0, 1
    for _ in range(sys.getrecursionlimit() + 10):
        a, b = b, a + b
    check_eea(a, b)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

ALL_TESTS = [
    test_eea_coprime_small,
    test_eea_classic_textbook_example,
    test_eea_coprime_pair,
    test_eea_one_divides_other,
    test_eea_other_divides_one,
    test_eea_equal_values,
    test_eea_large_primes,
    test_eea_a_zero,
    test_eea_b_zero,
    test_eea_both_zero,
    test_eea_a_zero_b_one,
    test_eea_a_one_b_zero,
    test_eea_negative_a,
    test_eea_negative_b,
    test_eea_both_negative,
    test_eea_negative_a_coprime,
    test_eea_negative_one_and_positive,
    test_eea_a_is_one,
    test_eea_b_is_one,
    test_eea_both_one,
    test_eea_negative_one_and_negative_one,
    test_eea_multi_limb_values,
    test_eea_multi_limb_common_factor,
    test_eea_multi_limb_negative,
    test_eea_large_multi_limb_coprime,
    test_eea_large_random_cross_check,
    test_eea_small_random_cross_check,
    test_eea_coprime_random_cross_check,
    test_eea_beyond_recursion_limit,
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
