"""The Juniper MX304 high-voltage AC/DC power supply has an inlet a power cord lands on.

The supply used to draw its inlet as a schematic cutout in its skin, so it offered no place for a cord. It now composes the library's own
Anderson Saf-D-Grid inlet, which the guide names ("an AC anderson inlet", an Anderson cord, "Saf-D-Grid 2007G" printed on the housing in
the cord-connection figure):

  - the supply composes std/saf-d-grid@1 as the part `inlet`, upright and turned 270, inside the face and clear of the fan and the lamp; the
    turn is read off the guide's flat front figure and the place is an estimate scaled from it, and the contract says so;
  - the drawn cutout is gone from the contract and the skin, which now draws only the bezel round the aperture; no other element or id went;
  - the build publishes one connector for the inlet that presents saf-d-grid and accepts the Saf-D-Grid plug;
  - the exported module types gain one power port, `{module}/inlet`, typed saf-d-grid, and say the new contract version; nothing else in
    them moves;
  - the MX304, which seats the supply in its HVAC/DC build, took a patch and its lock agrees.

These run against the real library, a components index built by the indexer the build runs and the committed exports. They read no
library/dist and render nothing.
"""
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

import onebuild

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
SVG = "{http://www.w3.org/2000/svg}"
SUPPLY = "juniper/mx304-psu-hvacdc@1"
PLUG = "generic/saf-d-grid-plug@1"
PART = ("inlet", "std/saf-d-grid@1", [37.3, 8.45])
FOLDER = LIB / "components" / "juniper" / "mx304-psu-hvacdc" / "v1"


def contract(ref):
    name, major = ref.split("@")
    ns, part = name.split("/")
    return yaml.safe_load((LIB / "components" / ns / part / f"v{major}" / "contract.yaml").read_text())


def skin():
    return ET.parse(FOLDER / "skins" / "default.svg").getroot()


def aperture():
    """(left, top, right, bottom) of the composed inlet's aperture once turned a quarter about its centre, in the module's millimetres."""
    size = contract(PART[1])["size"]
    w, h = size["w"], size["h"]
    cx, cy = PART[2][0] + w / 2, PART[2][1] + h / 2
    return cx - h / 2, cy - w / 2, cx + h / 2, cy + w / 2


def version(text):
    return tuple(int(n) for n in str(text).split("."))


@pytest.fixture(scope="module")
def index():
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    return {f"{c['ns']}/{c['name']}@{str(c['major']).lstrip('v')}": c for c in doc["components"]}


def test_the_supply_composes_the_saf_d_grid_inlet_upright_and_turned_270():
    d = contract(SUPPLY)
    assert d["version"] == "1.1.0"
    parts = d["parts"]
    assert [(p["id"], p["ref"], p["at"]) for p in parts] == [PART]
    assert parts[0]["rotate"] == 270 and not parts[0].get("behind")


def test_the_inlet_stands_inside_the_face_clear_of_the_fan_and_the_lamp():
    d = contract(SUPPLY)
    left, top, right, bottom = aperture()
    assert right - left < bottom - top                              # upright: taller than wide
    assert 0 < left and right < d["size"]["w"] and 0 < top and bottom < d["size"]["h"]
    root = skin()
    rotor = next(e for e in root.iter() if e.get("id") == "rotor")
    disc = rotor.find(f"{SVG}circle")
    assert left > float(disc.get("cx")) + float(disc.get("r"))      # right of the fan
    lamp = next(e for e in root.iter() if e.get("id") == "led-status")
    assert float(lamp.get("cx")) + float(lamp.get("r")) < left      # the lamp is left of the aperture
    flange = next(e for e in root.iter() if e.get("id") == "inlet-flange")
    fx, fy, fw, fh = (float(flange.get(k)) for k in ("x", "y", "width", "height"))
    assert (fw, fh) == (24.0, 31.0)                                 # the part's own flange, turned upright
    assert abs(fx + fw / 2 - (left + right) / 2) < 0.01 and abs(fy + fh / 2 - (top + bottom) / 2) < 0.01
    assert fx + fw <= d["size"]["w"] and fy >= 0 and fy + fh <= d["size"]["h"]


def test_the_drawn_cutout_is_gone_and_no_other_element_or_id_went():
    d = contract(SUPPLY)
    assert sorted(d["elements"]) == ["handle"]
    assert not [n for n in d["relief"]["features"] if n["node"] == "hv-inlet"]
    ids = sorted(e.get("id") for e in skin().iter() if e.get("id"))
    assert ids == ["face", "handle", "inlet-flange", "led-status", "rotor"]


def test_the_turn_is_read_off_a_flat_figure_and_the_place_is_said_to_be_an_estimate():
    text = " ".join(contract(SUPPLY)["provenance"]["inlet-part"].split())
    assert text.startswith("COMPOSED, NOT DRAWN") and "ESTIMATED" in text and len(text) >= 600
    assert "std/saf-d-grid@1" in text and "Figure 24" in text and "Figure 57" in text and "270" in text
    assert "hv-inlet" not in " ".join(str(v) for v in contract(SUPPLY)["provenance"].values())
    assert "no std/ part exists" not in " ".join(str(v) for v in contract(SUPPLY)["provenance"].values())


@pytest.mark.heavy
def test_the_build_publishes_one_connector_for_the_inlet_that_accepts_the_saf_d_grid_plug(index):
    cages = index[SUPPLY]["cages"]
    assert [(c["id"], c["kind"], c["interface"], c["accepts"], c["rotate"], c["at"]) for c in cages] == [
        ("inlet", "connector", "saf-d-grid", [PLUG], 270, PART[2])]


@pytest.mark.parametrize("flavour", ["netbox", "nautobot"])
def test_the_exported_module_type_gains_one_power_port_and_says_the_new_contract_version(flavour):
    path = LIB / "exports" / flavour / "module-types" / "Juniper" / "MX304 HVAC-DC PSU.yaml"
    text = path.read_text()
    doc = yaml.safe_load(text)
    assert [(p["name"], p["type"]) for p in doc["power-ports"]] == [("{module}/inlet", "saf-d-grid")]
    assert "Contract version 1.1.0 (juniper/mx304-psu-hvacdc)." in text
    assert "hv-inlet" not in text


@pytest.mark.heavy
def test_the_device_that_seats_the_supply_took_a_patch_and_its_lock_agrees():
    from portrayal import devicelock

    folder = LIB / "devices" / "juniper" / "mx304"
    assert not (folder / "layout.yaml").exists()
    assert version(yaml.safe_load((folder / "device.yaml").read_text())["version"]) >= (4, 1, 4)
    assert [f for f in devicelock.check(LIB) if f[0] in ("mx304", "juniper/mx304")] == []


def test_the_finding_this_change_closes_has_no_row_left():
    rows = yaml.safe_load((LIB / "conformance-exceptions.yaml").read_text())["rows"]
    assert [r for r in rows if r["part"] == SUPPLY and r["code"] == "C19"] == []
