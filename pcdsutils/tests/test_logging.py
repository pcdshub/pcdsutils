import json
import logging
import socket
import threading
import pprint
import queue

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
