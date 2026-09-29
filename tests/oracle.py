"""Driver for an external apk-tools oracle binary (not part of this repo).

Set APKVERSION_ORACLE to an executable that reads one request per line on
stdin and writes one answer per line on stdout. Fields are tab separated and
each field is hex-encoded UTF-8/latin-1 bytes:

    V a        -> 1 if a is a valid version, else 0
    C a b      -> bitmask of the comparison of a with b (1 equal, 2 less, 4 greater)
    M a op b   -> "<op mask> <0|1>": whether a satisfies op b
"""

from __future__ import annotations

import os
import subprocess

ENV = "APKVERSION_ORACLE"


def path() -> str | None:
    value = os.environ.get(ENV)
    if value and os.access(value, os.X_OK):
        return value
    return None


def _hx(text: str) -> str:
    return text.encode("utf-8").hex()


def _run(binary: str, lines: list[str]) -> list[str]:
    out: list[str] = []
    chunk = 20000
    for start in range(0, len(lines), chunk):
        part = lines[start : start + chunk]
        proc = subprocess.run(
            [binary], input="".join(f"{ln}\n" for ln in part), capture_output=True, text=True, check=True
        )
        answers = proc.stdout.split("\n")[: len(part)]
        if len(answers) != len(part):
            raise RuntimeError("oracle returned fewer answers than requests")
        out.extend(answers)
    return out


def validate(binary: str, versions: list[str]) -> list[bool]:
    return [a == "1" for a in _run(binary, [f"V\t{_hx(v)}" for v in versions])]


def compare(binary: str, pairs: list[tuple[str, str]]) -> list[int]:
    raw = _run(binary, [f"C\t{_hx(a)}\t{_hx(b)}" for a, b in pairs])
    return [-1 if int(r) & 2 else 1 if int(r) & 4 else 0 for r in raw]


def match(binary: str, cases: list[tuple[str, str, str]]) -> list[tuple[int, bool]]:
    raw = _run(binary, [f"M\t{_hx(a)}\t{_hx(op)}\t{_hx(b)}" for a, op, b in cases])
    result: list[tuple[int, bool]] = []
    for r in raw:
        mask, ok = r.split()
        result.append((int(mask), ok == "1"))
    return result
