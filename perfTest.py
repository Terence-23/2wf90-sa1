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

LIMIT = 5.0            # seconds, per single operation
MAX_VAL = 10 ** 500    # operands up to this
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
    "mod add":      ("xym", lambda x, y, m: (x+y)%m, lambda x, y, m: (x + y) % m),
    "mod sub":      ("xym", lambda x, y, m: (x-y)%m, lambda x, y, m: (x - y) % m),
    "mod mul":      ("xym", lambda x, y, m: (x*y)%m, lambda x, y, m: (x * y) % m),
    #"mod inv":      ("xm",  lambda x, m: x.mod_inv(m),      lambda x, m: pow(x, -1, m)),
}

# ---------------------------------------------------------------------------
# Input generation
# ---------------------------------------------------------------------------

def rand_signed(bound=MAX_VAL):
    return random.randint(-bound + 1, bound - 1)


def rand_modulus():
    # m in N (>= 2), up to 10^500
    return random.randint(2, MAX_VAL - 1)


def inputs_for(name, kind, trial):
    """Yield python-int inputs. Trial 0 is a worst case: max magnitude."""
    if kind == "xy":
        if trial == 0:
            return (MAX_VAL - 1, -(MAX_VAL - 1))          # max size, mixed sign
        return (rand_signed(), rand_signed())
    m = MAX_VAL - 1 if trial == 0 else rand_modulus()
    if name == "mod inv":
        while True:                                        # need gcd(x, m) == 1
            x = random.randint(1, m - 1)
            if math.gcd(x, m) == 1:
                return (x, m)
    if kind == "xm":
        return ((-(MAX_VAL - 1) if trial == 0 else rand_signed()), m)
    return (rand_signed(), rand_signed(), m)               # "xym"


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def run_op(name, kind, call, ref):
    worst = 0.0
    for trial in range(TRIALS):
        py = inputs_for(name, kind, trial)
        big = tuple(from_int(v) for v in py)
        t0 = time.perf_counter()
        result = call(*big)
        elapsed = time.perf_counter() - t0
        worst = max(worst, elapsed)
        expected = ref(*py)
        got = to_int(result)
        assert got == expected, f"wrong result on trial {trial} (inputs {py[0]:.3e}...)"
    return worst


def main():
    print(f"Operands up to 10^500 (~{MAX_VAL.bit_length()} bits, "
          f"~{(MAX_VAL.bit_length() + 15) // 16} limbs), limit {LIMIT}s\n")
    print(f"{'operation':<18}{'worst time':>12}   status")
    print("-" * 44)
    ok = True
    for name, (kind, call, ref) in OPS.items():
        try:
            t = run_op(name, kind, call, ref)
        except AttributeError as e:
            print(f"{name:<18}{'-':>12}   SKIP (missing method: {e})")
            continue
        except Exception as e:
            print(f"{name:<18}{'-':>12}   FAIL ({type(e).__name__}: {e})")
            ok = False
            continue
        status = "PASS" if t <= LIMIT else "SLOW"
        ok &= t <= LIMIT
        print(f"{name:<18}{t:>11.4f}s   {status}")

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
