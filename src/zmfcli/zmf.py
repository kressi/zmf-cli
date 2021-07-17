import logging
import os
import sys

from itertools import groupby
from pathlib import Path
from typing import Dict, Iterable, Optional, Union

import fire  # type: ignore

from .logrequests import debug_requests_on
from .session import (
    exit_nok,
    ZmfRequest,
    ZmfResult,
    ZmfSession,
    EXIT_CODE_ZMF_NOK,
)

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
PROCESSING_OPTION = {"delete": 1, "undelete": 2}
REQUEST_TYPE = {
    "full promotion history": 1,
    "current status per site": 2,
    "full, including lock records": 3,
}
SOURCE_LOCATION: Dict[str, Union[str, int]] = {
    "development dataset": 1,
    "package": 5,
    "temp sequential dataset": 7,
    "edit from package lib": "E",
}
SOURCE_STORAGE: Dict[str, Union[str, int]] = {
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
        delete                DELETE component
        build                 PUT component/build
        scratch               PUT component/scratch
        audit                 PUT package/audit
        promote               PUT package/promote
        demote                PUT package/demote
        freeze                PUT package/freeze
        revert                PUT package/revert
        search_package        GET package/search
        create_package        POST package
        delete_package        DELETE package
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

    def _get(
        self, path_name: str, **params: Union[int, str, bool, Iterable[str]]
    ) -> Optional[ZmfResult]:
        return self.__session.result_get(
            to_path(path_name), data=prepare_bools(params)
        )

    def _post(
        self, path_name: str, **params: Union[int, str, bool, Iterable[str]]
    ) -> Optional[ZmfResult]:
        return self.__session.result_post(
            to_path(path_name), data=prepare_bools(params)
        )

    def _put(
        self, path_name: str, **params: Union[int, str, bool, Iterable[str]]
    ) -> Optional[ZmfResult]:
        return self.__session.result_put(
            to_path(path_name), data=prepare_bools(params)
        )

    def _delete(
        self, path_name: str, **params: Union[int, str, bool, Iterable[str]]
    ) -> Optional[ZmfResult]:
        return self.__session.result_delete(
            to_path(path_name), data=prepare_bools(params)
        )

    def checkin(
        self, package: str, pds: str, components: Iterable[str]
    ) -> None:
        """Checkin components to Changeman from a partitioned dataset (PDS)"""
        for tp, comps in groupby(sorted(components, key=extension), extension):
            self._put(
                "component_checkin",
                package=package,
                chkInSourceLocation=SOURCE_LOCATION["development dataset"],
                sourceStorageMeans=SOURCE_STORAGE["pds"],
                componentType=tp.upper(),
                sourceLib=pds + "." + tp.upper(),
                targetComponent=[Path(c).stem for c in comps],
            )

    def delete(self, package: str, component: str, componentType: str) -> None:
        self._delete(
            "component",
            package=package,
            targetComponent=component,
            componentType=componentType,
        )

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
        jobcard_dict = jobcard(self.__user, "build")
        data: ZmfRequest = {}
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
            self._put(
                "component_build",
                package=package,
                componentType=t.upper(),
                component=[Path(c).stem for c in comps],
                **jobcard_dict,
                **data,
            )

    def scratch(self, package: str, components: Iterable[str]) -> None:
        for comp in components:
            self._put(
                "component_scratch",
                package=package,
                componentType=extension(comp).upper(),
                oldComponent=Path(comp).stem,
            )

    def audit(self, package: str) -> None:
        jobcard_dict = jobcard(self.__user, "audit")
        self._put("package_audit", package=package, **jobcard_dict)

    def promote(
        self,
        package: str,
        promSiteName: str,
        promLevel: int,
        promName: str,
        overlay: Optional[bool] = None,
    ) -> None:
        """Promote a package"""
        data = {}
        if overlay is not None:
            data["overlayTargetComponents"] = to_yes_no(overlay)
        jobcard_dict = jobcard_s(self.__user, "promote")
        self._put(
            "package/promote",
            package=package,
            promotionSiteName=promSiteName,
            promotionLevel=promLevel,
            promotionName=promName,
            **data,
            **jobcard_dict,
        )

    def demote(
        self,
        package: str,
        promSiteName: str,
        promLevel: int,
        promName: str,
    ) -> None:
        """Demote a package"""
        jobcard_dict = jobcard_s(self.__user, "demote")
        self._put(
            "package/demote",
            package=package,
            promotionSiteName=promSiteName,
            promotionLevel=promLevel,
            promotionName=promName,
            **jobcard_dict,
        )

    def freeze(self, package: str) -> None:
        jobcard_dict = jobcard(self.__user, "freeze")
        self._put("package/freeze", package=package, **jobcard_dict)

    def revert(self, package: str, revertReason: Optional[str] = None) -> None:
        data = {}
        if revertReason is not None:
            data["revertReason01"] = revertReason
        jobcard_dict = jobcard(self.__user, "revert")
        self._put("package/revert", package=package, **data, **jobcard_dict)

    def search_package(
        self,
        applName: str,
        packageTitle: str,
        workChangeRequest: Optional[str] = None,
    ) -> Optional[str]:
        data = {}
        if workChangeRequest is not None:
            data["workChangeRequest"] = workChangeRequest
        result = self._get(
            "package_search",
            package=applName + "*",
            packageTitle=packageTitle,
            **data,
        )
        pkg_id = None
        # in case multiple packages have been found take the youngest
        if result:
            for pkg in sorted(
                result,
                key=lambda p: int_or_zero(p.get("packageId")),
                reverse=True,
            ):
                # search matches title as substring, ensure full title matches
                if pkg.get("packageTitle") == packageTitle:
                    pkg_id = pkg.get("package")
                    break
        return str_or_none(pkg_id)

    def create_package(
        self,
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
        result = self.__session.result_post("package", data=data)
        self.logger.info(result)
        return str_or_none(result[0].get("package")) if result else None

    def delete_package(
        self,
        package: str,
    ) -> None:
        data = {
            "package": package,
            "processingOption": PROCESSING_OPTION["delete"],
        }
        self.__session.result_delete("package", data=data)

    def get_package(
        self,
        applName: Optional[str] = None,
        packageTitle: Optional[str] = None,
        workChangeRequest: Optional[str] = None,
        params: Optional[Dict[str, str]] = None,
    ) -> Optional[str]:
        pkg_id = None
        if params is not None:
            pkg_id = params.get("package")
        if not pkg_id:
            if params is None:
                search_app = applName
                search_title = packageTitle
                search_request = workChangeRequest
            else:
                search_app = params.get("applName", applName)
                search_title = params.get("packageTitle", packageTitle)
                search_request = params.get(
                    "workChangeRequest", workChangeRequest
                )
            if search_app is not None and search_title is not None:
                try:
                    pkg_id = self.search_package(
                        applName=search_app,
                        packageTitle=search_title,
                        workChangeRequest=search_request,
                    )
                except SystemExit as e:
                    if e.code != EXIT_CODE_ZMF_NOK:
                        sys.exit(e.code)
        if not pkg_id:
            pkg_id = self.create_package(
                applName=applName,
                packageTitle=packageTitle,
                workChangeRequest=workChangeRequest,
                params=params,
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


def to_path(name: str) -> str:
    return name.replace("__", "-").replace("_", "/")


def prepare_bools(
    params: Dict[str, Union[str, int, bool, Iterable[str]]]
) -> Dict[str, Union[str, int, Iterable[str]]]:
    return {
        key: to_yes_no(value) if type(value) is bool else value
        for key, value in params.items()
    }


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
