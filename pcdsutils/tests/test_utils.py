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


def test_get_instance_by_name():
    class MockClass:
        def __init__(self, *args, throw=False, **kwargs):
            self.args = args
            self.kwargs = kwargs
            if throw:
                raise NotImplementedError('Raising for test')

    # Test passing args and kwargs
    args = (1, 2, 3)
    kwargs = {"arg1": 1, "arg2": 2}
    obj = pcdsutils.utils.get_instance_by_name(MockClass, *args, **kwargs)
    assert isinstance(obj, MockClass)
    assert obj.args == args
    assert obj.kwargs == kwargs

    # Test passing no args
    obj = pcdsutils.utils.get_instance_by_name(MockClass)
    assert obj.args == ()
    assert obj.kwargs == {}

    # Test with string
    obj = pcdsutils.utils.get_instance_by_name("pathlib.Path")
    assert obj is not None

    # Test invalid string
    with pytest.raises(ImportError):
        obj = pcdsutils.utils.get_instance_by_name("pathlib.INVALID")

    with pytest.raises(NotImplementedError):
        obj = pcdsutils.utils.get_instance_by_name(MockClass, throw=True)
