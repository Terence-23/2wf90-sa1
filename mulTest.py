"""
Standalone multiplication tests for a base-2^16 limb BigInt.
Runs the full suite against both simple_mul and karatsuba.
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




MULTIPLIERS = {
    "simple": lambda a, b: a.simple_mul(b),
    "karatsuba": lambda a, b: a.karatsuba(b),
}
_current = "simple"


def mul(a: BigInt, b: BigInt) -> BigInt:
    """Dispatches to whichever multiplication is currently under test."""
    return MULTIPLIERS[_current](a, b)


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
# Karatsuba-specific tests (split / recombination stress)
# ---------------------------------------------------------------------------

def test_mul_unbalanced_sizes():
    random.seed(7)
    for small_bits, big_bits in [(16, 400), (17, 300), (32, 640), (100, 101)]:
        for _ in range(10):
            x = random.getrandbits(small_bits) * random.choice([-1, 1])
            y = random.getrandbits(big_bits) * random.choice([-1, 1])
            assert_equal_value(mul(from_int(x), from_int(y)), x * y)


def test_mul_all_ones_limbs_various_lengths():
    # RADIX**k - 1 maximizes carries in every partial product
    for k in range(1, 20):
        x = (1 << (16 * k)) - 1
        assert_equal_value(mul(from_int(x), from_int(x)), x * x)
        assert_equal_value(mul(from_int(-x), from_int(x)), -x * x)


def test_mul_zero_low_or_high_halves():
    # low half all zero / high half all zero after the split
    x = 1 << (16 * 8)
    y = (1 << (16 * 8)) + 5
    assert_equal_value(mul(from_int(x), from_int(y)), x * y)
    assert_equal_value(mul(from_int(5), from_int(y)), 5 * y)


def test_mul_odd_and_even_limb_counts():
    random.seed(11)
    for n in range(1, 25):
        x = random.getrandbits(16 * n) | (1 << (16 * n - 1))
        y = random.getrandbits(16 * n) | (1 << (16 * n - 1))
        assert_equal_value(mul(from_int(x), from_int(y)), x * y)


def test_mul_very_large_random():
    random.seed(2024)
    for _ in range(10):
        x = random.randint(-(1 << 2000), 1 << 2000)
        y = random.randint(-(1 << 2000), 1 << 2000)
        assert_equal_value(mul(from_int(x), from_int(y)), x * y)


def test_mul_commutative_and_agrees_with_simple():
    random.seed(5)
    for _ in range(20):
        x = random.randint(-(1 << 600), 1 << 600)
        y = random.randint(-(1 << 600), 1 << 600)
        a, b = from_int(x), from_int(y)
        assert to_int(a.karatsuba(b)) == to_int(a.simple_mul(b))
        assert to_int(a.karatsuba(b)) == to_int(b.karatsuba(a))


def test_karatsuba_does_not_mutate_operands():
    x, y = (1 << 500) + 12345, -((1 << 480) + 999)
    a, b = from_int(x), from_int(y)
    a.karatsuba(b)
    assert_equal_value(a, x)
    assert_equal_value(b, y)

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
    test_mul_unbalanced_sizes,
    test_mul_all_ones_limbs_various_lengths,
    test_mul_zero_low_or_high_halves,
    test_mul_odd_and_even_limb_counts,
    test_mul_very_large_random,
]

# only meaningful once both methods exist
CROSS_TESTS = [
    test_mul_commutative_and_agrees_with_simple,
    test_karatsuba_does_not_mutate_operands,
]


def run_all():
    global _current
    total_failed = 0
    for impl in MULTIPLIERS:
        _current = impl
        tests = ALL_TESTS + (CROSS_TESTS if impl == "karatsuba" else [])
        passed, failures = 0, []
        print(f"\n=== {impl} ===")
        for fn in tests:
            try:
                fn()
            except Exception as e:
                failures.append((fn.__name__, e, traceback.format_exc()))
                print(f"FAIL  {fn.__name__}: {e}")
            else:
                passed += 1
                print(f"PASS  {fn.__name__}")
        print(f"{passed} passed, {len(failures)} failed out of {len(tests)}")
        for name, e, tb in failures:
            print(f"\n{name}:\n{tb}")
        total_failed += len(failures)
    return total_failed == 0


if __name__ == "__main__":
    import sys
    success = run_all()
    sys.exit(0 if success else 1)
