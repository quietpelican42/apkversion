"""Implementation of apk version syntax, ordering and constraint matching."""

from __future__ import annotations

import re
from functools import lru_cache, total_ordering
from typing import Final

__all__ = [
    "AlpineVersion",
    "Constraint",
    "InvalidVersion",
    "compare",
    "match",
    "satisfies",
    "sort_key",
    "validate",
]

# One item of a sort key: (kind, sub, value, text). Kinds order the different
# things that can follow a common prefix; the other fields order items of the
# same kind.
Item = tuple[int, int, int, str]
SortKey = tuple[Item, ...]

_SUFFIXES: Final = ("alpha", "beta", "pre", "rc", "cvs", "svn", "git", "hg", "p")

_VERSION_RE: Final = re.compile(
    r"([0-9]+(?:\.[0-9]+)*)"  # dotted numbers
    r"([a-z])?"  # one letter
    r"((?:_(?:alpha|beta|pre|rc|cvs|svn|git|hg|p)[0-9]*)*)"  # suffixes
    r"(?:~([0-9a-f]+))?"  # commit hash
    r"(?:-r([0-9]+))?"  # package revision
)
_SUFFIX_RE: Final = re.compile(r"_([a-z]+)([0-9]*)")

# Ordering of item kinds at the first position where two versions diverge.
_K_END: Final = 0
_K_REV: Final = 1
_K_HASH: Final = 2
_K_SUFFIX_NUMBER: Final = 3
_K_LETTER: Final = 9
_K_COMPONENT: Final = 10
_SUFFIX_KIND: Final = {
    "alpha": -4,
    "beta": -3,
    "pre": -2,
    "rc": -1,
    "cvs": 4,
    "svn": 5,
    "git": 6,
    "hg": 7,
    "p": 8,
}

_END: Final[Item] = (_K_END, 0, 0, "")

_OP_BITS: Final = {"<": 2, ">": 4, "=": 1, "~": 9}
_LESS: Final = 2
_EQUAL: Final = 1
_GREATER: Final = 4
_FUZZY: Final = 8


class InvalidVersion(ValueError):
    """Raised for a string that is not a valid apk version."""


def validate(version: str) -> bool:
    """Return True if `version` is a valid apk version string."""
    if not isinstance(version, str):
        raise TypeError(f"version must be str, not {type(version).__name__}")
    return _VERSION_RE.fullmatch(version) is not None


_MASK: Final = (1 << 64) - 1


def _number(digits: str) -> int:
    """Value of a digit string modulo 2**64, as apk computes it."""
    if len(digits) <= 19:
        return int(digits)
    value = 0
    for start in range(0, len(digits), 18):
        chunk = digits[start : start + 18]
        value = (value * 10 ** len(chunk) + int(chunk)) & _MASK
    return value


@lru_cache(maxsize=4096)
def _items(version: str) -> SortKey:
    m = _VERSION_RE.fullmatch(version)
    if m is None:
        raise InvalidVersion(f"invalid apk version: {version!r}")
    nums, letter, suffixes, commit, revision = m.groups()
    items: list[Item] = []
    for index, part in enumerate(nums.split(".")):
        if index > 0 and part.startswith("0"):
            # A later component with a leading zero orders as text.
            items.append((_K_COMPONENT, 0, 0, part))
        else:
            items.append((_K_COMPONENT, 1, _number(part), ""))
    if letter:
        items.append((_K_LETTER, 0, 0, letter))
    for sm in _SUFFIX_RE.finditer(suffixes):
        items.append((_SUFFIX_KIND[sm.group(1)], 0, 0, ""))
        if sm.group(2):
            items.append((_K_SUFFIX_NUMBER, 0, _number(sm.group(2)), ""))
    if commit:
        items.append((_K_HASH, 0, 0, commit))
    if revision:
        items.append((_K_REV, 0, _number(revision), ""))
    return tuple(items)


def sort_key(version: str) -> SortKey:
    """Return a hashable key whose ordering matches apk's version ordering.

    Two versions have equal keys exactly when `compare` returns 0.
    Raises InvalidVersion for an invalid version.
    """
    if not isinstance(version, str):
        raise TypeError(f"version must be str, not {type(version).__name__}")
    return _items(version) + (_END,)


