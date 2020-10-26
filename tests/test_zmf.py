import pytest
import requests
import responses
import yaml

from zmfcli.zmf import ChangemanZmf, RequestNok, ZmfRestNok


ZMF_REST_URL = "http://example.com:8080/zmfrest/"
COMPONENTS = [
    "src/CPY/APPI0001.cpy",
    "src/SRB/APPB0001.srb",
    "src/SRB/APPB0002.srb",
    "src/SRE/APPE0001.sre",
    "src/SRE/APPE0002.sre",
]

ZMF_RESP_XXXX_OK = {
    "returnCode": "00",
    "message": "CMNXXXXI - ...",
    "reasonCode": "XXXX",
}

ZMF_RESP_XXXX_INFO = {
    "returnCode": "04",
    "message": "CMNXXXXI - ...",
    "reasonCode": "XXXX",
}

ZMF_RESP_BUILD_OK = {
    "returnCode": "00",
    "message": "CMN8700I - Component Build service completed",
    "reasonCode": "8700",
}

ZMF_RESP_CREATE_000009 = {
    "returnCode": "00",
    "message": "CMN2100I - APP 000008 change package has been created.",
    "reasonCode": "2100",
    "result": [
        {
            "package": "APP 000009",
            "packageId": 9,
            "packageTitle": "fancy package title",
        }
    ],
}

ZMF_RESP_SEARCH_000007 = {
    "returnCode": "00",
    "message": "CMN8600I - The Package search list is complete.",
    "reasonCode": "8600",
    "result": [
        {
            "package": "APP 000006",
            "packageId": 6,
            "packageTitle": "fancy package title",
        },
        {
            "package": "APP 000007",
            "packageId": 7,
            "packageTitle": "fancy package title",
        },
        {
            "package": "APP 000008",
            "packageId": 8,
            "packageTitle": "unexpected package title",
        },
    ],
}


@pytest.fixture
def zmfapi():
    return ChangemanZmf(
        user="U000000",
        password="Pa$$w0rd",
        url=ZMF_REST_URL,
    )


@responses.activate
def test_checkin(zmfapi):
    responses.add(
        responses.PUT,
        ZMF_REST_URL + "component/checkin",
        json=ZMF_RESP_XXXX_OK,
        headers={"content-type": "application/json"},
        status=requests.codes.ok,
    )
    assert zmfapi.checkin("APP 000000", "U000000.LIB", COMPONENTS) is None
    responses.reset()
    responses.add(
        responses.PUT,
        ZMF_REST_URL + "component/checkin",
        headers={"content-type": "application/json"},
        status=requests.codes.bad_request,
    )
    with pytest.raises(RequestNok) as excinfo:
        zmfapi.checkin("APP 000000", "U000000.LIB", COMPONENTS)
    assert str(requests.codes.bad_request) in str(excinfo.value)


@responses.activate
def test_build(zmfapi):
    responses.add(
        responses.PUT,
        ZMF_REST_URL + "component/build",
        json=ZMF_RESP_BUILD_OK,
        headers={"content-type": "application/json"},
        status=requests.codes.ok,
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
        ZMF_REST_URL + "component/build",
        json=data_no_info,
        headers={"content-type": "application/json"},
        status=requests.codes.ok,
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
        ZMF_REST_URL + "component/build",
        json=data_no_comp,
        headers={"content-type": "application/json"},
        status=requests.codes.ok,
    )
    with pytest.raises(ZmfRestNok) as excinfo:
        zmfapi.build("APP 000000", ["file/does/not/exist.sre"])
    assert "CMN8464I" in str(excinfo.value)


@responses.activate
def test_build_config(zmfapi, tmp_path):
    responses.add(
        responses.PUT,
        ZMF_REST_URL + "component/build",
        json=ZMF_RESP_BUILD_OK,
        headers={"content-type": "application/json"},
        status=requests.codes.ok,
    )
    file = tmp_path / "test.yml"
    build_config = {
        "SRB/APPB0001.srb": {
            "language": "DELTACOB",
            "buildproc": "CMNCOB2",
        },
        "SRB/APPB0002.srb": {
            "language": "DELTACOB",
            "buildproc": "CMNCOB2",
        },
        "SRE/APPE0001.sre": {
            "language": "DELTACOB",
            "buildproc": "CMNCOB2",
            "useDb2PreCompileOption": "N",
        },
        "SRE/APPE0002.sre": {
            "language": "DELTACOB",
            "buildproc": "CMNCOB2",
            "useDb2PreCompileOption": "N",
        },
    }
    file.write_text(yaml.dump(build_config))
    assert zmfapi.build_config("APP 000000", COMPONENTS, file) is None


