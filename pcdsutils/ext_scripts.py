import logging
import re
import socket
import subprocess


logger = logging.getLogger(__name__)
CNF = '/reg/g/pcds/dist/pds/{0}/scripts/{0}.cnf'
SCRIPTS = '/reg/g/pcds/engineering_tools/{}/scripts/{}'
TOOLS = '/reg/g/pcds/dist/pds/tools/{}/{}'


def call_script(args, timeout=None, ignore_return_code=False):
    logger.debug('Calling external script %s with timeout=%s,'
                 ' ignore_fail=%s', args, timeout, ignore_return_code)
    try:
        return subprocess.check_output(args, universal_newlines=True,
                                       timeout=timeout)
    except subprocess.CalledProcessError as exc:
        if ignore_return_code:
            return exc.output
        else:
            logger.debug('CalledProcessError from %s', args, exc_info=True)
            raise
    except Exception:
        logger.debug('Exception raised from %s', args, exc_info=True)
        raise


cache = {}


def cache_script(args, timeout=None, ignore_return_code=False):
    key = ' '.join(args)
    try:
        return cache[key]
    except KeyError:
        output = call_script(args, timeout=timeout,
                             ignore_return_code=ignore_return_code)
        cache[key] = output
        return output


def clear_script_cache():
    global cache
    cache = {}


def get_hutch_name(timeout=10):
    script = SCRIPTS.format('latest', 'get_hutch_name')
    name = cache_script(script, timeout=timeout)
    return name.lower().strip(' \n')


# API Backwards compatibility
hutch_name = get_hutch_name


def get_run_number(hutch=None, live=False, timeout=1):
    latest = hutch or 'latest'
    script = SCRIPTS.format(latest, 'get_lastRun')
    args = [script]
    if hutch is not None:
        args += ['-i', hutch]
    if live:
        args += ['-l']
    run_number = call_script(args, timeout=timeout)
    return int(run_number)


def get_ami_proxy(hutch, timeout=10):
    """
    Match the output text from procmgr ami status.

    The line we're looking for always includes the text ami_proxy.
    The -I argument holds the IP address or hostname of the ami proxy.

    I thought the first host in the list was the name of the ami proxy, but
    this does not seem to be consistent with what the old hutch python is
    doing, so I will continue to searching for -I here.
    """
    domain_re = re.compile('.pcdsn$')
    proxy_re = re.compile(r'ami_proxy.+-I\s+(?P<proxy>\S+)\s')
    ip_re = re.compile(r'\d+\.\d+\.\d+\.\d+')
    hutch = hutch.lower()
    cnf = CNF.format(hutch)
    procmgr = TOOLS.format('procmgr', 'procmgr')
    output = cache_script([procmgr, 'status', cnf, 'ami_proxy'],
                          timeout=timeout,
                          ignore_return_code=True)
    for line in output.split('\n'):
        proxy_match = proxy_re.search(line)
        if proxy_match:
            ami_proxy = proxy_match.group('proxy')
            ip_match = ip_re.match(ami_proxy)
            if ip_match:
                domain_name, _, _ = socket.gethostbyaddr(ami_proxy)
                ami_proxy = domain_re.sub('', domain_name)
            return ami_proxy
