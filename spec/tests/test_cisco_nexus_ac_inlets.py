"""The power inlets of the Cisco Nexus 9500 supplies N9K-PAC-3000W-B, N9K-PUV-3000W-B and N9K-PUV2-3000W-B are places a power cord lands.

Each supply used to draw its inlet as art in its skin, so it offered no place for a cord. Each now composes the library's own inlet part,
standing where the drawn inlet stood and turned as the vendor's guides show the supply (the place and the turn are estimates, read off
pictures, and each contract says so):

  - the N9K-PAC-3000W-B composes std/c20-inlet@1 as the part `inlet` and publishes one connector that presents iec-c20 and accepts the
    C19 plug;
  - the N9K-PUV-3000W-B composes std/saf-d-grid@1 as the part `inlet` and publishes one connector that presents saf-d-grid and accepts the
    Saf-D-Grid plug;
  - the N9K-PUV2-3000W-B composes std/saf-d-grid@1 twice, as `inlet-1` above `inlet-2`, standing clear of each other, of the vent above and
    of the power switch below; its skin's vent is 2.4 shorter than the other two supplies' for that;
  - the drawn receptacles are gone from the skins and no other element or id of a supply went; the two Saf-D-Grid supplies no longer say
    `inlet: other`, which a composed part makes the weaker of two statements;
  - a part's id is lower case, so the exported power ports change with them: `{module}/Inlet` is `{module}/inlet` for the first two
    supplies, with the type `saf-d-grid` where it was `other` for the second, and the third's one port is two, `{module}/inlet-1` and
    `{module}/inlet-2`, both `saf-d-grid`; nothing else in the six module-type files moves but the contract version the comment names.

These run against the real library, a components index built by the indexer the build runs, the committed exports and the records
file. They read no library/dist and render nothing.
"""
import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

import onebuild

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SVG = "{http://www.w3.org/2000/svg}"

C20, SAF = "std/c20-inlet@1", "std/saf-d-grid@1"
C19_PLUG, SAF_PLUG = "generic/c19-plug@1", "generic/saf-d-grid-plug@1"

# supply -> its parts after the change (id, ref, at, rotate), the interface and plug each presents and takes, the module type's file name, its
# power ports in the export, the skin ids that stay, and the devices that seat it with the lowest version that carries the change
SUPPLIES = {
    "cisco/n9k-pac-3000w-b@1": dict(
        parts=[("inlet", C20, [6.05, 84.8])], interface="iec-c20", plug=C19_PLUG, model="N9K-PAC-3000W-B",
        ports=[("{module}/inlet", "iec-60320-c20")], skin_ids=["fail", "handle", "ok", "plate", "screw-bot", "vent"]),
    "cisco/n9k-puv-3000w-b@1": dict(
        parts=[("inlet", SAF, [8.85, 79.05])], interface="saf-d-grid", plug=SAF_PLUG, model="N9K-PUV-3000W-B",
        ports=[("{module}/inlet", "saf-d-grid")], skin_ids=["fail", "handle", "ok", "plate", "screw-bot", "switch", "vent"]),
    "cisco/n9k-puv2-3000w-b@1": dict(
        parts=[("inlet-1", SAF, [8.85, 61.85]), ("inlet-2", SAF, [8.85, 89.25])], interface="saf-d-grid", plug=SAF_PLUG, model="N9K-PUV2-3000W-B",
        ports=[("{module}/inlet-1", "saf-d-grid"), ("{module}/inlet-2", "saf-d-grid")],
        skin_ids=["fail", "handle", "ok", "plate", "screw-bot", "switch", "vent"]),
}
DEVICES = {"n9k-c9504": (2, 1, 1), "n9k-c9508": (1, 1, 1), "n9k-c9516": (2, 1, 1)}   # the lowest version of each that carries the change
# the box each drawn inlet had in its skin (x, y, width, height), which the part's own centre is taken from; the dual input supply's two
# boxes were 24.0 apart and the parts, 26.8 tall once turned, cannot stand on both centres
DRAWN_BEFORE = {
    "cisco/n9k-pac-3000w-b@1": [[6.0, 76.0, 32.5, 42.0]],
    "cisco/n9k-puv-3000w-b@1": [[8.0, 76.0, 28.5, 26.0]],
    "cisco/n9k-puv2-3000w-b@1": [[8.0, 66.0, 28.5, 20.0], [8.0, 90.0, 28.5, 20.0]],
}


