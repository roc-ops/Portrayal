"""#712: the kit and the DCIM export give a port one NOS name, not two.

`kit/nosnames.js` expands a listing's `interfaces` for the explorer's
inspector; `dcim_export.listing_names` expands the same rules for NetBox and
Nautobot. A port the inspector calls `swp7` while the NetBox document calls it
something else is the drift #63 was filed about, so the two are run over the
same inputs - shared edge-case vectors and every listing in the build - and
must agree name for name. Skipped where node is not installed.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from portrayal import dcim_export as dx

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / "js/nos-names.mjs"
VECTORS = json.loads((HERE / "js/nos-name-vectors.json").read_text())


@pytest.fixture(scope="module")
def out():
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True, cwd=str(HERE))
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def py_names(listing):
    try:
        return {k: v[0] for k, v in dx.listing_names(listing).items()}
    except SystemExit:
        return {"error": True}


def test_the_edge_case_vectors_agree(out):
    for label, rule in VECTORS["rules"].items():
        assert out["vectors"][label] == py_names({"interfaces": [rule]}), label


def test_python_arithmetic_is_what_both_mean(out):
    """`/` truncates toward zero, `//` floors, `%` takes the divisor's sign -
    Python's int() and operators, which the export has always used."""
    v = out["vectors"]
    assert v["floor-division"]["port-0"] == "e-4"      # (0-7)//2
    assert v["modulo"]["port-0"] == "e2"               # (0-4)%3
    assert v["true-division"]["port-5"] == "e2"        # int(5/2)
    assert v["negative-offset"]["port-49"] == "Ethernet48"


def test_a_pattern_that_is_not_arithmetic_is_refused_by_both(out):
    for pat in VECTORS["refused"]:
        assert out["refused"][pat], f"kit expanded {pat!r}"
        with pytest.raises((SystemExit, ZeroDivisionError)):
            dx._expand(pat, 3)


def test_every_listing_in_the_build_names_its_ports_alike(out):
    if out["dist"] is None:
        pytest.skip("library/dist not built")
    dist = json.loads((HERE.parents[1] / "library/dist/listings.json").read_text())["listings"]
    named = 0
    for key, ls in dist.items():
        assert out["dist"][key] == py_names(ls), key
        named += len(out["dist"][key])
    assert named > 1000, f"only {named} names compared; the check measured little"


def test_the_inspector_says_the_name_or_why_not(out):
    if out["dist"] is None:
        pytest.skip("library/dist not built")
    i = out["inspector"]
    assert i["arcos7"]["name"] == "swp7" and i["arcos7"]["vendor"] == "Arrcus"
    assert "children swp7s{i}" in i["arcos7"]["note"]
    assert i["arcosGap"] == {"vendor": "Arrcus", "name": None, "gap": "arcos-port-names"}
    assert i["none"] is None, "no listing chosen, nothing said"
