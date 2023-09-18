from qtpy import QtCore, QtGui, QtWidgets

from pcdsutils.qt import QPopBar


class InnerWidget(QtWidgets.QWidget):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent=parent, *args, **kwargs)
        self.setupUi()

    def setupUi(self):
        self.setLayout(QtWidgets.QVBoxLayout())

        self.cb_group = QtWidgets.QComboBox(self)
        self.cb_group.addItems(
            ['Name', 'Functional Group', 'Functional Location']
        )

        self.le_filter = QtWidgets.QLineEdit(self)

        filter_form = QtWidgets.QFormLayout()
        self.layout().addLayout(filter_form)
        filter_form.addRow(QtWidgets.QLabel("Group by:", self), self.cb_group)
        filter_form.addRow(QtWidgets.QLabel("Filter:", self), self.le_filter)

        self.tree = QtWidgets.QTreeWidget(self)
        self.tree.setSortingEnabled(True)
        self.tree.setHeaderLabel("Devices")
        self.layout().addWidget(self.tree)
        self.installEventFilter(self)
        self.setMouseTracking(True)


class MainWindow(QtWidgets.QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setLayout(QtWidgets.QHBoxLayout())
        self.layout().setSpacing(1)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.explorer_bar = QPopBar(self, pin=True)
        self.explorer_bar.title = "Devices"

        font = QtGui.QFont()
        # font.setPixelSize(36)

        self.explorer_bar.font = font

        self.widget = InnerWidget(self)
        self.explorer_bar.setWidget(self.widget)

        self.content_frame = QtWidgets.QFrame(self)
        self.content_frame.setObjectName("content")
        self.content_frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.content_frame.setLayout(QtWidgets.QGridLayout())
        self.fill_content_frame()

        self.layout().addWidget(self.explorer_bar)
        self.layout().addWidget(self.content_frame)

    def sizeHint(self):
        return QtCore.QSize(800, 600)

    def fill_content_frame(self):
        cols = 10
        rows = 10
        for c in range(cols):
            for r in range(rows):
                w = QtWidgets.QPushButton(self.content_frame)
                w.setText(f"Button {r}-{c}")
                self.content_frame.layout().addWidget(w, r, c)


def main():
    app = QtWidgets.QApplication([])
    main_window = MainWindow()
    main_window.show()
    app.exec_()


if __name__ == "__main__":
    main()
