"""Differential tests against a compiled apk-tools oracle (not in this repo).

Set APKVERSION_ORACLE to the oracle executable; see tests/oracle.py for the
protocol. Without it these tests skip.
"""

from __future__ import annotations

import pytest

import diff
import gen
import oracle

BINARY = oracle.path()

pytestmark = pytest.mark.skipif(
    BINARY is None,
    reason=f"SKIPPED: {oracle.ENV} is unset or not executable; differential tests against apk-tools did not run",
)


def test_generated_pairs_agree() -> None:
    assert BINARY is not None
    bad, n = diff.check_pairs(BINARY, gen.version_pairs(40000, 101))
    assert n > 10000
    assert bad == []


def test_generated_validation_agrees() -> None:
    assert BINARY is not None
    versions = [a for a, b in gen.version_pairs(40000, 102)] + [b for a, b in gen.version_pairs(40000, 102)]
    assert diff.check_validate(BINARY, versions) == []


def test_generated_match_cases_agree() -> None:
    assert BINARY is not None
    bad, n = diff.check_match(BINARY, gen.match_cases(40000, 103))
    assert n > 10000
    assert bad == []