@responses.activate
def test_scratch(zmfapi):
    responses.add(
        responses.PUT,
        ZMF_REST_URL + "component/scratch",
        json=ZMF_RESP_XXXX_OK,
        headers={"content-type": "application/json"},
        status=requests.codes.ok,
    )
    assert zmfapi.scratch("APP 000000", COMPONENTS) is None


@responses.activate
def test_audit(zmfapi):
    data = {
        "returnCode": "00",
        "message": "CMN2600I - The job to audit this package has been submitted.",  # noqa: E501
        "reasonCode": "2600",
    }
    responses.add(
        responses.PUT,
        ZMF_REST_URL + "package/audit",
        json=data,
        headers={"content-type": "application/json"},
        status=requests.codes.ok,
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
    responses.add(
        responses.GET,
        ZMF_REST_URL + "package/search",
        json=ZMF_RESP_SEARCH_000007,
        headers={"content-type": "application/json"},
        status=requests.codes.ok,
        match=[
            responses.urlencoded_params_matcher(
                {"package": "APP*", "packageTitle": "fancy package title"}
            ),
        ],
    )
    assert zmfapi.search_package("APP", "fancy package title") == "APP 000007"


PKG_CONF_YAML_INCL_ID = {
    "applName": "APP",
    "packageTitle": "fancy package title",
    "package": "APP 000001",
}

PKG_CONF_YAML_EXCL_ID = {
    "applName": "APP",
    "packageTitle": "fancy package title",
}


@responses.activate
def test_create_package(zmfapi, tmp_path):
    config_file = tmp_path / "test.yml"
    config_file.write_text(yaml.dump(PKG_CONF_YAML_INCL_ID))
    responses.add(
        responses.POST,
        ZMF_REST_URL + "package",
        json=ZMF_RESP_CREATE_000009,
        headers={"content-type": "application/json"},
        status=requests.codes.ok,
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
    assert zmfapi.create_package(config_file) == "APP 000009"


@responses.activate
def test_get_package(zmfapi, tmp_path):
    config_incl_id_file = tmp_path / "test.yml"
    config_incl_id_file.write_text(yaml.dump(PKG_CONF_YAML_INCL_ID))
    assert zmfapi.get_package(config_incl_id_file) == "APP 000001"

    config_excl_id_file = tmp_path / "test.yml"
    config_excl_id_file.write_text(yaml.dump(PKG_CONF_YAML_EXCL_ID))
    responses.add(
        responses.GET,
        ZMF_REST_URL + "package/search",
        json=ZMF_RESP_SEARCH_000007,
        headers={"content-type": "application/json"},
        status=requests.codes.ok,
        match=[
            responses.urlencoded_params_matcher(
                {"package": "APP*", "packageTitle": "fancy package title"}
            ),
        ],
    )
    assert zmfapi.get_package(config_excl_id_file) == "APP 000007"

    responses.reset()
    responses.add(
        responses.GET,
        ZMF_REST_URL + "package/search",
        json=ZMF_RESP_XXXX_INFO,
        headers={"content-type": "application/json"},
        status=requests.codes.ok,
        match=[
            responses.urlencoded_params_matcher(
                {"package": "APP*", "packageTitle": "fancy package title"}
            ),
        ],
    )
    responses.add(
        responses.POST,
        ZMF_REST_URL + "package",
        json=ZMF_RESP_CREATE_000009,
        headers={"content-type": "application/json"},
        status=requests.codes.ok,
        match=[
            responses.urlencoded_params_matcher(PKG_CONF_YAML_EXCL_ID),
        ],
    )
    assert zmfapi.get_package(config_excl_id_file) == "APP 000009"
