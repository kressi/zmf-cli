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
from .session import (
    exit_nok,
    ZmfRequest,
    ZmfResult,
    ZmfSession,
    EXIT_CODE_ZMF_NOK,
)

SRC_DIR = "src/"
COMP_STATUS = {
    "Active": "0",
    "Approved": "1",
    "Checkout": "2",
    "Demoted": "3",
    "Frozen": "4",
    "Inactive": "5",
    "Incomplete": "6",
    "Promoted": "7",
    "Refrozen": "8",
    "Rejected": "9",
    "Remote promoted": "A",
    "Submitted for approval": "B",
    "Unfrozen": "C",
}
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
    """
    Command line interface for ZMF REST API

    Available commands:
        checkin               PUT component/checkin
        build                 PUT component/build
        build_config          PUT component/build
        scratch               PUT component/scratch
        audit                 PUT package/audit
        promote               PUT package/promote
        freeze                PUT package/freeze
        revert                PUT package/revert
        search_package        GET package/search
        create_package        POST package
        get_package           Search or create if package does not exist
        get_components        GET component
        get_load_components   GET component/load
        get_package_list      GET component/packagelist
        browse_component      GET component/browse

    Get help for commands with
        zmf [command] --help
    """

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
        """Checkin components to Changeman from a partitioned dataset (PDS)"""
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

    def delete(self, package: str, component: str, componentType: str) -> None:
        data = {
            "package": package,
            "targetComponent": component,
            "componentType": componentType,
        }
        self.__session.result_delete("component", data=data)

    def build(
        self,
        package: str,
        components: Iterable[str],
        procedure: Optional[str] = None,
        language: Optional[str] = None,
        db2Precompile: Optional[bool] = None,
        useHistory: Optional[bool] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> None:
        """Build source like components"""
        data: ZmfRequest = {"package": package}
        data.update(jobcard(self.__user, "build"))
        if params is not None:
            data.update(params)
        if procedure is not None:
            data["buildProc"] = procedure
        if language is not None:
            data["language"] = language
        if db2Precompile is not None:
            data["useDb2PreCompileOption"] = to_yes_no(db2Precompile)
        if useHistory is not None:
            data["useHistory"] = to_yes_no(useHistory)
        for t, comps in groupby(sorted(components, key=extension), extension):
            dt = data.copy()
            dt["componentType"] = t.upper()
            dt["component"] = [Path(c).stem for c in comps]
            self.__session.result_put("component/build", data=dt)

    def build_config(
        self, package: str, components: Iterable[str], config_file: str
    ) -> None:
        """Build source like components with build configuration"""
        allconfigs = read_config(config_file)
        data = {"package": package}
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
        for comp in components:
            data = {"package": package}
            data["componentType"] = extension(comp).upper()
            data["oldComponent"] = Path(comp).stem
            self.__session.result_put("component/scratch", data=data)

    def audit(self, package: str) -> None:
        data = {"package": package}
        data.update(jobcard(self.__user, "audit"))
        self.__session.result_put("package/audit", data=data)

    def promote(
        self, package: str, promSiteName: str, promLevel: int, promName: str
    ) -> None:
        """Promote a package"""
        data = {
            "package": package,
            "promotionSiteName": promSiteName,
            "promotionLevel": promLevel,
            "promotionName": promName,
        }
        data.update(jobcard_s(self.__user, "promote"))
        self.__session.result_put("package/promote", data=data)

    def freeze(self, package: str) -> None:
        data = {"package": package}
        data.update(jobcard(self.__user, "freeze"))
        self.__session.result_put("package/freeze", data=data)

    def revert(self, package: str, revertReason: Optional[str] = None) -> None:
        data = {"package": package}
        data.update(jobcard(self.__user, "revert"))
        if revertReason is not None:
            data["revertReason01"] = revertReason
        self.__session.result_put("package/revert", data=data)

    def search_package(
        self, app: str, title: str, workChangeRequest: Optional[str] = None
    ) -> Optional[str]:
        data = {
            "package": app + "*",
            "packageTitle": title,
        }
        if workChangeRequest is not None:
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
        config_file: Union[str, "os.PathLike[str]", None] = None,
        applName: Optional[str] = None,
        packageTitle: Optional[str] = None,
        workChangeRequest: Optional[str] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> Optional[str]:
        if params is not None:
            data = params.copy()
        else:
            data = {}
        if applName is not None:
            data["applName"] = applName
        if packageTitle is not None:
            data["packageTitle"] = packageTitle
        if workChangeRequest is not None:
            data["workChangeRequest"] = workChangeRequest
        if config_file is not None:
            config = read_config(config_file)
            data.update(config)
        result = self.__session.result_post("package", data=data)
        self.logger.info(result)
        return str_or_none(result[0].get("package")) if result else None

    def get_package(
        self,
        config_file: Union[str, "os.PathLike[str]", None] = None,
        applName: Optional[str] = None,
        packageTitle: Optional[str] = None,
        workChangeRequest: Optional[str] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> Optional[str]:
        pkg_id = None
        if params is not None:
            pkg_id = params.get("package")
        elif config_file is not None:
            config = read_config(config_file)
            pkg_id = config.get("package")
        if not pkg_id:
            if params is not None:
                search_app = params.get("applName", applName)
                search_title = params.get("packageTitle", packageTitle)
                search_request = params.get(
                    "workChangeRequest", workChangeRequest
                )
            elif config_file is not None:
                search_app = config.get("applName", applName)
                search_title = config.get("packageTitle", packageTitle)
                search_request = config.get(
                    "workChangeRequest", workChangeRequest
                )
            else:
                search_app = applName
                search_title = packageTitle
                search_request = workChangeRequest
            if search_app is not None and search_title is not None:
                try:
                    pkg_id = self.search_package(
                        search_app, search_title, search_request
                    )
                except SystemExit as e:
                    if e.code != EXIT_CODE_ZMF_NOK:
                        sys.exit(e.code)
        if not pkg_id:
            pkg_id = self.create_package(
                config_file, applName, packageTitle, workChangeRequest, params
            )
        return pkg_id

    def get_components(
        self,
        package: str,
        componentType: Optional[str] = None,
        component: Optional[str] = None,
        targetComponent: Optional[str] = None,
        filterActive: Optional[bool] = None,
        filterIncomplete: Optional[bool] = None,
        filterInactive: Optional[bool] = None,
    ) -> Optional[ZmfResult]:
        data = {"package": package}
        if componentType is not None:
            data["componentType"] = componentType
        if component is not None:
            data["component"] = component
        if targetComponent is not None:
            data["targetComponent"] = targetComponent
        if filterActive is not None:
            data["filterActiveStatus"] = to_yes_no(filterActive)
        if filterIncomplete is not None:
            data["filterIncompleteStatus"] = to_yes_no(filterIncomplete)
        if filterInactive is not None:
            data["filterInactiveStatus"] = to_yes_no(filterInactive)
        return self.__session.result_get("component", data=data)

    def get_load_components(
        self,
        package: str,
        sourceType: Optional[str] = None,
        sourceComponent: Optional[str] = None,
        targetType: Optional[str] = None,
        targetComponent: Optional[str] = None,
    ) -> Optional[ZmfResult]:
        data = {"package": package}
        if sourceType is not None:
            data["componentType"] = sourceType
        if sourceComponent is not None:
            data["component"] = sourceComponent
        if targetType is not None:
            data["targetComponentType"] = targetType
        if targetComponent is not None:
            data["targetComponent"] = targetComponent
        return self.__session.result_get("component/load", data=data)

    def get_package_list(
        self,
        package: str,
        componentType: Optional[str] = None,
        component: Optional[str] = None,
        targetComponent: Optional[str] = None,
    ) -> Optional[ZmfResult]:
        data = {"package": package}
        if componentType is not None:
            data["sourceComponentType"] = componentType
        if component is not None:
            data["sourceComponent"] = component
        if targetComponent is not None:
            data["targetComponent"] = targetComponent
        return self.__session.result_get("component/packagelist", data=data)

    def browse_component(
        self, package: str, component: str, componentType: str
    ) -> Optional[str]:
        result = None
        data = {
            "package": package,
            "component": component,
            "componentType": componentType,
        }
        resp = self.__session.get("component/browse", data=data)
        exit_nok(resp, logger=self.logger)
        self.logger.info(
            {
                k: resp.headers.get(k)
                for k in ["content-type", "content-disposition"]
            }
        )
        tp = resp.headers.get("content-type", "")
        disp = resp.headers.get("content-disposition", "")
        if tp.startswith("application/json"):
            self.logger.warning(resp.json())
        elif tp.startswith("text/plain") and disp.startswith("attachment"):
            result = resp.text
        else:
            self.logger.error("Unexpected content-type '{}'".format(tp))
            sys.exit(EXIT_CODE_ZMF_NOK)
        return result


def extension(file: str) -> str:
    return Path(file).suffix.lstrip(".")


def jobcard(user: str, action: str = "@") -> Dict[str, str]:
    return {
        "jobCard01": "//" + user + action[:1].upper() + " JOB 0,'CHANGEMAN',",
        "jobCard02": "//         CLASS=A,MSGCLASS=A,",
        "jobCard03": "//         NOTIFY=&SYSUID",
        "jobCard04": "//*",
    }


def jobcard_s(user: str, action: str = "@") -> Dict[str, str]:
    return {
        "jobCards01": "//" + user + action[:1].upper() + " JOB 0,'CHANGEMAN',",
        "jobCards02": "//         CLASS=A,MSGCLASS=A,",
        "jobCards03": "//         NOTIFY=&SYSUID",
        "jobCards04": "//*",
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


def removeprefix(self: str, prefix: str) -> str:
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


def to_yes_no(x: bool) -> str:
    if x is True:
        return "Y"
    else:
        return "N"


def main() -> None:
    fire.Fire(ChangemanZmf)
