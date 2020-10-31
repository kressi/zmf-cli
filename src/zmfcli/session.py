import logging

from typing import Any, Callable, Dict, List, Optional, TypedDict, Union
from urllib.parse import urljoin

from requests import Response, Session

ZMF_STATUS_OK = "00"
ZMF_STATUS_INFO = "04"
ZMF_STATUS_FAILURE = "08"

ZmfRequest = Dict[str, Union[str, List[str]]]
ZmfResult = List[Dict[str, Union[str, int]]]


class ZmfResponse(TypedDict, total=False):
    returnCode: str
    message: str
    reasonCode: str
    result: ZmfResult


# Credits to: https://stackoverflow.com/a/51026159
class LoggedSession(Session):
    def __init__(
        self, prefix_url: str = "", *args: Any, **kwargs: Any
    ) -> None:
        # Ignore type issue, https://github.com/python/mypy/issues/5887
        # super().__init__(....) in mixins fails with `Too many arguments...`
        super().__init__(*args, **kwargs)  # type: ignore
        self.prefix_url = prefix_url
        self.logger = logging.getLogger(__name__)

    def request(
        self, method: str, url: Union[str, bytes], *args: Any, **kwargs: Any
    ) -> Response:
        if isinstance(url, bytes):
            url = url.decode("utf-8")
        req_url = urljoin(self.prefix_url, url)
        self.logger.info("%s %s", method, req_url)
        self.logger.info(kwargs.get("data"))
        return super().request(method, req_url, *args, **kwargs)


def unpack_result(
    req: Callable[..., Response]
) -> Callable[..., Optional[ZmfResult]]:
    def wrapper(
        self: LoggedSession, *args: Any, **kwargs: Any
    ) -> Optional[ZmfResult]:
        resp = req(self, *args, **kwargs)
        check_json(resp)
        payload: ZmfResponse = resp.json()
        self.logger.info(
            {
                k: payload.get(k)
                for k in ["returnCode", "message", "reasonCode"]
            }
        )
        if payload.get("returnCode") not in [ZMF_STATUS_OK, ZMF_STATUS_INFO]:
            raise ZmfRestNok(payload.get("message"))
        return payload.get("result")

    return wrapper


class ZmfSession(LoggedSession):
    @unpack_result
    def result_get(self, *args: Any, **kwargs: Any) -> Response:
        return super().get(*args, **kwargs)

    @unpack_result
    def result_post(self, *args: Any, **kwargs: Any) -> Response:
        return super().post(*args, **kwargs)

    @unpack_result
    def result_put(self, *args: Any, **kwargs: Any) -> Response:
        return super().put(*args, **kwargs)


class RequestNok(Exception):
    pass


class ZmfRestNok(Exception):
    pass


def check_json(r: Response) -> None:
    if not r.ok:
        raise RequestNok(r.status_code)
    t = r.headers.get("content-type", "")
    if not t.startswith("application/json"):
        raise RequestNok("Expected content-type 'application/json'", t)
