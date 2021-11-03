from __future__ import annotations

import copy
import dataclasses
import functools
import getpass
import json
import logging
import logging.handlers
import os
import platform
import queue as queue_module
import socket
import sys
import typing
import warnings

from .utils import get_fully_qualified_domain_name

# The special logger:
logger = logging.getLogger('pcds-logging')

# Do not propagate messages to the root logger:
logger.propagate = False

# Exceptions that should just be ignored entirely:
NO_LOG_EXCEPTIONS = (KeyboardInterrupt, SystemExit)

DEFAULT_LOG_HOST = os.environ.get('PCDS_LOG_HOST', 'ctl-logsrv01.pcdsn')
DEFAULT_LOG_PORT = int(os.environ.get('PCDS_LOG_PORT', 54320))
DEFAULT_LOG_PROTO = os.environ.get('PCDS_LOG_PROTO', 'tcp')
ALLOWED_LOG_DOMAINS = set(
    os.environ.get("PCDS_LOG_DOMAINS", ".pcdsn .slac.stanford.edu").split(" ")
)

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


def validate_log_level(level: typing.Union[str, int]) -> int:
    """
    Return a logging level integer for level comparison.

    Parameters
    ----------
    level : str or int
        The logging level string or integer value.

    Returns
    -------
    log_level : int
        The integral log level.

    Raises
    ------
    ValueError
        If the logging level is invalid.
    """
    if isinstance(level, int):
        return level
    if isinstance(level, str):
        levelno = logging.getLevelName(level)
    else:
        raise TypeError(
            f"Invalid type {type(level)} of argument level. "
            "Must be of type int or str."
        )

    if not isinstance(levelno, int):
        raise ValueError(
            f"Invalid logging level {levelno!r} (use e.g., DEBUG or 6)"
        )

    return levelno


def get_handler():
    """
    Return the handler configured by the most recent call to
    :func:`configure_pcds_logging`.

    If :func:`configure_pcds_logging` has not yet been called, this returns
    ``None``.
    """
    return _CURRENT_HANDLER


def log_exception(
    exc_info,
    *,
    context='exception',
    message=None,
    level=logging.ERROR,
    stacklevel=1,
):
    """
    Log an exception to the central server (i.e., logstash/grafana).

    Parameters
    ----------
    exc_info : (exc_type, exc_value, exc_traceback)
        The exception information.

    context : str, optional
        Additional context for the log message.

    message : str, optional
        Override the default log message.

    level : int, optional
        The log level to use.  Defaults to ERROR.

    stacklevel : int, optional
        The stack level of the message being reported.  Defaults to 1, meaning
        that the message will be reported as having come from the caller of
        ``log_exception_to_central_server``.  Applies only to Python 3.8+, and
        ignored below.
    """
    exc_type, exc_value, _ = exc_info
    if issubclass(exc_type, NO_LOG_EXCEPTIONS):
        return

    if not logger.handlers:
        # Do not allow log messages unless the central logger has been
        # configured with a log handler.  Otherwise, the log message will hit
        # the default handler and output to the terminal.
        return

    message = message or f'[{context}] {exc_value}'
    kwargs = dict()
    if sys.version_info >= (3, 8):
        kwargs = dict(stacklevel=stacklevel + 1)

    logger.log(level, message, exc_info=exc_info, **kwargs)


def centralized_logging_enabled() -> bool:
    """Returns True if centralized logging should be enabled."""
    fqdn = get_fully_qualified_domain_name()
    return any(fqdn.endswith(domain) for domain in ALLOWED_LOG_DOMAINS)


warnings_logger = logging.getLogger(f'{__name__}.warnings')


def log_warning_handler(
    message: Warning,
    category: type[Warning],
    filename: str,
    lineno: int,
    file: typing.Optional[typing.TextIO] = None,
    line: typing.Optional[str] = None,
    logger: logging.Logger = warnings_logger,
) -> None:
    """
    Warning handler that redirects all of the warnings to a logger.

    This can be used as a drop-in replacement for warnings.showwarning to
    redirect unfiltered warnings into the logging stream.

    Rather than duplicate the warning display text, this handler opts to
    simplify it and put the extra details into the "extra" dictionary
    argument in the logging library.

    The warnings module displays the warnings as:
    filename:lineno: category: message\\nline
    (where, in all cases I've seen, "line" is generated by reading the file)

    The log message generated here will simply be:
    category: message

    All arguments (except "logger") will be included in the "extra" dictionary.
    This means they can be used in log filters without parsing the message.
    The keys used will be "warning_{key}" for each keyword parameter to this
    function, to avoid collisions.

    Parameters
    ----------
    message : Warning
        This is the Warning object created by a warnings.warn call.
        When converted using str, this becomes the string message
        that was passed into warnings.warn. This will be put into the
        generated log message text and into the extra dict.
    category : type[Warning]
        The warning type, e.g. UserWarning, DeprecationWarning, etc.
        this will be put into the generated log message text and into
        the extra dict.
    filename : str
        The name of the source code file that generated the warning.
        This will be put into the extra dict.
    lineno : int
        The line number in the file that generated the warning. This will
        be put into the extra dict.
    file : file-like, optional
        A file-like object that is normally used in the warnings handler as
        the destination for warnings, defaulting to sys.stderr. This will
        be put into the extra dict.
    line : str, optional
        The string line in the file that generated the warning. I have never
        seen this passed into the warning handler. This will be put into
        the extra dict.
    logger : Logger, optional
        Use this argument to override the default logger for the warnings
        handler, which is the warnings_logger defined in this module.
        This is currently the pcdsutils.log.warnings logger.
    """
    logger.warning(
        '%s: %s',
        category.__name__,
        message,
        extra={
            'warning_message': message,
            'warning_category': category,
            'warning_filename': filename,
            'warning_lineno': lineno,
            'warning_file': file,
            'warning_line': line,
        },
    )


