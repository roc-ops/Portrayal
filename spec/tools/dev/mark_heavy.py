"""Mark the suite's heavy tests from what a full run measured.

    mark_heavy.py TIMES.json [--threshold 5] [--tests spec/tests] [--write]

TIMES.json is a full run's `test-times` artifact (suite_times.py --out). A test
FUNCTION whose parameters sum to `--threshold` seconds or more is heavy: it gets
`@pytest.mark.heavy`, which takes it out of the pull request push and leaves it
in the run before a merge and the nightly. Without `--write` this prints what it
would mark and changes nothing.

ONE-OFF AND ON REQUEST, not a gate. The budget (spec/test-budget.json,
portrayal/test_budget.py) is what holds the tiers to their size; this is how the
first marking was made and how a re-measured suite is re-marked. It only ADDS
the mark: a test that has become cheap keeps it until somebody takes it off,
because unmarking moves cost into the light tier and that is a decision.

A METHOD IS MARKED, NOT ITS CLASS, so a class keeps its cheap methods light.
"""
import argparse
import ast
import json
import pathlib
import sys

from portrayal.suite_times import fold_function

MARK = "@pytest.mark.heavy"


def heavy_functions(times, threshold=5.0):
    """{(module stem, function)} whose parameters sum to `threshold` seconds or more."""
    summed = {}
    for key, seconds in times.items():
        f = fold_function(key)
        summed[f] = summed.get(f, 0.0) + seconds
    return {f for f, s in summed.items() if s >= threshold}


def _is_heavy_mark(node):
    return ast.unparse(node) == MARK[1:]


def _targets(tree, names):
    """(def node, indent) for each named function: `f` at module level, `C.m` in a class."""
    out = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            out.append((node, ""))
        elif isinstance(node, ast.ClassDef):
            for sub in node.body:
                if (isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef))
                        and f"{node.name}.{sub.name}" in names):
                    out.append((sub, " " * sub.col_offset))
    return out


def _imports_pytest(tree):
    return any(isinstance(n, ast.Import) and any(a.name == "pytest" for a in n.names)
               for n in tree.body)


def mark_file(path, names):
    """Put the mark on each function in `names` that lacks it; the number added."""
    path = pathlib.Path(path)
    text = path.read_text()
    tree = ast.parse(text)
    lines = text.splitlines(keepends=True)
    inserts = []
    for node, indent in _targets(tree, names):
        if any(_is_heavy_mark(d) for d in node.decorator_list):
            continue
        first = min([d.lineno for d in node.decorator_list] + [node.lineno])
        inserts.append((first - 1, f"{indent}{MARK}\n"))
    if not inserts:
        return 0
    if not _imports_pytest(tree):
        after = max((n.end_lineno for n in tree.body
                     if isinstance(n, (ast.Import, ast.ImportFrom))), default=None)
        if after is None:
            doc = tree.body[0] if tree.body and isinstance(tree.body[0], ast.Expr) \
                and isinstance(getattr(tree.body[0], "value", None), ast.Constant) else None
            after = doc.end_lineno if doc else 0
        inserts.append((after, "import pytest\n"))
    for at, line in sorted(inserts, reverse=True):
        lines.insert(at, line)
    path.write_text("".join(lines))
    return len([i for i in inserts if i[1].strip() == MARK])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("times", help="a full run's test-times JSON")
    ap.add_argument("--threshold", type=float, default=5.0)
    ap.add_argument("--tests", default="spec/tests")
    ap.add_argument("--write", action="store_true", help="edit the files; without it, only print")
    args = ap.parse_args(argv)
    doc = json.loads(pathlib.Path(args.times).read_text())
    heavy = heavy_functions(doc.get("tests", doc), args.threshold)
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
        if args.write:
            n = mark_file(path, names)
            added += n
            print(f"  {n:3d} marked  {path}")
        else:
            print(f"  {len(names):3d} heavy   {path}")
    print(f"{len(heavy)} heavy function(s) in {len(by_file)} file(s)"
          + (f"; {added} mark(s) added" if args.write else "; nothing written (--write)")
          + (f"; {missing} file(s) not found" if missing else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
