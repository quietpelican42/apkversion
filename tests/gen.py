"""Seeded generators for differential testing (versions, mutations, pairs)."""

from __future__ import annotations

import random

SUFFIXES = ["alpha", "beta", "pre", "rc", "cvs", "svn", "git", "hg", "p"]
NUMS = ["0", "00", "1", "01", "2", "5", "05", "9", "10", "010", "11", "100", "20200101", "007"]
MUTATION_ALPHABET = "0123456789abcfz._-r~+pAB "


def valid_version(rng: random.Random) -> str:
    parts = [rng.choice(["0", "1", "2", "3", "10", "01"])]
    for _ in range(rng.choice([0, 0, 1, 1, 2, 3, 5])):
        parts.append("." + rng.choice(NUMS))
    if rng.random() < 0.25:
        parts.append(rng.choice("abcdz"))
    for _ in range(rng.choice([0, 0, 0, 1, 1, 2, 3])):
        parts.append("_" + rng.choice(SUFFIXES) + rng.choice(["", "", "0", "1", "2", "01", "10", "20200101"]))
    if rng.random() < 0.15:
        parts.append("~" + rng.choice(["a", "1", "0a", "abc", "ab12", "10", "9", "deadbeef"]))
    if rng.random() < 0.4:
        parts.append("-r" + rng.choice(["0", "1", "01", "2", "10", "100"]))
    return "".join(parts)


def token_soup(rng: random.Random) -> str:
    toks = [
        "0", "00", "1", "01", "9", "10", "123", "a", "b", "z", "A", ".", "..", "-r0", "-r1", "-r10",
        "_rc", "_rc1", "_alpha", "_beta", "_pre", "_p", "_p1", "_cvs", "_svn", "_git", "_hg", "_x",
        "_r", "~", "~a", "~1", "-", "_", "+", "_p20200101",
    ]
    head = rng.choice(["1", "0", "2", "1.2", "3.4.5", ""])
    return head + "".join(rng.choice(toks) for _ in range(rng.randint(0, 5)))


def mutate(version: str, rng: random.Random) -> str:
    chars = list(version)
    for _ in range(rng.randint(1, 2)):
        op = rng.choice("ird")
        pos = rng.randrange(len(chars) + 1)
        if op == "i":
            chars.insert(pos, rng.choice(MUTATION_ALPHABET))
        elif op == "r" and chars:
            chars[min(pos, len(chars) - 1)] = rng.choice(MUTATION_ALPHABET)
        elif op == "d" and chars:
            del chars[min(pos, len(chars) - 1)]
    return "".join(chars)


def near(version: str, rng: random.Random) -> str:
    """A valid-looking neighbour: same prefix, one token changed or appended."""
    extra = rng.choice(
        ["", ".0", ".1", "a", "_rc1", "_p1", "_p", "-r0", "-r1", "~a", ".00", "_git20200101", "0"]
    )
    cut = rng.choice([version, version, version.split("-r")[0], version.split("_")[0]])
    return cut + extra


def version_pairs(count: int, seed: int) -> list[tuple[str, str]]:
    rng = random.Random(seed)
    pairs: list[tuple[str, str]] = []
    for i in range(count):
        kind = i % 4
        if kind == 0:
            pairs.append((valid_version(rng), valid_version(rng)))
        elif kind == 1:
            v = valid_version(rng)
            pairs.append((v, near(v, rng)))
        elif kind == 2:
            v = valid_version(rng)
            pairs.append((v, mutate(v, rng)))
        else:
            pairs.append((token_soup(rng), token_soup(rng)))
    return pairs


OPS = ["<", "<=", "=", ">=", ">", "~", "=~", "~=", "><", "<>", "<~", ">~", "==", "<<", "=>", "=<", "~~", "<=>"]


def match_cases(count: int, seed: int) -> list[tuple[str, str, str]]:
    rng = random.Random(seed)
    cases: list[tuple[str, str, str]] = []
    for i in range(count):
        a = valid_version(rng)
        b = near(a, rng) if i % 2 else valid_version(rng)
        if i % 5 == 0:
            a, b = b, a
        cases.append((a, rng.choice(OPS), b))
    return cases
