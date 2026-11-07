"""The whole-library census tests count a `kind: kit` where it belongs (roc-ops/Portrayal#904).

A kit (#905) is a set a device names from `chassis.kits`. It has no `class`, no
`size` and no skin, it is never placed, and the index publishes it in `kits.json`,
never in `components.json`. The census tests walk every contract in the library,
so the first kit made them fail: the class vocabulary, the cage census, the
catalogue and index columns tests, and a `components.json` count, each assuming
that every contract is a placed component with a `class` and a row of
`components.json`.

This holds the join the census tests rely on, through the tools the build runs
(`components_index.py` and `components_catalogue.py`), on a library built on
tmp_path with one ordinary component and one kit, and then on the real library,
whatever kits it holds:

- the kit is in `kits.json` and the catalogue's "Rail kits" table, and in neither
  `components.json` nor the component tables;
- the ordinary component is still counted, in both;
- the class census still fails a component with no `class`, and does not read a
  kit at all.
"""
import json
import pathlib
import subprocess
import sys

import pytest
import yaml

import onebuild
import test_class_and_provenance_vocabulary as vocab
from portrayal import components_catalogue as cat
from portrayal.manifest import load_yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"

PART = {"format": 1, "kind": "component", "name": "inner", "version": "1.0.0",
        "class": "bracket", "size": {"w": 20, "h": 40},
        "description": "A rail member. Test part."}
KIT = {"format": 1, "kind": "kit", "name": "slide", "version": "1.0.0",
       "description": "A slide. Test kit.", "motion": "fixed",
       "parts": [{"ref": "acme/inner@1", "id": "inner", "count": 2}],
       "configurations": [{"id": "four-post", "racks": ["4-post"],
                           "parts": ["inner"], "depth": [500, 600]}]}


def _write(lib, ref, doc):
    ns, rest = ref.split("/")
    name, major = rest.split("@")
    d = lib / "components" / ns / name / f"v{major}"
    d.mkdir(parents=True, exist_ok=True)
    (d / "contract.yaml").write_text(yaml.safe_dump(doc, sort_keys=False))


@pytest.fixture
def lib(tmp_path):
    lib = tmp_path / "library"
    _write(lib, "acme/inner@1", PART)
    _write(lib, "acme/slide@1", KIT)
    (lib / "devices").mkdir()
    return lib


def _refs(entries):
    return {f"{e['ns']}/{e['name']}@{e['major'][1:]}" for e in entries}


def _component_tables(page):
    return page.split("## Rail kits")[0]


def test_a_kit_is_in_kits_json_and_the_kit_table_and_in_no_component_list(lib, tmp_path):
    out = tmp_path / "dist"
    r = subprocess.run([sys.executable, str(ROOT / "spec/tools/portrayal/components_index.py"),
                        "--library", str(lib), "--out", str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    comps = json.loads((out / "components.json").read_text())["components"]
    kits = json.loads((out / "kits.json").read_text())["kits"]
    assert _refs(kits) == {"acme/slide@1"}
    assert _refs(comps) == {"acme/inner@1"}      # the ordinary component is still counted

    page = cat.build(lib)
    assert "## Rail kits (1)" in page
    assert "| `acme/slide@1` | fixed |" in page.split("## Rail kits")[1]
    tables = _component_tables(page)
    assert "acme/slide@1" not in tables
    assert "| `acme/inner@1` | component | bracket |" in tables
    assert "\n1 component majors in " in page


def test_the_class_census_does_not_read_a_kit_and_still_reads_a_component_with_no_class(lib):
    contracts = vocab.read_contracts(lib)
    assert set(contracts) == {"acme/inner@1"}
    assert {d.get("class") for d in contracts.values()} == {"bracket"}
    # THE PLANTED FAULT: a component with no `class` is in the census as None, which
    # test_every_class_the_library_uses_is_in_the_list refuses
    _write(lib, "acme/classless@1", {k: v for k, v in PART.items() if k != "class"}
           | {"name": "classless"})
    contracts = vocab.read_contracts(lib)
    assert set(contracts) == {"acme/inner@1", "acme/classless@1"}
    assert None in {d.get("class") for d in contracts.values()}


def test_every_kit_in_the_library_is_in_kits_json_and_the_kit_table_only():
    """The real library, whatever kits it holds: a kit on disk is published in
    kits.json and listed under "Rail kits", and the component totals of
    components.json and of the page agree with the contracts that are not kits."""
    docs = {f"{c.parts[-4]}/{c.parts[-3]}@{c.parts[-2][1:]}": load_yaml(c) or {}
            for c in LIB.glob("components/*/*/v*/contract.yaml")}
    kit_refs = {ref for ref, d in docs.items() if d.get("kind") == "kit"}
    placed = set(docs) - kit_refs
    assert placed, "the walk found no component"

    out = onebuild.components_index()
    comps = _refs(json.loads((out / "components.json").read_text())["components"])
    kits = _refs(json.loads((out / "kits.json").read_text())["kits"])
    assert kits == kit_refs
    assert comps == placed

    page = cat.build(LIB)
    assert f"\n{len(placed)} component majors in " in page
    if kit_refs:
        assert f"## Rail kits ({len(kit_refs)})" in page
        kit_table = page.split("## Rail kits")[1]
        tables = _component_tables(page)
        for ref in kit_refs:
            assert f"| `{ref}` |" in kit_table, ref
            assert f"`{ref}`" not in tables, ref
    else:
        assert "Rail kits" not in page
