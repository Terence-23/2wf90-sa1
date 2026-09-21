"""
Standalone multiplication tests for a base-2^16 limb BigInt, using simple_mul.
No pytest required -- just run: python test_bigint_mul.py

Assumes:
  - BigInt(values: list[int], is_negative: bool = False)
  - values is little-endian (values[0] = least significant limb)
  - a.simple_mul(b) returns a new BigInt equal to a * b

If simple_mul is instead a standalone function (e.g. simple_mul(a, b)) rather
than a method, adjust the `mul()` helper below -- everything else stays the same.
"""

import random
import traceback

from fixedint import UInt16

from integer import BigInt  # adjust import to your module

RADIX = 1 << 16
MASK = RADIX - 1
RADIX_SHIFT = 16




def mul(a: BigInt, b: BigInt) -> BigInt:
    """Wrapper around simple_mul so the call site is adjustable in one place."""
    return a.simple_mul(b)



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

# ---------------------------------------------------------------------------
# Multiplication tests
# ---------------------------------------------------------------------------

def test_mul_by_zero():
    a = mk(123)
    b = mk(0)
    assert_equal_value(mul(a, b), 0)


def test_mul_zero_by_negative():
    a = mk(0)
    b = mk(50, neg=True)
    assert_equal_value(mul(a, b), 0)


def test_mul_by_one():
    a = mk(0xABCD, 0x1234)
    b = mk(1)
    assert_equal_value(mul(a, b), to_int(a))


def test_mul_positive_positive_no_carry():
    a = mk(3)
    b = mk(4)
    assert_equal_value(mul(a, b), 12)


def test_mul_positive_positive_single_limb_overflow():
    # 0xFFFF * 2 overflows a single limb, forces carry into a new limb
    a = mk(0xFFFF)
    b = mk(2)
    assert_equal_value(mul(a, b), 0xFFFF * 2)


def test_mul_max_single_limbs():
    # largest possible product of two single limbs
    a = mk(0xFFFF)
    b = mk(0xFFFF)
    assert_equal_value(mul(a, b), 0xFFFF * 0xFFFF)


def test_mul_multi_limb_by_single_limb():
    # multi-limb value times a single limb, carry propagates across limbs
    a = mk(0xFFFF, 0xFFFF, 0xFFFF)
    b = mk(2)
    assert_equal_value(mul(a, b), to_int(a) * 2)


def test_mul_multi_limb_by_multi_limb():
    a = mk(0x1234, 0x5678)   # 0x5678_1234
    b = mk(0x9ABC, 0xDEF0)   # 0xDEF0_9ABC
    assert_equal_value(mul(a, b), to_int(a) * to_int(b))


def test_mul_result_spans_many_limbs():
    # two 3-limb max values -> product spans up to 6 limbs
    a = mk(0xFFFF, 0xFFFF, 0xFFFF)
    b = mk(0xFFFF, 0xFFFF, 0xFFFF)
    assert_equal_value(mul(a, b), to_int(a) * to_int(b))


def test_mul_positive_positive():
    a = mk(100)
    b = mk(200)
    assert_equal_value(mul(a, b), 20000)


def test_mul_negative_negative():
    # (-a) * (-b) = positive
    a = mk(100, neg=True)
    b = mk(200, neg=True)
    assert_equal_value(mul(a, b), 20000)


def test_mul_positive_negative():
    a = mk(100)
    b = mk(200, neg=True)
    assert_equal_value(mul(a, b), -20000)


def test_mul_negative_positive():
    a = mk(100, neg=True)
    b = mk(200)
    assert_equal_value(mul(a, b), -20000)


def test_mul_negative_by_zero():
    a = mk(100, neg=True)
    b = mk(0)
    assert_equal_value(mul(a, b), 0)


def test_mul_negative_carry_across_limbs():
    a = mk(0xFFFF, 0xFFFF, neg=True)
    b = mk(3)
    assert_equal_value(mul(a, b), -(to_int(mk(0xFFFF, 0xFFFF)) * 3))


def test_mul_powers_of_two():
    # exercises clean shifts, e.g. 2^16 * 2^16 = 2^32
    a = mk(0, 1)      # 2^16
    b = mk(0, 1)      # 2^16
    assert_equal_value(mul(a, b), 1 << 32)


def test_mul_large_random_cross_check():
    random.seed(99)
    for _ in range(50):
        x = random.randint(-(1 << 80), 1 << 80)
        y = random.randint(-(1 << 80), 1 << 80)
        result = mul(from_int(x), from_int(y))
        assert_equal_value(result, x * y)


def test_mul_small_random_cross_check():
    # smaller magnitudes to catch off-by-one / single-limb edge cases
    random.seed(123)
    for _ in range(50):
        x = random.randint(-1000, 1000)
        y = random.randint(-1000, 1000)
        result = mul(from_int(x), from_int(y))
        assert_equal_value(result, x * y)


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

ALL_TESTS = [
    test_mul_by_zero,
    test_mul_zero_by_negative,
    test_mul_by_one,
    test_mul_positive_positive_no_carry,
    test_mul_positive_positive_single_limb_overflow,
    test_mul_max_single_limbs,
    test_mul_multi_limb_by_single_limb,
    test_mul_multi_limb_by_multi_limb,
    test_mul_result_spans_many_limbs,
    test_mul_positive_positive,
    test_mul_negative_negative,
    test_mul_positive_negative,
    test_mul_negative_positive,
    test_mul_negative_by_zero,
    test_mul_negative_carry_across_limbs,
    test_mul_powers_of_two,
    test_mul_large_random_cross_check,
    test_mul_small_random_cross_check,
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
