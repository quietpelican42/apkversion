# apkversion

Validate, order and constraint-match Alpine Linux (apk) package versions in pure Python, with the same results as apk-tools.

```python
from apkversion import AlpineVersion, compare, validate, satisfies

validate("0.0.0_git20210925-r0")                 # True
compare("1.2.0-r0", "1.10.0-r0")                 # -1
sorted(["1.0-r1", "1.0_rc1", "1.0", "1.0_p1"], key=AlpineVersion)
# ['1.0_rc1', '1.0', '1.0-r1', '1.0_p1']
satisfies("3.19.1-r0", "~3.19")                  # True
AlpineVersion("1.2.0-r0") <= AlpineVersion("1.10.0-r0")  # True
```

## Why

The only comparator for Python on PyPI is `AlpineLinuxVersion` in `univers`, which implements a Gentoo-style ordering rather than apk's. Measured against a compiled apk-tools:

- Real Alpine versions such as `0.0.0_git20210925-r0` raise `InvalidVersion`.
- Orderings differ for a small share of valid pairs.
- `<` and `<=` disagree on some inputs (`1.2.0-r0 < 1.10.0-r0` is `True` while `<=` is `False`).

Checked: `univers` 32.0.1 and the copy of that class vendored by osv.dev.

Measured: `APKVERSION_ORACLE=<apk-tools oracle> python bench/measure.py --versions real.txt --pairs real.tsv mut.tsv adv.tsv --osv-parent <dir>`

```
pairs_apk_real.tsv: 16000 pairs, 15982 valid per apk
  apkversion     agree 15982/15982 = 100.00%  raised 0  wrong order 0
  univers        agree 14525/15982 = 90.88%  raised 1440  wrong order 17
  osv vendored   agree 14566/15982 = 91.14%  raised 1399  wrong order 17

pairs_apk_mut.tsv: 10000 pairs, 3290 valid per apk
  apkversion     agree 3290/3290 = 100.00%  raised 0  wrong order 0
  univers        agree 2865/3290 = 87.08%  raised 414  wrong order 11
  osv vendored   agree 3083/3290 = 93.71%  raised 196  wrong order 11

pairs_apk_adv.tsv: 10000 pairs, 4086 valid per apk
  apkversion     agree 4086/4086 = 100.00%  raised 0  wrong order 0
  univers        agree 1804/4086 = 44.15%  raised 2237  wrong order 45
  osv vendored   agree 2009/4086 = 49.17%  raised 2074  wrong order 3

generated (seed 1, n=20000): 20000 pairs, 10392 valid per apk
  apkversion     agree 10392/10392 = 100.00%  raised 0  wrong order 0
  univers        agree 3379/10392 = 32.52%  raised 6848  wrong order 165
  osv vendored   agree 4253/10392 = 40.93%  raised 5964  wrong order 175

validity over 7731 versions (7727 valid per apk)
  apkversion     constructor rejects 4/7731
  univers        constructor rejects 410/7731
  osv vendored   constructor rejects 393/7731

consistency of < and <= over 300 generated valid versions (all ordered pairs)
  apkversion     inconsistent 0/90000 pairs (300 parsed)
  univers        inconsistent 5248/20449 pairs (143 parsed)
  osv vendored   inconsistent 0/26244 pairs (162 parsed)
```

The corpora are not in this repository. `real.txt` holds 7,731 versions from Alpine edge (main, community, testing) and v3.7 indexes. `real.tsv` holds 16,000 pairs of them (random and near-neighbor), `mut.tsv` holds 1-2 character mutations, and `adv.tsv` holds pairs built from a token grammar. The `generated` block uses only files in this repository. A pair counts as valid when the oracle accepts both versions. The 4 versions in `real.txt` that apk rejects are also rejected by `apkversion`.

The oracle is apk-tools' `apk_version_validate`, `apk_version_compare` and `apk_version_match`, compiled locally. It is not distributed here because apk-tools is GPL-2.0. This package is a reimplementation from documented behavior and black-box testing, and contains no apk-tools code.

## Installation

```sh
pip install apkversion
```

No runtime dependencies. Requires Python 3.11 or newer.

## Usage

### Validate

```python
from apkversion import validate

validate("1.2.3_rc1-r4")   # True
validate("1.0bc")          # False
```

### Compare

`compare` returns -1, 0 or 1. It raises `InvalidVersion` when either argument is invalid.

```python
from apkversion import compare

compare("1.0_rc1", "1.0")      # -1
compare("1.0-r1", "1.0")       # 1
compare("1.0_p1", "1.0-r5")    # 1
```

### Sort

```python
from apkversion import AlpineVersion, sort_key

sorted(["3.10", "3.9", "3.9_rc1"], key=sort_key)   # ['3.9_rc1', '3.9', '3.10']
max(AlpineVersion(v) for v in ["3.10", "3.9"])     # AlpineVersion('3.10')
```

