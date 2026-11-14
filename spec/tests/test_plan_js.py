"""kit/plan.js: the x-sweep written again in JavaScript, held to the answers Python is held to.

`portrayal.plan` (Python) and `kit/plan.js` are one function written twice. They read the same two
files: `fixtures/plan_outline/sweep-cases.json` (every answer worked by hand, read by
`test_plan_sweep.py`) and `fixtures/plan_outline/body-cases.json` (what `plan.py` computes for two
made-up boxes, kept honest by `test_plan_body_cases.py`). The node script reads both files itself
and checks every case; this module asserts nothing was skipped and nothing failed.
"""
import json
import pathlib
import shutil
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
KIT = ROOT / "kit"
FIX = ROOT / "spec/tests/fixtures/plan_outline"
JS = ROOT / "spec/tests/js"

needs_node = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")

# the most the biggest outline the format allows (16 bands, 2048 points) may take in node, in
# milliseconds: the cut and the union take about 130 ms where this was written, so a budget of
# 1000 ms is room for a slow runner and still fails on a sweep that has gone quadratic
SWEEP_BUDGET_MS = 1000


def node(script, *args):
    p = subprocess.run(["node", str(JS / script), *map(str, args)], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr[-1500:]
    return json.loads(p.stdout.strip().splitlines()[-1])


@pytest.fixture(scope="module")
def parity():
    return node("plan-parity.mjs", KIT / "plan.js", FIX / "sweep-cases.json", FIX / "body-cases.json")


@needs_node
def test_the_js_sweep_gives_every_answer_in_the_shared_files(parity):
    assert parity["failures"] == [], json.dumps(parity["failures"], indent=1)[:3000]


@needs_node
def test_every_case_of_both_files_was_checked(parity):
    """The JS reads the two files itself; a case it has no handler for or never reaches would be a
    silent pass, so the names it checked are held against the files."""
    sweep = json.loads((FIX / "sweep-cases.json").read_text())["cases"]
    body = json.loads((FIX / "body-cases.json").read_text())["cases"]
    checked = set(parity["names"])
    for c in sweep:
        assert c["name"] in checked or f"{c['name']} (points)" in checked, c["name"]
    for c in body:
        for part in ("snaps", "bands", "rows", "solid", "outline"):
            assert f"{c['name']}: {part}" in checked, (c["name"], part)
    assert {c["kind"] for c in sweep} == {"abscissae", "clip", "union", "snap", "body", "minus",
                                          "clipped-union", "rows"}


@needs_node
def test_the_biggest_outline_the_format_allows_is_cut_in_the_budget():
    got = node("plan-timing.mjs", KIT / "plan.js")
    assert got["points"] == 2048 and got["bands"] == 16
    assert got["pieces"] > 0 and got["loops"] >= 1
    assert got["ms"] < SWEEP_BUDGET_MS, f"{got['ms']:.0f} ms for {got['points']} points over {got['bands']} bands"


def test_the_new_module_is_in_the_kit_test_script_and_exports():
    pkg = json.loads((KIT / "package.json").read_text())
    assert "node --check plan.js" in pkg["scripts"]["test"]
    assert "node --check plan-body.js" in pkg["scripts"]["test"]
    assert pkg["exports"]["./plan"] == "./plan.js"
    assert pkg["exports"]["./plan-body"] == "./plan-body.js"


def test_the_python_and_js_constants_are_the_same():
    from portrayal import plan as P
    src = (KIT / "plan.js").read_text()
    for name, value in (("MERGE", P.MERGE), ("SNAP", P.SNAP), ("TOL", P.TOL), ("DECIMALS", P.DECIMALS)):
        assert f"export const {name} = {value:g};" in src or f"export const {name} = {value};" in src, name
