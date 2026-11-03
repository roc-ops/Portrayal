"""A power cord can be addressed to a NEMA outlet and to an Eaton C39 (#1045).

docs/connectors-power-design.md section 9. Three things, each read from the
real library:

1. `mates` is one interface or a list, and every reader takes both
   (manifest.mates_of). A contract that states one interface reads as before.
2. `std/nema-5-20r@1` and `eaton/c39-outlet@1` present an interface, so each
   outlet of a PDU is a connector slot that offers its cord ends.
3. Making an outlet a slot moves nothing a DCIM imports: the same outlets, by
   the same names, of the same types.
"""
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

from portrayal import dcim_export as dx
from portrayal import lint
from portrayal import render as render_mod
from portrayal.manifest import mates_of
from test_coax_slots import _device_slot

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
COMP = LIB / "components"
SVG = "{http://www.w3.org/2000/svg}"

CORD_15, CORD_20 = "generic/nema-5-15p-cord@1", "generic/nema-5-20p-cord@1"
C14, C20 = "generic/c14-plug@1", "generic/c20-plug@1"
# what each cord end mates, in the order its contract states it
MATES = {CORD_15: ["nema-5-15r", "nema-5-20r"], CORD_20: ["nema-5-20r"],
         C14: ["iec-c13", "eaton-c39"], C20: ["iec-c19", "eaton-c39"]}
# what each interface is offered, the accept list a slot publishes
OFFERED = {"nema-5-15r": [CORD_15], "nema-5-20r": [CORD_15, CORD_20],
           "eaton-c39": [C14, C20], "iec-c13": [C14], "iec-c19": [C20]}


def contract(ref):
    ns_name, major = ref.split("@")
    return yaml.safe_load((COMP / ns_name / f"v{major}" / "contract.yaml").read_text())


def skin(ref):
    ns_name, major = ref.split("@")
    return ET.parse(COMP / ns_name / f"v{major}" / "skins/default.svg").getroot()


def std():
    return yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())["standards"]


# --- 1. `mates` is one interface or a list ------------------------------------

def test_mates_of_reads_both_shapes():
    assert mates_of({"mates": "sfp"}) == ["sfp"]
    assert mates_of({"mates": ["nema-5-15r", "nema-5-20r"]}) == ["nema-5-15r", "nema-5-20r"]
    assert mates_of({}) == [] and mates_of({"mates": None}) == [] and mates_of(None) == []


def test_the_schema_takes_one_interface_or_a_list_and_no_other_shape():
    import jsonschema
    schema = json.loads((ROOT / "spec/schemas/component.schema.json").read_text())
    sub = {**schema["properties"]["mates"], "$defs": schema["$defs"]}
    ok = jsonschema.Draft202012Validator(sub).is_valid
    assert ok("iec-c13") and ok(["iec-c13", "eaton-c39"]) and ok(["iec-c13"])
    assert not ok([]) and not ok(["iec-c13", "iec-c13"]) and not ok(["Not An Interface"])
    assert not ok({"interface": "iec-c13"}) and not ok(13)


@pytest.mark.parametrize("ref", sorted(MATES))
def test_each_cord_end_mates_what_it_should(ref):
    assert mates_of(contract(ref)) == MATES[ref]
    # one interface is written as one interface, never as a one-item list
    assert isinstance(contract(ref)["mates"], list) == (len(MATES[ref]) > 1)


def test_every_interface_a_part_mates_is_one_something_registers():
    """NON-VACUOUS: the walk reads every contract; a `mates` list whose second
    item is a typo would otherwise offer the part to nothing, silently."""
    fams = {f.get("interface") for f in render_mod._pluggable_families().values()}
    reg = set(render_mod._connector_registry())
    listed, seen = 0, 0
    for cf in sorted(COMP.glob("*/*/v*/contract.yaml")):
        c = yaml.safe_load(cf.read_text())
        if isinstance(c.get("mates"), list):
            listed += 1
            for iface in c["mates"]:
                seen += 1
                assert iface in reg or iface in fams, (str(cf), iface)
    assert listed >= 3 and seen >= 6


def test_a_part_that_lists_two_interfaces_is_a_candidate_for_each():
    cands = render_mod._pluggable_candidates([str(LIB)])
    for iface, refs in OFFERED.items():
        assert sorted({r for r, _c in cands.get(iface, [])}) == sorted(refs), iface
    # a part is listed once under each interface, never twice under one
    for iface, rows in cands.items():
        refs = [r for r, _c in rows]
        assert len(refs) == len(set(refs)), iface