def install_log_warning_handler(
    logger: logging.Logger = warnings_logger,
) -> None:
    """
    Replaces warnings.showwarning with the log_warning_handler above.

    Parameters
    ----------
    logger : Logger, optional
        Use this argument to override the default logger for the warnings
        handler, which is the warnings_logger defined in this module.
        This is currently the pcdsutils.log.warnings logger.
    """
    warnings.showwarning = functools.partial(
        log_warning_handler,
        logger=logger,
    )


def uninstall_log_warning_handler() -> None:
    """
    Restores the default behavior of the warnings module.

    Intended to undo the effects of "install_log_warning_handler"
    from this module.
    """
    warnings.showwarning = warnings._showwarning_orig


@dataclasses.dataclass(eq=True, frozen=True)
class WarningRecordInfo:
    """
    Hashable collection of the unique information from a warnings.warn call.
    """
    message: str
    category: type[Warning]
    filename: str
    lineno: int

    @classmethod
    def from_record(cls, record: logging.LogRecord) -> WarningRecordInfo:
        """
        Create a WarningRecordInfo from a LogRecord.

        This can be used as a utility to inspect or compare warnings log
        messages inside a log filter.
        """
        try:
            return cls(
                message=str(record.warning_message),
                category=record.warning_category,
                filename=record.warning_filename,
                lineno=record.warning_lineno,
            )
        except AttributeError as exc:
            raise ValueError(
                'Received invalid record, must be from '
                'the log_warning_handler'
            ) from exc


class LogWarningLevelFilter(logging.Filter):
    """
    Filter to decrease the log level of repeat warnings.

    Once installed, the first instance of a "warnings.warn" converted to
    a log message will be at "WARNING" level, while subsequent repeats of
    the same warning will be at "DEBUG" level.

    When running a normal program, typically the warnings module will
    handle warning filtering for you as the default behavior, making every
    unique warning only appear once.

    When running in ipython, the warnings cache is reset prior to running
    every command, so it's possible to see repeat warnings during or after
    each command. This is a annoying. The filter here allows us to
    adjust the level of the repeat messages to avoid cluttering the user's
    view, or to remove them entirely.

    Parameters
    ----------
    level : str or int, optional
        The log level or name of the log level to reduce dupliacte
        log messages to. Defaults to logging.DEBUG.
    """
    levelno: int
    levelname: str
    cache: set[WarningRecordInfo]
    _logger: typing.Optional[logging.Logger]

    def __init__(
        self,
        level: typing.Union[str, int] = logging.DEBUG,
    ):
        self.levelno = validate_log_level(level)
        self.levelname = logging.getLevelName(self.levelno)
        self.cache = set()
        self._logger = None

    def filter(self, record: logging.LogRecord) -> typing.Literal[True]:
        """
        Adjust the level of the warnings log message if we've seen it before.

        Always returns "True" to let the log pass through.
        """
        try:
            info = WarningRecordInfo.from_record(record)
        except ValueError:
            # Must not be a warnings log record, skip
            return True
        if info in self.cache:
            record.levelno = self.levelno
            record.levelname = self.levelname
        else:
            self.cache.add(info)
        return True

    @classmethod
    def install(
        cls,
        level: typing.Union[str, int] = logging.DEBUG,
        logger: logging.Logger = warnings_logger,
    ) -> LogWarningLevelFilter:
        """
        Apply the LogWarningLevelFilter to the warnings logger.

        Parameters
        ----------
        level : str or int, optional
            The log level or name of the log level to reduce dupliacte
            log messages to. Defaults to logging.DEBUG.
        logger : logging.Logger, optional
            The logger to apply the filter to. Defaults to the warnings_logger.

        Returns
        -------
        filt : LogWarningLevelFilter
            The filter object that we've applied to the logger. Useful for
            debugging.
        """
        filt = cls(level=level)
        logger.addFilter(filt)
        filt._logger = logger
        return filt

    def uninstall(self) -> None:
        """
        Convenience method for removing this filter.

        Requires the filter to have been originally created and applied using
        the "install" class method.

        Intended to help with the unit testing.
        """
        if self._logger is not None:
            self._logger.removeFilter(self)


def standard_warnings_config() -> LogWarningLevelFilter:
    """
    Use the standard pcds warnings config.

    This installs the log warning handler pointed to the "warnings_logger"
    and also installs the LogWarningLevelFilter at logging.DEBUG level
    and returns it.

    Returns
    -------
    filt : LogWarningLevelFilter
        The filter installed on the warnings logger.
    """
    install_log_warning_handler()
    return LogWarningLevelFilter.install()
