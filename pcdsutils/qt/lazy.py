from typing import ClassVar, Optional, Type

from qtpy import QtCore, QtGui, QtWidgets


class LazyWidget(QtWidgets.QWidget):
    """
    A lazy widget which only is created when first shown.

    Parameters
    ----------
    widget_cls : QtWidgets.QWidget subclass
        The widget class to instantiate.
    """

    widget_cls: Type[QtWidgets.QWidget]
    widget: Optional[QtWidgets.QWidget]

    widget_created: ClassVar[QtCore.Signal] = QtCore.Signal(QtWidgets.QWidget)
    widget_shown: ClassVar[QtCore.Signal] = QtCore.Signal()
    widget_hidden: ClassVar[QtCore.Signal] = QtCore.Signal()

    def __init__(self, widget_cls: Type[QtWidgets.QWidget]):
        super().__init__()
        self.widget_cls = widget_cls
        self.widget = None

        self.setVisible(False)
        self.setLayout(QtWidgets.QVBoxLayout())

    def hideEvent(self, event: QtGui.QHideEvent):
        """Hook for when the tool is hidden."""
        super().hideEvent(event)
        self.widget_hidden.emit()

    def _create_widget(self):
        """Make the widget no longer lazy."""
        if self.widget is not None:
            return

        self.widget = self.widget_cls()
        self.layout().addWidget(self.widget)
        self.setSizePolicy(self.widget.sizePolicy())

        self._widget_created.emit(self.widget)

    def showEvent(self, event: QtGui.QShowEvent):
        """Hook for when the tool is shown in the suite."""
        if self.widget is None:
            self._create_widget()

        super().showEvent(event)
        self.widget_shown.emit()

    def minimumSizeHint(self):
        """Minimum size hint forwarder from the embedded widget."""
        if self.widget is not None:
            return self.widget.minimumSizeHint()
        return self.sizeHint()

    def sizeHint(self):
        """Size hint forwarder from the embedded widget."""
        if self.widget is not None:
            return self.widget.sizeHint()
        return QtCore.QSize(100, 100)