def test_a_single_interface_part_is_offered_where_it_was():
    """The other AC cord ends state one interface, and their slots offer what
    they did before `mates` could be a list."""
    cands = render_mod._pluggable_candidates([str(LIB)])
    assert [r for r, _c in cands["iec-c14"]] == ["generic/c13-plug@1"]
    assert [r for r, _c in cands["iec-c20"]] == ["generic/c19-plug@1"]
    assert "generic/rj45-plug@1" in [r for r, _c in cands["rj45"]]


def test_lint_seats_a_listed_plug_in_either_receptacle_and_in_no_other(capsys):
    """L12 through the one check both `mate-to` and `occupants:` call."""
    def said(host, occ):
        found = []
        orig = lint.err
        lint.err = lambda path, code, msg, *a, **k: found.append((code, msg))
        try:
            lint._mate_check("x.yaml", "front/p", occ, host, [str(LIB)])
        finally:
            lint.err = orig
        return found

    assert said("std/nema-5-20r@1", CORD_15) == []
    assert said("std/nema-5-20r@1", CORD_20) == []
    assert said("eaton/c39-outlet@1", C14) == [] and said("eaton/c39-outlet@1", C20) == []
    assert said("std/c13-outlet@1", C14) == [] and said("std/c19-outlet@1", C20) == []
    # and the pairs that do not fit are still refused, naming what was stated
    wrong = said("std/nema-5-20r@1", C14)
    assert [c for c, _m in wrong] == ["L12"] and "nema-5-20r" in wrong[0][1]
    assert [c for c, _m in said("std/c13-outlet@1", C20)] == ["L12"]
    assert [c for c, _m in said("std/c19-outlet@1", CORD_15)] == ["L12"]


def test_the_catalogue_column_reads_a_list_as_text():
    from portrayal import components_catalogue as cat
    assert cat.fits({"mates": ["iec-c13", "eaton-c39"]}) == "iec-c13, eaton-c39"
    assert cat.fits({"mates": "sfp"}) == "sfp"
    assert cat.fits({"conforms": "x", "mates": ["a", "b"]}) == "x" and cat.fits({}) == ""


def test_mount_points_order_a_list_beside_a_string():
    """`mount-points` publishes `mates` as stated; a part that listed two must
    sort beside one that states one."""
    rows = [{"mates": ["b", "a"], "at": 1.0}, {"mates": "pdu-button", "at": 1.0}]
    got = sorted(rows, key=lambda m: (m["at"], render_mod._interface_text(m["mates"])))
    assert [type(m["mates"]) for m in got] == [list, str]


# --- 2. the outlets are slots --------------------------------------------------

@pytest.mark.parametrize("iface,ref", [("nema-5-20r", "std/nema-5-20r@1"),
                                        ("eaton-c39", "eaton/c39-outlet@1")])
def test_the_outlet_presents_a_registered_interface_at_a_mate_point(iface, ref):
    reg = render_mod._connector_registry()
    assert iface in reg and "nema-5-15r" in reg
    c = contract(ref)
    assert c["interface"] == iface and c["class"] == "inlet" and "mates" not in c
    mate = c["connection-points"]["mate"]["at"]
    assert 0 < mate[0] < c["size"]["w"] and 0 < mate[1] < c["size"]["h"]
    assert "NO `interface:` YET" not in c["provenance"]["interface"]


def test_the_5_20r_mate_is_on_its_own_blade_pattern():
    """The earth axis, at the line of the two blades, read off the skin."""
    root = skin("std/nema-5-20r@1")
    by = {e.get("id"): e for e in root.iter() if e.get("id")}
    line = by["slot-line"]
    blade_y = float(line.get("y")) + float(line.get("height")) / 2
    earth = [float(v) for v in by["hole-earth"].get("d").replace("M", "").split("H")[0].split()]
    earth_x = (earth[0] + 13.53) / 2
    mx, my = contract("std/nema-5-20r@1")["connection-points"]["mate"]["at"]
    assert mx == pytest.approx(earth_x, abs=0.01) and my == pytest.approx(blade_y, abs=0.05)
    # 6.35 either side of the earth axis is where a 5-15P's blades go
    assert float(line.get("x")) + float(line.get("width")) / 2 == pytest.approx(mx - 6.35, abs=0.05)


