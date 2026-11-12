#!/usr/bin/env python3
"""Print the `npm deprecate` line for each held package this build no longer ships.

    npm_deprecate_lines.py --held FILE [--dist library/dist]

THIS PRINTS TEXT AND RUNS NOTHING. A device that is removed or renamed leaves
its package on npm, and nothing in the release marks it (`npm_packages.py`
publishes what a build makes and never looks for what it stopped making).
Deprecating is done by a maintainer from their own npm login with two-factor,
and each line is meant to be read before it is run (docs/maintainers.md).

`--held` is a file of the package names npm holds under the scope, one to a
line, that the maintainer made from their own login; blank lines and lines
starting with `#` are skipped. This tool asks npm nothing. A name that is not
`@portrayal/<name>` is an error and nothing is printed. The lines are for the
held names that are not among the packages `npm_packages.py` would write from
`--dist` (one per device, component namespace and rack product, and the index),
sorted, one to a name.
"""
import argparse
import re
import shlex
import sys

from portrayal import npm_packages

# Held under the scope but not made by a build: the kit is published by hand from
# kit/, and `@portrayal/components` was split by namespace and is deprecated once,
# by hand (docs/maintainers.md). Neither is stale.
NOT_FROM_THE_BUILD = ("@portrayal/kit", "@portrayal/components")

MESSAGE = ("no longer part of the Portrayal library (removed or renamed); "
           "@portrayal/index lists the packages it ships")

_NAME = re.compile(r"^@portrayal/[a-z0-9][a-z0-9._-]*$")


def deprecate_line(package):
    return shlex.join(["npm", "deprecate", package, MESSAGE])


def read_held(path):
    names = []
    for raw in open(path, encoding="utf-8").read().splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            names.append(line)
    return names


def stale(held, shipped):
    """The held names the build does not ship, sorted, once each."""
    skip = set(shipped) | set(NOT_FROM_THE_BUILD)
    return sorted({n for n in held if n not in skip})


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dist", default="library/dist")
    ap.add_argument("--held", required=True, metavar="FILE",
                    help="the package names npm holds under the scope, one to a line")
    args = ap.parse_args(argv)
    held = read_held(args.held)
    bad = [n for n in held if not _NAME.match(n)]
    if bad:
        ap.error("not a package of the @portrayal scope: " + ", ".join(bad))
    names = stale(held, npm_packages.package_names(args.dist))
    for name in names:
        print(deprecate_line(name))
    print(f"{len(names)} lines", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
