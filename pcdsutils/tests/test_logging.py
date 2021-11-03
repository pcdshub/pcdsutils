import json
import logging
import pprint
import queue
import socket
import threading
import warnings

import pytest

import pcdsutils

logging.basicConfig()


LOGGER = pcdsutils.log.logger


@pytest.fixture
def udp_socket():
    return socket.socket(socket.AF_INET, socket.SOCK_DGRAM)


@pytest.fixture
def udp_log_listener(udp_socket):
    received = queue.Queue()
    ev = threading.Event()
    try:
        def listener_thread():
            while not ev.is_set():
                try:
                    data = udp_socket.recvfrom(4096)
                except socket.timeout:
                    ...
                else:
                    received.put(data)
            udp_socket.close()

        threading.Thread(target=listener_thread, daemon=True).start()
        yield received
    finally:
        ev.set()


@pytest.fixture
def udp_listening_port(udp_socket):
    udp_socket.settimeout(0.1)
    udp_socket.bind(('127.0.0.1', 0))
    return udp_socket.getsockname()[1]


def test_log_warning_udp(udp_listening_port: int,
                         udp_log_listener: queue.Queue):
    pcdsutils.log.configure_pcds_logging(log_host='127.0.0.1',
                                         log_port=udp_listening_port,
                                         protocol='udp')

    LOGGER.warning('test1')
    msg, addr = udp_log_listener.get()
    log_dict = json.loads(msg)
    pprint.pprint(log_dict)
    assert log_dict['msg'] == 'test1'


def test_log_exception_udp(udp_listening_port: int,
                           udp_log_listener: queue.Queue):
    pcdsutils.log.configure_pcds_logging(log_host='127.0.0.1',
                                         log_port=udp_listening_port,
                                         protocol='udp')
    try:
        testabcd  # noqa
    except Exception:
        LOGGER.exception('test2')

    msg, addr = udp_log_listener.get()
    log_dict = json.loads(msg)
    pprint.pprint(log_dict)

    assert log_dict['msg'] == 'test2'
    assert 'testabcd' in log_dict['exc_text']


@pytest.fixture(scope='function')
def warnings_filter():
    filter = pcdsutils.log.standard_warnings_config()
    yield filter
    filter.uninstall()
    pcdsutils.log.uninstall_log_warning_handler()


def test_warning_redirects(
    caplog: pytest.LogCaptureFixture,
    monkeypatch: pytest.MonkeyPatch,
    warnings_filter: pcdsutils.log.LogWarningLevelFilter,
):
    normal_warning_count = 0

    def showwarnmsg_and_count(msg):
        nonlocal normal_warning_count
        warnings._showwarnmsg_impl(msg)

    monkeypatch.setattr(warnings, "_showwarnmsg_impl", showwarnmsg_and_count)

    message = "test_warning_redirects"
    for _ in range(10):
        caplog.clear()
        warnings.warn(message)
        assert normal_warning_count == 0, "Saw a normal warning!"
        assert caplog.records, "Did not find any log records!"
        assert message in caplog.records[0].message, "Wrong record!"

    pcdsutils.log.uninstall_log_warning_handler()

    for num in range(10):
        caplog.clear()
        warnings.warn(message)
        assert not caplog.records, "Found log records after uninstall!"
        assert normal_warning_count == num + 1, "Missed normal warning!"


def test_warning_filter(
    caplog: pytest.LogCaptureFixture,
    warnings_filter: pcdsutils.log.LogWarningLevelFilter,
):
    def inner_test(filtered: bool):
        for message in (
            "test_warning_filter",
            "some other message",
            "a third message maybe?",
        ):
            for num in range(10):
                caplog.clear()
                warnings.warn(message)
                assert caplog.records, "Did not find any log records!"
                record = caplog.records[0]
                if not filtered or num == 0:
                    assert record.levelno == logging.WARNING
                else:
                    assert record.levelno == logging.DEBUG
                assert message in record.message

    inner_test(filtered=True)
    warnings_filter.uninstall()
    inner_test(filtered=False)
