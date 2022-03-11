import ophyd
from ophyd import Component as Cpt
from ophyd import Device
from ophyd.sim import SynSignal

from .. import ophyd_helpers as helpers


def test_no_device_lazy_load():
    class TestDevice(Device):
        c = Cpt(Device, suffix='Test')

    dev = TestDevice(name='foo')

    old_val = Device.lazy_wait_for_connection
    assert dev.lazy_wait_for_connection is old_val
    assert dev.c.lazy_wait_for_connection is old_val

    with helpers.no_device_lazy_load():
        dev2 = TestDevice(name='foo')

        assert Device.lazy_wait_for_connection is False
        assert dev2.lazy_wait_for_connection is False
        assert dev2.c.lazy_wait_for_connection is False

    assert Device.lazy_wait_for_connection is old_val
    assert dev.lazy_wait_for_connection is old_val
    assert dev.c.lazy_wait_for_connection is old_val


def test_sub_context():
    sig = SynSignal(name="sig")

    def callback(**_):
        ...

    with helpers.subscription_context(sig, callback=callback) as ctx:
        assert sig in ctx
        assert len(sig._callbacks["value"])
    assert not sig._callbacks["value"]


def test_sub_context_device():
    class TestDevice(Device):
        a = Cpt(SynSignal)
        b = Cpt(SynSignal)

    def callback(**_):
        ...

    dev = TestDevice(name="dev")

    with helpers.subscription_context_device(dev, callback=callback) as ctx:
        assert len(dev.a._callbacks["value"])
        assert len(dev.b._callbacks["value"])
        assert dev.a in ctx
        assert dev.b in ctx
    assert not dev.a._callbacks["value"]
    assert not dev.b._callbacks["value"]


def test_sub_context_device_filter():
    class TestDevice(Device):
        a = Cpt(SynSignal)
        b = Cpt(SynSignal)

    def callback(**_):
        ...

    def filter_by(walk: ophyd.device.ComponentWalk) -> bool:
        return walk.item.name == "dev_a"

    dev = TestDevice(name="dev")

    with helpers.subscription_context_device(
        dev, callback=callback, filter_by=filter_by
    ) as ctx:
        assert len(dev.a._callbacks["value"])
        assert not len(dev.b._callbacks["value"])
        assert dev.a in ctx
        assert dev.b not in ctx
    assert not dev.a._callbacks["value"]
    assert not dev.b._callbacks["value"]


def test_get_all_signals():
    class TestDevice(Device):
        a = Cpt(SynSignal)
        b = Cpt(SynSignal, lazy=True)

    dev = TestDevice(name="dev")

    assert helpers.get_all_signals_from_device(dev) == [dev.a]
    assert helpers.get_all_signals_from_device(dev, include_lazy=True) == [
        dev.a, dev.b
    ]


def test_get_all_signals_filter():
    class TestDevice(Device):
        a = Cpt(SynSignal)
        b = Cpt(SynSignal)

    dev = TestDevice(name="dev")

    def filter_by(walk: ophyd.device.ComponentWalk) -> bool:
        return walk.item.name == "dev_a"

    assert helpers.get_all_signals_from_device(dev, filter_by=filter_by) == [
        dev.a
    ]


def test_acquire_blocking():
    sig = ophyd.Signal(name="sig")
    sig.put(10)
    values = helpers.acquire_blocking(sig, duration=0.05)
    assert len(values) > 0
    assert sig.get() in values
