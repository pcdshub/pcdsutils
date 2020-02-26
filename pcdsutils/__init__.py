from ._version import get_versions
from . import utils
from . import log

__version__ = get_versions()['version']
del get_versions

__all__ = ['utils', 'log']
