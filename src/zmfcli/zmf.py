#!/bin/env python

import fire
import json
import os
import requests

from itertools import groupby
from pathlib import Path
from urllib.parse import urljoin


def extension(file):
    return Path(file).suffix.lstrip(".")


class ChangemanZmf:
    def __init__(self, user=None, password=None, url=None):
        self.url = url if url else os.getenv("ZMF_REST_URL")
        self.__user = user if user else os.getenv("ZMF_REST_USER")
        self.__password = password if password else os.getenv("ZMF_REST_PWD")
        self.__session = requests.session()
        self.__session.auth = (self.__user, self.__password)

    def checkin(self, package, pds, components):
        """checkin components from a partitioned dataset (PDS)"""
        data = {"package": package, "chkInSourceLocation": 1, "sourceStorageMeans": 6}
        for tp, comps in groupby(sorted(components, key=extension), extension):
            dt = data.copy()
            dt["componentType"] = tp.upper()
            dt["sourceLib"] = pds + "." + tp.upper()
            dt["targetComponent"] = [Path(c).stem for c in comps]
            url = urljoin(self.url, "component/checkin")
            resp = self.__session.put(url, data=dt)
            print("Status: ", resp.status_code)
            if resp.ok:
                print(json.dumps(resp.josn(), indent=4, sort_keys=True))

    def build(self, package, components):
        """build source like components"""
        data = {
            "package": package,
            "buildProc": "CMNCOB2",
            "language": "DELTACOB",
            "jobCard01": "//" + self.__user + "A JOB 0,'CHANGEMAN',",
            "jobCard02": "//         CLASS=A,MSGCLASS=A,",
            "jobCard03": "//         NOTIFY=&SYSUID",
            "jobCard04": "//*",
        }
        for tp, comps in groupby(sorted(components, key=extension), extension):
            if tp.upper() == "SRE":
                dt = data.copy()
                dt["componentType"] = tp.upper()
                dt["component"] = [Path(c).stem for c in comps]
                url = urljoin(self.url, "component/build")
                resp = self.__session.put(url, data=dt)
                print("Status: ", resp.status_code)
                if resp.ok:
                    print(json.dumps(resp.josn(), indent=4, sort_keys=True))

    def audit(self, package):
        print("audit")

    def promote(self, package):
        """promote a package"""
        print("promote")

    def freeze(self, package):
        print("freeze")

    def revert(self, package):
        print("revert")

    def search(self, package, title=None):
        data = {"package": package}
        if title:
            data["packageTitle"] = title
        url = urljoin(self.url, "package/search")
        resp = self.__session.get(url, data=data)
        print("Status: ", resp.status_code)
        if resp.ok:
            print(json.dumps(resp.josn(), indent=4, sort_keys=True))

    # def create(
    #         self,
    #         applName,
    #         title,
    #         description,
    #         workChangeRequest,
    #         requestorDept,
    #         requestorName,
    #         requestorPhone,
    #         siteName,
    #         installDate,
    #         fromInstallTime,
    #         toInstallTime,
    #         contactName,
    #         contactPhone,
    #         alternateContactName,
    #         alternateContactPhone ):
    #     data = {
    #         'package': package
    #     }
    #     if title:
    #         data['packageTitle'] = title
    #     url = urljoin(self.url, 'package')
    #     resp = self.__session.post(url, data=data)
    #     print('Status: ', resp.status_code)
    #     if resp.ok:
    #         print(json.dumps(resp.josn(), indent=4, sort_keys=True))


def main():
    fire.Fire(ChangemanZmf)
