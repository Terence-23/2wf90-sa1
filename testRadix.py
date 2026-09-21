"""
Standalone tests for BigInt.from_radix(self, radix: int, num: str).
No pytest required -- just run: python test_bigint_from_radix.py

Assumptions (adjust if your implementation differs):
  - from_radix mutates `self` in place (doesn't return a new BigInt).
    If it instead returns a new BigInt, change `call_from_radix` below.
  - radix must be in [2, 16] inclusive; anything outside that raises
    (assumed ValueError -- change EXPECTED_RANGE_ERROR if it's different).
  - num may have an optional leading '-' for negative numbers.
  - digits above 9 use lowercase letters 'a'-'f' (adjust if uppercase expected,
    or add a test for whichever case your implementation does NOT accept).
  - "0" (and "-0") produce a zero BigInt with is_negative == False.
  - values is little-endian (values[0] = least significant limb), base 2^16.
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

# Change these if your implementation raises different exception types.
EXPECTED_RANGE_ERROR = ValueError
EXPECTED_DIGIT_ERROR = ValueError

def call_from_radix(radix: int, num: str) -> BigInt:
    """Build a fresh BigInt and populate it via from_radix."""
    return BigInt.from_radix(radix, num)

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


# ---------------------------------------------------------------------------
# Basic conversions across radixes
# ---------------------------------------------------------------------------

def test_binary_simple():
    b = call_from_radix(2, "1010")
    assert_equal_value(b, 10)


def test_binary_zero():
    b = call_from_radix(2, "0")
    assert_equal_value(b, 0)
    assert b.is_negative is False


def test_octal_simple():
    b = call_from_radix(8, "17")
    assert_equal_value(b, 15)


def test_decimal_simple():
    b = call_from_radix(10, "12345")
    assert_equal_value(b, 12345)


def test_hex_simple_digits():
    b = call_from_radix(16, "ff")
    assert_equal_value(b, 255)


def test_hex_all_letters():
    b = call_from_radix(16, "abcdef")
    assert_equal_value(b, 0xABCDEF)


def test_radix_9_boundary_digit():
    # radix 9 -> digit '9' is invalid (digits are 0-8)
    assert_raises(EXPECTED_DIGIT_ERROR, call_from_radix, 9, "9")


def test_radix_lower_bound():
    b = call_from_radix(2, "1")
    assert_equal_value(b, 1)


def test_radix_upper_bound():
    b = call_from_radix(16, "f")
    assert_equal_value(b, 15)


# ---------------------------------------------------------------------------
# Out-of-range radix
# ---------------------------------------------------------------------------

def test_radix_too_low_raises():
    assert_raises(EXPECTED_RANGE_ERROR, call_from_radix, 1, "0")


def test_radix_zero_raises():
    assert_raises(EXPECTED_RANGE_ERROR, call_from_radix, 0, "0")


def test_radix_negative_raises():
    assert_raises(EXPECTED_RANGE_ERROR, call_from_radix, -2, "0")


def test_radix_too_high_raises():
    assert_raises(EXPECTED_RANGE_ERROR, call_from_radix, 17, "0")


def test_radix_way_too_high_raises():
    assert_raises(EXPECTED_RANGE_ERROR, call_from_radix, 100, "0")


# ---------------------------------------------------------------------------
# Invalid digits for a given radix
# ---------------------------------------------------------------------------

def test_binary_invalid_digit():
    assert_raises(EXPECTED_DIGIT_ERROR, call_from_radix, 2, "102")


def test_octal_invalid_digit():
    assert_raises(EXPECTED_DIGIT_ERROR, call_from_radix, 8, "8")


def test_decimal_invalid_digit():
    assert_raises(EXPECTED_DIGIT_ERROR, call_from_radix, 10, "12a3")


def test_hex_invalid_digit():
    assert_raises(EXPECTED_DIGIT_ERROR, call_from_radix, 16, "g")


# ---------------------------------------------------------------------------
# Sign handling
# ---------------------------------------------------------------------------

def test_negative_decimal():
    b = call_from_radix(10, "-42")
    assert_equal_value(b, -42)
    assert b.is_negative is True


def test_negative_hex():
    b = call_from_radix(16, "-ff")
    assert_equal_value(b, -255)


def test_negative_binary():
    b = call_from_radix(2, "-1010")
    assert_equal_value(b, -10)


def test_negative_zero_normalizes_to_non_negative():
    b = call_from_radix(10, "-0")
    assert_equal_value(b, 0)
    assert b.is_negative is False


# ---------------------------------------------------------------------------
# Leading zeros / whitespace-free padding
# ---------------------------------------------------------------------------

def test_leading_zeros_decimal():
    b = call_from_radix(10, "007")
    assert_equal_value(b, 7)


def test_leading_zeros_hex():
    b = call_from_radix(16, "00ff")
    assert_equal_value(b, 255)


def test_all_zeros():
    b = call_from_radix(10, "000")
    assert_equal_value(b, 0)
    assert b.is_negative is False


# ---------------------------------------------------------------------------
# Values that force multi-limb results / carry across limbs
# ---------------------------------------------------------------------------

def test_decimal_value_exceeds_one_limb():
    # 2^16 = 65536, needs two limbs
    b = call_from_radix(10, "65536")
    assert_equal_value(b, 65536)


def test_decimal_value_exceeds_multiple_limbs():
    big = (1 << 48) + 12345
    b = call_from_radix(10, str(big))
    assert_equal_value(b, big)


def test_hex_value_exceeds_one_limb():
    b = call_from_radix(16, "10000")  # 0x10000 = 65536
    assert_equal_value(b, 0x10000)


def test_binary_value_exceeds_one_limb():
    b = call_from_radix(2, "1" + "0" * 16)  # 2^16
    assert_equal_value(b, 1 << 16)


def test_negative_multi_limb():
    big = (1 << 48) + 999
    b = call_from_radix(10, f"-{big}")
    assert_equal_value(b, -big)


# ---------------------------------------------------------------------------
# Cross-check against Python's own int(str, base) for a range of radixes
# ---------------------------------------------------------------------------

def test_cross_check_all_radixes():
    samples = ["0", "1", "9", "15", "123", "10000", "999999"]
    for radix in range(2, 17):
        for s in samples:
            try:
                expected = int(s, radix)
            except ValueError:
                continue  # sample has digits invalid for this radix, skip
            b = call_from_radix(radix, s)
            assert_equal_value(b, expected)


def test_cross_check_negative_all_radixes():
    for radix in range(2, 17):
        s = "-101" if radix == 2 else "-11"
        expected = int(s, radix)
        b = call_from_radix(radix, s)
        assert_equal_value(b, expected)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

ALL_TESTS = [
    test_binary_simple,
    test_binary_zero,
    test_octal_simple,
    test_decimal_simple,
    test_hex_simple_digits,
    test_hex_all_letters,
    test_radix_9_boundary_digit,
    test_radix_lower_bound,
    test_radix_upper_bound,
    test_radix_too_low_raises,
    test_radix_zero_raises,
    test_radix_negative_raises,
    test_radix_too_high_raises,
    test_radix_way_too_high_raises,
    test_binary_invalid_digit,
    test_octal_invalid_digit,
    test_decimal_invalid_digit,
    test_hex_invalid_digit,
    test_negative_decimal,
    test_negative_hex,
    test_negative_binary,
    test_negative_zero_normalizes_to_non_negative,
    test_leading_zeros_decimal,
    test_leading_zeros_hex,
    test_all_zeros,
    test_decimal_value_exceeds_one_limb,
    test_decimal_value_exceeds_multiple_limbs,
    test_hex_value_exceeds_one_limb,
    test_binary_value_exceeds_one_limb,
    test_negative_multi_limb,
    test_cross_check_all_radixes,
    test_cross_check_negative_all_radixes,
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
