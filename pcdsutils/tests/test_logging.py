import logging

import pcdsutils


logging.basicConfig()


def test_smoke_logging():
    pcdsutils.log.configure_pcds_logging(log_host='127.0.0.1')
    # logger = logging.getLogger('pcds-logging')
    logger = pcdsutils.log.logger

    logger.warning('test1')

    try:
        testabcd  # noqa
    except Exception:
        logger.exception('test2')

    import time
    time.sleep(0.1)
