#!/usr/bin/env python3
"""Every skipped test gave a reason the project has agreed to.

WHY NOT A COUNT, which is what this replaced. The gate allowed "at most 5
skipped": a global integer that any contributor's legitimate optional test
spends for everyone, and which says nothing about WHICH test stopped running.
The failure it exists to catch is a tool going missing from the runner - `node`
disappearing skips fourteen files at a stroke - and a budget catches that only
because fourteen happens to be larger than five. A budget of twenty would not,
and nobody would notice the day it was raised.

An allow-list says the other thing: a skip is the suite reporting that it did
not test something, and the reason has to be a fact about the world - a part
this library does not contain, a genuinely optional tool - rather than about the
runner being short of something it should have.

    check_skips.py <pytest -rs output> <allow-list>

Reads pytest's `-rs` short summary, which prints one `SKIPPED [n] file:line:
reason` line per distinct reason.
"""
import pathlib
import re
import sys

SKIP = re.compile(r"^SKIPPED \[(\d+)\] ([^:]+:\d+): (.*)$")


def allowed(path):
    out = []
    for line in pathlib.Path(path).read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(line)
    return out


def main(report, allowlist):
    ok = allowed(allowlist)
    text = pathlib.Path(report).read_text()
    bad, total = [], 0
    for line in text.splitlines():
        m = SKIP.match(line.strip())
        if not m:
            continue
        n, where, reason = int(m.group(1)), m.group(2), m.group(3).strip()
        total += n
        if not any(a in reason for a in ok):
            bad.append((n, where, reason))
    print(f"skipped: {total}")
    if bad:
        print(f"::error::{sum(n for n, _, _ in bad)} test(s) skipped for a reason "
              f"{allowlist} does not list:")
        for n, where, reason in bad:
            print(f"::error::  {n:3d}  {where}: {reason}")
        print("::error::A skip is the suite saying it did not test something. If the")
        print("::error::reason is a fact about the world, add it to the allow-list in")
        print("::error::the same commit that explains why; if it is the runner missing")
        print("::error::something it should have, that is the bug this step exists for.")
        return 1
    # NON-VACUITY, one level up: an allow-list nothing matches is indistinguishable
    # from a run that skipped nothing, and both print `skipped: 0`. Say which.
    if total == 0:
        print("no tests skipped")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__.strip().splitlines()[-3].strip(), file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
