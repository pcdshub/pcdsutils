"""
Utilities for finding objects in submodules
"""
import importlib
import pkgutil
from inspect import isclass, isfunction
from types import ModuleType
from typing import Any


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
