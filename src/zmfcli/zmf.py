import logging
import os
import sys

from itertools import groupby
from pathlib import Path
from typing import Any, Dict, Iterable, MutableMapping, Optional, Union

import fire  # type: ignore
import toml
import yaml

from .logrequests import debug_requests_on
from .session import ZmfRequest, ZmfSession

SRC_DIR = "src/"
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
            logging.getLogger().setLevel(logging.DEBUG)
            debug_requests_on()
        else:
            logging.getLogger().setLevel(logging.INFO)

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
        data: ZmfRequest = {
            "package": package,
            "buildProc": procedure,
            "language": language,
        }
        data.update(jobcard(self.__user, "build"))
        if db2Precompile:
            data["useDb2PreCompileOption"] = "Y"
        for t, comps in groupby(sorted(components, key=extension), extension):
            dt = data.copy()
            dt["componentType"] = t.upper()
            dt["component"] = [Path(c).stem for c in comps]
            self.__session.result_put("component/build", data=dt)

    def build_config(
        self, package: str, components: Iterable[str], config_file: str
    ) -> None:
        """build source like components"""
        allconfigs = read_config(config_file)
        data = {
            "package": package,
            "buildProc": "CMNCOB2",
            "language": "COBOL",
        }
        data.update(jobcard(self.__user, "build"))
        for comp in components:
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

    def promote(
        self, package: str, promSiteName: str, promLevel: int, promName: str
    ) -> None:
        """promote a package"""
        data = {
            "package": package,
            "promotionSiteName": promSiteName,
            "promotionLevel": promLevel,
            "promotionName": promName,
        }
        data.update(jobcard(self.__user, "promote"))
        self.__session.result_put("package/promote", data=data)

    def freeze(self, package: str) -> None:
        data = {"package": package}
        data.update(jobcard(self.__user, "freeze"))
        self.__session.result_put("package/freeze", data=data)

    def revert(self, package: str) -> None:
        data = {"package": package}
        data.update(jobcard(self.__user, "revert"))
        self.__session.result_put("package/revert", data=data)

    def search_package(
        self, app: str, title: str, workChangeRequest: Optional[str] = None
    ) -> Optional[str]:
        data = {
            "package": app + "*",
            "packageTitle": title,
        }
        if workChangeRequest:
            data["workChangeRequest"] = workChangeRequest
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
        return str_or_none(pkg_id)

    def create_package(
        self,
        config_file: Union[str, "os.PathLike[str]"] = "-",
        app: Optional[str] = None,
        title: Optional[str] = None,
    ) -> Optional[str]:
        data = {
            "applName": app,
            "packageTitle": title,
        }
        config = read_config(config_file)
        data.update(config)
        result = self.__session.result_post("package", data=data)
        self.logger.info(result)
        return str_or_none(result[0].get("package")) if result else None

    def get_package(
        self,
        config_file: Union[str, "os.PathLike[str]"] = "-",
        app: Optional[str] = None,
        title: Optional[str] = None,
        workChangeRequest: Optional[str] = None,
    ) -> Optional[str]:
        config = read_config(config_file)
        pkg_id = config.get("package")
        if not pkg_id:
            search_app = config.get("applName", app)
            search_title = config.get("packageTitle", title)
            search_request = config.get("workChangeRequest", workChangeRequest)
            pkg_id = self.search_package(
                search_app, search_title, search_request
            )
        if not pkg_id:
            pkg_id = self.create_package(config_file, app, title)
        return pkg_id


def extension(file: str) -> str:
    return Path(file).suffix.lstrip(".")


def jobcard(user: str, action: str = "@") -> Dict[str, str]:
    return {
        "jobCard01": "//" + user + action[:1].upper() + " JOB 0,'CHANGEMAN',",
        "jobCard02": "//         CLASS=A,MSGCLASS=A,",
        "jobCard03": "//         NOTIFY=&SYSUID",
        "jobCard04": "//*",
    }


def read_config(
    file: Union[str, "os.PathLike[str]"]
) -> MutableMapping[str, Any]:
    if isinstance(file, str) and file == "-":
        fh = sys.stdin
    else:
        fh = open(file)
    if Path(file).suffix == ".toml":
        data = toml.load(fh)
    else:
        data = yaml.safe_load(fh)
    if fh != sys.stdin:
        fh.close()
    return data


def removeprefix(self: str, prefix: str, /) -> str:
    if self.startswith(prefix):
        return self[len(prefix) :]
    else:
        return self[:]


def int_or_zero(a: Union[int, str, None]) -> int:
    if isinstance(a, int):
        return a
    elif isinstance(a, str) and a.isdigit():
        return int(a)
    else:
        return 0


def str_or_none(a: Union[int, str, None]) -> Optional[str]:
    if a is None:
        return None
    else:
        return str(a)


def main() -> None:
    fire.Fire(ChangemanZmf)
