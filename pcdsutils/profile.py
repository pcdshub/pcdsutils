"""
Utilities for setting up line_profiler to debug a specific module
"""
from __future__ import annotations

import importlib
import logging
import pkgutil
from contextlib import contextmanager
from inspect import isclass, isfunction
from types import ModuleType
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

logger = logging.getLogger(__name__)

_optional_err = ('Optional dependency line_profiler missing from python '
                 'environment. Cannot run profiler.')
try:
    from line_profiler import LineProfiler, show_func
    has_line_profiler = True
except ImportError:
    has_line_profiler = False
    logger.debug(_optional_err)


# Global profiler instance
profiler = None


def get_profiler() -> LineProfiler:
    """Returns the global profiler instance, creating it if necessary."""
    global profiler
    if not has_line_profiler:
        raise ImportError(_optional_err)
    elif profiler is None:
        profiler = LineProfiler()
    return profiler


@contextmanager
def profiler_context(
    module_names: Iterable[str],
    filename: Optional[str] = None,
) -> None:
    """
    Context manager for profiling a fixed span of an application.

    Parameters
    ----------
    module_names : iterable of str
        The modules whose functions we'd like to include in the profile.
    filename : str, optional
        If provided, the results will be saved to this filename.
        If omitted, we'll print the results to stdout.
    """
    setup_profiler(module_names=module_names)

    toggle_profiler(True)
    yield
    toggle_profiler(False)

    if filename is None:
        print_results()
    else:
        save_results(filename)


def setup_profiler(module_names: Iterable[str]) -> None:
    """
    Sets up the global profiler.

    Includes all functions and classes from all submodules of the given
    module names.

    Parameters
    ----------
    module_names : iterable of str
        The modules to profile. You can make this an entire module like
        "typhos", specific submodules like "typhos.display", or
        several modules if you want to profile many different things.
    """
    profiler = get_profiler()

    functions = set()
    for module_name in module_names:
        modules = get_submodules(module_name)
        for module in modules:
            native_functions = get_native_functions(module)
            functions.update(native_functions)

    for function in functions:
        profiler.add_function(function)


def toggle_profiler(turn_on: bool) -> None:
    """Turns the profiler off or on."""
    profiler = get_profiler()
    if turn_on:
        profiler.enable_by_count()
    else:
        profiler.disable_by_count()


def save_results(filename: str) -> None:
    """Saves the formatted profiling results to filename."""
    stats = get_profiler().get_stats()
    with open(filename, 'w') as fd:
        for (fn, lineno, name), timings in sort_timings().items():
            show_func(
                fn,
                lineno,
                name,
                timings,
                stats.unit,
                output_unit=1e-3,
                stream=fd,
                stripzeros=True,
            )


def print_results() -> None:
    """Prints the formatted results directly to screen."""
    stats = get_profiler().get_stats()
    for (fn, lineno, name), timings in sort_timings().items():
        show_func(
            fn,
            lineno,
            name,
            timings,
            stats.unit,
            output_unit=1e-3,
            stream=None,
            stripzeros=True,
        )


def sort_timings() -> Dict[Tuple[str, int, str], List[Tuple[int, int, int]]]:
    profiler = get_profiler()
    stats = profiler.get_stats()
    new_timings = {}
    ranks = []
    for key, inner_timings in stats.timings.items():
        tot_time = 0
        for lineo, nhits, time in inner_timings:
            tot_time += time
        ranks.append((tot_time, key))
    for _, key in sorted(ranks, reverse=True):
        new_timings[key] = stats.timings[key]
    return new_timings


def is_native(obj: Any, module: ModuleType) -> bool:
    """
    Determines if obj was defined in module.

    Returns True if obj was defined in this module.
    Returns False if obj was not defined in this module.

    Parameters
    ----------
    obj : Any
        Any object. Note that if obj is a primitive type, or
        any other type without explicit references to its module,
        this check will fail.
    module : module
        Any Python module

    Returns
    -------
    native : bool
        True if obj was defined in the module
        False otherwise

    Raises
    ------
    TypeError
        If the object type cannot be traced back to any particular
        module, e.g. a primitive type like int, or if the module
        argument cannot be interpreted as a module.
    """
    try:
        module_name = module.__name__
    except AttributeError:
        raise TypeError(
            f'{module} of type {type(module)} is not a module.'
        )
    try:
        object_module = obj.__module__
    except AttributeError:
        raise TypeError(
            f'Object {obj} of type {type(obj)} can have no native module.'
        )
    return module_name == object_module


def get_native_functions(module: ModuleType) -> set[Callable]:
    """
    Returns a set of all functions and methods defined in module.

    This does not include any functions defined in submodules.

    Parameters
    ----------
    module : ModuleType
        The module object that you import

    Returns
    native_functions : set of callables
        The functions defined in that module.
    """
    return get_native_methods(module, module)


def get_native_methods(
    module_or_cls: Any,
    module: ModuleType,
    *,
    native_methods: Optional[set[Callable]] = None,
    seen: Optional[set[Any]] = None,
) -> set[Callable]:
    """
    Recursive step of get_native_functions.

    Paremeters
    ----------
    module_or_cls : any
        Either the original module or a class defined in it.
    module : ModuleType
        The source module to compare with to avoid including
        imported functions, etc. in the profile
    seen : set of any, optional
        All objects we've processed already, to avoid
        infinite loops.

    Returns
    -------
    native_methods : set of Callables
        The functions defined on that class or module that
        are native.
    """
    native_methods = set()
    if seen is None:
        seen = set()
    for obj in module_or_cls.__dict__.values():
        try:
            if obj in seen:
                continue
            seen.add(obj)
        except TypeError:
            # Unhashable type, definitely not a class or function
            continue
        try:
            if not is_native(obj, module):
                continue
        except TypeError:
            continue
        if isclass(obj):
            inner_methods = get_native_methods(obj, module, seen=seen)
            native_methods.update(inner_methods)
        elif isfunction(obj):
            native_methods.add(obj)
    return native_methods


def get_submodules(module_name: str) -> list[ModuleType]:
    """Returns a list of the imported module plus all submodules."""
    submodule_names = get_submodule_names(module_name)
    return import_modules(submodule_names)


def get_submodule_names(module_name: str) -> list[str]:
    """
    Returns a list of the module name plus all importable submodule names.
    """
    module = importlib.import_module(module_name)
    submodule_names = [module_name]

    try:
        module_path = module.__path__
    except AttributeError:
        # This attr is missing if there are no submodules
        return submodule_names

    for _, submodule_name, is_pkg in pkgutil.walk_packages(module_path):
        if submodule_name != '__main__':
            full_submodule_name = module_name + '.' + submodule_name
            submodule_names.append(full_submodule_name)
            if is_pkg:
                try:
                    subsubmodule_names = get_submodule_names(
                        full_submodule_name
                    )
                except Exception:
                    # The recursive check failed, some import failed here
                    continue
                submodule_names.extend(subsubmodule_names)
    return submodule_names


def import_modules(module_names: Iterable[str]) -> Iterable[ModuleType]:
    """
    Utility function to import an iterator of module names as a list.

    Skips over modules that are not importable.
    """
    module_objects = []
    for module_name in module_names:
        try:
            module_objects.append(importlib.import_module(module_name))
        except Exception:
            pass
    return module_objects
