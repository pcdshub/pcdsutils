from ._version import get_versions
from . import utils

__version__ = get_versions()['version']
del get_versions

__all__ = ['utils']