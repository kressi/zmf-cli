import logging
import os
import sys

from itertools import groupby
from pathlib import Path
from urllib.parse import urljoin

import fire
import requests
import yaml

from .logrequests import debug_requests_on

RC_HTML_STATUS_NOK = 3
ZMF_STATUS_OK = "00"


def extension(file):
    return Path(file).suffix.lstrip(".")


def jobcard(user, action="@"):
    return {
        "jobCard01": "//" + user + action[:1].upper() + " JOB 0,'CHANGEMAN',",
        "jobCard02": "//         CLASS=A,MSGCLASS=A,",
        "jobCard03": "//         NOTIFY=&SYSUID",
        "jobCard04": "//*",
    }


class ChangemanZmf:
    def __init__(self, user=None, password=None, url=None, verbose=False):
        self.url = url if url else os.getenv("ZMF_REST_URL")
        self.__user = user if user else os.getenv("ZMF_REST_USER")
        self.__password = password if password else os.getenv("ZMF_REST_PWD")
        self.__session = requests.session()
        self.__session.auth = (self.__user, self.__password)
        self.logger = logging.getLogger(__name__)
        if verbose:
            self.logger.setLevel(logging.DEBUG)
            debug_requests_on()
        else:
            self.logger.setLevel(logging.INFO)

    def __execute(self, method, endpoint, data):
        url = urljoin(self.url, endpoint)
        self.logger.info(url)
        self.logger.info(data)
        resp = method(self.__session, url, data=data)
        self.logger.info(resp)
        if resp.ok:
            return resp.json()
        else:
            return None

    def checkin(self, package, pds, components):
        """checkin components from a partitioned dataset (PDS)"""
        resp_ok = True
        data = {
            "package": package,
            "chkInSourceLocation": 1,
            "sourceStorageMeans": 6,
        }
        for tp, comps in groupby(sorted(components, key=extension), extension):
            dt = data.copy()
            dt["componentType"] = tp.upper()
            dt["sourceLib"] = pds + "." + tp.upper()
            dt["targetComponent"] = [Path(c).stem for c in comps]
            resp = self.__execute(
                requests.Session.put, "component/checkin", dt
            )
            if not resp:
                resp_ok = False
                break
        if not resp_ok:
            exit(RC_HTML_STATUS_NOK)

    def build(
        self,
        package,
        components,
        procedure="CMNCOB2",
        language="COBOL",
        db2Precompile=None,
    ):
        """build source like components"""
        resp_ok = True
        data = {
            "package": package,
            "buildProc": procedure,
            "language": language,
        }
        data.update(jobcard(self.__user, "build"))
        if db2Precompile:
            data["useDb2PreCompileOption"] = "Y"
        for tp, comps in groupby(sorted(components, key=extension), extension):
            if tp.lower() in ["sre", "srb"]:
                dt = data.copy()
                dt["componentType"] = tp.upper()
                dt["component"] = [Path(c).stem for c in comps]
                resp = self.__execute(
                    requests.Session.put, "component/build", dt
                )
                if not resp:
                    resp_ok = False
                    break
        if not resp_ok:
            exit(RC_HTML_STATUS_NOK)

    def scratch(self, package, components):
        resp_ok = True
        data = {
            "package": package,
        }
        for comp in components:
            dt = data.copy()
            dt["componentType"] = extension(comp).upper()
            dt["oldComponent"] = Path(comp).stem
            resp = self.__execute(
                requests.Session.put, "component/scratch", dt
            )
            if not resp:
                resp_ok = False
                break
        if not resp_ok:
            exit(RC_HTML_STATUS_NOK)

    def audit(self, package):
        data = {"package": package}
        data.update(jobcard(self.__user, "audit"))
        resp = self.__execute(requests.Session.put, "package/audit", data)
        if not resp:
            exit(RC_HTML_STATUS_NOK)

    def promote(self, package):
        """promote a package"""
        print("promote")

    def freeze(self, package):
        print("freeze")

    def revert(self, package):
        print("revert")

    def search_package(self, app, title):
        data = {
            "package": app + "*",
            "packageTitle": title,
        }
        resp = self.__execute(requests.Session.get, "package/search", data)
        if not resp:
            exit(RC_HTML_STATUS_NOK)
        pkg_id = None
        if resp["returnCode"] == ZMF_STATUS_OK:
            # TODO handle response with multiple packages
            pkg_id = resp["result"][0]["package"]
        return pkg_id

    def create_package(self, package_config=sys.stdin, app=None, title=None):
        with open(package_config, "r") as file:
            config = yaml.safe_load(file)
        data = {
            "applName": app,
            "packageTitle": title,
        }
        data.update(config)
        resp = self.__execute(requests.Session.post, "package", data)
        if not resp:
            exit(RC_HTML_STATUS_NOK)
        return resp["result"][0]["package"]

    def get_package(self, package_config=sys.stdin, app=None, title=None):
        search_title = title
        search_app = app
        if not search_app or not search_title:
            with open(package_config, "r") as file:
                config = yaml.safe_load(file)
                if not search_title:
                    search_title = config["packageTitle"]
                if not search_app:
                    search_app = config["applName"]
        pkg_id = self.search_package(search_app, search_title)
        if not pkg_id:
            pkg_id = self.create_package(package_config, app, title)
        if not pkg_id:
            exit(RC_HTML_STATUS_NOK)
        return pkg_id


def main():
    fire.Fire(ChangemanZmf)