def compare(a: str, b: str) -> int:
    """Return -1, 0 or 1 as `a` is older than, equal to or newer than `b`.

    Raises InvalidVersion if either argument is not a valid apk version.
    """
    ka, kb = sort_key(a), sort_key(b)
    return (ka > kb) - (ka < kb)


def _mask(op: str) -> int:
    if not isinstance(op, str):
        raise TypeError(f"operator must be str, not {type(op).__name__}")
    if not op or any(c not in _OP_BITS for c in op):
        raise ValueError(f"invalid version operator: {op!r}")
    mask = 0
    for c in op:
        mask |= _OP_BITS[c]
    return mask


def match(version: str, op: str, target: str) -> bool:
    """Return True if `version` satisfies the constraint `op target`.

    `op` is a string of the characters `<`, `>`, `=` and `~` in any order and
    combination, as in apk dependencies (`<`, `<=`, `=`, `>=`, `>`, `~`, `=~`,
    `><`). `~` alone or with `=` means a prefix match: `version` equals
    `target` after ignoring anything `version` has beyond `target`.
    Raises InvalidVersion for an invalid version and ValueError for an
    operator that is empty or contains any other character.
    """
    mask = _mask(op)
    ka = sort_key(version)
    kb = sort_key(target)
    result = (_GREATER if ka > kb else _LESS if ka < kb else _EQUAL)
    if mask & _FUZZY and result != _EQUAL and _is_prefix(kb, ka):
        result = _EQUAL
    return bool(mask & result)


def _is_prefix(prefix: SortKey, full: SortKey) -> bool:
    body = prefix[:-1]
    return full[: len(body)] == body


_CONSTRAINT_RE: Final = re.compile(r"([<>=~]+)(.*)", re.DOTALL)


def satisfies(version: str, constraint: str) -> bool:
    """Return True if `version` satisfies a constraint such as `>=1.2-r0`."""
    return Constraint.parse(constraint).matches(version)


class Constraint:
    """An operator and a version, as written in an apk dependency."""

    __slots__ = ("op", "version")

    op: str
    version: str

    def __init__(self, op: str, version: str) -> None:
        _mask(op)
        sort_key(version)
        object.__setattr__(self, "op", op)
        object.__setattr__(self, "version", version)

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("Constraint is immutable")

    @classmethod
    def parse(cls, text: str) -> Constraint:
        """Parse `>=1.2.3-r0` style text. Raises ValueError on bad input."""
        m = _CONSTRAINT_RE.fullmatch(text)
        if m is None:
            raise ValueError(f"invalid constraint: {text!r}")
        return cls(m.group(1), m.group(2))

    def matches(self, version: str) -> bool:
        return match(version, self.op, self.version)

    def __str__(self) -> str:
        return f"{self.op}{self.version}"

    def __repr__(self) -> str:
        return f"Constraint({self.op!r}, {self.version!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Constraint):
            return NotImplemented
        return (self.op, self.version) == (other.op, other.version)

    def __hash__(self) -> int:
        return hash((self.op, self.version))


@total_ordering
class AlpineVersion:
    """A valid apk version with a consistent total ordering.

    Equality follows apk ordering, so `AlpineVersion("1")` equals
    `AlpineVersion("01")`. `str()` returns the original text.
    """

    __slots__ = ("_text", "_key")

    def __init__(self, text: str) -> None:
        self._key = sort_key(text)
        self._text = text

    def __str__(self) -> str:
        return self._text

    def __repr__(self) -> str:
        return f"AlpineVersion({self._text!r})"

    def __hash__(self) -> int:
        return hash(self._key)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, AlpineVersion):
            return NotImplemented
        return self._key == other._key

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, AlpineVersion):
            return NotImplemented
        return self._key < other._key

    def matches(self, op: str, target: str | AlpineVersion) -> bool:
        """Return True if this version satisfies `op target`."""
        return match(self._text, op, str(target))
