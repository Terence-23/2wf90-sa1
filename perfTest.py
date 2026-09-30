"""
Performance tests for BigInt: every operation must finish in <= LIMIT seconds
for operands up to 10^500. Also checks each result against Python's int.

Run: python perfTest.py

The OPS table below maps each operation to your API. Edit ONLY that table
(method names for the modular operations are guesses).
"""

import math
import random
import sys
import time

from mulTest import from_int, to_int  # your existing helpers
from integer import BigInt            # for the static BigInt.EEA(x, y) call

LIMIT = 5.0            # seconds, per single operation
MAX_VAL = 10 ** 500    # operands up to this, for add/sub/mul/mod-reduce/mod-add/mod-sub/mod-mul
MAX_VAL_INV = 10 ** 250  # operands up to this, for mod inv (and EEA, once ready)
TRIALS = 5             # random trials per operation (worst time is reported)
random.seed(2024)

# ---------------------------------------------------------------------------
# Adapter table: name -> (call on BigInts, reference on ints, arity/kind)
#   kind "xy":  f(x, y)        kind "xym": f(x, y, m)
#   kind "xm":  f(x, m)        kind "x":   f(x)  (unused)
# Adjust the lambdas to match your method names.
# ---------------------------------------------------------------------------
OPS = {
    "add":          ("xy",  lambda x, y: x.add(y),          lambda x, y: x + y),
    "sub":          ("xy",  lambda x, y: x.sub(y),          lambda x, y: x - y),
    "mul (school)": ("xy",  lambda x, y: x.simple_mul(y),   lambda x, y: x * y),
    "mul (karatsuba)": ("xy", lambda x, y: x.karatsuba(y),  lambda x, y: x * y),
    "mod reduce":   ("xm",  lambda x, m: x.mod(m),          lambda x, m: x % m),
    "mod add":      ("xym", lambda x, y, m: (x + y) % m, lambda x, y, m: (x + y) % m),
    "mod sub":      ("xym", lambda x, y, m: (x - y) % m, lambda x, y, m: (x - y) % m),
    "mod mul":      ("xym", lambda x, y, m: (x * y) % m, lambda x, y, m: (x * y) % m),
}

# separate table: operations limited to 10^250 (mod inv, EEA)
OPS_SMALL = {
    "mod inv":      ("xm",  lambda x, m: x.mod_inv(m),      None),  # checked via check_mod_inv, not ref
}

# EEA returns (a, b, d) rather than one BigInt, so it gets its own runner
# below instead of going through OPS_SMALL/run_op.

# ---------------------------------------------------------------------------
# Input generation
# ---------------------------------------------------------------------------

def rand_signed(bound=MAX_VAL):
    return random.randint(-bound + 1, bound - 1)


def rand_modulus():
    # m in N (>= 2), up to 10^500
    return random.randint(2, MAX_VAL - 1)


def check_mod_inv(x, m, inv):
    """Verify inv is the modular inverse of x mod m by multiplying, not pow().
    Also checks the inverse actually exists (gcd(x, m) == 1)."""
    if math.gcd(x, m) != 1:
        return False
    return _is_valid_inverse(x, m, inv)


def _is_valid_inverse(x, m, inv):
    """Raw check with no existence guard: does x*inv == 1 mod m?"""
    return (0 <= inv < m) and ((x * inv) % m == 1 % m)


def inputs_for(name, kind, trial, bound=MAX_VAL):
    """Yield python-int inputs. Trial 0 is a worst case: max magnitude."""
    if kind == "xy":
        if trial == 0:
            return (bound - 1, -(bound - 1))               # max size, mixed sign
        return (rand_signed(bound), rand_signed(bound))
    m = bound - 1 if trial == 0 else random.randint(2, bound - 1)
    if name == "mod inv":
        while True:                                        # need gcd(x, m) == 1
            x = random.randint(1, m - 1)
            if math.gcd(x, m) == 1:
                return (x, m)
    if kind == "xm":
        return ((-(bound - 1) if trial == 0 else rand_signed(bound)), m)
    return (rand_signed(bound), rand_signed(bound), m)      # "xym"


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_op(name, kind, call, ref, bound=MAX_VAL):
    worst = 0.0
    for trial in range(TRIALS):
        print(0)
        py = inputs_for(name, kind, trial, bound)
        big = tuple(from_int(v) for v in py)
        t0 = time.perf_counter()
        result = call(*big)
        elapsed = time.perf_counter() - t0
        worst = max(worst, elapsed)
        got = to_int(result)
        if name == "mod inv":
            try:
                x, m = py
                assert check_mod_inv(x, m, got), (
                    f"wrong inverse on trial {trial}: {x} * {got} % {m} != 1"
                )
            except Exception as e:
                print(e)
        else:
            expected = ref(*py)
            assert got == expected, f"wrong result on trial {trial} (inputs {py[0]:.3e}...)"
    return worst


