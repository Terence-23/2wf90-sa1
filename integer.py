from fixedint import UInt16, UInt32
from typing import Iterable

class BigInt:
    is_negative: bool
    values: list[UInt16] =[]
    RADIX = 1<<16
    RADIX_SHIFT =16
    RADIX_MASK = (1<<16)-1
    
    DIGITS ={
            '0':0,
            '1':1,
            '2':2,
            '3':3,
            '4':4,
            '5':5,
            '6':6,
            '7':7,
            '8':8,
            '9':9,
            'A':10,
            'B':11,
            'C':12,
            'D':13,
            'E':14,
            'F':15
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

    def __init__(self, values: list[UInt16], is_negative: bool = False):
        self.is_negative = is_negative
        self.values = values;

    def neg(self):
        self.is_negative = not self.is_negative

    def add(self, oth: BigInt):
        #handle signs
        if self.is_negative != oth.is_negative:
            oth.neg()
            self.sub(oth)
        #both have the same sign

        #add
        l =  max(len(self.values), len(oth.values))
        added =[]
        carry = UInt32(0)
        for x, y in long_zip(self.values, oth.values):
            res = UInt32(x) + UInt32(y) + UInt32(carry)
            added.append(res & self.RADIX_MASK)
            carry = res >> self.RADIX_SHIFT

        return BigInt(added, self.is_negative)
    def sub(self, oth: BigInt):
        if self.is_negative != oth.is_negative:
            oth.neg()
            self.sub(oth)
        #both have the same sign
        
        #ensure |self| > |oth|
        is_negative = self.is_negative
        cmp = self.abs_compare(oth)
        if cmp ==0:
            return BigInt([])
        if cmp < 0:
            is_negative = not is_negative
            self, oth = oth,self

        #add
        l =  max(len(self.values), len(oth.values))
        added =[]
        carry = UInt32(0)
        for x, y in long_zip(self.values, oth.values):
            res = UInt32(x) - UInt32(y) - UInt32(carry)
            while (res < 0):
                carry+=1
                res+=self.RADIX
            added.append(res & self.RADIX_MASK)

        return BigInt(added, is_negative)

    def from_radix(self, radix: int, num:str):
        pass

def long_zip(*args, zero=UInt16(0)):

    def get(l: list, ind: int):
        if len(l) >= ind: return zero
        else: return l[ind]

    length = max(len(x) for x in args)
    
    return (tuple((get(x, i) for x in args )) for i in range(length))


def test():
    pass

if __name__ == "__main__":
    test()


