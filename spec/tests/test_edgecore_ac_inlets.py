"""The power inlet of the Edgecore AMX3200, COR550 and DCS500 AC supplies is a place a power cord lands.

Each supply used to draw its IEC C14 inlet as art in its skin, so it offered no place for a cord. Each now composes the library's
std/c14-inlet@1 as the part `inlet`, standing where the drawn inlet stood and turned as the vendor's guide shows the supply's
inlet (the place and the turn are estimates, read off pictures, and each contract says so):

  - the drawn `inlet` element and its group in the skin are gone, and no other element or id of the supply went;
  - the build publishes one connector `inlet` that presents iec-c14 and accepts the C13 plug;
  - the COR550 supply stands its inlet behind the skin and knocks the skin's body out where it stands, because the vendor's
    elevations show the red release latch in front of the inlet;
  - a part's id is lower case, so the exported power port of each supply, `{module}/Inlet` before, is `{module}/inlet` in both
    module-type files of each supply, and nothing else in those files moves but the contract version the comment names.

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

INLET = "std/c14-inlet@1"
PLUG = "generic/c13-plug@1"

# supply -> where its inlet part stands and how it is turned, its elements after the change, its module type's model and the device
# that seats it with the lowest version that carries the change
SUPPLIES = {
    "edgecore/amx-3200-ac-psu@1": dict(at=[6.3, 12.55], rotate=90, behind=False, elements=["fan", "handle", "latch", "status"],
                                       model="AMX-3200-AC-PSU", device="amx3200", device_version=(1, 0, 9), skin_ids=["body", "fan", "handle", "latch", "status"]),
    "edgecore/cor550-psu-ac@1": dict(at=[26.1, 8.15], rotate=270, behind=True, elements=["handle", "latch", "vent"],
                                     model="cor550-psu-ac", device="cor550", device_version=(3, 2, 1), skin_ids=["body", "handle", "latch", "vent"]),
    "edgecore/dcs500-psu-ac@1": dict(at=[0.8, 8.3], rotate=90, behind=False, elements=["handle", "latch", "vent"],
                                     model="dcs500-psu-ac", device="dcs500", device_version=(4, 2, 1), skin_ids=["body", "handle", "latch", "vent"]),
}
DRAWN_BEFORE = {  # the box each drawn inlet had, which the part's own centre is taken from
    "edgecore/amx-3200-ac-psu@1": [10.6, 8.3, 18.8, 28.5],
    "edgecore/cor550-psu-ac@1": [31.6, 5.7, 17.0, 24.9],
    "edgecore/dcs500-psu-ac@1": [6.2, 4.6, 17.2, 27.4],
}
SVG = "{http://www.w3.org/2000/svg}"


def path_of(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return LIB / "components" / ns / part / f"v{major}"


def contract(ref):
    return yaml.safe_load((path_of(ref) / "contract.yaml").read_text())


def skin(ref):
    return ET.parse(path_of(ref) / "skins" / "default.svg").getroot()


def version(text):
    return tuple(int(n) for n in text.split("."))


@pytest.fixture(scope="module")
def index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_supply_composes_the_c14_inlet_once_as_inlet_where_the_drawn_inlet_stood(ref):
    want = SUPPLIES[ref]
    parts = contract(ref)["parts"]
    assert len(parts) == 1
    assert parts[0]["ref"] == INLET and parts[0]["id"] == "inlet"
    assert parts[0]["at"] == want["at"] and parts[0]["rotate"] == want["rotate"]
    assert bool(parts[0].get("behind")) == want["behind"]
    # the part's own box is 28.0 x 20.0 before it is turned, and a quarter turn keeps its centre: it stands on the drawn inlet's centre
    # (the AMX3200's is moved 0.3 mm to the right so that it does not cover the latch's edge)
    x, y, w, h = DRAWN_BEFORE[ref]
    cx, cy = parts[0]["at"][0] + 14.0, parts[0]["at"][1] + 10.0
    assert abs(cy - (y + h / 2)) < 0.01
    assert abs(cx - (x + w / 2)) < (0.31 if ref.startswith("edgecore/amx") else 0.01)


@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_drawn_inlet_is_gone_from_the_contract_and_the_skin_and_no_other_element_went(ref):
    want = SUPPLIES[ref]
    d = contract(ref)
    assert sorted(d["elements"]) == want["elements"]
    assert "inlet" not in d["elements"]
    ids = sorted(e.get("id") for e in skin(ref).iter() if e.get("id"))
    assert "inlet" not in ids
    assert sorted(i for i in ids if i in want["skin_ids"]) == want["skin_ids"]
    assert d["version"] == "1.1.0" and d["attrs"]["inlet"] == "c14" and d["attrs"]["input"] == "ac"


@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_place_and_the_turn_are_said_to_be_estimates_read_off_a_guide_figure(ref):
    text = " ".join(contract(ref)["provenance"]["inlet-part"].split())
    assert text.startswith("COMPOSED, NOT DRAWN") and "ESTIMATED" in text and len(text) >= 400
    assert "Quick Start" in text or "quick start" in text or "datasheet" in text
    assert re.search(r"turned (90|270)\b", text) and str(SUPPLIES[ref]["rotate"]) in text


def test_the_cor550_supply_stands_its_inlet_behind_the_skin_and_the_body_is_knocked_out_where_it_stands():
    root = skin("edgecore/cor550-psu-ac@1")
    body = next(e for e in root.iter() if e.get("id") == "body")
    assert body.tag == f"{SVG}path" and body.get("fill-rule") == "evenodd"
    assert body.get("d").count("M") == 2 and "H33.10 a3 3" in body.get("d")
    assert [e.get("id") for e in root if e.tag == f"{SVG}g"] == ["vent", "handle", "latch"]
    for ref in ("edgecore/amx-3200-ac-psu@1", "edgecore/dcs500-psu-ac@1"):
        assert next(e for e in skin(ref).iter() if e.get("id") == "body").tag == f"{SVG}rect"


@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_build_publishes_one_c14_connector_named_inlet_that_accepts_the_c13_plug(index, ref):
    want = SUPPLIES[ref]
    cages = index[ref]["cages"]
    assert [(c["id"], c["kind"], c["interface"], c["accepts"], c["rotate"]) for c in cages] == [
        ("inlet", "connector", "iec-c14", [PLUG], want["rotate"])]
    assert cages[0]["at"] == want["at"]


@pytest.mark.parametrize("ref", SUPPLIES)
@pytest.mark.parametrize("flavour", ["netbox", "nautobot"])
def test_the_exported_module_type_names_its_power_port_in_lower_case_and_says_the_new_contract_version(ref, flavour):
    want = SUPPLIES[ref]
    text = (LIB / "exports" / flavour / "module-types" / "Edgecore" / f"{want['model']}.yaml").read_text()
    assert "- name: '{module}/inlet'\n    type: iec-60320-c14\n" in text
    assert "/Inlet" not in text
    assert f"Contract version 1.1.0 ({ref.split('@')[0]})." in text
    assert text.count("power-ports:") == 1


@pytest.mark.parametrize("ref", SUPPLIES)
def test_the_device_that_seats_the_supply_took_a_patch_and_its_lock_agrees(ref):
    from portrayal import devicelock

    want = SUPPLIES[ref]
    folder = LIB / "devices" / "edgecore" / want["device"]
    for name in ("layout.yaml", "device.yaml"):
        assert version(yaml.safe_load((folder / name).read_text())["version"]) >= want["device_version"], (want["device"], name)
    assert [f for f in devicelock.check(LIB) if f[0] in (want["device"], ref.split("/")[1].split("@")[0])] == []


def test_the_findings_this_change_closes_have_no_row_left_and_the_48v_supply_of_the_amx3200_keeps_its_own():
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    for ref in SUPPLIES:
        assert [r for r in rows if r["part"] == ref and r["code"] == "C19"] == []
    assert len([r for r in rows if r["part"] == "edgecore/amx-3200-48v-psu@1" and r["code"] == "C19"]) == 1
