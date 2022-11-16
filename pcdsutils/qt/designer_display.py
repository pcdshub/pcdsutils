"""
Helper for using designer to layout GUIs.
"""
from pathlib import Path
from typing import ClassVar, Protocol, Type, Union

from qtpy.uic import loadUiType


class _UiForm(Protocol):
    @staticmethod  # <-- this is not entirely true, but PyQt5 uses it as such
    def setupUi(*args):
        ...

    @staticmethod
    def retranslateUi(*args, **kwargs):
        ...


class DesignerDisplay:
    """Helper class for loading designer .ui files and adding logic."""

    # You must set a filename, the path to your .ui file
    filename: ClassVar[str]
    # You can set this for your whole app, override in a subclass, or ignore it
    ui_dir: ClassVar[Union[str, Path]]
    # Created automatically
    ui_form: ClassVar[Type[_UiForm]]

    @classmethod
    def _load_ui_if_needed(cls):
        """Load the UI file on first load."""
        if not hasattr(cls, "ui_form"):
            try:
                path = str(Path(cls.ui_dir) / cls.filename)
            except AttributeError:
                path = str(cls.filename)
            cls.ui_form, _ = loadUiType(path)

    def __init__(self, *args, **kwargs):
        """Apply the file to this widget when the instance is created"""
        self._load_ui_if_needed()
        super().__init__(*args, **kwargs)
        self.ui_form.setupUi(self, self)

    def retranslateUi(self, *args, **kwargs):
        """Required function for setupUi to work in __init__"""
        self.ui_form.retranslateUi(self, *args, **kwargs)

    def show_type_hints(self):
        """Show type hints of widgets included in the display for development help."""
        cls_attrs = set()
        obj_attrs = set(dir(self))
        annotated = set(self.__annotations__)
        for cls in type(self).mro():
            cls_attrs |= set(dir(cls))
        likely_from_ui = obj_attrs - cls_attrs - annotated
        for attr in sorted(likely_from_ui):
            try:
                obj = getattr(self, attr, None)
            except Exception:
                ...
            else:
                if obj is not None:
                    cls = f"{obj.__class__.__module__}.{obj.__class__.__name__} "
                    cls = cls.removeprefix("PyQt5.")
                    print(f"{attr}: {cls}")
