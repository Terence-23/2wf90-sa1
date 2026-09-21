"""
Standalone addition/subtraction tests for a base-2^16 limb BigInt.
No pytest required -- just run: python test_bigint.py

Assumes:
  - BigInt(values: list[int], is_negative: bool = False)
  - values is little-endian (values[0] = least significant limb)
  - __add__ and __sub__ are implemented
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
    print(b.values)
    val = 0
    for i, limb in enumerate(int(x) for x in b.values):
        val += limb << (RADIX_SHIFT * i)
    print(val)
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


# ---------------------------------------------------------------------------
# Addition tests
# ---------------------------------------------------------------------------

def test_add_zero():
    a = mk(5)
    b = mk(0)
    assert_equal_value(a + b, 5)


def test_add_positive_positive_no_carry():
    a = mk(10)
    b = mk(20)
    assert_equal_value(a + b, 30)


def test_add_positive_positive_single_limb_carry():
    # 0xFFFF + 0x0001 -> carries into a new limb
    a = mk(0xFFFF)
    b = mk(1)
    assert_equal_value(a + b, RADIX)


def test_add_positive_positive_multi_limb_carry():
    # limbs all at max, forces carry to propagate across several limbs
    a = mk(0xFFFF, 0xFFFF, 0xFFFF)
    b = mk(1)
    assert_equal_value(a + b, (1 << 48))


def test_add_negative_negative():
    a = mk(10, neg=True)
    b = mk(20, neg=True)
    assert_equal_value(a + b, -30)


def test_add_negative_negative_with_carry():
    a = mk(0xFFFF, neg=True)
    b = mk(1, neg=True)
    assert_equal_value(a + b, -RADIX)


def test_add_positive_negative_result_positive():
    # 100 + (-40) = 60
    a = mk(100)
    b = mk(40, neg=True)
    assert_equal_value(a + b, 60)


def test_add_positive_negative_result_negative():
    # 40 + (-100) = -60
    a = mk(40)
    b = mk(100, neg=True)
    assert_equal_value(a + b, -60)


def test_add_positive_negative_result_zero():
    a = mk(500)
    b = mk(500, neg=True)
    assert_equal_value(a + b, 0)


def test_add_negative_positive_borrow_across_limb():
    # (-0x10000) + 1 = -0xFFFF, exercises borrow when magnitudes subtract
    a = mk(0, 1, neg=True)  # -65536
    b = mk(1)
    assert_equal_value(a + b, -0xFFFF)


def test_add_large_random_cross_check():
    random.seed(42)
    for _ in range(50):
        x = random.randint(-(1 << 80), 1 << 80)
        y = random.randint(-(1 << 80), 1 << 80)
        result = from_int(x) + from_int(y)
        assert_equal_value(result, x + y)


# ---------------------------------------------------------------------------
# Subtraction tests
# ---------------------------------------------------------------------------

def test_sub_zero():
    a = mk(5)
    b = mk(0)
    assert_equal_value(a - b, 5)


def test_sub_positive_positive_no_borrow():
    a = mk(30)
    b = mk(10)
    assert_equal_value(a - b, 20)


def test_sub_positive_positive_result_negative():
    a = mk(10)
    b = mk(30)
    assert_equal_value(a - b, -20)


def test_sub_positive_positive_result_zero():
    a = mk(42)
    b = mk(42)
    assert_equal_value(a - b, 0)


def test_sub_single_limb_borrow():
    # 0x10000 - 1 = 0xFFFF, forces borrow from the next limb
    a = mk(0, 1)  # 65536
    b = mk(1)
    assert_equal_value(a - b, 0xFFFF)


def test_sub_multi_limb_borrow():
    # 0x1_0000_0000_0000 - 1, borrow ripples across three limbs
    a = mk(0, 0, 0, 1)
    b = mk(1)
    assert_equal_value(a - b, (1 << 48) - 1)


def test_sub_negative_negative():
    # (-30) - (-10) = -20
    a = mk(30, neg=True)
    b = mk(10, neg=True)
    assert_equal_value(a - b, -20)


def test_sub_negative_negative_result_positive():
    # (-10) - (-30) = 20
    a = mk(10, neg=True)
    b = mk(30, neg=True)
    assert_equal_value(a - b, 20)


def test_sub_positive_negative():
    # 10 - (-30) = 40
    a = mk(10)
    b = mk(30, neg=True)
    assert_equal_value(a - b, 40)


def test_sub_negative_positive():
    # (-10) - 30 = -40
    a = mk(10, neg=True)
    b = mk(30)
    assert_equal_value(a - b, -40)


def test_sub_negative_positive_with_carry():
    # (-0xFFFF) - 1 = -0x10000
    a = mk(0xFFFF, neg=True)
    b = mk(1)
    assert_equal_value(a - b, -RADIX)


def test_sub_large_random_cross_check():
    random.seed(7)
    for _ in range(50):
        x = random.randint(-(1 << 80), 1 << 80)
        y = random.randint(-(1 << 80), 1 << 80)
        result = from_int(x) - from_int(y)
        assert_equal_value(result, x - y)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

ALL_TESTS = [
    test_add_zero,
    test_add_positive_positive_no_carry,
    test_add_positive_positive_single_limb_carry,
    test_add_positive_positive_multi_limb_carry,
    test_add_negative_negative,
    test_add_negative_negative_with_carry,
    test_add_positive_negative_result_positive,
    test_add_positive_negative_result_negative,
    test_add_positive_negative_result_zero,
    test_add_negative_positive_borrow_across_limb,
    test_add_large_random_cross_check,
    test_sub_zero,
    test_sub_positive_positive_no_borrow,
    test_sub_positive_positive_result_negative,
    test_sub_positive_positive_result_zero,
    test_sub_single_limb_borrow,
    test_sub_multi_limb_borrow,
    test_sub_negative_negative,
    test_sub_negative_negative_result_positive,
    test_sub_positive_negative,
    test_sub_negative_positive,
    test_sub_negative_positive_with_carry,
    test_sub_large_random_cross_check,
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
