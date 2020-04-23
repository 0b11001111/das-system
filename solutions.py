#!/usr/bin/env python3
# Standard library modules.
from functools import partial

# Third party modules.

# Local modules

# Globals and constants variables.


# HelloWorld
print('hello world')


# LongestString
def longest_string(l):
    if not l:
        return None

    longest = ''
    for s in l:
        if len(s) >= len(longest):
            longest = s

    return longest


## FizzBuzz
def fizzbuzz(x):
    if x % 3 == 0 and x % 5 == 0:
        return 'FizzBuzz'
    elif x % 3 == 0:
        return 'Fizz'
    elif x % 5 == 0:
        return 'Buzz'

    return str(x)


## Palindrome
def palindrome(s):
    s = s.lower()
    return all(s[i] == s[-(i+1)] for i in range(len(s) // 2))


## CaesarI
def ascii_shift(c, shift=0):
    e = ord(c)
    offset = 65 if e < 97 else 97

    e -= offset

    if not 0 <= e < 26:
        return c

    return chr((e + shift) % 26 + offset)


def caesar(s, shift=0):
    return ''.join(map(partial(ascii_shift, shift=shift), s))


## CaesarII
# just send source code of `OutsideTheBox`


## Classes
class Shape:
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def __str__(self):
        return f'{type(self).__name__}(pos={(self.x, self.y)}, area={self.area()})'

    def area(self):
        # compute area of shape, has to be overwritten by subclasses
        raise NotImplementedError


class Rectangle(Shape):
    def __init__(self, x: float, y: float, h: float, w: float):
        super().__init__(x, y)
        self._h = h
        self._w = w

    def area(self):
        return self._h * self._w


class Square(Rectangle):
    def __init__(self, x: float, y: float, l: float):
        super().__init__(x, y, l, l)


class Circle(Shape):
    def __init__(self, x: float, y: float, r: float):
        super().__init__(x, y)
        self._r = r

    def area(self):
        from math import pi
        return pi * self._r**2


print(Rectangle(0, 0, 1, 5))
print(Square(5, 10, 4))
print(Circle(-3, 2.5, 1.0))


## OutsideTheBox
from collections import Counter


def blackbox(s):
    counts = list(Counter(s).values())
    if not counts:
        return True
    return all(counts[0] == c for c in counts)
