# https://stackoverflow.com/a/24588289/5498201

import logging
import contextlib
from http.client import HTTPConnection


def debug_requests_on():
    """switch debugging of requests module on"""
    HTTPConnection.debuglevel = 1
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagete = True


def debug_requests_off():
    HTTPConnection.debuglevel = 0
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.WARNING)
    root_logger.handlers = []
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.WARNING)
    requests_log.propagete = False


@contextlib.contextmanager
def debug_requests():
    """with debug_requests(): requests.get('http://httpbin.org/')"""
    debug_requests_on()
    yield
    debug_requests_off()
