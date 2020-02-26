import sys
import importlib
import inspect
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


def get_instance_by_name(klass, *args, **kwargs):
    """
    Instantiate a class with args and kwargs.

    Parameters
    ----------
    klass : str or class
        If klass is `str` then `import_helper` is invoked. Otherwise klass is
        used.

    args : tuple
        Tuple of arguments to pass to the class

    kwargs : dict
        Named arguments to pass to te class

    Returns
    -------
    object
        Instance of `klass`
    """
    if inspect.isclass(klass):
        k = klass
    else:
        try:
            k = import_helper(klass)
        except ImportError:
            logger.error('Failed to import class %s', klass)
            raise

    try:
        obj = k(*args, **kwargs)
        return obj
    except Exception:
        logger.exception('Failed to instantiate object for class %s '
                         'using %s and %s', klass, args, kwargs)
        raise
