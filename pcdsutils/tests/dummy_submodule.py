"""
Submodule to import from for test_profile
"""
from inspect import getmembers


class SomeClass:
    def __init__(self):
        self.some_attr = 1

    def method(self):
        return getmembers(self)

    @classmethod
    def cls_method(cls):
        return 2

    @staticmethod
    def stat_method():
        return 3


def some_function():
    return 4
