# Credits to: https://stackoverflow.com/a/24588289/5498201
# https://requests.readthedocs.io/en/latest/api/

import logging
import contextlib

from http.client import HTTPConnection
from typing import Iterator


def debug_requests_on() -> None:
    """switch debugging of requests module on"""
    HTTPConnection.debuglevel = 1  # type: ignore
    logging.basicConfig()
    logging.getLogger().setLevel(logging.DEBUG)
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.DEBUG)
    requests_log.propagate = True


def debug_requests_off() -> None:
    HTTPConnection.debuglevel = 0  # type: ignore
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.WARNING)
    root_logger.handlers = []
    requests_log = logging.getLogger("requests.packages.urllib3")
    requests_log.setLevel(logging.WARNING)
    requests_log.propagate = False


@contextlib.contextmanager
def debug_requests() -> Iterator[None]:
    """with debug_requests(): requests.get("http://httpbin.org/")"""
    debug_requests_on()
    yield
    debug_requests_off()
