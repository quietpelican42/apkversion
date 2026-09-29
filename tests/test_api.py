from __future__ import annotations

import itertools
import random

import pytest

from apkversion import AlpineVersion, Constraint, InvalidVersion, compare, match, satisfies, sort_key, validate

import gen


def test_documented_examples() -> None:
    assert validate("0.0.0_git20210925-r0")
    assert compare("1.2.0-r0", "1.10.0-r0") == -1
    assert AlpineVersion("1.2.0-r0") < AlpineVersion("1.10.0-r0")
    assert AlpineVersion("1.2.0-r0") <= AlpineVersion("1.10.0-r0")
    assert not AlpineVersion("1.2.0-r0") >= AlpineVersion("1.10.0-r0")


def test_type_errors() -> None:
    with pytest.raises(TypeError):
        validate(1)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        sort_key(b"1")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        match("1", 1, "1")  # type: ignore[arg-type]


def test_invalid_operator() -> None:
    for op in ["", "!", "=!>", "<a", " <", "!="]:
        with pytest.raises(ValueError):
            match("1", op, "1")


def test_invalid_version_is_value_error() -> None:
    with pytest.raises(ValueError):
        AlpineVersion("1.0bc")
    with pytest.raises(InvalidVersion):
        match("x", "=", "1")
    with pytest.raises(InvalidVersion):
        match("1", "=", "x")


def test_total_ordering_consistent() -> None:
    rng = random.Random(4)
    versions = [AlpineVersion(gen.valid_version(rng)) for _ in range(120)]
    for x, y in itertools.product(versions, repeat=2):
        lt, eq, gt = x < y, x == y, x > y
        assert lt + eq + gt == 1
        assert (x <= y) == (lt or eq)
        assert (x >= y) == (gt or eq)
        assert (compare(str(x), str(y)) == 0) == eq
        if eq:
            assert hash(x) == hash(y)


def test_ordering_is_transitive() -> None:
    rng = random.Random(9)
    versions = [AlpineVersion(gen.valid_version(rng)) for _ in range(60)]
    ordered = sorted(versions)
    for i in range(len(ordered) - 1):
        assert ordered[i] <= ordered[i + 1]
    for x, y, z in itertools.product(versions, repeat=3):
        if x <= y and y <= z:
            assert x <= z


def test_sorted_release_order() -> None:
    shuffled = ["1.0-r1", "1.0_p1", "1.0", "1.0_rc1", "1.0_alpha", "1.0.1", "1.0a", "1.0-r0", "0.9", "1.0_beta"]
    expected = ["0.9", "1.0_alpha", "1.0_beta", "1.0_rc1", "1.0", "1.0-r0", "1.0-r1", "1.0_p1", "1.0a", "1.0.1"]
    assert sorted(shuffled, key=sort_key) == expected
    assert [str(v) for v in sorted(AlpineVersion(s) for s in shuffled)] == expected


def test_equal_versions_share_key_and_hash() -> None:
    assert sort_key("01") == sort_key("1")
    assert sort_key("1-r1") == sort_key("1-r01")
    assert AlpineVersion("01") == AlpineVersion("1")
    assert len({AlpineVersion("01"), AlpineVersion("1")}) == 1
    assert sort_key("1_p") != sort_key("1_p0")
    assert sort_key("1.0") != sort_key("1.00")


def test_eq_with_other_types() -> None:
    assert AlpineVersion("1") != "1"
    assert (AlpineVersion("1") == "1") is False
    with pytest.raises(TypeError):
        AlpineVersion("1") < "2"


def test_str_and_repr() -> None:
    v = AlpineVersion("01.5-r02")
    assert str(v) == "01.5-r02"
    assert repr(v) == "AlpineVersion('01.5-r02')"


def test_numbers_wrap_at_64_bits() -> None:
    assert compare("18446744073709551616", "0") == 0
    assert compare("18446744073709551617", "1") == 0
    assert compare("18446744073709551615", "18446744073709551616") == 1
    assert validate("9" * 5000)
    assert compare("9" * 5000, "1") in (-1, 0, 1)


def test_constraint_parse_and_match() -> None:
    c = Constraint.parse(">=1.2.3-r0")
    assert (c.op, c.version) == (">=", "1.2.3-r0")
    assert str(c) == ">=1.2.3-r0"
    assert repr(c) == "Constraint('>=', '1.2.3-r0')"
    assert c.matches("1.2.3-r0")
    assert c.matches("1.10")
    assert not c.matches("1.2.3_rc1")
    assert c == Constraint(">=", "1.2.3-r0")
    assert len({c, Constraint(">=", "1.2.3-r0")}) == 1
    with pytest.raises(AttributeError):
        c.op = "<"
    assert (c == 1) is False


def test_constraint_parse_errors() -> None:
    for text in ["1.2", "", ">=", "foo>=1", ">=1.0bc", "!1"]:
        with pytest.raises(ValueError):
            Constraint.parse(text)


def test_satisfies() -> None:
    assert satisfies("1.2.3-r4", "~1.2")
    assert not satisfies("1.20", "~1.2")
    assert satisfies("1.5", "<2")
    assert satisfies("1.5", "><2")
    assert not satisfies("2", "><2")


def test_alpine_version_matches() -> None:
    v = AlpineVersion("3.19.1-r0")
    assert v.matches("~", "3.19")
    assert v.matches(">=", AlpineVersion("3.18"))
    assert not v.matches("<", "3.19")


def test_fuzzy_semantics() -> None:
    assert match("1.2.3", "~", "1.2")
    assert match("1_rc1", "~", "1")
    assert match("1.2b", "=~", "1.2")
    assert not match("1.2", "~", "1.2.3")
    assert not match("1", "~", "1_rc1")
    assert not match("1.20", "~", "1.2")
    assert match("1.20", ">~", "1.2")
    assert match("1.2.3", "<~", "1.2")
