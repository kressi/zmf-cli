# https://www.nerdwallet.com/blog/engineering/5-pytest-best-practices/
# https://docs.pytest.org/en/stable/capture.html

import io

import pytest
import yaml

from zmfcli.zmf import extension, int_or_zero, jobcard, read_yaml, removeprefix


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


@pytest.mark.parametrize(
    "x, expected",
    [
        ("1", 1),
        ("a", 0),
        ("-1", 0),
        (-1, -1),
        (1.9, 0),
        (None, 0),
        ({}, 0),
    ],
)
def test_int_or_zero(x, expected):
    assert int_or_zero(x) == expected
