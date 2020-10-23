import logging
import os
import sys

from itertools import groupby
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin

import fire
import requests
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


class ChangemanZmf:
    def __init__(
        self,
        user: Optional[str] = None,
        password: Optional[str] = None,
        url: Optional[str] = None,
        verbose: bool = False,
    ) -> None:
        self.url = url if url else os.getenv("ZMF_REST_URL")
        self.__user = user if user else os.getenv("ZMF_REST_USER")
        self.__password = password if password else os.getenv("ZMF_REST_PWD")
        logging.basicConfig()
        self.logger = logging.getLogger(__name__)
        self.__session = ZmfSession(self.url, self.logger)
        self.__session.auth = (self.__user, self.__password)
        if verbose:
            self.logger.setLevel(logging.DEBUG)
            debug_requests_on()
        else:
            self.logger.setLevel(logging.INFO)

    def checkin(self, package: str, pds: str, components: List[str]):
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
            resp = self.__session.put("component/checkin", data=dt)
            self.logger.info(resp)

    def build(
        self,
        package: str,
        components: List[str],
        procedure: str = "CMNCOB2",
        language: str = "COBOL",
        db2Precompile: Optional[bool] = None,
    ) -> None:
        """build source like components"""
        data = {
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
            resp = self.__session.put("component/build", data=dt)
            self.logger.info(resp)

    def build_config(
        self, package: str, components: List[str], config_file: str = "-"
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
            dt.update(allconfigs.get(removeprefix(comp, SRC_DIR)))
            dt["componentType"] = extension(comp).upper()
            dt["component"] = Path(comp).stem
            resp = self.__session.put("component/build", data=dt)
            self.logger.info(resp)

    def scratch(self, package: str, components: List[str]) -> None:
        data = {"package": package}
        for comp in components:
            dt = data.copy()
            dt["componentType"] = extension(comp).upper()
            dt["oldComponent"] = Path(comp).stem
            resp = self.__session.put("component/scratch", data=dt)
            self.logger.info(resp)

    def audit(self, package: str) -> None:
        data = {"package": package}
        data.update(jobcard(self.__user, "audit"))
        resp = self.__session.put("package/audit", data=data)
        self.logger.info(resp)

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
        resp = self.__session.get("package/search", data=data)
        pkg_id = None
        if resp.get("returnCode") == ZMF_STATUS_OK:
            # in case multiple packages have been found take the youngest
            for pkg in sorted(
                resp.get("result"),
                key=lambda p: p.get("packageId"),
                reverse=True,
            ):
                # search matches title as substring, ensure full title matches
                if pkg.get("packageTitle") == title:
                    pkg_id = pkg.get("package")
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
        resp = self.__session.post("package", data=data)
        self.logger.info(resp)
        return resp.get("result", [{}])[0].get("package")

    def get_package(self, config_file="-", app=None, title=None):
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
class ZmfSession(requests.Session):
    def __init__(
        self,
        prefix_url: Optional[str] = None,
        logger: Optional[logging.Logger] = None,
        *args,
        **kwargs,
    ) -> None:
        super(ZmfSession, self).__init__(*args, **kwargs)
        self.prefix_url = prefix_url
        self.logger = logger

    def request(
        self,
        method: str,
        url: str,
        data: Optional[dict] = None,
        *args,
        **kwargs,
    ) -> dict:
        url = urljoin(self.prefix_url, url)
        if self.logger:
            self.logger.info(url)
            self.logger.info(data)
        resp = super(ZmfSession, self).request(
            method, url, data=data, *args, **kwargs
        )
        if self.logger:
            self.logger.info(resp)
        if not resp.ok:
            raise RequestNok(resp.status_code)
        return resp.json()


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
    if file in ["-", "/dev/stdin"]:
        fh = sys.stdin
    else:
        fh = open(file)
    data = yaml.safe_load(fh)
    if file != "-":
        fh.close()
    return data


def removeprefix(self: str, prefix: str, /) -> str:
    if self.startswith(prefix):
        return self[len(prefix) :]
    else:
        return self[:]


def main():
    fire.Fire(ChangemanZmf)
