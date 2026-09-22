"""
Standalone tests for BigInt.div(self, oth) -- integer division, quotient only,
truncating toward zero (sign-magnitude style, like the shift operators).
No pytest required -- just run: python test_bigint_div.py

Assumptions (adjust if your implementation differs):
  - div(self, oth) returns a NEW BigInt equal to the truncated quotient
    self / oth (i.e. Python's `math.trunc(self / oth)`, NOT Python's `//`
    which floors -- these differ for mixed-sign operands).
  - Division by zero raises ZeroDivisionError (change EXPECTED_DIVZERO_ERROR
    if your implementation raises/returns something else).
  - Sign of the quotient follows normal sign rules (+/+ = +, -/- = +,
    +/- = -, -/+ = -), and a zero quotient is never negative.
  - values is little-endian (values[0] = least significant limb), base 2^16.
"""

import random
import traceback

from integer import BigInt  # adjust import to your module
from fixedint import UInt16


EXPECTED_DIVZERO_ERROR = EXPECTED_MODZERO_ERROR = ZeroDivisionError

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


def assert_raises(exc_type, fn, *args):
    try:
        fn(*args)
    except exc_type:
        return
    except Exception as e:
        raise AssertionError(
            f"expected {exc_type.__name__}, but got {type(e).__name__}: {e}"
        )
    else:
        raise AssertionError(f"expected {exc_type.__name__}, but no exception was raised")


def trunc_div(a: int, b: int) -> int:
    """Truncate-toward-zero division, like C/most CPUs, unlike Python's //."""
    q = abs(a) // abs(b)
    sign = -1 if (a < 0) != (b < 0) else 1
    return sign * q


# ---------------------------------------------------------------------------
# Basic division, exact and with truncated remainder
# ---------------------------------------------------------------------------

def test_div_exact_positive():
    a = mk(20)
    b = mk(4)
    assert_equal_value(a.div(b), 5)


def test_div_positive_with_remainder_truncates():
    a = mk(7)
    b = mk(2)
    assert_equal_value(a.div(b), 3)  # 3.5 -> truncates to 3


def test_div_by_one():
    a = mk(0x1234, 0x5678)
    b = mk(1)
    assert_equal_value(a.div(b), to_int(a))


def test_div_self_by_self():
    a = mk(123)
    assert_equal_value(a.div(mk(123)), 1)


def test_div_zero_numerator():
    a = mk(0)
    b = mk(5)
    result = a.div(b)
    assert_equal_value(result, 0)
    assert result.is_negative is False


def test_div_result_zero_from_smaller_numerator():
    a = mk(3)
    b = mk(10)
    result = a.div(b)
    assert_equal_value(result, 0)
    assert result.is_negative is False


# ---------------------------------------------------------------------------
# Sign handling
# ---------------------------------------------------------------------------

def test_div_negative_by_positive():
    a = mk(20, neg=True)
    b = mk(4)
    assert_equal_value(a.div(b), -5)


def test_div_positive_by_negative():
    a = mk(20)
    b = mk(4, neg=True)
    assert_equal_value(a.div(b), -5)


def test_div_negative_by_negative():
    a = mk(20, neg=True)
    b = mk(4, neg=True)
    assert_equal_value(a.div(b), 5)


def test_div_negative_truncates_toward_zero_not_floor():
    # -7 / 2 = -3.5 -> truncate to -3 (Python's // would floor to -4)
    a = mk(7, neg=True)
    b = mk(2)
    assert_equal_value(a.div(b), -3)


def test_div_positive_by_negative_truncates_toward_zero():
    a = mk(7)
    b = mk(2, neg=True)
    assert_equal_value(a.div(b), -3)


def test_div_negative_by_negative_truncates_toward_zero():
    a = mk(7, neg=True)
    b = mk(2, neg=True)
    assert_equal_value(a.div(b), 3)


