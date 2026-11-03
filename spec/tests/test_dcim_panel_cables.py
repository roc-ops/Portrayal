"""A cable on a fibre port of a seated panel or cassette, in the DCIM cables
files (roc-ops/Portrayal#1020).

A module type does not name a fibre port by its part: a duplex adapter `lc01`
is the front ports `1` and `2`, its back `b01` the rear port `B01-1`. The build
publishes which, per part, as `optical.ports` in components.json, from the walk
that writes the type file; the kit reads it and never derives a name.

Three things are held here. The published names are the committed type files'
names, for every module whose glass is projected, on both targets. The
projection's two views (`ports`, `part_ports`) are one walk. And the kit's own
rows, by its node tests, against the committed files and two golden CSVs.

WHAT A CABLES FILE REACHES is narrower than what agrees here, and the node
sweep states it: of the 63 modules that publish ports, the kit finds a type
file for all, by the part number or, with no `attrs.model`, by the contract
name; on NetBox they resolve, less the one adapter of each of 4 DCMs; on
Nautobot, less the 4 DCMs, 4 types carry no glass there and the rest resolve
whole. This file finds a type by its model OR its contract name, as the kit
does, so it compares the names of all 63.

A MODULE IN A BAY OF ANOTHER MODULE (#1024) is reached too: 28 of the 63 (the
20 Fibrain holders in the XCU10 drawer, the 8 Smartoptics modules in the
DCP-F-A22), named through the carrier's bay. The node sweep seats each and
checks every name against the committed type files of both targets.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
import yaml

import onebuild
from portrayal import optical_ports
from portrayal.dcim_export import MODULE_TOKEN

ROOT = Path(__file__).resolve().parents[2]
EXPORTS = ROOT / "library" / "exports"
JS = Path(__file__).resolve().parent / "js" / "dcim-panel-cables.mjs"
SECTIONS = ("front-ports", "rear-ports")


def _index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return [e for e in doc["components"] if e.get("kind") == "module" and not e.get("superseded-by")]


def _type_file(target, entry):
    """The committed module type a contract is written as, or None: by its
    model, else by its contract name, which is how the exporter names the file
    (`dcim_export.build_module`); the kit looks for the part number
    (export-data.js partNumber, then moduleTypePath), then the name (#1025)."""
    model = str((entry.get("attrs") or {}).get("model") or entry["name"]).replace("/", "-")
    hits = sorted((EXPORTS / target / "module-types").glob(f"*/{model}.yaml"))
    return yaml.safe_load(hits[0].read_text()) if hits else None


def _bare(name):
    """A written name without its bay token(s): `{module}/1` and Nautobot's
    `{module.parent}/{module}/1` are both `1`."""
    assert MODULE_TOKEN in name, name
    return name.rsplit("}/", 1)[1]


def test_every_module_with_a_fibre_graph_that_projects_publishes_its_ports():
    idx = _index()
    with_ends = [e for e in idx if (e.get("optical") or {}).get("ends")]
    with_ports = [e for e in idx if (e.get("optical") or {}).get("ports")]
    assert len(with_ports) >= 60, f"only {len(with_ports)} modules publish optical.ports"
    # the gate is the exporter's own: a type file has fibre ports exactly where the index names them
    for e in with_ends:
        doc = _type_file("netbox", e)
        if doc is None:
            continue
        has = bool(doc.get("front-ports") or doc.get("rear-ports"))
        assert has == bool(e["optical"].get("ports")), f"{e['ns']}/{e['name']}"


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
def test_the_published_names_are_the_committed_type_files_names(target):
    checked = names = 0
    bare = []
    for e in _index():
        ports = (e.get("optical") or {}).get("ports")
        if not ports:
            continue
        doc = _type_file(target, e)
        if doc is None:
            continue
        ref = f"{e['ns']}/{e['name']}"
        listed = {s: {_bare(r["name"]) for r in doc.get(s) or []} for s in SECTIONS}
        published = {s: set() for s in SECTIONS}
        for part, lists in ports.items():
            assert set(lists) <= set(SECTIONS), f"{ref} {part}: {sorted(lists)}"
            for section, row in lists.items():
                published[section] |= {n for n in row if n is not None}
        if target == "nautobot" and not (listed["front-ports"] or listed["rear-ports"]):
            bare.append(ref)   # Nautobot was given this type without its glass (for_target); the kit leaves such a cable out
            continue
        for section in SECTIONS:
            assert published[section] == listed[section], \
                f"{ref}: {section} published {sorted(published[section] ^ listed[section])} differently from the {target} file"
            names += len(listed[section])
        checked += 1
    # two couplers and two add/drop filters: a split has no Nautobot spelling
    assert len(bare) == (4 if target == "nautobot" else 0), bare
    assert checked >= (59 if target == "nautobot" else 63) and names >= 900, \
        f"measured too little: {checked} types, {names} names"


def test_the_panel_and_a_cassette_by_hand():
    """Read off the committed files, not off the function under test."""
    by = {f"{e['ns']}/{e['name']}": e for e in _index()}
    panel = by["fs/fhd-fap12lcd-os2"]["optical"]["ports"]
    assert panel["lc01"] == {"front-ports": ["1", "2"]}
    assert panel["lc12"] == {"front-ports": ["23", "24"]}
    assert panel["rear:b01"] == {"rear-ports": ["B01-1", "B01-1"]}
    assert panel["rear:b12"] == {"rear-ports": ["B12-1", "B12-1"]}
    cassette = by["fs/fhd-1mtp6lcd-os2-a"]["optical"]["ports"]
    assert cassette["lc6"] == {"front-ports": ["11", "12"]}
    assert cassette["rear:mtp"] == {"rear-ports": ["MTP-1"] * 12}
    # an MPO front is one port with a position a fibre, not twelve ports
    assert by["fs/fhd-fap12mtp-a"]["optical"]["ports"]["mtp02"] == {"front-ports": ["2"] * 12}
    # a stated trunk position is a rear port, and the rest of its adapter a front one
    assert by["smartoptics/ppm-dcm-10"]["optical"]["ports"]["dcm"] == \
        {"front-ports": ["1", None], "rear-ports": [None, "DCM-1"]}


def test_ports_and_part_ports_are_one_walk():
    """`ports` writes the type file and `part_ports` the index; every name of
    one is a name of the other, with as many positions."""
    from portrayal import libwalk
    load_ref = lambda ref: libwalk.load_contract(ref, [str(ROOT / "library")])  # noqa: E731
    seen = 0
    for e in _index():
        if not (e.get("optical") or {}).get("ports"):
            continue
        data = load_ref(f"{e['ns']}/{e['name']}@{str(e['major']).lstrip('v')}")
        rows = optical_ports.ports(data, load_ref)
        by_part = optical_ports.part_ports(data, load_ref)
        assert by_part == e["optical"]["ports"]
        for section, key in (("front-ports", "front"), ("rear-ports", "rear")):
            count = {}
            for lists in by_part.values():
                for n in lists.get(section) or []:
                    if n is not None:
                        count[n] = count.get(n, 0) + 1
            assert count == {r["name"]: r["positions"] for r in rows[key]}, f"{e['ns']}/{e['name']} {section}"
        seen += 1
    assert seen >= 60


@pytest.mark.heavy
def test_the_kit_writes_the_committed_names():
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    p = subprocess.run(["node", "--test", str(JS)], capture_output=True, text=True, cwd=str(JS.parent),
                       env={**os.environ, "PORTRAYAL_COMPONENTS": str(onebuild.components_index())})
    assert p.returncode == 0, p.stdout[-6000:] + p.stderr[-2000:]
