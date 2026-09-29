"""Differential run: compare this package against an oracle over generated and
supplied corpora. Usage:

    APKVERSION_ORACLE=/path/to/oracle python tests/diff.py [--real versions.txt]
        [--pairs pairs.tsv ...] [--count N]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import gen  # noqa: E402
import oracle  # noqa: E402

from apkversion import InvalidVersion, compare, match, validate  # noqa: E402


def check_validate(binary: str, versions: list[str]) -> list[str]:
    bad = []
    for v, want in zip(versions, oracle.validate(binary, versions)):
        if validate(v) != want:
            bad.append(f"validate({v!r}): mine={validate(v)} oracle={want}")
    return bad


def check_pairs(binary: str, pairs: list[tuple[str, str]]) -> tuple[list[str], int]:
    valid_a = oracle.validate(binary, [a for a, _ in pairs])
    valid_b = oracle.validate(binary, [b for _, b in pairs])
    both = [p for p, x, y in zip(pairs, valid_a, valid_b) if x and y]
    bad = []
    for (a, b), want in zip(both, oracle.compare(binary, both)):
        got = compare(a, b)
        if got != want:
            bad.append(f"compare({a!r}, {b!r}): mine={got} oracle={want}")
    for (a, b), x, y in zip(pairs, valid_a, valid_b):
        if not (x and y):
            try:
                compare(a, b)
                bad.append(f"compare({a!r}, {b!r}): mine accepted, oracle rejects")
            except InvalidVersion:
                pass
    return bad, len(both)


def check_match(binary: str, cases: list[tuple[str, str, str]]) -> tuple[list[str], int]:
    valid = oracle.validate(binary, [a for a, _, _ in cases] + [b for _, _, b in cases])
    n = len(cases)
    ok_cases = [c for c, x, y in zip(cases, valid[:n], valid[n:]) if x and y]
    bad = []
    for (a, op, b), (mask, want) in zip(ok_cases, oracle.match(binary, ok_cases)):
        if mask == 0:
            try:
                match(a, op, b)
                bad.append(f"match({a!r}, {op!r}, {b!r}): mine accepted op the oracle maps to mask 0")
            except ValueError:
                pass
            continue
        got = match(a, op, b)
        if got != want:
            bad.append(f"match({a!r}, {op!r}, {b!r}): mine={got} oracle={want}")
    return bad, len(ok_cases)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", help="file of versions, one per line")
    ap.add_argument("--pairs", nargs="*", default=[], help="TSV files of pairs")
    ap.add_argument("--count", type=int, default=60000)
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()
    binary = oracle.path()
    if binary is None:
        print(f"set {oracle.ENV} to an oracle binary", file=sys.stderr)
        return 2
    total_bad = 0

    def report(name: str, bad: list[str], n: int) -> None:
        nonlocal total_bad
        total_bad += len(bad)
        print(f"{name}: {n - len(bad)}/{n} agree")
        for line in bad[:15]:
            print("   ", line)

    if args.real:
        versions = [ln for ln in Path(args.real).read_text().split("\n") if ln]
        bad = check_validate(binary, versions)
        report("validate real", bad, len(versions))
    for file in args.pairs:
        pairs = [tuple(ln.split("\t")) for ln in Path(file).read_text().split("\n") if ln]
        bad, n = check_pairs(binary, [(a, b) for a, b in pairs])
        report(f"pairs {Path(file).name} (valid pairs {n} of {len(pairs)})", bad, len(pairs))
    pairs2 = gen.version_pairs(args.count, args.seed)
    bad, n = check_pairs(binary, pairs2)
    report(f"generated pairs (valid pairs {n} of {len(pairs2)})", bad, len(pairs2))
    cases = gen.match_cases(args.count, args.seed + 1)
    bad, n = check_match(binary, cases)
    report(f"generated match cases (valid {n} of {len(cases)})", bad, len(cases))
    return 1 if total_bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
