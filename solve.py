##
# 2WF90 Algebra for Security -- Software Assignment 1 
# Integer and Modular Arithmetic
# solve.py
#
#
# Group number:
# group_number 
#
# Author names and student IDs:
# Jerzy Puchalski 2253461
# author_name_2 (author_student_ID_2)
# author_name_3 (author_student_ID_3)
# author_name_4 (author_student_ID_4)
##

# Import built-in json library for handling input/output 
import json
from integer import BigInt


DIGIT_CHARS = "0123456789ABCDEF"
 
 
def is_zero(a):
    return all(int(v) == 0 for v in a.values)
 
 
def to_radix(a, radix):
    """BigInt -> string in the given radix (2..16). Repeated short division of the
    16-bit limbs by radix**k, so every intermediate value stays below 2**32."""
    k = 1
    while radix ** (k + 1) <= 0xFFFF:
        k += 1
    chunk = radix ** k
    limbs = [int(v) for v in a.values]
    out = []
    while any(limbs):
        rem = 0
        for i in range(len(limbs) - 1, -1, -1):
            cur = (rem << 16) | limbs[i]
            limbs[i] = cur // chunk
            rem = cur % chunk
        for _ in range(k):
            out.append(DIGIT_CHARS[rem % radix])
            rem //= radix
    while out and out[-1] == "0":
        out.pop()
    if not out:
        return "0"
    s = "".join(reversed(out))
    return "-" + s if a.is_negative else s
 
 
def solve_exercise(exercise_location: str, answer_location: str):
    """
    solves an exercise specified in the file located at exercise_location and
    writes the answer to a file at answer_location. Note: the file at
    answer_location might not exist yet and, hence, might still need to be created.
    """
 
    # Open file at exercise_location for reading.
    with open(exercise_location, "r") as exercise_file:
        # Deserialize JSON exercise data present in exercise_file to corresponding Python exercise data
        exercise = json.load(exercise_file)
 
    ### Parse and solve ###
    radix = exercise["radix"]
    op = exercise["operation"]
    x = BigInt.from_radix(radix, exercise["x"])
    y = BigInt.from_radix(radix, exercise["y"]) if "y" in exercise else None
 
    def fmt(a):
        return to_radix(a, radix)
 
    answer = None
 
    # Check type of exercise
    if exercise["type"] == "integer_arithmetic":
        # Check what operation within the integer arithmetic operations we need to solve
        if op == "addition":
            answer = {"answer": fmt(x + y)}
        elif op == "subtraction":
            answer = {"answer": fmt(x - y)}
        elif op == "multiplication_primary":
            answer = {"answer": fmt(x.simple_mul(y))}
        elif op == "multiplication_karatsuba":
            answer = {"answer": fmt(x.karatsuba(y))}
        elif op == "extended_euclidean_algorithm":
            if is_zero(x) and is_zero(y):
                answer = {"answer-a": None, "answer-b": None, "answer-gcd": None}
            else:
                d, a, b = BigInt.EEA(x, y)
                answer = {"answer-a": fmt(a), "answer-b": fmt(b), "answer-gcd": fmt(d)}
    else:  # exercise["type"] == "modular_arithmetic"
        m = BigInt.from_radix(radix, exercise["modulus"])
        if is_zero(m):
            # undefined: all keys of the answer are null
            answer = {"answer": None}
        # Check what operation within the modular arithmetic operations we need to solve
        elif op == "reduction":
            answer = {"answer": fmt(x.mod(m))}
        elif op == "addition":
            answer = {"answer": fmt((x + y)%(m))}
        elif op == "subtraction":
            answer = {"answer": fmt((x - y)%(m))}
        elif op == "multiplication":
            answer = {"answer": fmt((x * y)%(m))}
        elif op == "inversion":
            try:
                answer = {"answer": fmt(x.mod_inv(m))}
            except ValueError as e:
                answer = {"answer": None}
 
    # Open file at answer_location for writing, creating the file if it does not exist yet
    # (and overwriting it if it does already exist).
    with open(answer_location, "w") as answer_file:
        # Serialize Python answer data (stored in answer) to JSON answer data and write it to answer_file
        json.dump(answer, answer_file, indent=4)
 
 
# You can call your function from here
# Please do not *run* code outside this block
# You can however define other functions or constants
if __name__ == '__main__':
    # to avoid using sys.setrecursionlimit
    import ctypes
    ctypes.pythonapi.Py_SetRecursionLimit(ctypes.c_int(4000))
    solve_exercise('Simple/Exercises/exercise0.json', 'Simple/Answers/answer0.json')
