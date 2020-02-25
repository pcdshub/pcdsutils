from ._version import get_versions
from . import log

__version__ = get_versions()['version']
del get_versions

__all__ = ['log']