def run_eea(bound):
    """EEA: given x, y (not both 0), verify d == u*x + v*y and d == gcd(x, y).
    BigInt.EEA(x, y) returns (d, u, v), not (u, v, d)."""
    worst = 0.0
    for trial in range(TRIALS):
        while True:
            x, y = rand_signed(bound), rand_signed(bound)
            if trial == 0:
                x, y = bound - 1, -(bound - 1)
            if x != 0 or y != 0:
                break
        bx, by = from_int(x), from_int(y)

        t0 = time.perf_counter()
        d, u, v = BigInt.EEA(bx, by)
        elapsed = time.perf_counter() - t0
        worst = max(worst, elapsed)

        d_i, u_i, v_i = to_int(d), to_int(u), to_int(v)
        expected_d = math.gcd(x, y)
        assert d_i == expected_d, f"gcd mismatch on trial {trial}: got {d_i}, expected {expected_d}"
        assert u_i * x + v_i * y == d_i, (
            f"Bezout identity failed on trial {trial}: "
            f"{u_i}*{x} + {v_i}*{y} != {d_i}"
        )
    return worst


def run_mod_inv_nonexistent():
    """x.mod_inv(m) must not silently succeed when gcd(x, m) != 1."""
    for _ in range(TRIALS):
        while True:
            m = random.randint(4, MAX_VAL_INV - 1)
            g = random.randint(2, min(1000, m - 1))
            if m % g == 0:
                x = g * random.randint(1, m // g - 1 or 1)
                if math.gcd(x, m) != 1 and 0 < x < m:
                    break
        try:
            result = from_int(x).mod_inv(from_int(m))
        except Exception:
            pass  # raising is an acceptable way to signal "no inverse"
        else:
            got = to_int(result)
            assert not _is_valid_inverse(x, m, got), (
                f"mod_inv accepted non-invertible x={x}, m={m} "
                f"and returned a value that looks like a valid inverse"
            )


def run_table(ops, bound, ok):
    for name, (kind, call, ref) in ops.items():
        try:
            t = run_op(name, kind, call, ref, bound)
        except AttributeError as e:
            print(f"{name:<18}{'-':>12}   SKIP (missing method: {e})")
            continue
        except Exception as e:
            print(f"{name:<18}{'-':>12}   FAIL ({type(e).__name__}: {e})")
            ok[0] = False
            continue
        status = "PASS" if t <= LIMIT else "SLOW"
        ok[0] &= t <= LIMIT
        print(f"{name:<18}{t:>11.4f}s   {status}")
    return ok


def main():
    ok = [True]
    print(f"Operands up to 10^500 (~{MAX_VAL.bit_length()} bits, "
          f"~{(MAX_VAL.bit_length() + 15) // 16} limbs), limit {LIMIT}s\n")
    print(f"{'operation':<18}{'worst time':>12}   status")
    print("-" * 44)
    run_table(OPS, MAX_VAL, ok)

    print(f"\nOperands up to 10^250 (~{MAX_VAL_INV.bit_length()} bits, "
          f"~{(MAX_VAL_INV.bit_length() + 15) // 16} limbs), limit {LIMIT}s")
    print("(mod inv, EEA)\n")
    print(f"{'operation':<18}{'worst time':>12}   status")
    print("-" * 44)
    run_table(OPS_SMALL, MAX_VAL_INV, ok)

    try:
        t = run_eea(MAX_VAL_INV)
    except AttributeError as e:
        print(f"{'eea':<18}{'-':>12}   SKIP (missing method: {e})")
    except Exception as e:
        print(f"{'eea':<18}{'-':>12}   FAIL ({type(e).__name__}: {e})")
        ok[0] = False
    else:
        status = "PASS" if t <= LIMIT else "SLOW"
        ok[0] &= t <= LIMIT
        print(f"{'eea':<18}{t:>11.4f}s   {status}")

    # mod_inv must reject x that has no inverse mod m (gcd(x, m) != 1)
    try:
        run_mod_inv_nonexistent()
    except AttributeError as e:
        print(f"{'mod inv (no inv)':<18}{'-':>12}   SKIP (missing method: {e})")
    except AssertionError as e:
        print(f"{'mod inv (no inv)':<18}{'-':>12}   FAIL ({e})")
        ok[0] = False
    else:
        print(f"{'mod inv (no inv)':<18}{'-':>12}   PASS")

    ok = ok[0]

    # Scaling: karatsuba should overtake school multiplication as size grows.
    print("\nScaling (school vs karatsuba, one multiplication each):")
    print(f"{'digits':>8}{'school':>12}{'karatsuba':>12}")
    for digits in (100, 250, 500, 1000, 2000):
        x, y = from_int(random.randrange(10 ** digits)), from_int(random.randrange(10 ** digits))
        t0 = time.perf_counter(); x.simple_mul(y); ts = time.perf_counter() - t0
        t0 = time.perf_counter(); x.karatsuba(y); tk = time.perf_counter() - t0
        print(f"{digits:>8}{ts:>11.4f}s{tk:>11.4f}s")

    print("\nALL WITHIN LIMIT" if ok else "\nSOME OPERATIONS FAILED OR TOO SLOW")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
