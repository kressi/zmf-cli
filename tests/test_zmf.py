# https://www.nerdwallet.com/blog/engineering/5-pytest-best-practices/
# https://docs.pytest.org/en/stable/capture.html
# https://docs.pytest.org/en/stable/fixture.html

import io

import pytest
import responses
import yaml

from zmfcli.zmf import (
    extension,
    jobcard,
    read_yaml,
    removeprefix,
    ChangemanZmf,
)


@pytest.mark.parametrize(
    "path, expected",
    [
        ("file/with/path/and.ext", "ext"),
        ("file/with/path/and", ""),
        ("file/with/path.ext/and", ""),
        ("file.ext", "ext"),
        (".ext", ""),
        (".", ""),
        ("", ""),
    ],
)
def test_extension(path, expected):
    assert extension(path) == expected


@pytest.mark.parametrize(
    "user, action, expected",
    [
        (
            "",
            "",
            {
                "jobCard01": "// JOB 0,'CHANGEMAN',",
                "jobCard02": "//         CLASS=A,MSGCLASS=A,",
                "jobCard03": "//         NOTIFY=&SYSUID",
                "jobCard04": "//*",
            },
        ),
        (
            "U000000",
            "audit",
            {
                "jobCard01": "//U000000A JOB 0,'CHANGEMAN',",
                "jobCard02": "//         CLASS=A,MSGCLASS=A,",
                "jobCard03": "//         NOTIFY=&SYSUID",
                "jobCard04": "//*",
            },
        ),
        (
            "U000000",
            "AUDIT",
            {
                "jobCard01": "//U000000A JOB 0,'CHANGEMAN',",
                "jobCard02": "//         CLASS=A,MSGCLASS=A,",
                "jobCard03": "//         NOTIFY=&SYSUID",
                "jobCard04": "//*",
            },
        ),
    ],
)
def test_jobcard(user, action, expected):
    assert jobcard(user, action) == expected


@pytest.mark.parametrize(
    "string, prefix, expected",
    [
        ("", "pre", ""),
        ("pre", "pre", ""),
        ("prefix", "pre", "fix"),
        ("prefix", "", "prefix"),
        ("prefix", "fix", "prefix"),
    ],
)
def test_removeprefix(string, prefix, expected):
    assert removeprefix(string, prefix) == expected


yaml_data = {"A": [1, 2.0, False], "B": {"1": True, "2": None}}


def test_read_yaml_file(tmp_path):
    file = tmp_path / "test.yml"
    file.write_text(yaml.dump(yaml_data))
    assert read_yaml(file) == yaml_data


def test_read_yaml_stdin(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO(yaml.dump(yaml_data)))
    assert read_yaml("-") == yaml_data


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
    assert zmfapi.checkin("APP 000000", "U000000.LIB", COMPONENTS) is None


@responses.activate
def test_build(zmfapi):
    data = {
        "returnCode": "00",
        "message": "CMNXXXXI - ...",
        "reasonCode": "XXXX",
    }
    responses.add(
        responses.PUT,
        "https://example.com:8080/zmfrest/component/build",
        json=data,
        headers={"content-type": "application/json"},
        status=200,
    )
    assert zmfapi.build("APP 000000", COMPONENTS) is None
    assert zmfapi.build("APP 000000", COMPONENTS, db2Precompile=True) is None


@responses.activate
def test_build_config(zmfapi, tmp_path):
    data = {
        "returnCode": "00",
        "message": "CMNXXXXI - ...",
        "reasonCode": "XXXX",
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
    )
    assert zmfapi.audit("APP 000000") is None
