"""The compiler directory holds the compiler, and the dependency runs one way.

`spec/tools/portrayal/` held fifty modules: the twenty-one `build.sh`,
`publish.sh` and CI actually reach, and twenty-nine that nothing in the pipeline
imports - modelling probes written to answer one question, seven ML benchmarks,
four corrective sweeps, a Visio stencil reader, a USD converter, an audit of one
device's rear face. A reader could not tell which twenty-one mattered, and
neither could a grep (#179).

They are four packages now, and the split is asserted by WALKING THE IMPORTS
rather than by keeping a list - the list is what went stale in the first place.
"""
import ast
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
TOOLS = ROOT / "spec/tools"
PKGS = {"portrayal": "portrayal", "dev": "portrayal_dev", "bench": "portrayal_bench",
        "sweeps": "portrayal_sweeps", "intake": "portrayal_intake"}


def _imports(path):
    """Which tool packages this file reaches, by parsing rather than grepping."""
    out = set()
    for n in ast.walk(ast.parse(path.read_text())):
        if isinstance(n, ast.ImportFrom) and n.module:
            out.add(n.module.split(".")[0])
        elif isinstance(n, ast.Import):
            out |= {a.name.split(".")[0] for a in n.names}
    return out & set(PKGS.values())


def test_the_compiler_imports_none_of_the_others():
    """THE DIRECTION THAT MATTERS. dev, bench and sweeps may reach into the
    compiler - a sweep asks the lint rule it is the remedy for - and the
    compiler must reach back into none of them, or the split is decorative and
    `pip install portrayal` drags in seven ML benchmarks."""
    bad = {}
    for f in sorted((TOOLS / "portrayal").glob("*.py")):
        reaches = _imports(f) - {"portrayal"}
        if reaches:
            bad[f.name] = sorted(reaches)
    assert not bad, bad


def test_every_package_has_an_init_and_pyproject_lists_it():
    import tomllib
    setup = tomllib.loads((ROOT / "pyproject.toml").read_text())["tool"]["setuptools"]
    assert set(setup["packages"]) == set(PKGS.values())
    for d, pkg in PKGS.items():
        assert (TOOLS / d / "__init__.py").exists(), f"{d} is not a package"
        assert setup["package-dir"][pkg] == f"spec/tools/{d}"


def test_what_the_gates_run_is_what_the_compiler_holds():
    """THE ASSERTION THAT CANNOT GO STALE: the closure of everything build.sh,
    publish.sh and CI invoke, walked through the imports, must be exactly the
    modules left in the compiler directory. Add a tool the gates need and it has
    to live here; stop needing one and it has to leave.
    """
    here = {p.stem for p in (TOOLS / "portrayal").glob("*.py")} - {"__init__", "__main__"}

    def imports_of(stem):
        out = set()
        for n in ast.walk(ast.parse((TOOLS / "portrayal" / f"{stem}.py").read_text())):
            if isinstance(n, ast.ImportFrom) and n.module:
                p = n.module.split(".")
                if p[0] == "portrayal":
                    out |= {p[1]} if len(p) > 1 else {a.name for a in n.names}
            elif isinstance(n, ast.Import):
                for a in n.names:
                    p = a.name.split(".")
                    if p[0] == "portrayal" and len(p) > 1:
                        out.add(p[1])
        return out & here

    entry = {"lint", "render", "dcim_export", "devicelock", "check_skips", "suite_times", "expand",
             "devices_index", "components_index", "labs_index", "gaps_index",
             "registry_index", "comparable_index", "components_catalogue", "npm_packages",
             "changelog"}
    seen, stack = set(), list(entry)
    while stack:
        m = stack.pop()
        if m in seen:
            continue
        seen.add(m)
        stack += list(imports_of(m))
    assert seen == here, (
        f"in the compiler but unreachable from the gates: {sorted(here - seen)}; "
        f"reachable but not here: {sorted(seen - here)}")


def test_nothing_does_its_work_on_import():
    """A SCRIPT THAT RUNS AT MODULE SCOPE IS A LANDMINE ONCE IT IS IMPORTABLE.
    Making the sweeps a package turned `import portrayal_sweeps.sweep_ids` into
    a run of the sweep - it printed its dry-run table from inside a test
    collection - and `audit_r740xd_rear`, which #179 names for having no guard,
    audited a device on import.

    A module-level `if` opens no scope, so guarding costs nothing: everything
    below stays a global and only the import path changes.
    """
    offenders = []
    for d in PKGS:
        for f in sorted((TOOLS / d).glob("*.py")):
            tree = ast.parse(f.read_text())
            work = [n for n in tree.body
                    if not isinstance(n, (ast.Import, ast.ImportFrom, ast.FunctionDef,
                                          ast.AsyncFunctionDef, ast.ClassDef, ast.Assign,
                                          ast.AnnAssign, ast.Expr, ast.If, ast.Try))]
            loops = [n for n in tree.body if isinstance(n, (ast.For, ast.While))]
            if work or loops:
                offenders.append(str(f.relative_to(ROOT)))
    assert not offenders, f"these run at module scope: {offenders}"


@pytest.mark.parametrize("d", sorted(PKGS))
def test_every_script_answers_help(d):
    """#179's last clause. A file with a `__main__` guard is a script someone
    will run, and a script that cannot say what it wants is one they will run
    wrong."""
    bad = []
    for f in sorted((TOOLS / d).glob("*.py")):
        src = f.read_text()
        if '__name__ == "__main__"' in src or "__name__ == '__main__'" in src:
            if "ArgumentParser" not in src:
                bad.append(str(f.relative_to(ROOT)))
    assert not bad, f"scripts with no --help: {bad}"
