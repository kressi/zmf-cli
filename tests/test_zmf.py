import json
import pytest
import requests
import responses
import toml
import yaml

from zmfcli.zmf import ChangemanZmf
from zmfcli.session import EXIT_CODE_REQUEST_NOK, EXIT_CODE_ZMF_NOK


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

ZMF_RESP_ERR_NO_INFO = {
    "returnCode": "08",
    "message": "CMN6504I - No information found for this request.",
    "reasonCode": "6504",
}

ZMF_RESP_AUDIT_OK = {
    "returnCode": "00",
    "message": "CMN2600I - The job to audit this package has been submitted.",
    "reasonCode": "2600",
}

ZMF_RESP_BROWSE_INFO = {
    "returnCode": "04",
    "message": "Member NOTEXIST not found",
    "reasonCode": "0000",
}

ZMF_RESP_BUILD_OK = {
    "returnCode": "00",
    "message": "CMN8700I - Component Build service completed",
    "reasonCode": "8700",
}

ZMF_RESP_COMP_OK = {
    "returnCode": "00",
    "message": "CMN8700I - LIST service completed",
    "reasonCode": "8700",
    "result": [
        {
            "componentType": "SRB",
            "package": "APP 000001",
            "setssi": "BK72NB9A",
            "targetComponent": "APPB0001",
            "rebuildFromBaseline": "N",
            "packageId": 1,
            "timeLastModifiedUtc": "1604083542",
            "timeLastModified": "1604083542",
            "componentStatus": "0 - Active",
            "updater": "U000000",
            "component": "APPB0001",
            "targetComponentType": "SRB",
            "dateLastModified": "20200101",
            "applName": "APP",
            "dateLastModifiedUtc": "20200101",
        },
    ],
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

ZMF_RESP_DELETE_OK = {
    "returnCode": "00",
    "message": "CMN8270I - Component APPE0001.SRE has been deleted.",
    "reasonCode": "8270",
}

ZMF_RESP_FREEZE_ERR = {
    "returnCode": "08",
    "message": "CMN3025A - Package must be audited when audit level is greater than 0.",  # noqa: E501
    "reasonCode": "3025",
}

ZMF_RESP_LOAD_COMP_OK = {
    "returnCode": "00",
    "message": "CMN8700I - LIST service completed",
    "reasonCode": "8700",
    "result": [
        {
            "componentType": "SRB",
            "package": "APP 000001",
            "setssi": "BK72NB9A",
            "targetComponent": "APPB0001",
            "rebuildFromBaseline": "N",
            "packageId": 1,
            "timeLastModifiedUtc": "1604083542",
            "timeLastModified": "1604083542",
            "componentStatus": "0 - Active",
            "updater": "U000000",
            "component": "APPB0001",
            "targetComponentType": "LST",
            "dateLastModified": "20200101",
            "applName": "APP",
            "dateLastModifiedUtc": "20200101",
        },
        {
            "componentType": "SRE",
            "package": "APP 000001",
            "setssi": "BK72NB9B",
            "targetComponent": "APPE0001",
            "rebuildFromBaseline": "N",
            "packageId": 1,
            "timeLastModifiedUtc": "1604083579",
            "timeLastModified": "1604083579",
            "componentStatus": "0 - Active",
            "updater": "U000000",
            "component": "APPE0001",
            "targetComponentType": "LST",
            "dateLastModified": "20200101",
            "applName": "APP",
            "dateLastModifiedUtc": "20200101",
        },
    ],
}

ZMF_RESP_PROMOTE_OK = {
    "returnCode": "00",
    "message": "CMN3281I - request submitted for promotion to DEV0,ALL.",
    "reasonCode": "3281",
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
def test_checkin(zmfapi, caplog):
    responses.add(
        responses.PUT,
        ZMF_REST_URL + "component/checkin",
        json=ZMF_RESP_XXXX_OK,
    )
    assert zmfapi.checkin("APP 000000", "U000000.LIB", COMPONENTS) is None
    responses.reset()
    responses.add(
        responses.PUT,
        ZMF_REST_URL + "component/checkin",
        status=requests.codes.bad_request,
    )
    with pytest.raises(SystemExit) as excinfo:
        zmfapi.checkin("APP 000000", "U000000.LIB", COMPONENTS)
    assert excinfo.value.code == EXIT_CODE_REQUEST_NOK
    assert "400 Bad Request" in caplog.text


@responses.activate
def test_delete(zmfapi):
    responses.add(
        responses.DELETE,
        ZMF_REST_URL + "component",
        json=ZMF_RESP_DELETE_OK,
    )
    assert zmfapi.delete("APP 000000", "APPE0001", "SRE") is None


@responses.activate
def test_build(zmfapi, caplog):
    responses.add(
        responses.PUT,
        ZMF_REST_URL + "component/build",
        json=ZMF_RESP_BUILD_OK,
    )
    assert zmfapi.build("APP 000000", COMPONENTS) is None
    assert zmfapi.build("APP 000000", COMPONENTS, db2Precompile=True) is None
    responses.reset()
    responses.add(
        responses.PUT,
        ZMF_REST_URL + "component/build",
        json=ZMF_RESP_ERR_NO_INFO,
    )
    with pytest.raises(SystemExit) as excinfo:
        zmfapi.build("APP 000000", COMPONENTS)
    assert excinfo.value.code == EXIT_CODE_ZMF_NOK
    assert "CMN6504I" in caplog.text
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
    )
    with pytest.raises(SystemExit) as excinfo:
        zmfapi.build("APP 000000", ["file/does/not/exist.sre"])
    assert excinfo.value.code == EXIT_CODE_ZMF_NOK
    assert "CMN8464I" in caplog.text


@responses.activate
def test_build_config(zmfapi, tmp_path):
    responses.add(
        responses.PUT,
        ZMF_REST_URL + "component/build",
        json=ZMF_RESP_BUILD_OK,
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
    )
    assert zmfapi.scratch("APP 000000", COMPONENTS) is None


@responses.activate
def test_audit(zmfapi):
    responses.add(
        responses.PUT,
        ZMF_REST_URL + "package/audit",
        json=ZMF_RESP_AUDIT_OK,
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
def test_freeze(zmfapi):
    responses.add(
        responses.PUT,
        ZMF_REST_URL + "package/freeze",
        json=ZMF_RESP_XXXX_OK,
        match=[
            responses.urlencoded_params_matcher(
                {
                    "package": "APP 000000",
                    "jobCard01": "//U000000F JOB 0,'CHANGEMAN',",
                    "jobCard02": "//         CLASS=A,MSGCLASS=A,",
                    "jobCard03": "//         NOTIFY=&SYSUID",
                    "jobCard04": "//*",
                }
            ),
        ],
    )
    assert zmfapi.freeze("APP 000000") is None


@responses.activate
def test_revert(zmfapi):
    responses.add(
        responses.PUT,
        ZMF_REST_URL + "package/revert",
        json=ZMF_RESP_XXXX_OK,
        match=[
            responses.urlencoded_params_matcher(
                {
                    "package": "APP 000000",
                    "jobCard01": "//U000000R JOB 0,'CHANGEMAN',",
                    "jobCard02": "//         CLASS=A,MSGCLASS=A,",
                    "jobCard03": "//         NOTIFY=&SYSUID",
                    "jobCard04": "//*",
                }
            ),
        ],
    )
    assert zmfapi.revert("APP 000000") is None


@responses.activate
def test_promote(zmfapi):
    responses.add(
        responses.PUT,
        ZMF_REST_URL + "package/promote",
        json=ZMF_RESP_PROMOTE_OK,
        match=[
            responses.urlencoded_params_matcher(
                {
                    "package": "APP 000000",
                    "promotionSiteName": "DEV0",
                    "promotionLevel": "42",
                    "promotionName": "ALL",
                    "jobCards01": "//U000000P JOB 0,'CHANGEMAN',",
                    "jobCards02": "//         CLASS=A,MSGCLASS=A,",
                    "jobCards03": "//         NOTIFY=&SYSUID",
                    "jobCards04": "//*",
                }
            ),
        ],
    )
    assert zmfapi.promote("APP 000000", "DEV0", 42, "ALL") is None


@responses.activate
def test_search_package(zmfapi, caplog):
    responses.add(
        responses.GET,
        ZMF_REST_URL + "package/search",
        json=ZMF_RESP_SEARCH_000007,
        match=[
            responses.urlencoded_params_matcher(
                {"package": "APP*", "packageTitle": "fancy package title"}
            ),
        ],
    )
    responses.add(
        responses.GET,
        ZMF_REST_URL + "package/search",
        json=ZMF_RESP_ERR_NO_INFO,
        match=[
            responses.urlencoded_params_matcher(
                {"package": "APP*", "packageTitle": "not exist package"}
            ),
        ],
    )
    assert zmfapi.search_package("APP", "fancy package title") == "APP 000007"
    with pytest.raises(SystemExit) as excinfo:
        zmfapi.search_package("APP", "not exist package")
    assert excinfo.value.code == EXIT_CODE_ZMF_NOK
    assert "CMN6504I" in caplog.text


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
    config_incl_id_file = tmp_path / "test.toml"
    config_incl_id_file.write_text(toml.dumps(PKG_CONF_YAML_INCL_ID))
    assert zmfapi.get_package(config_incl_id_file) == "APP 000001"

    config_excl_id_file = tmp_path / "test.yml"
    config_excl_id_file.write_text(yaml.dump(PKG_CONF_YAML_EXCL_ID))
    responses.add(
        responses.GET,
        ZMF_REST_URL + "package/search",
        json=ZMF_RESP_SEARCH_000007,
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
        json=ZMF_RESP_ERR_NO_INFO,
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
        match=[
            responses.urlencoded_params_matcher(PKG_CONF_YAML_EXCL_ID),
        ],
    )
    assert zmfapi.get_package(config_excl_id_file) == "APP 000009"


@responses.activate
def test_get_components(zmfapi):
    responses.add(
        responses.GET,
        ZMF_REST_URL + "component",
        json=ZMF_RESP_COMP_OK,
        match=[
            responses.urlencoded_params_matcher(
                {
                    "package": "APP 000001",
                    "component": "APPB0001",
                }
            ),
        ],
    )
    assert (
        zmfapi.get_components("APP 000001", component="APPB0001")
        == ZMF_RESP_COMP_OK["result"]
    )


@responses.activate
def test_get_load_components(zmfapi):
    responses.add(
        responses.GET,
        ZMF_REST_URL + "component/load",
        json=ZMF_RESP_LOAD_COMP_OK,
        match=[
            responses.urlencoded_params_matcher(
                {
                    "package": "APP 000001",
                    "targetComponentType": "LST",
                }
            ),
        ],
    )
    assert (
        zmfapi.get_load_components("APP 000001", targetType="LST")
        == ZMF_RESP_LOAD_COMP_OK["result"]
    )


ZMF_RESP_BROWSE_RICK = (
    "You ever hear about Wall Street, Morty? "
    "You know what those guys do in their\n"
    "fancy boardrooms? They take their balls "
    "and they dip them in cocaine and wipe\n"
    "them all over each other.\n\n"
    "àáâãäåæçèéêëìíîï"
)


@responses.activate
def test_browse_component(zmfapi):
    responses.add(
        responses.GET,
        ZMF_REST_URL + "component/browse",
        body=ZMF_RESP_BROWSE_RICK.encode("iso-8859-1"),
        content_type="text/plain;charset=ISO-8859-1",
        headers={
            "Content-Disposition": "attachment;filename=RICK",
            "Content-Length": str(len(ZMF_RESP_BROWSE_RICK)),
        },
        match=[
            responses.urlencoded_params_matcher(
                {
                    "package": "APP 000001",
                    "component": "RICK",
                    "componentType": "LST",
                }
            ),
        ],
    )
    responses.add(
        responses.GET,
        ZMF_REST_URL + "component/browse",
        body=json.dumps(ZMF_RESP_BROWSE_INFO).encode("iso-8859-1"),
        content_type="application/json;charset=ISO-8859-1",
        match=[
            responses.urlencoded_params_matcher(
                {
                    "package": "APP 000001",
                    "component": "NOTEXIST",
                    "componentType": "LST",
                }
            ),
        ],
    )
    assert (
        zmfapi.browse_component("APP 000001", "RICK", "LST")
        == ZMF_RESP_BROWSE_RICK
    )
    assert zmfapi.browse_component("APP 000001", "NOTEXIST", "LST") is None
