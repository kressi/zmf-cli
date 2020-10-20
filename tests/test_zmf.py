# TODO: https://www.nerdwallet.com/blog/engineering/5-pytest-best-practices/
# TODO: https://docs.pytest.org/en/stable/capture.html

import io
import json
import sys

import pytest
import requests
import responses
import yaml

from zmfcli.zmf import extension, jobcard


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

yaml_data = {'A': [1, 2., False], 'B': {'1': True, '2': None}}

def test_read_yaml_file(tmpdir):
    file = tmpdir.join("test.yml")
    file.write(json.dumps(yaml_data))
    assert read_yaml(file) == yaml_data

def test_read_yaml_stdin(monkeypatch):
    monkeypatch.setattr('sys.stdin', io.StringIO(json.dumps(yaml_data)))
    assert read_yaml("-") == yaml_data