def path_of(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return LIB / "components" / ns / part / f"v{major}"


def contract(ref):
    return yaml.safe_load((path_of(ref) / "contract.yaml").read_text())


def skin(ref):
    return ET.parse(path_of(ref) / "skins" / "default.svg").getroot()


def box(ref, part):
    """(left, top, right, bottom) of a composed part once turned a quarter about its centre, in the module's own millimetres."""
    size = contract(part[1])["size"]
    w, h = size["w"], size["h"]
    cx, cy = part[2][0] + w / 2, part[2][1] + h / 2
    return cx - h / 2, cy - w / 2, cx + h / 2, cy + w / 2


def version(text):
    return tuple(int(n) for n in str(text).split("."))


@pytest.fixture(scope="module")
def index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_supply_composes_its_inlet_parts_turned_90_where_the_drawn_inlet_stood(ref):
    want = SUPPLIES[ref]
    parts = contract(ref)["parts"]
    assert [(p["id"], p["ref"], p["at"]) for p in parts] == [(i, r, a) for i, r, a in want["parts"]]
    assert all(p["rotate"] == 90 and not p.get("behind") for p in parts)
    boxes = [box(ref, (i, r, a)) for i, r, a in want["parts"]]
    drawn = DRAWN_BEFORE[ref]
    if len(boxes) == len(drawn) == 1:
        # one part stands on the centre of the box its drawing had
        (x, y, w, h), (left, top, right, bottom) = drawn[0], boxes[0]
        assert abs((left + right) / 2 - (x + w / 2)) < 0.01 and abs((top + bottom) / 2 - (y + h / 2)) < 0.01
    else:
        # two parts cannot: they stand one above the other on the boxes' common centre line
        assert {round((l + r) / 2, 2) for l, _, r, _ in boxes} == {round(d[0] + d[2] / 2, 2) for d in drawn}


def test_the_two_receptacles_of_the_dual_input_supply_stand_clear_of_each_other_the_vent_and_the_switch():
    ref = "cisco/n9k-puv2-3000w-b@1"
    root = skin(ref)
    vent = next(e for e in root.iter() if e.get("id") == "vent")
    switch = next(e for e in next(g for g in root.iter() if g.get("id") == "switch") if e.tag == f"{SVG}rect")
    vent_bottom = float(vent.get("y")) + float(vent.get("height"))
    switch_top = float(switch.get("y"))
    (l1, t1, r1, b1), (l2, t2, r2, b2) = (box(ref, p) for p in SUPPLIES[ref]["parts"])
    plate = next(e for e in root.iter() if e.get("id") == "plate")
    assert float(vent.get("height")) == 53.6                     # the other two supplies' vents are 56.0
    assert vent_bottom + 0.5 < t1 < b1 < t2 - 0.5 < t2 < b2 < switch_top - 0.3
    assert min(l1, l2) > float(plate.get("x")) and max(r1, r2) < float(plate.get("x")) + float(plate.get("width"))
    for other in ("cisco/n9k-pac-3000w-b@1", "cisco/n9k-puv-3000w-b@1"):
        assert float(next(e for e in skin(other).iter() if e.get("id") == "vent").get("height")) == 56.0


@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_drawn_inlet_is_gone_from_the_skin_and_no_other_element_or_id_went(ref):
    want = SUPPLIES[ref]
    d = contract(ref)
    assert sorted(d["elements"]) == ["fail", "ok"]
    ids = sorted(e.get("id") for e in skin(ref).iter() if e.get("id"))
    assert ids == want["skin_ids"]
    assert d["version"] == "1.1.0" and d["attrs"]["input"] == ("ac" if ref.startswith("cisco/n9k-pac") else "ac-dc")


def test_the_c20_supply_keeps_what_it_declared_and_the_saf_d_grid_supplies_no_longer_say_other():
    assert contract("cisco/n9k-pac-3000w-b@1")["attrs"]["inlet"] == "c20"
    for ref in ("cisco/n9k-puv-3000w-b@1", "cisco/n9k-puv2-3000w-b@1"):
        assert "inlet" not in contract(ref)["attrs"]
    assert contract("cisco/n9k-puv2-3000w-b@1")["attrs"]["inputs"] == 2


@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_place_and_the_turn_are_said_to_be_estimates_read_off_the_guides_figures(ref):
    text = " ".join(contract(ref)["provenance"]["inlet-part"].split())
    assert text.startswith("COMPOSED, NOT DRAWN") and "ESTIMATED" in text and len(text) >= 600
    assert "Hardware Installation Guide" in text and re.search(r"\b90\b", text)
    if ref.startswith("cisco/n9k-puv"):
        assert "NOT SOURCED" in text


@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_build_publishes_one_connector_for_each_inlet_that_accepts_the_matching_plug(index, ref):
    want = SUPPLIES[ref]
    cages = index[ref]["cages"]
    assert [(c["id"], c["kind"], c["interface"], c["accepts"], c["rotate"], c["at"]) for c in cages] == [
        (i, "connector", want["interface"], [want["plug"]], 90, a) for i, _, a in want["parts"]]


@pytest.mark.parametrize("ref", SUPPLIES)
@pytest.mark.parametrize("flavour", ["netbox", "nautobot"])
def test_the_exported_module_type_names_its_power_ports_in_lower_case_and_says_the_new_contract_version(ref, flavour):
    want = SUPPLIES[ref]
    text = (LIB / "exports" / flavour / "module-types" / "Cisco" / f"{want['model']}.yaml").read_text()
    doc = yaml.safe_load(text)
    assert [(p["name"], p["type"]) for p in doc["power-ports"]] == want["ports"]
    assert "/Inlet" not in text and "- inlet:" not in text
    assert f"Contract version 1.1.0 ({ref.split('@')[0]})." in text
    assert text.count("power-ports:") == 1


@pytest.mark.heavy
@pytest.mark.parametrize("device", DEVICES)
def test_the_device_that_seats_the_supplies_took_a_patch_and_its_lock_agrees(device):
    from portrayal import devicelock

    folder = LIB / "devices" / "cisco" / device
    assert not (folder / "layout.yaml").exists()
    assert version(yaml.safe_load((folder / "device.yaml").read_text())["version"]) >= DEVICES[device]
    assert [f for f in devicelock.check(LIB) if f[0] in (device, "cisco/" + device)] == []


def test_the_findings_this_change_closes_have_no_row_left():
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    for ref in SUPPLIES:
        assert [r for r in rows if r["part"] == ref and r["code"] == "C19"] == []
