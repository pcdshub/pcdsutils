import copy
import getpass
import json
import logging
import logging.handlers
import os
import platform
import queue as queue_module
import socket
import sys

# The special logger:
logger = logging.getLogger('pcds-logging')

# Do not propagate messages to the root logger:
logger.propagate = False

DEFAULT_LOG_HOST = os.environ.get('PCDS_LOG_HOST', 'ctl-logsrv01.pcdsn')
DEFAULT_LOG_PORT = int(os.environ.get('PCDS_LOG_PORT', 54320))
DEFAULT_LOG_PROTO = os.environ.get('PCDS_LOG_PROTO', 'udp')

_LOGGER_SCHEMA_VERSION = 0

_LOGGER_ALLOWED_KEYS = {
    # 'args',
    # 'created',
    # 'exc_info',
    'exc_text',
    'filename',
    # 'funcName',
    # 'levelname',
    # 'levelno',
    'lineno',
    # 'message',
    # 'module',
    # 'msecs',
    'msg',
    # 'name',
    'pathname',
    # 'process',
    'processName',
    # 'relativeCreated',
    # 'stack_info',
    # 'thread',
    'threadName',

    # Ones our schema specifies:
    'schema',
    'source',
    'versions',
    'hostname',
    'username',
    'host_info',
}

_LOGGER_KEY_RENAMES = {
    'created': 'ts',  # created time -> timestamp (ts)
    'levelname': 'severity',
    'processName': 'process_name',
    'threadName': 'thread_name',
}

_SYSTEM_UNAME_DICT = dict(platform.uname()._asdict())
_CURRENT_HANDLER = None


class _PassthroughStreamHandler(logging.handlers.SocketHandler):
    def makePickle(self, record):
        'Overrides super().makePickle'
        return record.encode('utf-8') + b'\n'


class _PassthroughDatagramHandler(logging.handlers.DatagramHandler):
    def makePickle(self, record):
        'Overrides super().makePickle'
        return record.encode('utf-8')


class _LogQueueListener(logging.handlers.QueueListener):
    'A log handler which listens in a separate thread for queued records'


def _get_module_versions():
    'Yields module version tuples: (module_name, module_version)'
    def fix_version(version):
        if isinstance(version, bytes):
            # _curses, for example
            return version.decode('utf-8')
        if not isinstance(version, str):
            # Some may have incorrectly specified version as a tuple
            return '.'.join([str(part) for part in version])
        return version

    for name, module in sys.modules.items():
        if hasattr(module, '__version__'):
            try:
                version = fix_version(module.__version__)
            except Exception:
                version = repr(module.__version__)
            yield name.replace('.', '_'), version


def _get_module_version_dict():
    'Returns module version dictionary: {module_name: module_version}'
    return dict(_get_module_versions())


def create_log_dictionary_from_record(record: logging.LogRecord) -> dict:
    '''
    Create a PCDS logging-compliant dictionary from a given logging.LogRecord

    Ensure that exceptions have been formatted with `logging.Handler` prior to
    calling this function.

    Parameters
    ----------
    record : logging.LogRecord or dict
        The record to interpret

    Returns
    -------
    dict
        The ready-to-be-JSON'd record dictionary
    '''
    # Shallow-copy the record dictionary
    ret = dict(record if isinstance(record, dict) else vars(record))

    ret['schema'] = f'python-event-{_LOGGER_SCHEMA_VERSION}'

    def failsafe_call(func, *args, value_on_failure=None, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as ex:
            if value_on_failure is None:
                return f'FAILURE: {type(ex).__name__}: {ex}'
            return value_on_failure

    ret['source'] = failsafe_call('{module}.{funcName}:{lineno}'.format, **ret)
    ret['versions'] = failsafe_call(_get_module_version_dict)
    ret['pathname'] = str(failsafe_call(os.path.abspath, ret['pathname']))
    ret['hostname'] = failsafe_call(socket.gethostname)
    ret['host_info'] = _SYSTEM_UNAME_DICT
    ret['username'] = getpass.getuser()

    for from_, to in _LOGGER_KEY_RENAMES.items():
        ret[to] = ret.pop(from_)

    other_keys = set(ret) - _LOGGER_ALLOWED_KEYS
    for key in other_keys:
        ret.pop(key)

    return ret


class _JsonLogQueueHandler(logging.handlers.QueueHandler):
    'Logging handler which pushes `logging.LogRecord`s to a separate thread'
    def __init__(self, *handlers, queue=None):
        queue = queue or queue_module.Queue()
        super().__init__(queue)
        self.listener = _LogQueueListener(self.queue)
        self.listener.handlers = list(handlers)
        self.listener.start()

    def prepare(self, record):
        'Overrides QueueHandle prepare'
        # Avoid modifying the record in-place; other handlers will be affected
        record = copy.copy(record)
        if record.exc_info:
            # Format the traceback into record.exc_text:
            _ = self.format(record)

        # Send along the serialized JSON to any downstream handlers, at least
        # `self.listener`
        return json.dumps(create_log_dictionary_from_record(record))


def configure_pcds_logging(
        file=sys.stdout, *,
        log_host=DEFAULT_LOG_HOST, log_port=DEFAULT_LOG_PORT,
        protocol=DEFAULT_LOG_PROTO,
        level='DEBUG'):
    """
    Set a new handler on the ``logging.getLogger('pcds-logging')`` logger.

    If this is called more than once, the handler from the previous invocation
    is removed (if still present) and replaced.

    Parameters
    ----------
    log_host : str, optional
        The log host server host. Defaults to the environment variable
        PCDS_LOG_HOST.

    log_port : int, optional
        The log host server port. Defaults to the environment variable
        PCDS_LOG_PORT.

    protocol : {'tcp', 'udp'}
        Use UDP or TCP as the transport protocol. Defaults to the environment
        variable PCDS_LOG_PROTO.

    level : str or int
        Minimum logging level, given as string or corresponding integer.
        Default is 'DEBUG'.

    Returns
    -------
    handler : logging.Handler
        The handler, which has already been added to the 'pcds-logging' logger.
    """
    global _CURRENT_HANDLER

    handler_cls = {
        'udp': _PassthroughDatagramHandler,
        'tcp': _PassthroughStreamHandler
    }[protocol.lower()]

    socket_handler = handler_cls(log_host, log_port)

    handler = _JsonLogQueueHandler(socket_handler)

    levelno = validate_log_level(level)
    handler.setLevel(levelno)

    # handler.setFormatter(_LogFormatter(PLAIN_LOG_FORMAT))
    if _CURRENT_HANDLER in logger.handlers:
        logger.removeHandler(_CURRENT_HANDLER)
        _CURRENT_HANDLER.listener.stop()

    logger.addHandler(handler)
    _CURRENT_HANDLER = handler

    if logger.getEffectiveLevel() > levelno:
        logger.setLevel(levelno)
    return handler


def validate_log_level(level) -> int:
    '''
    Return a int for level comparison
    '''
    if isinstance(level, int):
        levelno = level
    elif isinstance(level, str):
        levelno = logging.getLevelName(level)

    if isinstance(levelno, int):
        return levelno
    raise ValueError("Log level is invalid")


def get_handler():
    """
    Return the handler configured by the most recent call to
    :func:`configure_pcds_logging`.

    If :func:`configure_pcds_logging` has not yet been called, this returns
    ``None``.
    """
    return _CURRENT_HANDLER
