import fire
import json
import os
import requests
import yaml

from itertools import groupby
from pathlib import Path
from urllib.parse import urljoin


HTML_STATUS_NOK = 3


def extension(file):
    return Path(file).suffix.lstrip(".")


def jobcard(user, action="@"):
    return {
        "jobCard01": "//" + user + action[:1].upper() + " JOB 0,'CHANGEMAN',",
        "jobCard02": "//         CLASS=A,MSGCLASS=A,",
        "jobCard03": "//         NOTIFY=&SYSUID",
        "jobCard04": "//*",
    }


def exit_if_nok(status_code):
    if status_code != requests.codes.ok:
        print("Status: ", status_code)
        exit(HTML_STATUS_NOK)


class ChangemanZmf:
    def __init__(self, user=None, password=None, url=None):
        self.url = url if url else os.getenv("ZMF_REST_URL")
        self.__user = user if user else os.getenv("ZMF_REST_USER")
        self.__password = password if password else os.getenv("ZMF_REST_PWD")
        self.__session = requests.session()
        self.__session.auth = (self.__user, self.__password)

    def checkin(self, package, pds, components):
        """checkin components from a partitioned dataset (PDS)"""
        result = []
        resp_status = requests.codes.ok
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
            url = urljoin(self.url, "component/checkin")
            resp = self.__session.put(url, data=dt)
            if not resp.ok:
                resp_status = resp.status_code
                break
            result.append(resp.json())
        if resp_status == requests.codes.ok:
            return result
        else:
            print(json.dumps(result), indent=4)
            print("Status: ", resp_status)
            exit(HTML_STATUS_NOK)

    def build(
        self,
        package,
        components,
        procedure="CMNCOB2",
        language="COBOL",
        db2Precompile=None,
    ):
        """build source like components"""
        result = []
        resp_status = requests.codes.ok
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
                url = urljoin(self.url, "component/build")
                resp = self.__session.put(url, data=dt)
                if not resp.ok:
                    resp_status = resp.status_code
                    break
                result.append(resp.json())
        if resp_status == requests.codes.ok:
            return result
        else:
            print(json.dumps(result), indent=4)
            print("Status: ", resp_status)
            exit(HTML_STATUS_NOK)

    def scratch(self, package, components):
        data = {
            "package": package,
        }
        for comp in components:
            dt = data.copy()
            dt["componentType"] = extension(comp).upper()
            dt["oldComponent"] = Path(comp).stem
            url = urljoin(self.url, "component/scratch")
            resp = self.__session.put(url, data=dt)
            if not resp.ok:
                resp_status = resp.status_code
                break
            result.append(resp.json())
        if resp_status == requests.codes.ok:
            return result
        else:
            print(json.dumps(result), indent=4)
            print("Status: ", resp_status)
            exit(HTML_STATUS_NOK)

    def audit(self, package):
        data = {
            "package": package,
        }
        data.update(jobcard(self.__user, "audit"))
        dt = data.copy()
        url = urljoin(self.url, "package/audit")
        resp = self.__session.put(url, data=dt)
        exit_if_nok(resp.status_code)
        return resp.json()

    def promote(self, package):
        """promote a package"""
        print("promote")

    def freeze(self, package):
        print("freeze")

    def revert(self, package):
        print("revert")

    def search_package(self, title):
        data = {"packageTitle": title}
        url = urljoin(self.url, "package/search")
        resp = self.__session.get(url, data=data)
        exit_if_nok(resp.status_code)
        return resp.json()

    def create_package(
        self, package_config="/dev/stdin", app=None, title=None
    ):
        with open(package_config, "r") as file:
            config = yaml.safe_load(file)
        data = {
            "applName": app,
            "packageTitle": title,
        }
        data.update(config)
        url = urljoin(self.url, "package")
        resp = self.__session.post(url, data=data)
        exit_if_nok(resp.status_code)
        return resp.json()


def main():
    fire.Fire(ChangemanZmf)
