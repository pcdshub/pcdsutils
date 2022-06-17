"""
Check some of the profiler internal utilities.
"""
import logging
import os.path

import pytest

from ..profile import (get_native_functions, get_submodules, is_native,
                       profiler_context)
from . import dummy_submodule

logger = logging.getLogger(__name__)


def test_is_native():
    # Was defined there
    assert is_native(dummy_submodule.some_function, dummy_submodule)
    # Is available here, but was not defined here
    assert not is_native(dummy_submodule.getmembers, dummy_submodule)
    # Argument 2 must be a module
    with pytest.raises(TypeError):
        is_native(dummy_submodule.some_function, "profile")
    # Primitives have no source module information
    with pytest.raises(TypeError):
        is_native('text', dummy_submodule)


def test_get_native_functions():
    dummy_natives = get_native_functions(dummy_submodule)
    # We know about these from the way the test is set up
    assert dummy_submodule.some_function in dummy_natives
    assert dummy_submodule.SomeClass.method in dummy_natives
    assert dummy_submodule.SomeClass.cls_method in dummy_natives
    assert dummy_submodule.SomeClass.stat_method in dummy_natives
    # This shouldn't be there at all
    assert test_get_native_functions not in dummy_natives
    # This is imported in profile but not native
    assert dummy_submodule.getmembers not in dummy_natives


def test_get_submodules():
    submodules = get_submodules('pcdsutils.tests')
    assert dummy_submodule in submodules


def test_basic_profiler():
    # Run through and make sure our functions are included
    with profiler_context(['pcdsutils']) as profiler:
        dummy_submodule.some_function()
        some_obj = dummy_submodule.SomeClass()
        some_obj.method()
        some_obj.cls_method()
        some_obj.stat_method()

    timings = profiler.get_stats().timings
    functions_profiled = [
        (os.path.basename(file), func)
        for (file, lineno, func), stats in timings.items() if stats
    ]
    logger.debug(functions_profiled)
    assert ('dummy_submodule.py', '__init__') in functions_profiled
    assert ('dummy_submodule.py', 'some_function') in functions_profiled
    assert ('dummy_submodule.py', 'method') in functions_profiled
    assert ('dummy_submodule.py', 'cls_method') in functions_profiled
    assert ('dummy_submodule.py', 'stat_method') in functions_profiled