PDUS = {
    # device: (view, a placement, its interface, how many outlets of that interface the unit has)
    "eaton/pdumh20net": [("front", "outlet-1", "nema-5-20r"), ("rear", "outlet-9", "nema-5-20r")],
    "eaton/evmi2130x": [("front", "outlet-a2", "eaton-c39")],
    "eaton/evma8365x": [("front", "outlet-a2", "eaton-c39")],
}


@pytest.mark.heavy
@pytest.mark.parametrize("device", sorted(PDUS))
def test_each_outlet_of_the_pdu_is_a_slot_that_offers_its_cord_ends(device, tmp_path):
    d = yaml.safe_load((LIB / "devices" / device / "device.yaml").read_text())
    for view, pid, iface in PDUS[device]:
        slot = _device_slot(device, view, pid, tmp_path)
        assert slot["kind"] == "connector" and slot["interface"] == iface, slot
        assert slot["accepts"] == OFFERED[iface], slot
        assert slot["default"] is None and slot["occupant"] is None, slot
    # EVERY placed outlet of the two parts, on every view, not the sample alone
    from test_coax_slots import _device_configs
    cfg = _device_configs(device, tmp_path)
    slots = {(v, c["id"]): c for v, cs in cfg["cages"].items() for c in cs}
    placed = [(v, p["id"], p["ref"]) for v, view in d["views"].items()
              for p in ((view or {}).get("components") or {}).get("placements") or []
              if p["ref"] in ("std/nema-5-20r@1", "eaton/c39-outlet@1")]
    assert len(placed) >= 16, device
    for v, pid, ref in placed:
        assert slots[(v, pid)]["interface"] == contract(ref)["interface"], (device, v, pid)


@pytest.mark.parametrize("ref", ["std/c13-outlet@1", "std/c19-outlet@1",
                                 "std/nema-5-20r@1", "eaton/c39-outlet@1"])
def test_an_ac_outlet_says_outlet_and_ac(ref):
    """`outlet` is which way power runs; `media: ac` is what tells an AC outlet
    from a DC terminal. The inlets state `input: ac` and `media: ac`."""
    a = contract(ref)["attrs"]
    assert a["outlet"] and a["media"] == "ac" and "input" not in a


def test_no_power_receptacle_of_an_ac_interface_is_silent_about_ac():
    """NON-VACUOUS census over every part presenting an AC power interface."""
    ac = {"iec-c13", "iec-c14", "iec-c19", "iec-c20", "saf-d-grid", "nema-5-20r", "eaton-c39"}
    seen = 0
    for cf in sorted(COMP.glob("*/*/v*/contract.yaml")):
        c = yaml.safe_load(cf.read_text())
        if c.get("interface") in ac:
            seen += 1
            a = c.get("attrs") or {}
            assert a.get("media") == "ac", str(cf)
            assert bool(a.get("outlet")) != bool(a.get("input")), str(cf)
    assert seen >= 7


# --- 3. the two cord ends ------------------------------------------------------

EACH = pytest.mark.parametrize("ref", [CORD_15, CORD_20])


@EACH
def test_it_is_a_cord_end_like_the_iec_ones(ref):
    d = contract(ref)
    assert d["class"] == "port" and "behaviour" not in d and "interface" not in d
    assert "d" not in d["size"]
    name = ref.split("/")[1].split("@")[0]
    entry = std()[d["conforms"]]
    assert d["conforms"] == name
    assert (d["size"]["w"], d["size"]["h"]) == (entry["w"], entry["h"])
    assert set(d["fields"]) == {"cable-od", "jacket-color"}
    assert d["connection-points"]["cable"]["on"] == "stub"
    assert d["elements"] == {}


def test_the_ratings_put_the_15_a_plug_first():
    """A reader that orders the plugs of a 5-20R by `rating-a` offers the
    5-15P first; both state a number."""
    r15, r20 = contract(CORD_15)["attrs"]["rating-a"], contract(CORD_20)["attrs"]["rating-a"]
    assert (r15, r20) == (15, 20)
    assert sorted(OFFERED["nema-5-20r"], key=lambda r: contract(r)["attrs"]["rating-a"])[0] == CORD_15


