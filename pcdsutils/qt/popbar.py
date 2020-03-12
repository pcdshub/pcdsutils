import functools
import logging

from qtpy import QtCore, QtGui, QtWidgets

logger = logging.getLogger(__name__)


class QVerticalLabel(QtWidgets.QLabel):
    """
    A vertically aligned QLabel
    """
    resized = QtCore.Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed,
                           QtWidgets.QSizePolicy.Minimum)
        self.setAlignment(QtCore.Qt.AlignCenter)

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)

        hint = self.sizeHint()
        center_shift = (self.height() - hint.height()) / 2.0
        painter.translate(hint.width(), hint.height() + center_shift)
        painter.rotate(270)
        painter.drawText(0, 0, self.text())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resized.emit()

    def minimumSizeHint(self):
        hint = super().minimumSizeHint()
        return QtCore.QSize(hint.height(), hint.width())

    def sizeHint(self):
        hint = super().sizeHint()
        return QtCore.QSize(hint.height(), hint.width())


class QPopBar(QtWidgets.QFrame):
    """
    A popup toolbar that shows/hide on hover a certain widget

    Parameters
    ----------
    title : str, optional
        The title to be used
    widget : QWidget, optional
        The widget that will be displayed
    pin : bool, optional
        Pin the toolbar at the start
    """
    def __init__(self, parent=None, title="Pop Bar", widget=None, pin=False,
                 *args, **kwargs):
        super(QPopBar, self).__init__(parent=parent, *args, **kwargs)
        self._title = title
        self._label_font = None
        self._pin_at_startup = pin
        self._setup(widget=widget)

    def _setup(self, widget=None):
        self.installEventFilter(self)
        self.setAttribute(QtCore.Qt.WA_Hover)

        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setSpacing(0)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.setSizePolicy(QtWidgets.QSizePolicy.Fixed,
                           QtWidgets.QSizePolicy.MinimumExpanding)

        self.bar_frame = QtWidgets.QFrame(self)
        self.bar_frame.setLayout(QtWidgets.QHBoxLayout())
        self.bar_frame.layout().setAlignment(QtCore.Qt.AlignCenter)
        self.bar_frame.layout().setSpacing(0)
        self.bar_frame.layout().setContentsMargins(0, 0, 0, 0)
        self.bar_frame.setFrameShape(QtWidgets.QFrame.Panel)
        self.bar_frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.bar_frame.setSizePolicy(QtWidgets.QSizePolicy.Fixed,
                                     QtWidgets.QSizePolicy.MinimumExpanding)

        self.title_label = QVerticalLabel(self)
        self.title_label.setText(self._title)
        self.title_label.setMouseTracking(False)
        self.title_label.resized.connect(self._label_resized)

        # Property which sets the title label font:
        self.font = QtWidgets.QApplication.font()
        self.bar_frame.layout().addWidget(self.title_label)

        self.layout().addWidget(self.bar_frame)

        self.overlay = QPopBarOverlay(bar=self, parent=self.parent())

        self._debounce_timer = QtCore.QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(300)
        self._debounce_timer.timeout.connect(self.overlay.activate)

        self._pinned = False
        self.pin(pinned=False)

        if widget is not None:
            self.setWidget(widget)

            if self._pin_at_startup:
                self.overlay.activate(force=True, animate=False)
                self.overlay.pin_check.setChecked(self._pin_at_startup)

    def _label_resized(self):
        w = self.title_label.width() + 10
        if w < 32:
            w = 32
        self.bar_frame.setFixedWidth(w)

    def pin(self, pinned=False):
        """
        Pin or unpin the popup toolbar.

        Parameters
        ----------
        pinned : bool
            Wether or not to pin the toolbar
        """
        self._pinned = bool(pinned)

        mouse_tracking = not pinned
        self.setMouseTracking(mouse_tracking)
        self.overlay.setMouseTracking(mouse_tracking)

        if pinned:
            self.resize(self.width() + self.overlay.width(), self.height())
            self.layout().addWidget(self.overlay)
            self.overlay.setParent(self)
        else:
            self.layout().removeWidget(self.overlay)
            self.overlay.setParent(self.parent())
            self.resize(self.bar_frame.width(), self.height())

        self.update()

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.MouseButtonPress:
            logger.debug('Mouse Press at PopBar')
            self._debounce_timer.stop()
            self.overlay.toggle_active()
        elif event.type() == QtCore.QEvent.MouseButtonDblClick:
            logger.debug('Double-clicked PopBar')
            self._debounce_timer.stop()
            pin = not self._pinned
            self.overlay.pin_check.setChecked(pin)
            if not pin:
                self.overlay.deactivate(force=True, animate=False)

        elif event.type() == QtCore.QEvent.HoverEnter and \
                not self.overlay.is_active():
            self._debounce_timer.start()
            logger.debug('Hover Enter at PopBar')
            return True
        elif event.type() == QtCore.QEvent.HoverLeave and \
                not self.overlay.is_active():
            logger.debug('Hover Leave at PopBar and overlay not active')
            self._debounce_timer.stop()
            return True
        elif event.type() == QtCore.QEvent.HoverLeave:
            logger.debug('Hover Leave at PopBar')
            QtCore.QTimer.singleShot(200, self.overlay.deactivate)
        return False

    @QtCore.Property(str)
    def title(self):
        """
        Get the title used for the bar.

        Returns
        -------
        title : str
        """
        return self._title

    @title.setter
    def title(self, title):
        """
        Set the title used for the bar.

        Parameters
        ----------
        title : str
        """
        if self._title != title:
            self._title = title or ""
            self.title_label.setText(self._title)

    @QtCore.Property(QtGui.QFont)
    def font(self):
        return self._label_font

    @font.setter
    def font(self, font):
        if self._label_font != font:
            self._label_font = font
            self.title_label.setFont(font)

    def widget(self):
        """
        The overlay bar widget to `widget`

        Returns
        -------
        widget: QWidget
        """
        return self.overlay.widget

    def setWidget(self, widget):
        """
        Set the overlay bar widget to `widget`

        Parameters
        ----------
        widget: QWidget
        """
        pin = self.overlay.widget is None and self._pin_at_startup
        self.overlay.widget = widget

        if pin:
            self.overlay.activate(force=True, animate=False)
            self.overlay.pin_check.setChecked(self._pin_at_startup)