def test_div_zero_result_not_negative():
    # -3 / 10 truncates to 0, should not be "negative zero"
    a = mk(3, neg=True)
    b = mk(10)
    result = a.div(b)
    assert_equal_value(result, 0)
    assert result.is_negative is False


# ---------------------------------------------------------------------------
# Division by zero
# ---------------------------------------------------------------------------

def test_div_by_zero_raises():
    a = mk(10)
    b = mk(0)
    assert_raises(EXPECTED_DIVZERO_ERROR, a.div, b)


def test_div_negative_by_zero_raises():
    a = mk(10, neg=True)
    b = mk(0)
    assert_raises(EXPECTED_DIVZERO_ERROR, a.div, b)


def test_div_zero_by_zero_raises():
    a = mk(0)
    b = mk(0)
    assert_raises(EXPECTED_DIVZERO_ERROR, a.div, b)


# ---------------------------------------------------------------------------
# Multi-limb / carry-across-limb cases
# ---------------------------------------------------------------------------

def test_div_multi_limb_by_single_limb():
    a = mk(0xFFFF, 0xFFFF, 0xFFFF)  # spans 3 limbs
    b = mk(2)
    assert_equal_value(a.div(b), to_int(a) // 2)


def test_div_result_spans_limb_boundary():
    # numerator just over 2^16, divide by 1 to check no off-by-one at the boundary
    a = mk(0, 1)  # 65536
    b = mk(1)
    assert_equal_value(a.div(b), 65536)


def test_div_multi_limb_by_multi_limb():
    a = mk(0x1234, 0x5678)     # 0x5678_1234
    b = mk(0x0010)             # 16
    assert_equal_value(a.div(b), to_int(a) // 16)


def test_div_large_by_large_close_quotient():
    a = mk(0xFFFF, 0xFFFF, 0xFFFF)
    b = mk(0xFFFE, 0xFFFF, 0xFFFF)
    assert_equal_value(a.div(b), 1)


def test_div_truncation_across_limb_boundary():
    # (2^16 + 1) / 2 -> 32768.5 -> truncates to 32768
    a = mk(1, 1)  # 65537
    b = mk(2)
    assert_equal_value(a.div(b), 32768)


def test_div_larger_divisor_than_dividend_negative():
    a = mk(0, 1, neg=True)  # -65536
    b = mk(0, 1, 1)         # 2^32 + 2^16
    result = a.div(b)
    assert_equal_value(result, 0)
    assert result.is_negative is False


# ---------------------------------------------------------------------------
# Cross-check against Python (with explicit truncate-toward-zero semantics)
# ---------------------------------------------------------------------------

def test_div_large_random_cross_check():
    random.seed(31)
    for _ in range(50):
        x = random.randint(-(1 << 80), 1 << 80)
        y = random.randint(-(1 << 80), 1 << 80)
        if y == 0:
            continue
        result = from_int(x).div(from_int(y))
        assert_equal_value(result, trunc_div(x, y))


def test_div_small_random_cross_check():
    random.seed(53)
    for _ in range(50):
        x = random.randint(-1000, 1000)
        y = random.randint(-1000, 1000)
        if y == 0:
            continue
        result = from_int(x).div(from_int(y))
        assert_equal_value(result, trunc_div(x, y))


def test_div_dividend_smaller_than_divisor_random():
    random.seed(64)
    for _ in range(20):
        y = random.randint(1000, 1 << 40)
        x = random.randint(-(y - 1), y - 1)  # |x| < |y|
        if x == 0:
            continue
        result = from_int(x).div(from_int(y))
        assert_equal_value(result, trunc_div(x, y))

# ---------------------------------------------------------------------------
# Basic cases, positive x
# ---------------------------------------------------------------------------
 
def test_mod_exact_division():
    a = mk(20)
    m = mk(5)
    assert_equal_value(a.mod(m), 0)
 
 
def test_mod_basic_remainder():
    a = mk(7)
    m = mk(3)
    assert_equal_value(a.mod(m), 1)
 
 
def test_mod_result_equals_x_when_smaller_than_m():
    a = mk(3)
    m = mk(10)
    assert_equal_value(a.mod(m), 3)
 
 
def test_mod_by_one_always_zero():
    a = mk(12345)
    m = mk(1)
    assert_equal_value(a.mod(m), 0)
 
 
def test_mod_x_equals_m():
    a = mk(42)
    m = mk(42)
    assert_equal_value(a.mod(m), 0)
 
 
def test_mod_zero_numerator():
    a = mk(0)
    m = mk(7)
    assert_equal_value(a.mod(m), 0)
 
 
# ---------------------------------------------------------------------------
# Negative x -- the interesting cases: result must stay nonnegative
# ---------------------------------------------------------------------------
 
def test_mod_negative_x_basic():
    # -7 mod 3 == 2  (not -1, which C-style remainder would give)
    a = mk(7, neg=True)
    m = mk(3)
    assert_equal_value(a.mod(m), 2)
 
 
def test_mod_negative_x_exact_multiple():
    # -20 mod 5 == 0
    a = mk(20, neg=True)
    m = mk(5)
    assert_equal_value(a.mod(m), 0)
 
 
def test_mod_negative_x_smaller_magnitude_than_m():
    # -3 mod 10 == 7
    a = mk(3, neg=True)
    m = mk(10)
    assert_equal_value(a.mod(m), 7)
 
 
def test_mod_negative_x_equal_magnitude_to_m():
    # -10 mod 10 == 0
    a = mk(10, neg=True)
    m = mk(10)
    assert_equal_value(a.mod(m), 0)
 
 
def test_mod_negative_x_one_off_multiple():
    # -1 mod 5 == 4
    a = mk(1, neg=True)
    m = mk(5)
    assert_equal_value(a.mod(m), 4)
 
 
def test_mod_negative_x_large_m():
    # -1000000 mod 7 -> check against Python's %, which is already correct here
    a = from_int(-1_000_000)
    m = mk(7)
    assert_equal_value(a.mod(m), (-1_000_000) % 7)
 
 
# ---------------------------------------------------------------------------
# Division-by-zero modulus
# ---------------------------------------------------------------------------
 
def test_mod_by_zero_raises():
    a = mk(10)
    m = mk(0)
    assert_raises(EXPECTED_MODZERO_ERROR, a.mod, m)
 
 
def test_mod_negative_x_by_zero_raises():
    a = mk(10, neg=True)
    m = mk(0)
    assert_raises(EXPECTED_MODZERO_ERROR, a.mod, m)
 
 
def test_mod_zero_by_zero_raises():
    a = mk(0)
    m = mk(0)
    assert_raises(EXPECTED_MODZERO_ERROR, a.mod, m)
 
 
# ---------------------------------------------------------------------------
# Multi-limb / carry-across-limb cases
# ---------------------------------------------------------------------------
 
def test_mod_multi_limb_x_single_limb_m():
    a = mk(0xFFFF, 0xFFFF, 0xFFFF)  # spans 3 limbs
    m = mk(1000)
    assert_equal_value(a.mod(m), to_int(a) % 1000)
 
 
def test_mod_across_limb_boundary():
    a = mk(0, 1)  # 65536
    m = mk(3)
    assert_equal_value(a.mod(m), 65536 % 3)
 
 
def test_mod_multi_limb_negative_x():
    a = mk(0, 1, neg=True)  # -65536
    m = mk(1000)
    assert_equal_value(a.mod(m), (-65536) % 1000)
 
 
def test_mod_multi_limb_m():
    a = mk(0x1234, 0x5678)   # 0x5678_1234
    m = mk(0, 1)              # 65536
    assert_equal_value(a.mod(m), to_int(a) % 65536)
 
 
def test_mod_negative_x_multi_limb_m():
    a = mk(0x1234, 0x5678, neg=True)
    m = mk(0, 1)  # 65536
    expected = (-to_int(mk(0x1234, 0x5678))) % 65536
    assert_equal_value(a.mod(m), expected)
 
 
def test_mod_m_larger_than_x():
    a = mk(5)
    m = mk(0, 1)  # 65536
    assert_equal_value(a.mod(m), 5)
 
 
def test_mod_negative_x_m_larger_than_magnitude():
    a = mk(5, neg=True)
    m = mk(0, 1)  # 65536
    assert_equal_value(a.mod(m), 65536 - 5)
 
 
# ---------------------------------------------------------------------------
# Cross-check against Python's own true-modulo `%`
# ---------------------------------------------------------------------------
 
def test_mod_large_random_cross_check():
    random.seed(101)
    for _ in range(50):
        x = random.randint(-(1 << 80), 1 << 80)
        m = random.randint(1, 1 << 40)
        result = from_int(x).mod(from_int(m))
        assert_equal_value(result, x % m)
 
 
def test_mod_small_random_cross_check():
    random.seed(202)
    for _ in range(50):
        x = random.randint(-1000, 1000)
        m = random.randint(1, 500)
        result = from_int(x).mod(from_int(m))
        assert_equal_value(result, x % m)
 
 
def test_mod_x_smaller_than_m_random():
    random.seed(303)
    for _ in range(20):
        m = random.randint(1000, 1 << 40)
        x = random.randint(-(m - 1), m - 1)
        result = from_int(x).mod(from_int(m))
        assert_equal_value(result, x % m)
 
 
# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

ALL_TESTS = [
    test_mod_exact_division,
    test_mod_basic_remainder,
    test_mod_result_equals_x_when_smaller_than_m,
    test_mod_by_one_always_zero,
    test_mod_x_equals_m,
    test_mod_zero_numerator,
    test_mod_negative_x_basic,
    test_mod_negative_x_exact_multiple,
    test_mod_negative_x_smaller_magnitude_than_m,
    test_mod_negative_x_equal_magnitude_to_m,
    test_mod_negative_x_one_off_multiple,
    test_mod_negative_x_large_m,
    test_mod_by_zero_raises,
    test_mod_negative_x_by_zero_raises,
    test_mod_zero_by_zero_raises,
    test_mod_multi_limb_x_single_limb_m,
    test_mod_across_limb_boundary,
    test_mod_multi_limb_negative_x,
    test_mod_multi_limb_m,
    test_mod_negative_x_multi_limb_m,
    test_mod_m_larger_than_x,
    test_mod_negative_x_m_larger_than_magnitude,
    test_mod_large_random_cross_check,
    test_mod_small_random_cross_check,
    test_mod_x_smaller_than_m_random,
    test_div_exact_positive,
    test_div_positive_with_remainder_truncates,
    test_div_by_one,
    test_div_self_by_self,
    test_div_zero_numerator,
    test_div_result_zero_from_smaller_numerator,
    test_div_negative_by_positive,
    test_div_positive_by_negative,
    test_div_negative_by_negative,
    test_div_negative_truncates_toward_zero_not_floor,
    test_div_positive_by_negative_truncates_toward_zero,
    test_div_negative_by_negative_truncates_toward_zero,
    test_div_zero_result_not_negative,
    test_div_by_zero_raises,
    test_div_negative_by_zero_raises,
    test_div_zero_by_zero_raises,
    test_div_multi_limb_by_single_limb,
    test_div_result_spans_limb_boundary,
    test_div_multi_limb_by_multi_limb,
    test_div_large_by_large_close_quotient,
    test_div_truncation_across_limb_boundary,
    test_div_larger_divisor_than_dividend_negative,
    test_div_large_random_cross_check,
    test_div_small_random_cross_check,
    test_div_dividend_smaller_than_divisor_random,
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
