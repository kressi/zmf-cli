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

SRC_DIR = 'src/'
SOURCE_LIKE = ['sre', 'srb', 'src', 'sra']
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


class ChangemanZmf:
    def __init__(self, user=None, password=None, url=None, verbose=False):
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

    def checkin(self, package, pds, components):
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
        package,
        components,
        procedure="CMNCOB2",
        language="COBOL",
        db2Precompile=None,
    ):
        """build source like components"""
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
                resp = self.__session.put("component/build", data=dt)
                self.logger.info(resp)

    def build_config(self, package, components, config_file="-"):
        """build source like components"""
        allconfigs = read_yaml(config_file)
        data = {
            "package": package,
            "buildProc": "CMNCOB2",
            "language": "COBOL",
        }
        data.update(jobcard(self.__user, "build"))
        source_comps = (c for c in components if extension(c) in SOURCE_LIKE)
        for comp in source_comps
            dt = data.copy()
            dt.update(allconfigs.get(comp.removeprefix(SRC_DIR)))
            dt["componentType"] = extension(comp)
            dt["component"] = Path(comp).stem
            resp = self.__session.put("component/build", data=dt)
            self.logger.info(resp)

    def scratch(self, package, components):
        data = {"package": package}
        for comp in components:
            dt = data.copy()
            dt["componentType"] = extension(comp).upper()
            dt["oldComponent"] = Path(comp).stem
            resp = self.__session.put("component/scratch", data=dt)
            self.logger.info(resp)

    def audit(self, package):
        data = {"package": package}
        data.update(jobcard(self.__user, "audit"))
        resp = self.__session.put("package/audit", data=data)
        self.logger.info(resp)

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
        resp = self.__session.get("package/search", data=data)
        pkg_id = None
        if resp["returnCode"] == ZMF_STATUS_OK:
            # in case multiple packages have been found take the youngest
            for pkg in sorted(
                resp["result"], key=lambda p: p["packageId"], reverse=True
            ):
                # search matches title as substring, ensure full title matches
                if pkg["packageTitle"] == title:
                    pkg_id = pkg["package"]
        return pkg_id

    def create_package(self, config_file="-", app=None, title=None):
        data = {
            "applName": app,
            "packageTitle": title,
        }
        config = read_yaml(config_file)
        data.update(config)
        resp = self.__session.post("package", data=data)
        return resp["result"][0]["package"]

    def get_package(self, config_file="-", app=None, title=None):
        config = read_yaml(config_file)
        search_app = config.get("applName", app)
        search_title = config.get("packageTitle", title)
        pkg_id = self.search_package(search_app, search_title)
        if not pkg_id:
            pkg_id = self.create_package(config_file, app, title)
        return pkg_id


# https://stackoverflow.com/a/51026159
class ZmfSession(requests.Session):
    def __init__(self, prefix_url=None, logger=None, *args, **kwargs):
        super(ZmfSession, self).__init__(*args, **kwargs)
        self.prefix_url = prefix_url
        self.logger = logger

    def request(self, method, url, data=None, *args, **kwargs):
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


def extension(file):
    return Path(file).suffix.lstrip(".")


def jobcard(user, action="@"):
    return {
        "jobCard01": "//" + user + action[:1].upper() + " JOB 0,'CHANGEMAN',",
        "jobCard02": "//         CLASS=A,MSGCLASS=A,",
        "jobCard03": "//         NOTIFY=&SYSUID",
        "jobCard04": "//*",
    }


def read_yaml(file):
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
        return self[len(prefix):]
    else:
        return self[:]

def get_build_config(all_configs, component):
    config = all_configs.get(component.removeprefix(SRC_DIR))
    config.update({"componentType": extension(component)})
    return config


def main():
    fire.Fire(ChangemanZmf)
