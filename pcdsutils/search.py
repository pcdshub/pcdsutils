"""
Utilities for finding objects in submodules
"""
import importlib
import pkgutil
from inspect import isclass, isfunction


def is_native(obj, module):
    """
    Determines if obj was defined in module.
    Returns True if obj was defined in this module.
    Returns False if obj was not defined in this module.
    Returns None if we can't figure it out, e.g. if this is a primitive type.
    """
    try:
        return module.__name__ in obj.__module__
    except (AttributeError, TypeError):
        return None


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