@EACH
def test_the_solids_chain_from_the_receptacle_face_to_the_stub(ref):
    d = contract(ref)
    feats = d["relief"]["features"]
    at = 0.0
    for f in feats:
        assert f.get("lift", 0.0) == pytest.approx(at), (ref, f["node"])
        at = f["out"] if "out" in f else f.get("lift", 0.0) + f["cyl"]
    stub = feats[-1]
    assert stub["node"] == "stub" and stub["cyl"] == 30
    # the stub starts at the overall length, the face of the plug being on the
    # face of the receptacle
    assert stub["lift"] == pytest.approx(std()[d["conforms"]]["depth"])


@EACH
def test_the_skin_has_every_relief_node_and_binds_the_stub(ref):
    d, root = contract(ref), skin(ref)
    by = {e.get("id"): e for e in root.iter() if e.get("id")}
    assert {f["node"] for f in d["relief"]["features"]} <= set(by)
    stub = by["stub"]
    assert stub.tag == f"{SVG}circle"
    assert stub.get("data-r-from") == "cable-od" and stub.get("data-fill-from") == "jacket-color"
    assert float(stub.get("r")) == pytest.approx(d["fields"]["cable-od"]["default"] / 2)
    cx, cy = d["connection-points"]["cable"]["at"]
    assert (float(stub.get("cx")), float(stub.get("cy"))) == (cx, cy)
    # nothing drawn is a contact, a mark or text: it is seen from the cable
    assert not [e for e in root.iter() if e.tag in (f"{SVG}text", f"{SVG}image")]


@EACH
def test_every_part_behind_the_front_stays_inside_the_front_outline(ref):
    """The rear step, the strain relief and the cord are inside the box of the
    moulding, so no solid stands beside the part it belongs to."""
    d, root = contract(ref), skin(ref)
    w, h = d["size"]["w"], d["size"]["h"]
    for e in root.iter():
        if e.tag == f"{SVG}rect":
            x, y = float(e.get("x")), float(e.get("y"))
            assert 0 <= x and 0 <= y and x + float(e.get("width")) <= w and y + float(e.get("height")) <= h
        if e.tag == f"{SVG}circle":
            cx, cy, r = (float(e.get(k)) for k in ("cx", "cy", "r"))
            assert r <= cx <= w - r and r <= cy <= h - r, (ref, e.get("id"))


def test_the_cord_ends_differ_from_the_face_on_input_plug_and_say_so():
    face = contract("generic/nema-5-20p-plug@1")
    assert face["class"] == "inlet" and "mates" not in face and "interface" not in face
    assert dx.PART_POWER["generic/nema-5-20p-plug"] == "nema-5-20p"
    for ref in (CORD_15, CORD_20):
        d = contract(ref)
        assert "generic/nema-5-20p-plug@1" in d["provenance"]["not-the-input-plug"]
        assert ref.split("@")[0] not in dx.PART_POWER and ref.split("@")[0] not in dx.PART_OUTLET


# --- 4. nothing a DCIM imports has moved ---------------------------------------

EXPORTED = {
    "PDUMH20NET": [(str(n), "nema-5-20r") for n in range(1, 17)],
}


@pytest.mark.parametrize("target", ["netbox", "nautobot"])
def test_the_pdumh20net_exports_the_outlets_it_did(target):
    """A slotted outlet is still a power outlet, by its printed name: no
    interface row, no module bay, no front or rear port for it."""
    p = LIB / "exports" / target / "device-types/Eaton/PDUMH20NET.yaml"
    if not p.exists():
        pytest.skip("library/exports not built")
    doc = yaml.safe_load(p.read_text())
    assert [(o["name"], o["type"]) for o in doc["power-outlets"]] == EXPORTED["PDUMH20NET"]
    assert all(o["power_port"] == "input" for o in doc["power-outlets"])
    assert [b["name"] for b in doc["module-bays"]] == ["card"]
    for key in ("interfaces", "front-ports", "rear-ports", "console-ports"):
        assert not doc.get(key), key


@pytest.mark.parametrize("model,c39,c13", [("EVMI2130X", 18, 24), ("EVMA8365X", 18, 24)])
def test_the_g4_pdus_export_their_c39_outlets_as_outlets(model, c39, c13):
    p = LIB / "exports/netbox/device-types/Eaton" / f"{model}.yaml"
    if not p.exists():
        pytest.skip("library/exports not built")
    doc = yaml.safe_load(p.read_text())
    types = [o["type"] for o in doc["power-outlets"]]
    assert types.count("eaton-c39") == c39 and types.count("iec-60320-c13") == c13
    assert not doc.get("interfaces") or all("outlet" not in i["name"].lower() for i in doc["interfaces"])
    bays = [b["name"] for b in doc.get("module-bays") or []]
    assert not any(b.lower().startswith("outlet") for b in bays)


