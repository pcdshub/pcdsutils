import sys
import importlib
import logging

logger = logging.getLogger(__name__)


def import_helper(klass):
    """
    Extract the class object from a full qualified class name.

    Parameters
    ----------
    klass : str
        The module path to find the class e.g.
        ``"pcdsdevices.device_types.IPM"``

    Returns
    -------
    cls : type
        The class referred to by the input string.
    """
    mod, cls = klass.rsplit('.', 1)
    # Import the module if not already present
    # Otherwise use the stashed version in sys.modules
    if mod in sys.modules:
        logger.debug("Using previously imported version of %s", mod)
        mod = sys.modules[mod]
    else:
        logger.debug("Importing %s", mod)
        mod = importlib.import_module(mod)
    # Gather our device class from the given module
    try:
        return getattr(mod, cls)
    except AttributeError as exc:
        raise ImportError("Unable to import %s from %s" %
                          (cls, mod.__name__)) from exc
