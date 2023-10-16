"""
Tool that generates the source for ``source/api.rst``.

Borrows tools from the pcdsdevices test suite to enumerate modules, classes and
callables.
"""
import importlib
import inspect
import logging
import pathlib
import pkgutil
import sys
from types import ModuleType
from typing import Any, Callable, Optional

MODULE_PATH = pathlib.Path(__file__).resolve().absolute()
PCDSUTILS_PATH = MODULE_PATH.parents[1] / "pcdsutils"

logger = logging.getLogger(__name__)


def find_submodules(
    package_root: pathlib.Path = PCDSUTILS_PATH,
    prefix: str = "pcdsutils.",
) -> dict[str, ModuleType]:
    """Find all pcdsutils submodules, as a dictionary of name to module."""
    modules = {}
    for item in pkgutil.walk_packages(path=[str(package_root)], prefix=prefix):
        try:
            modules[item.name] = sys.modules[item.name]
        except KeyError:
            # Submodules may not yet be imported; do that here.
            try:
                modules[item.name] = importlib.import_module(
                    item.name, package=prefix.split(".")[0]
                )
            except Exception:
                logger.exception("Failed to import %s", item.name)

    return modules


def find_all_classes(
    classes,
    package_root: pathlib.Path = PCDSUTILS_PATH,
    prefix: str = "pcdsutils.",
    skip_prefixes: Optional[list[str]] = None
) -> list[Any]:
    """Find all classes in pcdsutils and return them as a list."""
    skip = skip_prefixes or []

    def should_include(obj):
        return (
            inspect.isclass(obj)
            and issubclass(obj, classes)
            and not obj.__module__.startswith("ophyd")
            and not any(obj.__name__.startswith(part) for part in skip)
            and not any(obj.__module__.startswith(part) for part in skip)
        )

    def sort_key(cls):
        return (cls.__module__, cls.__name__)

    classes = [
        obj
        for module in find_submodules(
            package_root,
            prefix,
        ).values()
        for _, obj in inspect.getmembers(module, predicate=should_include)
    ]

    return list(sorted(set(classes), key=sort_key))


def find_all_callables(
    package_root: pathlib.Path = PCDSUTILS_PATH,
    prefix: str = "pcdsutils.",
    skip_prefixes: Optional[list[str]] = None
) -> list[Callable]:
    """Find all callables in pcdsutils and return them as a list."""
    skip = skip_prefixes or []

    def should_include(obj):
        try:
            name = obj.__name__
            module = obj.__module__
        except AttributeError:
            return False

        return (
            callable(obj)
            and not inspect.isclass(obj)
            and module.startswith(prefix)
            and not name.startswith("_")
            and not any(obj.__name__.startswith(part) for part in skip)
            and not any(obj.__module__.startswith(part) for part in skip)
        )

    def sort_key(obj):
        return (obj.__module__, obj.__name__)

    callables = [
        obj
        for module in find_submodules(
            package_root,
            prefix,
        ).values()
        for _, obj in inspect.getmembers(module, predicate=should_include)
    ]

    return list(sorted(set(callables), key=sort_key))


skip_prefixes = [
    "pcdsutils.tests"
]

classes = find_all_classes(
    (object),
    skip_prefixes=skip_prefixes,
)

callables = find_all_callables(
    skip_prefixes=skip_prefixes,
)

modules = {
    obj.__module__
    for obj in list(classes) + list(callables)
    if obj.__module__.startswith("pcdsutils.")
}


def create_api_list() -> list[str]:
    """Create the API list with all classes and functions."""
    output = [
        "API",
        "###",
        "",
    ]

    for module_name in sorted(modules):
        underline = "-" * len(module_name)
        output.append(module_name)
        output.append(underline)
        output.append("")
        module = sys.modules[module_name]
        objects = [
            obj
            for obj in list(classes) + list(callables)
            if obj.__module__ == module_name and hasattr(module, obj.__name__)
        ]

        if objects:
            output.append(".. autosummary::")
            output.append("    :toctree: generated")
            output.append("")

            for obj in sorted(objects, key=lambda obj: obj.__name__):
                output.append(f"    {obj.__module__}.{obj.__name__}")

            output.append("")

    while output[-1] == "":
        output.pop(-1)
    return output


if __name__ == "__main__":
    output = create_api_list()
    print("\n".join(output))
