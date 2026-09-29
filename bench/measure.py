"""Measure agreement with apk-tools for apkversion, univers and (optionally)
osv.dev's vendored copy of univers' Alpine class.

    APKVERSION_ORACLE=/path/to/oracle python bench/measure.py \
        [--versions real.txt] [--pairs a.tsv b.tsv ...] [--osv-parent DIR] [--count N]

`univers` is measured when it is importable. `--osv-parent` is a directory
containing an `osvalp` package (alpine.py, gentoo.py, utils.py copied from
osv.dev's osv/third_party/univers).
"""

from __future__ import annotations

import argparse
import random
import sys
from collections.abc import Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tests"))

import gen  # noqa: E402
import oracle  # noqa: E402

import apkversion  # noqa: E402

Impl = Callable[[str, str], int]


def load_impls(osv_parent: str | None) -> dict[str, tuple[Callable[[str], object], Impl]]:
    impls: dict[str, tuple[Callable[[str], object], Impl]] = {
        "apkversion": (apkversion.AlpineVersion, apkversion.compare)
    }
    try:
        from univers.versions import AlpineLinuxVersion as U  # type: ignore[import-not-found,unused-ignore]

        impls["univers"] = (U, lambda a, b: (U(a) > U(b)) - (U(a) < U(b)))
    except ImportError:
        print("univers not importable; skipping it", file=sys.stderr)
    if osv_parent:
        sys.path.insert(0, osv_parent)
        from osvalp.alpine import AlpineLinuxVersion as O  # type: ignore[import-not-found,unused-ignore]

        impls["osv vendored"] = (O, lambda a, b: (O(a) > O(b)) - (O(a) < O(b)))
    return impls


def score_pairs(
    name: str, impl: Impl, pairs: list[tuple[str, str]], want: list[int | None]
) -> tuple[int, int, int, int]:
    """Return (agree, valid, raised, wrong_order) over pairs the oracle accepts."""
    agree = valid = raised = wrong = 0
    for (a, b), w in zip(pairs, want):
        if w is None:
            continue
        valid += 1
        try:
            got = impl(a, b)
        except Exception:
            raised += 1
            continue
        if got == w:
            agree += 1
        else:
            wrong += 1
    return agree, valid, raised, wrong


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--versions")
    ap.add_argument("--pairs", nargs="*", default=[])
    ap.add_argument("--osv-parent")
    ap.add_argument("--count", type=int, default=20000)
    args = ap.parse_args()
    binary = oracle.path()
    if binary is None:
        print(f"set {oracle.ENV} to an oracle binary", file=sys.stderr)
        return 2
    impls = load_impls(args.osv_parent)

    corpora: list[tuple[str, list[tuple[str, str]]]] = []
    for f in args.pairs:
        rows = [ln.split("\t") for ln in Path(f).read_text().split("\n") if ln]
        corpora.append((Path(f).name, [(r[0], r[1]) for r in rows]))
    corpora.append((f"generated (seed 1, n={args.count})", gen.version_pairs(args.count, 1)))

    for label, pairs in corpora:
        va = oracle.validate(binary, [a for a, _ in pairs])
        vb = oracle.validate(binary, [b for _, b in pairs])
        ok = [p for p, x, y in zip(pairs, va, vb) if x and y]
        want_ok = oracle.compare(binary, ok)
        it = iter(want_ok)
        want: list[int | None] = [next(it) if x and y else None for x, y in zip(va, vb)]
        print(f"\n{label}: {len(pairs)} pairs, {len(ok)} valid per apk")
        for name, (_, fn) in impls.items():
            agree, valid, raised, wrong = score_pairs(name, fn, pairs, want)
            print(f"  {name:14} agree {agree}/{valid} = {100 * agree / valid:.2f}%  raised {raised}  wrong order {wrong}")

    if args.versions:
        versions = [ln for ln in Path(args.versions).read_text().split("\n") if ln]
        good = oracle.validate(binary, versions)
        print(f"\nvalidity over {len(versions)} versions ({sum(good)} valid per apk)")
        for name, (ctor, _) in impls.items():
            rejected = 0
            for v, g in zip(versions, good):
                try:
                    ctor(v)
                except Exception:
                    rejected += 1
                    continue
            print(f"  {name:14} constructor rejects {rejected}/{len(versions)}")

    rng = random.Random(5)
    vs = [gen.valid_version(rng) for _ in range(300)]
    print("\nconsistency of < and <= over 300 generated valid versions (all ordered pairs)")
    for name, (ctor, _) in impls.items():
        objs = []
        for v in vs:
            try:
                objs.append(ctor(v))
            except Exception:
                pass
        bad = 0
        total = 0
        for x in objs:
            for y in objs:
                total += 1
                try:
                    lt, eq, gt = x < y, x == y, x > y  # type: ignore[operator]
                    le, ge = x <= y, x >= y  # type: ignore[operator]
                    if lt + eq + gt != 1 or le != (lt or eq) or ge != (gt or eq):
                        bad += 1
                except Exception:
                    bad += 1
        print(f"  {name:14} inconsistent {bad}/{total} pairs ({len(objs)} parsed)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