class QPopBarOverlay(QtWidgets.QFrame):
    _DEFAULT_WIDTH = 300

    def __init__(self, parent, bar, *args, **kwargs):
        super(QPopBarOverlay, self).__init__(parent=parent, *args,
                                             **kwargs)
        self.bar = bar
        self._pinned = False
        self._setup()
        self._widget = None

    def _setup(self):
        self.setAttribute(QtCore.Qt.WA_Hover)
        self.setFrameShape(QtWidgets.QFrame.Panel)
        self.setFrameShadow(QtWidgets.QFrame.Raised)
        self.setVisible(False)
        self.setAutoFillBackground(True)
        self.setLayout(QtWidgets.QVBoxLayout())
        self.layout().setSpacing(0)
        self.layout().setContentsMargins(0, 0, 0, 0)

        self.pin_panel = QtWidgets.QFrame(self)
        self.pin_panel.setLayout(QtWidgets.QHBoxLayout())
        self.pin_panel.layout().setSpacing(0)
        self.pin_panel.layout().setContentsMargins(0, 0, 0, 0)

        self.pin_check = QtWidgets.QCheckBox(self)
        self.pin_check.setText("Pin")
        self.pin_check.setChecked(False)
        self.pin_check.setLayoutDirection(QtCore.Qt.RightToLeft)
        self.pin_check.stateChanged.connect(self._handle_pin)
        spacer = QtWidgets.QSpacerItem(10, 5, QtWidgets.QSizePolicy.Expanding,
                                       QtWidgets.QSizePolicy.Minimum)

        self.pin_panel.layout().addItem(spacer)
        self.pin_panel.layout().addWidget(self.pin_check)

        self.layout().addWidget(self.pin_panel)

        self.installEventFilter(self)
        self.setMouseTracking(True)
        self.resize(0, self.bar.height())

    def _handle_pin(self, state):
        checked = state == QtCore.Qt.Checked
        self._pinned = checked
        self.bar.pin(pinned=checked)
        if not checked:
            self.activate(force=True, animate=False)

    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.HoverLeave:
            QtCore.QTimer.singleShot(500,
                                     functools.partial(self.deactivate,
                                                       hover_leave=True)
                                     )
            return True

        return False

    def is_active(self):
        return self.size().width() > 0

    def activate(self, force=False, animate=True):
        logger.debug('Overlay - activate')
        if self.is_active():
            logger.debug('Overlay - activate abort - already active')
            if not force:
                return

        for w in self.parent().findChildren(
                QtWidgets.QWidget, options=QtCore.Qt.FindDirectChildrenOnly):
            if w != self:
                w.stackUnder(self)

        x = self.bar.x() + self.bar.width()
        y = self.bar.y()
        self.move(x, y)
        self.setVisible(True)

        duration = 100 if animate else 0
        self._animate(duration=duration)

    def deactivate(self, hover_leave=False, force=False, animate=True):
        logger.debug('Overlay - deactivate')
        if not force:
            if self._pinned:
                logger.debug('Overlay deactivate abort: pinned')
                return
            if hover_leave and (self.underMouse() or self.bar.underMouse()):
                logger.debug('Overlay deactivate abort: mouse at overlay/bar')
                return
            if self.underMouse():
                logger.debug('Overlay deactivate abort: mouse at overlay')
                return
        duration = 100 if animate else 0
        self._animate(closing=True, duration=duration)

    def toggle_active(self):
        if self.is_active():
            self.deactivate()
        else:
            self.activate()

    def _get_optimal_width(self):
        remaining_window_width = self.window().width() - self.bar.width()
        hinted_widget_width = (self.widget.sizeHint().width() or
                               self._DEFAULT_WIDTH)
        end_width = min(hinted_widget_width, remaining_window_width)
        return end_width

    def _animate(self, closing=False, duration=100):
        bh = self.bar.height()
        start_value = QtCore.QSize(0, bh)

        end_width = self._get_optimal_width()
        end_value = QtCore.QSize(end_width, bh)
        if closing:
            start_value = QtCore.QSize(self.width(), bh)
            end_value = QtCore.QSize(0, bh)

        self._animation = QtCore.QPropertyAnimation(self, b"size")
        self._animation.setStartValue(start_value)
        self._animation.setEndValue(end_value)
        self._animation.setDuration(duration)
        self._animation.start()

    @property
    def widget(self):
        """
        The overlay bar widget to `widget`

        Returns
        -------
        widget: QWidget
        """
        return self._widget

    @widget.setter
    def widget(self, widget):
        """
        Set the overlay bar widget to `widget`

        Parameters
        ----------
        widget: QWidget
        """
        if self._widget != widget:
            overlay_layout = self.layout()
            overlay_layout.removeItem(self._widget)
            self._widget = widget
            if widget:
                overlay_layout.addWidget(widget)
