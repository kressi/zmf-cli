# https://www.nerdwallet.com/blog/engineering/5-pytest-best-practices/
# https://docs.pytest.org/en/stable/capture.html

import pytest

from zmfcli.zmf import (
    to_path,
    prepare_bools,
    chunks,
    extension,
    int_or_zero,
    jobcard,
    jobcard_s,
    removeprefix,
    str_or_none,
)


def test_to_path():
    assert to_path("aoeu__1234_AOEU__4321_ueoa") == "aoeu-1234/AOEU-4321/ueoa"


@pytest.mark.parametrize(
    "params, expected",
    [
        ({}, {}),
        (
            {"a": 1, "b": 0, "c": True, "d": False},
            {"a": 1, "b": 0, "c": "Y", "d": "N"},
        ),
    ],
)
def test_prepare_bools(params, expected):
    assert prepare_bools(params) == expected


@pytest.mark.parametrize(
    "it, n, expected",
    [
        ([], 1, []),
        (["1", "2", "3"], 2, [["1", "2"], ["3"]]),
        (["1", "2", "3"], 3, [["1", "2", "3"]]),
        (["1", "2", "3"], 5, [["1", "2", "3"]]),
    ],
)
def test_chunks(it, n, expected):
    assert all(x0 == x1 for x0, x1 in zip(chunks(it, n), expected))


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
    "user, action, expected",
    [
        (
            "",
            "",
            {
                "jobCards01": "// JOB 0,'CHANGEMAN',",
                "jobCards02": "//         CLASS=A,MSGCLASS=A,",
                "jobCards03": "//         NOTIFY=&SYSUID",
                "jobCards04": "//*",
            },
        ),
        (
            "U000000",
            "audit",
            {
                "jobCards01": "//U000000A JOB 0,'CHANGEMAN',",
                "jobCards02": "//         CLASS=A,MSGCLASS=A,",
                "jobCards03": "//         NOTIFY=&SYSUID",
                "jobCards04": "//*",
            },
        ),
        (
            "U000000",
            "AUDIT",
            {
                "jobCards01": "//U000000A JOB 0,'CHANGEMAN',",
                "jobCards02": "//         CLASS=A,MSGCLASS=A,",
                "jobCards03": "//         NOTIFY=&SYSUID",
                "jobCards04": "//*",
            },
        ),
    ],
)
def test_jobcard_s(user, action, expected):
    assert jobcard_s(user, action) == expected


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


@pytest.mark.parametrize(
    "x, expected",
    [("1", "1"), (1, "1"), (-1, "-1"), (1.9, "1.9"), (None, None), ({}, "{}")],
)
def test_str_or_none(x, expected):
    assert str_or_none(x) == expected
