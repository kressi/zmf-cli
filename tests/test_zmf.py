# https://www.nerdwallet.com/blog/engineering/5-pytest-best-practices/
# https://docs.pytest.org/en/stable/capture.html
# https://docs.pytest.org/en/stable/fixture.html

import io
import json
import sys

import pytest
import responses
import yaml

from zmfcli.zmf import extension, jobcard, ChangemanZmf


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


def read_yaml(file):
    if file in ["-", "/dev/stdin"]:
        fh = sys.stdin
    else:
        fh = open(file)
    data = yaml.safe_load(fh)
    if file != "-":
        fh.close()
    return data


yaml_data = {"A": [1, 2.0, False], "B": {"1": True, "2": None}}


def test_read_yaml_file(tmp_path):
    file = tmp_path / "test.yml"
    file.write_text(json.dumps(yaml_data))
    assert read_yaml(file) == yaml_data


def test_read_yaml_stdin(monkeypatch):
    monkeypatch.setattr("sys.stdin", io.StringIO(json.dumps(yaml_data)))
    assert read_yaml("-") == yaml_data


ZMF_REST_URL = "https://example.com:8080/zmfrest"


@pytest.fixture
def zmfapi():
    return ChangemanZmf(
        user="U000000",
        password="Pa$$w0rd",
        url="https://example.com:8080/zmfrest/",
    )


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
