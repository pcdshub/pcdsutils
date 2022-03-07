"""
Utilities for setting up line_profiler to debug a specific module
"""
import importlib
import logging
import pkgutil
from contextlib import contextmanager
from inspect import isclass, isfunction
from types import ModuleType
from typing import Any

logger = logging.getLogger(__name__)

_optional_err = ('Optional dependency line_profiler missing from python '
                 'environment. Cannot run profiler.')
try:
    from line_profiler import LineProfiler
    has_line_profiler = True
except ImportError:
    has_line_profiler = False
    logger.debug(_optional_err)


# Global profiler instance
profiler = None


def get_profiler():
    """Returns the global profiler instance, creating it if necessary."""
    global profiler
    if not has_line_profiler:
        raise ImportError(_optional_err)
    elif profiler is None:
        profiler = LineProfiler()
    return profiler


@contextmanager
def profiler_context(module_names=None, filename=None):
    """Context manager for profiling the cli typhos application."""
    setup_profiler(module_names=module_names)

    toggle_profiler(True)
    yield
    toggle_profiler(False)

    if filename is None:
        print_results()
    else:
        save_results(filename)


def setup_profiler(module_names=None):
    """
    Sets up the global profiler.
    Includes all functions and classes from all submodules of the given
    modules. This defaults to everything in the typhos module, but you can
    limit the scope by passing a particular submodule,
    e.g. module_names=['typhos.display'].
    """
    if module_names is None:
        module_names = ['typhos']

    profiler = get_profiler()

    functions = set()
    for module_name in module_names:
        modules = get_submodules(module_name)
        for module in modules:
            native_functions = get_native_functions(module)
            functions.update(native_functions)

    for function in functions:
        profiler.add_function(function)


def toggle_profiler(turn_on):
    """Turns the profiler off or on."""
    profiler = get_profiler()
    if turn_on:
        profiler.enable_by_count()
    else:
        profiler.disable_by_count()


def save_results(filename):
    """Saves the formatted profiling results to filename."""
    profiler = get_profiler()
    with open(filename, 'w') as fd:
        profiler.print_stats(fd, stripzeros=True, output_unit=1e-3)


def print_results():
    """Prints the formatted results directly to screen."""
    profiler = get_profiler()
    profiler.print_stats(stripzeros=True, output_unit=1e-3)


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


def get_native_functions(module):
    """Returns a set of all functions and methods defined in module."""
    return get_native_methods(module, module)


def get_native_methods(cls, module, *, native_methods=None, seen=None):
    """Returns a set of all methods defined in cls that belong to module."""
    if native_methods is None:
        native_methods = set()
    if seen is None:
        seen = set()
    for obj in cls.__dict__.values():
        try:
            if obj in seen:
                continue
            seen.add(obj)
        except TypeError:
            # Unhashable type, definitely not a class or function
            continue
        if not is_native(obj, module):
            continue
        elif isclass(obj):
            get_native_methods(obj, module, native_methods=native_methods,
                               seen=seen)
        elif isfunction(obj):
            native_methods.add(obj)
    return native_methods


def get_submodules(module_name):
    """Returns a list of the imported module plus all submodules."""
    submodule_names = get_submodule_names(module_name)
    return import_modules(submodule_names)


def get_submodule_names(module_name):
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
                subsubmodule_names = get_submodule_names(full_submodule_name)
                submodule_names.extend(subsubmodule_names)
    return submodule_names


def import_modules(modules):
    """
    Utility function to import an iterator of module names as a list.
    Skips over modules that are not importable.
    """
    module_objects = []
    for module_name in modules:
        try:
            module_objects.append(importlib.import_module(module_name))
        except ImportError:
            pass
    return module_objects
