import logging
import os
import sys

from itertools import groupby
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Union
from urllib.parse import urljoin

import fire  # type: ignore
import requests
import toml
import yaml

from .logrequests import debug_requests_on

SRC_DIR = "src/"
SOURCE_LIKE = ["sre", "srb", "src", "sra"]
SOURCE_LOCATION = {
    "development dataset": 1,
    "package": 5,
    "temp sequential dataset": 7,
    "edit from package lib": "E",
}
SOURCE_STORAGE = {
    "pds": 6,
    "sequential dataset": 8,
    "pds/extended": 9,
    "hfs": "H",
}
ZMF_STATUS_OK = "00"
ZMF_STATUS_INFO = "04"
ZMF_STATUS_FAILURE = "08"

Payload = Dict[str, Union[str, List[str]]]

"""
Sample ZmfResponse

{
    "returnCode": "00",
    "message": "CMN8600I - The Package search list is complete.",
    "reasonCode": "8600",
    "result": [
        {
            "package": "APP 000000",
            "tempChangeDuration": 0
        },
        {
            "package": "APP 000001",
            "tempChangeDuration": 0
        }
    ]
}
"""
ZmfResult = List[Dict[str, str]]
ZmfResponse = Dict[str, Union[str, ZmfResult]]


class ChangemanZmf:
    def __init__(
        self,
        user: Optional[str] = None,
        password: Optional[str] = None,
        url: Optional[str] = None,
        verbose: bool = False,
    ) -> None:
        self.url: str = url if url else os.environ["ZMF_REST_URL"]
        self.__user: str = user if user else os.environ["ZMF_REST_USER"]
        self.__password: str = (
            password if password else os.environ["ZMF_REST_PWD"]
        )
        logging.basicConfig()
        self.logger: logging.Logger = logging.getLogger(__name__)
        self.__session: ZmfSession = ZmfSession(self.url)
        self.__session.auth = (self.__user, self.__password)
        if verbose:
            self.logger.setLevel(logging.DEBUG)
            debug_requests_on()
        else:
            self.logger.setLevel(logging.INFO)

    def checkin(
        self, package: str, pds: str, components: Iterable[str]
    ) -> None:
        """checkin components from a partitioned dataset (PDS)"""
        data = {
            "package": package,
            "chkInSourceLocation": SOURCE_LOCATION["development dataset"],
            "sourceStorageMeans": SOURCE_STORAGE["pds"],
        }
        for tp, comps in groupby(sorted(components, key=extension), extension):
            dt = data.copy()
            dt["componentType"] = tp.upper()
            dt["sourceLib"] = pds + "." + tp.upper()
            dt["targetComponent"] = [Path(c).stem for c in comps]
            self.__session.result_put("component/checkin", data=dt)

    def build(
        self,
        package: str,
        components: Iterable[str],
        procedure: str = "CMNCOB2",
        language: str = "COBOL",
        db2Precompile: Optional[bool] = None,
    ) -> None:
        """build source like components"""
        data: Payload = {
            "package": package,
            "buildProc": procedure,
            "language": language,
        }
        data.update(jobcard(self.__user, "build"))
        if db2Precompile:
            data["useDb2PreCompileOption"] = "Y"
        source_comps = (c for c in components if extension(c) in SOURCE_LIKE)
        for t, comps in groupby(
            sorted(source_comps, key=extension), extension
        ):
            dt = data.copy()
            dt["componentType"] = t.upper()
            dt["component"] = [Path(c).stem for c in comps]
            self.__session.result_put("component/build", data=dt)

    def build_config(
        self, package: str, components: Iterable[str], config_file: str = "-"
    ) -> None:
        """build source like components"""
        allconfigs = read_yaml(config_file)
        data = {
            "package": package,
            "buildProc": "CMNCOB2",
            "language": "COBOL",
        }
        data.update(jobcard(self.__user, "build"))
        source_comps = (c for c in components if extension(c) in SOURCE_LIKE)
        for comp in source_comps:
            dt = data.copy()
            config = allconfigs.get(removeprefix(comp, SRC_DIR))
            if config:
                dt.update(config)
            dt["componentType"] = extension(comp).upper()
            dt["component"] = Path(comp).stem
            self.__session.result_put("component/build", data=dt)

    def scratch(self, package: str, components: Iterable[str]) -> None:
        data = {"package": package}
        for comp in components:
            dt = data.copy()
            dt["componentType"] = extension(comp).upper()
            dt["oldComponent"] = Path(comp).stem
            self.__session.result_put("component/scratch", data=dt)

    def audit(self, package: str) -> None:
        data = {"package": package}
        data.update(jobcard(self.__user, "audit"))
        self.__session.result_put("package/audit", data=data)

    def promote(self, package: str) -> None:
        """promote a package"""
        print("promote")

    def freeze(self, package: str) -> None:
        print("freeze")

    def revert(self, package: str) -> None:
        print("revert")

    def search_package(self, app: str, title: str) -> Optional[str]:
        data = {
            "package": app + "*",
            "packageTitle": title,
        }
        result = self.__session.result_get("package/search", data=data)
        pkg_id = None
        # in case multiple packages have been found take the youngest
        if result:
            for pkg in sorted(
                result,
                key=lambda p: int_or_zero(p.get("packageId")),
                reverse=True,
            ):
                # search matches title as substring, ensure full title matches
                if pkg.get("packageTitle") == title:
                    pkg_id = pkg.get("package")
                    break
        return pkg_id

    def create_package(
        self,
        config_file: str = "-",
        app: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Optional[str]:
        data = {
            "applName": app,
            "packageTitle": title,
        }
        config = read_yaml(config_file)
        data.update(config)
        result = self.__session.result_post("package", data=data)
        self.logger.info(result)
        return result[0].get("package") if result else None

    def get_package(
        self,
        config_file: str = "-",
        app: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Optional[str]:
        config = read_yaml(config_file)
        pkg_id = config.get("package")
        if not pkg_id:
            search_app = config.get("applName", app)
            search_title = config.get("packageTitle", title)
            pkg_id = self.search_package(search_app, search_title)
        if not pkg_id:
            pkg_id = self.create_package(config_file, app, title)
        return pkg_id


# https://stackoverflow.com/a/51026159
class LoggedSession(requests.Session):
    def __init__(self, prefix_url: str = "", *args, **kwargs) -> None:
        # Ignore type issue, https://github.com/python/mypy/issues/5887
        # super().__init__(....) in mixins fails with `Too many arguments...`
        super().__init__(*args, **kwargs)  # type: ignore
        self.prefix_url = prefix_url
        self.logger = logging.getLogger(__name__)

    def request(
        self, method: str, url: Union[str, bytes], *args, **kwargs
    ) -> requests.Response:
        if isinstance(url, bytes):
            url = url.decode("utf-8")
        req_url = urljoin(self.prefix_url, url)
        self.logger.info("%s %s", method, req_url)
        self.logger.info(kwargs.get("data"))
        return super().request(method, req_url, *args, **kwargs)


def unpack_result(
    req: Callable[..., requests.Response]
) -> Callable[..., Optional[ZmfResult]]:
    def wrapper(self, *args, **kwargs) -> Optional[ZmfResult]:
        resp = req(self, *args, **kwargs)
        if not resp.ok:
            raise RequestNok(resp.status_code)
        payload = resp.json()
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
    def result_get(self, *args, **kwargs):
        return super().get(*args, **kwargs)

    @unpack_result
    def result_post(self, *args, **kwargs):
        return super().post(*args, **kwargs)

    @unpack_result
    def result_put(self, *args, **kwargs):
        return super().put(*args, **kwargs)


class RequestNok(Exception):
    pass


class ZmfRestNok(Exception):
    pass


def extension(file: str) -> str:
    return Path(file).suffix.lstrip(".")


def jobcard(user: str, action: str = "@") -> Dict[str, str]:
    return {
        "jobCard01": "//" + user + action[:1].upper() + " JOB 0,'CHANGEMAN',",
        "jobCard02": "//         CLASS=A,MSGCLASS=A,",
        "jobCard03": "//         NOTIFY=&SYSUID",
        "jobCard04": "//*",
    }


def read_yaml(file: str) -> dict:
    if file == "-":
        fh = sys.stdin
    else:
        fh = open(file)
    if file.endswith(".toml"):
        data = toml.load(fh)
    else:
        data = yaml.safe_load(fh)
    if file != "-":
        fh.close()
    return data


def removeprefix(self: str, prefix: str, /) -> str:
    if self.startswith(prefix):
        return self[len(prefix) :]
    else:
        return self[:]


def int_or_zero(a: Optional[Union[int, str]]) -> int:
    if isinstance(a, int):
        return a
    elif isinstance(a, str) and a.isdigit():
        return int(a)
    else:
        return 0


def main() -> None:
    fire.Fire(ChangemanZmf)
