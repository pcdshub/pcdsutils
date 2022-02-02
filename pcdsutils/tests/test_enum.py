import pytest

from ..enum import HelpfulIntEnum


def test_subclass():
    class MyEnum(HelpfulIntEnum):
        A = 4
        B = 5
        C = 6

    assert MyEnum(4) == MyEnum.A
    assert MyEnum(5) == MyEnum.B
    assert MyEnum(6) == MyEnum.C

    with pytest.raises(ValueError):
        MyEnum(7)

    assert MyEnum["A"] == MyEnum.A == 4
    assert MyEnum["a"] == MyEnum.A == 4
    assert MyEnum["a"] == MyEnum.a == 4
    assert MyEnum.from_any("a") == MyEnum.A == 4
    assert MyEnum.from_any(4) == MyEnum.A == 4

    assert MyEnum["C"] == MyEnum.C == 6
    assert MyEnum["c"] == MyEnum.C == 6
    assert MyEnum["c"] == MyEnum.c == 6
    assert MyEnum.from_any("c") == MyEnum.C == 6
    assert MyEnum.from_any(6) == MyEnum.C == 6


def test_functional():
    MyEnum = HelpfulIntEnum("MyEnum", {"a": 1, "B": 2}, module=__name__)

    assert MyEnum["A"] == MyEnum.A == 1
    assert MyEnum["a"] == MyEnum.A == 1
    assert MyEnum["a"] == MyEnum.a == 1
    assert MyEnum.from_any("a") == MyEnum.A
    assert MyEnum.from_any(1) == MyEnum.A

    assert MyEnum["B"] == MyEnum.B == 2
    assert MyEnum["b"] == MyEnum.B == 2
    assert MyEnum["b"] == MyEnum.b == 2
    assert MyEnum.from_any("b") == MyEnum.B == 2
    assert MyEnum.from_any(2) == MyEnum.B == 2


def test_functional_list():
    MyEnum = HelpfulIntEnum("MyEnum", ["a", "b"], start=1, module=__name__)

    assert MyEnum["A"] == MyEnum.A == 1
    assert MyEnum["a"] == MyEnum.A == 1
    assert MyEnum["a"] == MyEnum.a == 1
    assert MyEnum.from_any("a") == MyEnum.A
    assert MyEnum.from_any(1) == MyEnum.A

    assert MyEnum["B"] == MyEnum.B == 2
    assert MyEnum["b"] == MyEnum.B == 2
    assert MyEnum["b"] == MyEnum.b == 2
    assert MyEnum.from_any("b") == MyEnum.B == 2
    assert MyEnum.from_any(2) == MyEnum.B == 2


def test_include():
    class MyEnum(HelpfulIntEnum):
        A = 4
        B = 5
        C = 6

    assert MyEnum.include([4, "c"]) == {MyEnum.A, MyEnum.C}


def test_exclude():
    class MyEnum(HelpfulIntEnum):
        A = 4
        B = 5
        C = 6

    assert MyEnum.exclude([4, "c"]) == {MyEnum.B}
