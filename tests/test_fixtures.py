"""Fixtures whose expected results were captured from apk-tools' own code."""

from __future__ import annotations

from pathlib import Path

import pytest

from apkversion import InvalidVersion, compare, match, validate

FIXTURES = Path(__file__).parent / "fixtures"


def rows(name: str) -> list[list[str]]:
    text = (FIXTURES / name).read_text()
    return [ln.split("\t") for ln in text.split("\n") if ln]


VALIDATE = [(r[0].encode().decode("unicode_escape"), r[1] == "1") for r in rows("validate.tsv")]
COMPARE = [(r[0], r[1], int(r[2])) for r in rows("compare.tsv")]
MATCH = [(r[0], r[1], r[2], r[3] == "1") for r in rows("match.tsv")]


@pytest.mark.parametrize(("version", "expected"), VALIDATE)
def test_validate(version: str, expected: bool) -> None:
    assert validate(version) is expected


@pytest.mark.parametrize(("a", "b", "expected"), COMPARE)
def test_compare_and_reverse(a: str, b: str, expected: int) -> None:
    assert compare(a, b) == expected
    assert compare(b, a) == -expected


@pytest.mark.parametrize(("a", "op", "b", "expected"), MATCH)
def test_match(a: str, op: str, b: str, expected: bool) -> None:
    assert match(a, op, b) is expected


def test_fixture_sizes() -> None:
    assert len(VALIDATE) >= 60 and len(COMPARE) >= 50 and len(MATCH) >= 150


@pytest.mark.parametrize("version", [v for v, ok in VALIDATE if not ok])
def test_invalid_versions_raise_from_compare(version: str) -> None:
    with pytest.raises(InvalidVersion):
        compare(version, "1.0")
    with pytest.raises(InvalidVersion):
        compare("1.0", version)
