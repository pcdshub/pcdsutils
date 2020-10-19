import logging

import pytest
import socket
import subprocess

import pcdsutils.ext_scripts as ext

logger = logging.getLogger(__name__)


def test_call_script():
    logger.debug('test_call_script')
    assert isinstance(ext.call_script('uname'), str)
    with pytest.raises(FileNotFoundError):
        ext.call_script('definitelynotarealscriptgeezman')
    bad_args = ['uname', '-notanoption']
    with pytest.raises(subprocess.CalledProcessError):
        ext.call_script(bad_args)
    assert isinstance(ext.call_script(bad_args, ignore_return_code=True), str)


def test_hutch_name(monkeypatch):
    logger.debug('test_hutch_name')

    def fake_hutch_name(*args, **kwargs):
        return 'tst\n'

    monkeypatch.setattr(ext, 'call_script', fake_hutch_name)
    assert ext.get_hutch_name() == 'tst'


def test_run_number(monkeypatch):
    logger.debug('test_run_number')

    def fake_run_number(*args, **kwargs):
        return '1\n'

    monkeypatch.setattr(ext, 'call_script', fake_run_number)
    assert ext.get_run_number(hutch='tst', live=True) == 1


def test_get_ami_proxy(monkeypatch):
    logger.debug('test_get_ami_proxy')

    def fake_procmgr(*args, **kwargs):
        return ("/reg/g/pcds/dist/pds/tools/procmgr/procmgr: using config "
                "file '/reg/g/pcds/dist/pds/xpp/scripts/p1.cnf.last'\n"
                "Running, started on host xpp-daq by user xppopr.\n"
                "Warning! If current host xpp-control is not on the same "
                "subnets as start host xpp-daq, status could be incorrect.\n"
                "Host          UniqueID     Status     PID    PORT   "
                "Command+Args\n"
                "172.21.22.64  ami_proxy    RUNNING    7145   29118  "
                "/reg/g/pcds/dist/pds/ami-8.8.14-p8.9.0/build/ami/bin/"
                "x86_64-rhel7-opt/ami_proxy -I 172.21.38.64 -i 172.21.22.64 "
                "-s 239.255.35.1\n")

    def fake_gethostbyaddr(ip):
        logger.debug(ip)
        if ip == '172.21.38.64':
            return ('tst-amiproxy.pcdsn', None, None)
        else:
            return ('regex_fail', None, None)

    monkeypatch.setattr(ext, 'call_script', fake_procmgr)
    monkeypatch.setattr(socket, 'gethostbyaddr', fake_gethostbyaddr)

    assert ext.get_ami_proxy('tst') == 'tst-amiproxy'
