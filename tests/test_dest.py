# this_file: tests/test_dest.py
import pytest

from fontlab_instamix.dest import DestError, resolve


@pytest.mark.parametrize(
    ("rule", "expected"),
    [
        ("Scripts/.", "Scripts"),
        ("Scripts/./", "Scripts"),
        ("Scripts", "Scripts"),
        ("Scripts/{}", "Scripts/myext"),
        ("Scripts/{}/", "Scripts/myext"),
        ("Scripts/dir", "Scripts/dir"),
        ("Scripts/./dir/", "Scripts/dir"),
        ("Data/{family}/", "Data/adamtrix"),
        ("Encoding/{}", "Encoding/myext"),
        ("actions/.", "Actions"),
        ("codepage/x", "Codepage/x"),
        ("SITE-PACKAGES/.", "python/3.11/site-packages"),
    ],
)
def test_resolve_when_valid_rule_then_relative_posix_dir(rule, expected):
    assert resolve(rule, "myext", {"family": "adamtrix"}) == expected


@pytest.mark.parametrize(
    "rule",
    ["Scripts/../x", "Scripts/{}/../../x", "/Scripts", "C:/Scripts", "Fonts/x", "Scripts/{nope}", "", "."],
)
def test_resolve_when_bad_rule_then_error(rule):
    with pytest.raises(DestError):
        resolve(rule, "myext", {"family": "adamtrix"})


def test_resolve_when_var_contains_dotdot_then_error():
    with pytest.raises(DestError):
        resolve("Data/{v}", "x", {"v": ".."})


@pytest.mark.parametrize("value", ["..\\..", "a\\b", "C:", "c:\\x", "../x", ".."])
def test_resolve_when_var_has_windows_escape_then_error(value):
    with pytest.raises(DestError):
        resolve("Data/{v}", "x", {"v": value})


@pytest.mark.parametrize("rule", ["Data/a:b", "Scripts/x/c:"])
def test_resolve_when_part_has_colon_then_error(rule):
    with pytest.raises(DestError):
        resolve(rule, "x")
