from pathlib import Path

from qtpy.QtWidgets import QWidget

from pcdsutils.qt.designer_display import DesignerDisplay


class TestDesignerDisplayBase1(DesignerDisplay):
    ui_dir = Path(__file__).parent / "ui"


class TestDesignerDisplayBase2(DesignerDisplay):
    ui_dir = str(TestDesignerDisplayBase1.ui_dir)


class Display1(TestDesignerDisplayBase1, QWidget):
    filename = "test1.ui"


class Display2(TestDesignerDisplayBase2, QWidget):
    filename = "test2.ui"


class Display3(DesignerDisplay, QWidget):
    filename = str(Path(__file__).parent / "ui" / "test3.ui")


def test_display1(qtbot):
    display = Display1()
    qtbot.add_widget(display)
    display.widget1


def test_display2(qtbot):
    display = Display2()
    qtbot.add_widget(display)
    display.widget2


def test_display3(qtbot):
    display = Display3()
    qtbot.add_widget(display)
    display.widget3
