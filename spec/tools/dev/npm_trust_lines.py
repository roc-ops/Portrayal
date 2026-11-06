#!/usr/bin/env python3
"""Print the `npm trust github` line for each package a release publishes.

    npm_trust_lines.py [--dist library/dist] [--only NAME [NAME ...]]

THIS PRINTS TEXT AND RUNS NOTHING. Trusting the workflow on a package is done
by a maintainer from their own npm login with two-factor, and each line is
meant to be read before it is run (docs/maintainers.md). The list of packages
is the one `npm_packages.py` publishes from: one per device, one per component
namespace, one per rack product and the index.

With `--only`, the lines are for the names given, in the order of the full
list. A name that is not a package of this build is an error and nothing is
printed.
"""
import argparse
import sys

from portrayal import npm_packages

# What the line is built from. A test reads the workflow file's name and the
# job's `environment:` from .github/workflows/ and fails if either moves.
REPOSITORY = "roc-ops/Portrayal"
WORKFLOW = "release.yml"
ENVIRONMENT = "npm"


def trust_line(package):
    return (f"npm trust github {package} --file {WORKFLOW} --repository {REPOSITORY} "
            f"--environment {ENVIRONMENT} --allow-publish --yes")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dist", default="library/dist")
    ap.add_argument("--only", nargs="+", metavar="NAME",
                    help="only these packages, as the build names them")
    args = ap.parse_args(argv)
    names = npm_packages.package_names(args.dist)
    if args.only:
        unknown = [n for n in args.only if n not in names]
        if unknown:
            ap.error("not a package of this build: " + ", ".join(unknown))
        names = [n for n in names if n in args.only]
    for name in names:
        print(trust_line(name))
    print(f"{len(names)} lines", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
