from fixedint import UInt16, UInt32


class BigInt:
    is_negative: bool
    values: list[UInt16] =[]
    RADIX = 1<<16
    RADIX_SHIFT =16
    RADIX_MASK = (1<<16)-1
    
    ZERO=0
    
    DIGITS ={
            '0':UInt16(0),
            '1':UInt16(1),
            '2':UInt16(2),
            '3':UInt16(3),
            '4':UInt16(4),
            '5':UInt16(5),
            '6':UInt16(6),
            '7':UInt16(7),
            '8':UInt16(8),
            '9':UInt16(9),
            'A':UInt16(10),
            'B':UInt16(11),
            'C':UInt16(12),
            'D':UInt16(13),
            'E':UInt16(14),
            'F':UInt16(15)
            }

    #|self| > |oth|
    #returns:
    # 1 if self > oth
    # -1 if oth > self
    def abs_compare(self, oth):
        l1 = len(self.values)
        l2= len(oth.values)

        if l1> l2: return 1
        if l2 > l1: return -1 

        for x, y in zip(self.values[::-1], oth.values[::-1]):
            if x > y: return 1
            if y > x: return -1

        return 0
    
    def __lt__(self, oth):
        if self.is_negative:
            if not oth.is_negative:
                return True
            return self.abs_compare(oth) == 1
        else:
            if oth.is_negative:
                return False
            return self.abs_compare(oth) == -1


    def __init__(self, values: list[UInt16], is_negative: bool = False):
        self.is_negative = is_negative
        self.values = values;

    def neg_mut(self):
        self.is_negative = not self.is_negative

    def debug_str(self):
        return f"{'-' if self.is_negative else ''}{self.values}"


    def add(self, oth: BigInt):
        #handle signs
        if self.is_negative != oth.is_negative:
            oth.neg_mut()
            val = self.sub(oth)
            oth.neg_mut()
            return val
        #both have the same sign

        #add
        added =[]
        carry = UInt32(0)
        for x, y in long_zip(self.values, oth.values):
            res = UInt32(x) + UInt32(y) + UInt32(carry)
            added.append(UInt16(res & self.RADIX_MASK))
            carry = res >> self.RADIX_SHIFT

        if carry > 0:
            added.append(UInt16(carry))
        
        return BigInt(added, self.is_negative)
    
    __add__ = add 

    def sub(self, oth: BigInt):
        if self.is_negative != oth.is_negative:
            oth.neg_mut()
            val = self.add(oth)
            oth.neg_mut()
            return val
        #both have the same sign
        
        #ensure |self| > |oth|
        is_negative = self.is_negative
        cmp = self.abs_compare(oth)
        if cmp ==0:
            return BigInt([UInt16(0)])
        if cmp < 0:
            is_negative = not is_negative
            self, oth = oth,self

        #subtraction
        added =[]
        carry = UInt32(0)
        for x, y in long_zip(self.values, oth.values):
            x = UInt32(x)
            last_carry = UInt32(carry)
            carry = 0
            while x < (y + last_carry):
                carry+=1 
                x+= self.RADIX
            res = x - UInt32(y) - UInt32(last_carry)
            added.append(UInt16(res & self.RADIX_MASK))

        res =BigInt(added, is_negative)
        res.trim()
        return res

    __sub__ = sub

    def neg(self):
        return BigInt(self.values[::], not self.is_negative)
    __neg__ = neg


    def trim(self):
        i = len(self.values) -1
        while i > 0 and self.values[i] == 0:
            i-=1
        self.values = self.values[:i+1]

    def r_shift(self, n: int):
        if n<0: return self.l_shift(-n)
        words = n >> 4 #n/16

        if words >= len(self.values):
            return self.ZERO

        in_word = n & 0xf #n%16

        in_word_mask = (1 << in_word) - 1

        vals = self.values[words:]
        # print(words, in_word, self.values)
        #only if in_word != 0 otherwise nop
        if in_word:
            for i in range(len(vals) - 1):
                dword = UInt32(vals[i]) + (UInt32(vals[i+1]) << BigInt.RADIX_SHIFT)
                vals[i] = UInt16(dword >> in_word)
            vals[-1] = UInt16(vals[-1] >> in_word)
        res = BigInt(vals, self.is_negative) 
        res.trim()
        # print(res.values, res.abs_compare(BigInt([UInt16(0)])))
        if res.abs_compare(BigInt([UInt16(0)])) == 0:
            res.is_negative = False
        return  res

    def l_shift(self, n: int):
        if n < 0: return self.r_shift(-n)
        
        words = n >> 4 #n/16
        in_word = n & 15 #n%16

        in_word_mask = ((1 << in_word) - 1) << (BigInt.RADIX_SHIFT - in_word)
        # print(words, in_word, self.values)
        vals = [UInt16(0) for _ in range(words)] + self.values
        # print(vals, in_word)
        #only if in_word != 0 otherwise nop
        if in_word:
            carry = 0
            for i in range(words, len(vals)):
                # print(vals[i], vals[i] << in_word, carry)
                nvals = UInt16((vals[i] << in_word) + carry)
                carry = (vals[i] & in_word_mask) >> (BigInt.RADIX_SHIFT - in_word) 
                vals[i] = nvals
                # print(carry, vals[i])
            if carry != 0:
                vals.append(UInt16(carry))
        return BigInt(vals, self.is_negative)



    def simple_mul(self, oth):
        #^ - xor
        sign = self.is_negative^oth.is_negative
        
        intermediate = []

        #make intermediate
        for i1, a in enumerate(self.values):
            digits = [UInt32(0) for _ in range(len(self.values) + len(oth.values) + 2)]
            for i2, b in enumerate(oth.values):
                lo_ind = i1+i2
                res = UInt32(a) * UInt32(b) + digits[lo_ind]
                hi = UInt32(res >> BigInt.RADIX_SHIFT)
                lo = UInt32(res & BigInt.RADIX_MASK)
                digits[lo_ind] = lo
                digits[lo_ind+1] += hi

            #carry all digits
            carry = 0
            new_digits = [UInt16(0) for _ in range(len(digits))]
            for i, d in enumerate(digits):
                new_d = d+carry
                lo = UInt16(new_d & BigInt.RADIX_MASK)
                carry = UInt16(new_d >> BigInt.RADIX_SHIFT)
                new_digits[i] = lo
            intermediate.append(BigInt(new_digits))


        res = BigInt([UInt16(0)])
        #add intermediate
        
        for x in intermediate:
            res = res + x

        res.is_negative = sign 
        res.trim()
        return res



    @staticmethod
    def _trimmed(values, is_negative: bool = False) -> "BigInt":
        x = BigInt(list(values) if len(values) else [UInt16(0)], False)
        x.trim()                       # your in-place trim: zero -> [0]
        if x.values == [0]:            # zero is never negative
            return x
        x.is_negative = is_negative
        return x

    def _is_zero(self) -> bool:
        return all(int(v) == 0 for v in self.values)

    BITS = RADIX_SHIFT
    MASK = RADIX_MASK

    def karatsuba(self, other: BigInt) -> BigInt:
        a = BigInt._trimmed(self.values)
        b = BigInt._trimmed(other.values)
        negative = self.is_negative != other.is_negative

        if a._is_zero() or b._is_zero():
            return BigInt([UInt16(0)], False)

        la, lb = len(a.values), len(b.values)

        if la == 1 and lb == 1:
            p = int(a.values[0]) * int(b.values[0])
            return BigInt._trimmed([UInt16(p & self.MASK), UInt16(p >> self.BITS)], negative)

        m = (max(la, lb) + 1) // 2
        s = self.BITS * m

        a0 = BigInt._trimmed(a.values[:m])
        a1 = BigInt._trimmed(a.values[m:])
        b0 = BigInt._trimmed(b.values[:m])
        b1 = BigInt._trimmed(b.values[m:])

        z0 = a0.karatsuba(b0)
        z2 = a1.karatsuba(b1)
        z1 = z0 + z2 - (a0 - a1).karatsuba(b0 - b1)

        product = z0 + z1.l_shift(s) + z2.l_shift(2 * s)
        return BigInt._trimmed(product.values, negative)

    __mul__ = karatsuba

    def div(self, other):
        return self.divmod(other)[0]

    __floordiv__ = div

    def divmod(self, other):
        first = BigInt(self.values[::], self.is_negative)
        oth = BigInt(other.values[::], other.is_negative)
        sign = first.is_negative ^ oth.is_negative
        # print(first.debug_str(),'\n', oth.debug_str())
        if oth.abs_compare(BigInt([UInt16(0)])) == 0:
            raise ZeroDivisionError()
        if first.abs_compare(self.ZERO) == 0:
            return BigInt([UInt16(0)]), BigInt([UInt16(0)])

        i = 0
        while oth.abs_compare(first) < 0:
            i+=1
            oth = oth.l_shift(1)

        first.is_negative = False
        oth.is_negative = False
        res = BigInt([UInt16(0)])
        while i >= 0:
            # print(self.debug_str(), '/ ', oth.debug_str())
            if first.abs_compare(oth) >= 0:
                first = first - oth
                # print("new_self: ", self.debug_str())
                res = res + BigInt([UInt16(1)]).l_shift(i)

            oth = oth.r_shift(1)
            i -= 1

        if res.abs_compare(self.ZERO) != 0:
            res.is_negative = sign
        if first.abs_compare(self.ZERO) == 0:
            return (res,first)
        first.is_negative = self.is_negative
        # print(first.debug_str(), first < BigInt([UInt16(0)]))
        if first < self.ZERO:
            first = first + other
            # print(first.debug_str())

        return (res, first) 
        
    def mod(self, oth):
        return self.divmod(oth)[1]

    __mod__ = mod

    @staticmethod
    def from_radix_old(radix: int, num:str):
        if radix > 16 or radix <2:
            raise ValueError(f"Radix must be in range [2;16] is: {radix}")
        exp = BigInt([UInt16(1)])
        res = BigInt([UInt16(0)])
        _radix = BigInt([UInt16(radix)])
        if num[0] == '-':
            num = num[1:]
            is_negative =True
        else:
            is_negative = False
        num = num.upper()

        for d in num[::-1]:
            val = BigInt.DIGITS.get(d, None)
            if val == None or val >= radix:
                raise ValueError(f"Not a valid digit: {d}")
            res = res + BigInt([val]) * exp
            exp = exp*(_radix)

        res.is_negative = is_negative
        #remove -0
        if (len(res.values) ==1 and res.values[0] == UInt16(0)):
            res.is_negative = False
        return res
        

    @staticmethod
    def from_radix(radix: int, num: str):
        if radix > 16 or radix < 2:
            raise ValueError(f"Radix must be in range [2;16] is: {radix}")

        is_negative = num.startswith('-')
        if is_negative:
            num = num[1:]
        num = num.upper()

        # validate + convert to plain ints once
        digits = []
        for d in num:
            v = BigInt.DIGITS.get(d)
            if v is None or v >= radix:
                raise ValueError(f"Not a valid digit: {d}")
            digits.append(int(v))

        # largest k with radix**k <= 0xFFFF
        k = 1
        while radix ** (k + 1) <= 0xFFFF:
            k += 1

        limbs = [0]  # little endian, plain ints
        for i in range(0, len(digits), k):
            chunk = digits[i:i + k]
            mult = radix ** len(chunk)       # last chunk may be shorter
            carry = 0
            for v in chunk:                  # value of chunk, < 2^16
                carry = carry * radix + v

            # limbs = limbs * mult + carry, in place, one pass
            for j in range(len(limbs)):
                t = limbs[j] * mult + carry  # always < 2^32
                limbs[j] = t & 0xFFFF
                carry = t >> 16
            if carry:
                limbs.append(carry)

        res = BigInt([UInt16(x) for x in limbs])
        res.is_negative = is_negative and not (len(limbs) == 1 and limbs[0] == 0)
        return res

    @staticmethod
    def EEA(x, y):

        a = BigInt(x.values)
        b = BigInt(y.values)
        if a.abs_compare(b) < 0: 
            a,b=b,a
            swap =True
        else: 
            swap = False
        d, u,v =BigInt._EEA(a,b)


        if swap:
            u, v= v, u

        if x.is_negative:
            u.neg_mut()
        if y.is_negative:
            v.neg_mut()

        return d, u, v

    @staticmethod
    def _EEA(a: BigInt, b: BigInt):

        if b.abs_compare(BigInt.ZERO) == 0:
            return a, BigInt([UInt16(1)]), BigInt([UInt16(0)])
        q,r = a.divmod(b)
        d, u, v = BigInt._EEA(b,r)

        return d, v, u - q*v
        
    def mod_inv(self, m):
        d, inv,_ = BigInt.EEA(self, m)
        if d.abs_compare(BigInt([UInt16(1)])) != 0:
            raise ValueError(f"gcd of {self.debug_str()}, {m.debug_str} is {d.debug_str} not 1, no modular inverse")
        return inv



def long_zip(*args, zero=UInt16(0)):


    def get(l: list, ind: int):
        if len(l) <= ind: return zero
        else: return l[ind]

    length = max(len(x) for x in args)
    
    return (tuple((get(x, i) for x in args )) for i in range(length))



BigInt.ZERO = BigInt([UInt16(0)])
