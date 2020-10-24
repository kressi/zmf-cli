import io

import pytest
import responses
import yaml

from zmfcli.zmf import ChangemanZmf, ZmfRestNok
from zmfcli.logrequests import debug_requests_on


ZMF_REST_URL = "https://example.com:8080/zmfrest"
COMPONENTS = [
    "src/CPY/APPI0001.cpy",
    "src/SRB/APPB0001.srb",
    "src/SRB/APPB0002.srb",
    "src/SRE/APPE0001.sre",
    "src/SRE/APPE0002.sre",
]


@pytest.fixture
def zmfapi():
    return ChangemanZmf(
        user="U000000",
        password="Pa$$w0rd",
        url="https://example.com:8080/zmfrest/",
    )


@responses.activate
def test_checkin(zmfapi):
    data = {
        "returnCode": "00",
        "message": "CMNXXXXI - ...",
        "reasonCode": "XXXX",
    }
    responses.add(
        responses.PUT,
        "https://example.com:8080/zmfrest/component/checkin",
        json=data,
        headers={"content-type": "application/json"},
        status=200,
    )
    debug_requests_on()
    assert zmfapi.checkin("APP 000000", "U000000.LIB", COMPONENTS) is None


@responses.activate
def test_build(zmfapi):
    data_ok = {
        "returnCode": "00",
        "message": "CMN8700I - Component Build service completed",
        "reasonCode": "8700",
    }
    responses.add(
        responses.PUT,
        "https://example.com:8080/zmfrest/component/build",
        json=data_ok,
        headers={"content-type": "application/json"},
        status=200,
    )
    assert zmfapi.build("APP 000000", COMPONENTS) is None
    assert zmfapi.build("APP 000000", COMPONENTS, db2Precompile=True) is None
    data_no_info = {  # lowercase componentType
        "returnCode": "08",
        "message": "CMN6504I - No information found for this request.",
        "reasonCode": "6504",
    }
    responses.reset()
    responses.add(
        responses.PUT,
        "https://example.com:8080/zmfrest/component/build",
        json=data_no_info,
        headers={"content-type": "application/json"},
        status=200,
    )
    with pytest.raises(ZmfRestNok) as excinfo:
        zmfapi.build("APP 000000", COMPONENTS)
    assert "CMN6504I" in str(excinfo.value)
    data_no_comp = {
        "returnCode": "08",
        "message": "CMN8464I - exist.sre is not a component within the package",  # noqa: E501
        "reasonCode": "8464",
    }
    responses.reset()
    responses.add(
        responses.PUT,
        "https://example.com:8080/zmfrest/component/build",
        json=data_no_comp,
        headers={"content-type": "application/json"},
        status=200,
    )
    with pytest.raises(ZmfRestNok) as excinfo:
        zmfapi.build("APP 000000", ["file/does/not/exist.sre"])
    assert "CMN8464I" in str(excinfo.value)


response_create = {
    "returnCode": "00",
    "message": "CMN2100I - APP 000001 change package has been created.",
    "reasonCode": "2100",
    "result": [
        {
            "package": "APP 000001",
            "packageLevel": "1",
            "installDate": "20211231",
            "applName": "APP",
            "packageId": 11,
            "packageType": "1",
            "packageStatus": "6",
        }
    ],
}


@responses.activate
def test_build_config(zmfapi, tmp_path):
    data = {
        "returnCode": "00",
        "message": "CMN8700I - Component Build service completed",
        "reasonCode": "8700",
    }
    responses.add(
        responses.PUT,
        "https://example.com:8080/zmfrest/component/build",
        json=data,
        headers={"content-type": "application/json"},
        status=200,
    )
    file = tmp_path / "test.yml"
    build_config = {
        "APPB0001.srb": {
            "language": "DELTACOB",
            "buildproc": "CMNCOB2",
        },
        "APPB0002.srb": {
            "language": "DELTACOB",
            "buildproc": "CMNCOB2",
        },
        "APPE0001.sre": {
            "language": "DELTACOB",
            "buildproc": "CMNCOB2",
            "useDb2PreCompileOption": "N",
        },
        "APPE0002.sre": {
            "language": "DELTACOB",
            "buildproc": "CMNCOB2",
            "useDb2PreCompileOption": "N",
        },
    }
    file.write_text(yaml.dump(build_config))
    assert zmfapi.build("APP 000000", COMPONENTS, file) is None


@responses.activate
def test_audit(zmfapi):
    data = {
        "returnCode": "00",
        "message": "CMN2600I - The job to audit this package has been submitted.",  # noqa: E501
        "reasonCode": "2600",
    }
    responses.add(
        responses.PUT,
        "https://example.com:8080/zmfrest/package/audit",
        json=data,
        headers={"content-type": "application/json"},
        status=200,
        match=[
            responses.urlencoded_params_matcher(
                {
                    "package": "APP 000000",
                    "jobCard01": "//U000000A JOB 0,'CHANGEMAN',",
                    "jobCard02": "//         CLASS=A,MSGCLASS=A,",
                    "jobCard03": "//         NOTIFY=&SYSUID",
                    "jobCard04": "//*",
                }
            ),
        ],
    )
    assert zmfapi.audit("APP 000000") is None


@responses.activate
def test_search_package(zmfapi):
    data = {
        "returnCode": "00",
        "message": "CMN8600I - The Package search list is complete.",
        "reasonCode": "8600",
        "result": [
            {
                "package": "APP 000008",
                "packageId": 8,
                "packageTitle": "fancy package title",
            }
        ],
    }
    responses.add(
        responses.GET,
        "https://example.com:8080/zmfrest/package/search",
        json=data,
        headers={"content-type": "application/json"},
        status=200,
        match=[
            responses.urlencoded_params_matcher(
                {"package": "APP*", "packageTitle": "fancy package title"}
            ),
        ],
    )
    assert zmfapi.search_package("APP", "fancy package title") == "APP 000008"


@responses.activate
def test_create_package(zmfapi, monkeypatch):
    yaml_data = {
        "applName": "APP",
        "packageTitle": "fancy package title",
        "package": "APP 000001",
    }
    monkeypatch.setattr("sys.stdin", io.StringIO(yaml.dump(yaml_data)))
    data = {
        "returnCode": "00",
        "message": "CMNXXXXI - ...",
        "reasonCode": "XXXX",
        "result": [
            {
                "package": "APP 000008",
                "packageId": 8,
                "packageTitle": "fancy package title",
            }
        ],
    }
    responses.add(
        responses.POST,
        "https://example.com:8080/zmfrest/package",
        json=data,
        headers={"content-type": "application/json"},
        status=200,
        match=[
            responses.urlencoded_params_matcher(
                {
                    "applName": "APP",
                    "packageTitle": "fancy package title",
                    "package": "APP 000001",
                }
            ),
        ],
    )
    assert zmfapi.create_package("-") == "APP 000008"


@responses.activate
def test_get_package(zmfapi, monkeypatch):
    yaml_data = {
        "applName": "APP",
        "packageTitle": "fancy package title",
        "package": "APP 000001",
    }
    monkeypatch.setattr("sys.stdin", io.StringIO(yaml.dump(yaml_data)))
    assert zmfapi.get_package("-") == "APP 000001"
