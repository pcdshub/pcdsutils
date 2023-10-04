"""
Helpers for callbacks
"""
import weakref
from types import MethodType

from qtpy import QtCore


class WeakPartialMethodSlot:
    """
    A PyQt-compatible slot for a partial method.

    This utility handles deleting the connection when the method class instance
    gets garbage collected. This avoids cycles in the garbage collector
    that would prevent the instance from being garbage collected prior to the
    program exiting.

    Parameters
    ----------
    signal_owner : QtCore.QObject
        The owner of the signal.
    signal : QtCore.Signal
        The signal instance itself.  Should be a signal on ``signal_owner``
    method : instance method
        The method slot to call when the signal fires.
    *args :
        Arguments to pass to the method.
    **kwargs :
        Keyword arguments to pass to the method.
    """
    def __init__(
        self,
        signal_owner: QtCore.QObject,
        signal: QtCore.Signal,
        method: MethodType,
        *args,
        **kwargs
    ):
        self.signal = signal
        self.signal.connect(self._call, QtCore.Qt.QueuedConnection)
        self.method = weakref.WeakMethod(method)
        self._method_finalizer = weakref.finalize(
            method.__self__, self._method_destroyed
        )
        self._signal_finalizer = weakref.finalize(
            signal_owner, self._signal_destroyed
        )
        self.partial_args = args
        self.partial_kwargs = kwargs

    def _signal_destroyed(self):
        """Callback: the owner of the signal was destroyed; clean up."""
        if self.signal is None:
            return

        self.method = None
        self.partial_args = []
        self.partial_kwargs = {}
        self.signal = None

    def _method_destroyed(self):
        """Callback: the owner of the method was destroyed; clean up."""
        if self.signal is None:
            return

        self.method = None
        self.partial_args = []
        self.partial_kwargs = {}
        try:
            self.signal.disconnect(self._call)
        except Exception:
            ...
        self.signal = None

    def _call(self, *new_args, **new_kwargs):
        """
        PyQt callback slot which handles the internal WeakMethod.

        This method currently throws away arguments passed in from the signal.
        This is for backward-compatibility to how the previous
        `partial()`-using implementation worked.

        If reused beyond the TyphosSuite, this class may need revisiting in the
        future.
        """
        method = self.method()
        if method is None:
            self._method_destroyed()
            return

        return method(*self.partial_args, *new_args,
                      **{**self.partial_kwargs, **new_kwargs})