# --- 5. the built elements say what they are, however they are placed ----------

AC_INTERFACES = {"iec-c13", "iec-c14", "iec-c19", "iec-c20", "saf-d-grid", "nema-5-20r", "eaton-c39"}


def _ac_parts():
    """ref -> `outlet` or `input`, for every part presenting an AC interface."""
    out = {}
    for cf in sorted(COMP.glob("*/*/v*/contract.yaml")):
        c = yaml.safe_load(cf.read_text())
        if c.get("interface") in AC_INTERFACES:
            ns, name, v = cf.parts[-4:-1]
            out[f"{ns}/{name}@{v[1:]}"] = "outlet" if (c.get("attrs") or {}).get("outlet") else "input"
    return out


def _power_elements(svg_path, parts):
    """(ref, marker, element attributes) for each built element of an AC part."""
    for e in ET.parse(svg_path).getroot().iter(f"{SVG}g"):
        ref = (e.get("data-ref") or "").split(":")[0]
        if ref in parts:
            yield ref, parts[ref], e.attrib


@pytest.mark.heavy
def test_every_built_ac_outlet_and_inlet_element_says_what_it_is():
    """THE BUILD, NOT THE CONTRACT: a reader of a drawing holds the element.
    Every element of an AC outlet part on every built face carries
    `data-outlet` and `data-media="ac"`, and every element of an AC inlet part
    carries `data-input="ac"`, whether it is a bare placement, a placement in
    a group or a part of a supply seated in a bay. AN INLET'S AC FACT IS ITS
    `data-input`: two Edgecore placements restate `media` as the connector
    (`c14`) over the part's `ac`, and still say `input: ac`."""
    dist = LIB / "dist"
    faces = [p for p in sorted(dist.glob("*.svg")) if ".base." not in p.name] if dist.is_dir() else []
    if not faces:
        pytest.skip("library/dist not built")
    parts = _ac_parts()
    assert set(parts.values()) == {"outlet", "input"}
    seen = {"outlet": 0, "input": 0}
    under_module = 0
    for f in faces:
        for ref, marker, attrib in _power_elements(f, parts):
            seen[marker] += 1
            under_module += "/module/" in attrib.get("data-path", "")
            assert attrib.get(f"data-{marker}"), (f.name, attrib.get("data-path"), ref, marker)
            fact = "data-media" if marker == "outlet" else "data-input"
            assert attrib.get(fact) == "ac", (f.name, attrib.get("data-path"), ref)
    # the walk measured the library: 124 outlets on the four Eaton PDUs, and
    # the inlets of every AC supply, nearly all of them under a module
    assert seen["outlet"] >= 124 and seen["input"] >= 600 and under_module >= 600, (seen, under_module)


@pytest.mark.heavy
def test_a_mixed_group_of_outlets_drops_neither_fact(tmp_path):
    """A `mixed` group states no attrs, so nothing of the group says `outlet`;
    the element must still say it, from its part. Built: the PDUMH20NET with
    its outlet group made a mixed one."""
    import shutil
    import sys
    import warmrender
    from portrayal.artifacts import face_file
    dev = tmp_path / "pdumh20net" / "device.yaml"
    shutil.copytree(LIB / "devices/eaton/pdumh20net", dev.parent)
    d = yaml.safe_load(dev.read_text())
    g = d["groups"]["outlets"]
    assert g.pop("attrs") == {"outlet": "nema-5-20r"}
    g["mixed"] = "outlets of more than one kind, for this test"
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    out = tmp_path / "o"
    r = warmrender.run([sys.executable, str(ROOT / "spec/tools/portrayal/render.py"), str(dev),
                        "--library", str(LIB), "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    parts, n = _ac_parts(), 0
    for view in ("front", "rear"):
        for ref, marker, attrib in _power_elements(face_file(out, "pdumh20net", "base", view), parts):
            n += 1
            assert attrib.get("data-outlet") == "nema-5-20r" and attrib.get("data-media") == "ac", attrib
    assert n == 16
