"""
Utilities for setting up line_profiler to debug a specific module
"""
from __future__ import annotations

import importlib
import logging
import pkgutil
import warnings
from contextlib import contextmanager
from inspect import getmembers, isclass, isfunction, ismethod
from types import ModuleType
from typing import (Any, Callable, Dict, Iterable, Iterator, List, Optional,
                    Tuple)

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
    if profiler is None:
        reset_profiler()
    return profiler


def reset_profiler() -> LineProfiler:
    """Clears the old global profiler by replacing it with a new one."""
    global profiler
    if not has_line_profiler:
        raise ImportError(_optional_err)
    profiler = LineProfiler()
    return profiler


@contextmanager
def profiler_context(
    module_names: Iterable[str],
    filename: Optional[str] = None,
    use_global_profiler: bool = False,
    output_now: bool = True,
    min_threshold: float = 0,
) -> Iterator[LineProfiler]:
    """
    Context manager for profiling a fixed span of an application.

    Parameters
    ----------
    module_names : iterable of str
        The modules whose functions we'd like to include in the profile.
        If using the global profiler, these will persist between calls, only
        accumulating new modules and never clearing old ones.
    filename : str, optional
        If provided, the results will be saved to this filename.
        If omitted, we'll print the results to stdout.
    use_global_profiler : bool, optional
        If False, the default, this will create a new profiler instance for
        this context manager block. If True, this will use the global
        profiler. Using the global profiler is appropriate if you want to
        accumulate statistics across multiple context manager blocks, or
        the same block multiple times.
    output_now : bool, optional
        If True, the default, we'll print to screen or write to file the
        results upon exiting this block. If False, we will not. This is
        appropriate to change to False if you'd like to accumulate
        statistics across multiple context manager blocks, or perhaps the
        same context manager block multiple times.
    min_threshold : float, optional
        If provided, we will omit results from functions with total time
        less than this duration in seconds from the output.

    Yields
    ------
    profiler : LineProfiler
        The profile instance that is active in this code block, in case you'd
        like to do something with it.
    """
    context_profiler = setup_profiler(
        module_names=module_names,
        use_global_profiler=use_global_profiler,
    )
    context_profiler.enable_by_count()
    yield context_profiler
    context_profiler.disable_by_count()

    if output_now:
        if filename is None:
            print_results(
                context_profiler,
                min_threshold=min_threshold,
            )
        else:
            save_results(
                filename,
                context_profiler,
                min_threshold=min_threshold,
            )


def setup_profiler(
    module_names: Iterable[str],
    use_global_profiler: bool = True,
) -> LineProfiler:
    """
    Sets up a profiler.

    Includes all functions and classes from all submodules of the given
    module names.

    Parameters
    ----------
    module_names : iterable of str
        The modules to profile. You can make this an entire module like
        "typhos", specific submodules like "typhos.display", or
        several modules if you want to profile many different things.
    use_global_profiler : bool, optional
        Set to True, the default, to set up a global profiler.
        Set to False to set up an independent profiler.

    Returns
    -------
    profiler : LineProfiler
        The profiler that was just set up, global or otherwise.
    """
    if use_global_profiler:
        profiler_to_setup = get_profiler()
    else:
        profiler_to_setup = LineProfiler()

    functions = set()
    for module_name in module_names:
        # We don't care about import warnings
        # Most of these are "we moved the module"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            modules = get_submodules(module_name)
        for module in modules:
            native_functions = get_native_functions(module)
            functions.update(native_functions)

    for function in functions:
        profiler_to_setup.add_function(function)

    return profiler_to_setup


def toggle_profiler(turn_on: bool) -> None:
    """Turns the global profiler off or on."""
    profiler = get_profiler()
    if turn_on:
        profiler.enable_by_count()
    else:
        profiler.disable_by_count()


def get_preamble(
    timings_dict: Dict,
    min_threshold: float
) -> str:
    """
    Returns the text that goes before the line profile chunks in the output.
    """
    txt = 'Profile output: time is in units of milliseconds.\n'
    if not timings_dict:
        txt += (
            'No functions above minimum threshold of '
            f'{min_threshold} seconds.\n'
        )
    return txt + '\n'


def save_results(
    filename: str,
    prof: Optional[LineProfiler] = None,
    min_threshold: float = 0,
) -> None:
    """
    Saves the formatted profiling results.

    Parameters
    ----------
    filename : str
        The path to the file where we'd like to save the results.
    prof : LineProfiler, optional
        The profiler whose statistics we'd like to save.
        If omitted, we'll use the global profiler.
    min_threshold : float, optional
        If provided, we will omit results from functions with total time
        less than this duration in seconds from the output.
    """
    if prof is None:
        prof = get_profiler()
    stats = prof.get_stats()
    timings_dict = sort_timings(prof, min_threshold)
    with open(filename, 'w') as fd:
        fd.write(
            get_preamble(
                timings_dict,
                min_threshold,
            )
        )
        for (fn, lineno, name), timings in timings_dict.items():
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


def print_results(
    prof: Optional[LineProfiler] = None,
    min_threshold: float = 0,
) -> None:
    """
    Prints the formatted results directly to terminal.

    Parameters
    ----------
    prof : LineProfiler, optional
        The profiler whose statistics we'd like to save.
        If omitted, we'll use the global profiler.
    min_threshold : float, optional
        If provided, we will omit results from functions with total time
        less than this duration in seconds from the output.
    """
    if prof is None:
        prof = get_profiler()
    stats = prof.get_stats()
    timings_dict = sort_timings(prof, min_threshold)
    print(
        '\n' + get_preamble(
            timings_dict,
            min_threshold,
        ),
        end='',
    )
    for (fn, lineno, name), timings in timings_dict.items():
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


def sort_timings(
    prof: Optional[LineProfiler] = None,
    min_threshold: float = 0,
) -> Dict[Tuple[str, int, str], List[Tuple[int, int, int]]]:
    """
    Sort a profiler's stats in order of decreasing total time.

    Parameters
    ----------
    prof : LineProfiler, optional
        The line profiler whose statistics we'd like to sort. If omitted,
        we'll use the global profiler.
    min_threshold : float, optional
        A minimum total execution threshold for pre-filtering the output
        statistics. Any total execution time in seconds that is below
        this threshold will be excluded.
    """
    if prof is None:
        prof = get_profiler()
    stats = prof.get_stats()
    new_timings = {}
    ranks = []
    try:
        # stats.unit is e.g. 1e-6, the unit of the integer counts we see
        # so if min_threshold is, say, 1s, that needs to be 1e6 counts
        scaled_threshold = min_threshold / stats.unit
    except ZeroDivisionError:
        scaled_threshold = 0
    for key, inner_timings in stats.timings.items():
        tot_time = 0
        for lineo, nhits, time in inner_timings:
            tot_time += time
        if tot_time > scaled_threshold:
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
    for _, obj in getmembers(module_or_cls):
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
        elif isfunction(obj) or ismethod(obj):
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
        # Several modules are naughty and raise BaseException on import.
        # Sometimes this is even a SystemExit. That's so annoying.
        # I can't believe I'm catching SystemExit and preventing it.
        # But this is just an import. It should be OK.
        # Instead of a basic except Exception, we need to do this
        # But make sure to allow a KeyBoardInterrupt
        except KeyboardInterrupt:
            raise
        except BaseException:
            pass
    return module_objects
