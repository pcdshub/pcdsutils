import pytest
import pcdsutils

from pytest import PytestDeprecationWarning


def test_import_helper():
    # Test invalid entries
    with pytest.raises(ImportError):
        klass = pcdsutils.utils.import_helper("Invalid.Class.Name")

    with pytest.raises(ImportError):
        klass = pcdsutils.utils.import_helper("pathlib.INVALID")

    # Test available at modules
    klass = pcdsutils.utils.import_helper("pytest.PytestDeprecationWarning")
    assert klass is PytestDeprecationWarning

    # Test loading from package
    klass = pcdsutils.utils.import_helper("pathlib.PurePath")
    assert klass is not None
    assert klass.__name__ == "PurePath"
