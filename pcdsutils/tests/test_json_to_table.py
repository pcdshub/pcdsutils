import io

import pytest

from ..json_to_table import ProgramArguments, TableStyle, main


@pytest.fixture(
    params=[
        b"""
        [
            {"a": 1, "b": 2},
            {"a": 2, "b": 3},
            {"a": 4, "b": 5}
        ]
        """,
        b"""
        []
        """,
        b"""
        [
            {"a": 1, "b": 2}
        ]
        """,
    ]
)
def input_file(request):
    return io.BytesIO(request.param)


@pytest.fixture(
    params=list(val.name for val in TableStyle),
)
def format(request):
    return request.param


@pytest.fixture(
    params=["a", "b"],
)
def sort_key(request):
    return request.param


@pytest.fixture(
    params=[
        ["a", "b"],
        ["b"],
        [],
    ],
)
def columns(request):
    return request.param


def test_basic(input_file, format, sort_key, columns):
    args = ProgramArguments(
        input_file=input_file,
        format=format,
        sort_key=sort_key,
        columns=columns,
    )
    main(args)
