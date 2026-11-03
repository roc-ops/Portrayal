"""Mark the suite's heavy tests from what full runs measured.

    mark_heavy.py TIMES.json [TIMES.json ...] [--threshold 5] [--tests spec/tests] [--write]

Each TIMES.json is a run's `test-times` artifact (suite_times.py --out). A test
FUNCTION whose parameters sum to `--threshold` seconds or more is heavy: it gets
`@pytest.mark.heavy`, which takes it out of the pull request push and leaves it
in the run before a merge and the nightly. Without `--write` this prints what it
would mark and changes nothing.

A SHARED COST IS BILLED TO WHOEVER PAYS IT FIRST, which is why two rules widen
the plain threshold:

  - SEVERAL RUNS, THE HEAVIEST COUNTS. A module fixture is charged to the first
    test a worker runs from that module, so one function measures heavy in one
    run and light in the next. Give every run there is; a function heavy in any
    of them is heavy.
  - A GROUP IS HEAVY TOGETHER. The tests of an xdist group wait on one shared
    run (spec/tests/onebuild.py); in a full run one `full-lint` reader took 290 s
    and the others 0.01 s. If any member is heavy, every member is, or the light
    tier runs the whole-library lint through a reader that measured cheap.

A light run measures what the light tier really pays: give its record too, and
re-mark until nothing new comes up.

ONE-OFF AND ON REQUEST, not a gate. The budget (spec/test-budget.json,
portrayal/suite_budget.py) is what holds the tiers to their size; this is how
the first marking was made and how a re-measured suite is re-marked. It only
ADDS the mark: a test that has become cheap keeps it until somebody takes it
off, because unmarking moves cost into the light tier and that is a decision.

A METHOD IS MARKED, NOT ITS CLASS, so a class keeps its cheap methods light.
"""
import argparse
import ast
import json
import pathlib
import sys

from portrayal.suite_times import split_key

MARK = "@pytest.mark.heavy"


def heavy_functions(runs, threshold=5.0):
    """{(module stem, function)} heavy in any of `runs` (one {key: seconds} or a
    list of them): parameters summed to `threshold` or more, or in an xdist group
    with a function that is."""
    if isinstance(runs, dict):
        runs = [runs]
    heavy, groups = set(), {}
    for times in runs:
        summed = {}
        for key, seconds in times.items():
            stem, name, group = split_key(key)
            summed[(stem, name)] = summed.get((stem, name), 0.0) + seconds
            if group:
                groups.setdefault(group, set()).add((stem, name))
        heavy |= {f for f, s in summed.items() if s >= threshold}
    for members in groups.values():
        if members & heavy:
            heavy |= members
    return heavy


def _is_heavy_mark(node):
    return ast.unparse(node) == MARK[1:]


def _targets(tree, names):
    """(def node, indent, name) for each named function: `f` at module level,
    `C.m` in a class. A nested class or an inherited method is not found."""
    out = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            out.append((node, "", node.name))
        elif isinstance(node, ast.ClassDef):
            for sub in node.body:
                if not isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                qual = f"{node.name}.{sub.name}"
                if qual in names:
                    out.append((sub, " " * sub.col_offset, qual))
    return out


def unfound(path, names):
    """The names in `names` this file has no markable function for."""
    tree = ast.parse(pathlib.Path(path).read_text())
    return set(names) - {qual for _, _, qual in _targets(tree, names)}


def _imports_pytest(tree):
    """`import pytest` itself: `import pytest as pt` binds `pt`, not `pytest`."""
    return any(isinstance(n, ast.Import) and any(a.name == "pytest" and a.asname is None
                                                  for a in n.names)
               for n in tree.body)


def _import_line(tree):
    """Where `import pytest` goes: after the imports that open the module, so it
    is bound before any definition reads it - never after a late import."""
    after, body = 0, tree.body
    if body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], "value", None),
                                                             ast.Constant):
        after, body = body[0].end_lineno, body[1:]
    for node in body:
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            break
        after = node.end_lineno
    return after


def mark_file(path, names):
    """Put the mark on each function in `names` that lacks it; the number added."""
    path = pathlib.Path(path)
    text = path.read_text()
    tree = ast.parse(text)
    lines = text.splitlines(keepends=True)
    inserts = []
    for node, indent, _ in _targets(tree, names):
        if any(_is_heavy_mark(d) for d in node.decorator_list):
            continue
        first = min([d.lineno for d in node.decorator_list] + [node.lineno])
        inserts.append((first - 1, f"{indent}{MARK}\n"))
    if not inserts:
        return 0
    if not _imports_pytest(tree):
        inserts.append((_import_line(tree), "import pytest\n"))
    for at, line in sorted(inserts, reverse=True):
        lines.insert(at, line)
    path.write_text("".join(lines))
    return len([i for i in inserts if i[1].strip() == MARK])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("times", nargs="+", help="runs' test-times JSON; the heaviest counts")
    ap.add_argument("--threshold", type=float, default=5.0)
    ap.add_argument("--tests", default="spec/tests")
    ap.add_argument("--write", action="store_true", help="edit the files; without it, only print")
    args = ap.parse_args(argv)
    runs = []
    for path in args.times:
        doc = json.loads(pathlib.Path(path).read_text())
        runs.append(doc.get("tests", doc))
    heavy = heavy_functions(runs, args.threshold)
    by_file = {}
    for stem, name in heavy:
        by_file.setdefault(stem, set()).add(name)
    added = missing = 0
    for stem, names in sorted(by_file.items()):
        path = pathlib.Path(args.tests) / f"{stem}.py"
        if not path.is_file():
            print(f"  no file for {stem} ({len(names)} function(s)) - renamed or removed since the run")
            missing += 1
            continue
        lost = unfound(path, names)
        if args.write:
            n = mark_file(path, names)
            added += n
            print(f"  {n:3d} marked  {path}")
        else:
            print(f"  {len(names):3d} heavy   {path}")
        for name in sorted(lost):
            print(f"      NOT FOUND {name} - nested, inherited or made by assignment; mark it by hand")
            missing += 1
    print(f"{len(heavy)} heavy function(s) in {len(by_file)} file(s)"
          + (f"; {added} mark(s) added" if args.write else "; nothing written (--write)")
          + (f"; {missing} file(s) or function(s) not found, named above" if missing else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