`sort_key(v)` returns a hashable tuple. Two versions have equal keys exactly when `compare` returns 0.

### Match dependency constraints

```python
from apkversion import Constraint, match

match("1.2.3-r0", ">=", "1.2")        # True
match("1.2.3", "~", "1.2")            # True (prefix match)
match("1.20", "~", "1.2")             # False
Constraint.parse("<2.0").matches("1.9")  # True
```

## Reference

### Functions

| Name | Returns | Description |
| --- | --- | --- |
| `validate(version)` | `bool` | True if the string is a valid apk version. |
| `compare(a, b)` | `int` | -1, 0 or 1. Raises `InvalidVersion`. |
| `sort_key(version)` | `tuple` | Hashable, orderable key. Raises `InvalidVersion`. |
| `match(version, op, target)` | `bool` | True if `version` satisfies `op target`. |
| `satisfies(version, constraint)` | `bool` | Same, with the constraint as one string such as `>=1.2-r0`. |

### Operators

`op` is any non-empty string made of `<`, `>`, `=` and `~`. Each character contributes to a result mask, as in apk: `<` less, `=` equal, `>` greater, `~` equal by prefix. The match succeeds when the comparison result is in the mask. Common forms:

| Operator | Meaning |
| --- | --- |
| `<`, `<=`, `=`, `>=`, `>` | Ordinary comparison. |
| `~`, `=~`, `~=` | Equal after ignoring whatever `version` has beyond `target`. |
| `<~`, `>~` | Prefix-equal, or less / greater. |
| `><`, `<>` | Not equal. |

Prefix matching works on version components, so `1.2` matches `1.2.3`, `1.2b`, `1.2_rc1` and `1.2.3-r1` but not `1.20`. Any other character in `op`, or an empty `op`, raises `ValueError`.

### Classes

| Name | Description |
| --- | --- |
| `AlpineVersion(text)` | Immutable version. Supports `<`, `<=`, `==`, `>=`, `>`, `hash`, `str`, and `.matches(op, target)`. Raises `InvalidVersion`. |
| `Constraint(op, version)` | Operator and version. `Constraint.parse(">=1.2")`, `.matches(v)`, `str()`. |
| `InvalidVersion` | Subclass of `ValueError`. |

Equality follows apk ordering: `AlpineVersion("1") == AlpineVersion("01")`. The comparison operators are consistent with each other and with `hash`.

## How it works

A version is split into dotted numbers, an optional letter, suffixes (`_alpha`, `_beta`, `_pre`, `_rc`, `_cvs`, `_svn`, `_git`, `_hg`, `_p`, each with an optional number), an optional `~` commit hash in lowercase hex, and an optional `-rN` revision. Each part becomes an item in a tuple, and tuples compare lexicographically.

Item kinds order what may follow a shared prefix. From lowest to highest: `_alpha`, `_beta`, `_pre`, `_rc`, end of version, revision, commit hash, suffix number, `_cvs`, `_svn`, `_git`, `_hg`, `_p`, letter, further dotted component. A missing suffix number sorts below `0`.

Dotted components after the first compare numerically, unless either has a leading zero, in which case both compare as text (`1.01 < 1.1`, `1.0 < 1.00`). Numbers are taken modulo 2**64, so a 20-digit number can compare lower than a shorter one. The reference behaves this way and so does this package.

Prefix matching (`~`) succeeds when all of the target's items equal the version's leading items.

## Limitations

- `compare`, `sort_key` and `match` raise `InvalidVersion` on invalid input. apk-tools' compare function gives unspecified answers there, and callers validate first.
- Operators with characters other than `<>=~`, or empty operators, raise `ValueError`. apk-tools treats them as a mask of zero that never matches.
- Only version and operator semantics are covered. Package names, `!` conflicts, `@tag` pins and dependency-list parsing are out of scope.
- Input must be `str`. Anything that includes whitespace, a newline or non-ASCII characters is invalid.
- Behavior was matched to one apk-tools revision. Later releases may change edge cases.

## Compatibility

Run here: Python 3.14.7 on macOS. The CI workflow runs Python 3.11, 3.12, 3.13 and 3.14 on Linux. Only 3.14.7 has been run locally.

## Development

```sh
python3 -m venv .venv && .venv/bin/pip install -e '.[dev]'
.venv/bin/python -m pytest -q
.venv/bin/python -m mypy --strict src tests bench
```

To run the differential tests, point `APKVERSION_ORACLE` at an executable that speaks the protocol in `tests/oracle.py`. Without it those tests skip with a message. `python tests/diff.py --count 300000` prints per-corpus agreement.

## License

MIT. See [LICENSE](LICENSE).
