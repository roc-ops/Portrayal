"""The Chatsworth Motive horizontal cable managers with black fingers (#1093, part of #1091).

Seven devices, one per part number family and height, each with a black and a Glacier White chassis
and black fingers on both. The sizes and weights are the Motive Cable Management data sheet's ordering
table (page 7). What the part advertises has to WORK in the library, not only be drawn: a finger duct a
cable runs along, a pass-through port on the chassis that has them, a door that can be taken off, and the
DCIM types of a part that bolts to the rail face. No held page dimensions a Motive horizontal manager, so
each device is drawn as the Evolution horizontal manager of the same height and chassis style, and says so.
"""
import pathlib
import xml.etree.ElementTree as ET

import pytest
import yaml

from portrayal import render

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DEVICES = LIB / "devices/chatsworth"
EXPORTS = LIB / "exports"

# directory -> (chassis style, rack units, shipping weight in kg, part number family, units digits)
PARTS = {
    "35431-x02": ("ports", 2, 1.8, "35431", "02"),
    "35431-x03": ("ports", 3, 2.4, "35431", "03"),
    "35431-x04": ("ports", 4, 3.2, "35431", "04"),
    "35432-x01": ("solid", 1, 1.4, "35432", "01"),
    "35432-x02": ("solid", 2, 1.8, "35432", "02"),
    "35432-x03": ("solid", 3, 2.4, "35432", "03"),
    "35432-x04": ("solid", 4, 3.2, "35432", "04"),
}
RU_MM = 44.45

ids = sorted(PARTS)
FAMILIES = {v[3] for v in PARTS.values()}


def load(slug):
    return yaml.safe_load((DEVICES / slug / "device.yaml").read_text())


def front(slug):
    doc = load(slug)
    svg = render.render_view(doc, "front", doc["views"]["front"], render.Library([str(LIB)]), config={})
    svg = svg[0] if isinstance(svg, tuple) else svg
    return ET.fromstring(svg) if isinstance(svg, (str, bytes)) else svg


def test_there_are_seven_devices_and_no_other():
    assert sorted(p.name for p in DEVICES.iterdir() if p.is_dir() and p.name[:5] in FAMILIES) == ids


@pytest.mark.parametrize("slug", ids)
def test_the_envelope_and_weight_are_the_data_sheets_and_the_part_bolts_to_the_rail_face(slug):
    style, ru, kg, family, _ = PARTS[slug]
    doc = load(slug)
    ch = doc["chassis"]
    assert doc["manufacturer"] == "Chatsworth Products"
    assert doc["model"] == slug.upper()
    assert (ch["width"], ch["depth"]) == (482.6, 208.0), "19 in EIA by 8.2 in (208 mm)"
    assert ch["ru"] == ru and ch["mount"] == "rack-face" and ch["shell"] == "sheet"
    assert ch["height"] == pytest.approx(RU_MM * ru, abs=0.01)
    assert ch["weight-kg"] == kg == doc["attrs"]["physical"]["weight-kg"]
    assert doc["views"]["front"]["size"] == {"w": 482.6, "h": ch["height"]}
    assert doc["provenance"]["chassis"]["confidence"] == "datasheet"
    assert doc["provenance"]["mount"]["confidence"] == "estimated", "no held page says how it mounts"


@pytest.mark.parametrize("slug", ids)
def test_each_device_has_a_black_and_a_glacier_white_chassis_and_the_fingers_stay_black(slug):
    style, ru, _, family, nn = PARTS[slug]
    cfgs = load(slug)["configurations"]
    assert cfgs["black"]["kind"] == cfgs["glacier-white"]["kind"] == "orderable"
    assert cfgs["black"]["part-numbers"] == {f"{family}-7{nn}": {"part": f"{family}-7{nn}"}}
    assert cfgs["glacier-white"]["part-numbers"] == {f"{family}-E{nn}": {"part": f"{family}-E{nn}"}}
    assert cfgs["base"]["default"] is True and "part-numbers" not in cfgs["base"]
    # the table's heading is "White or Black Cable Manager with Black Fingers": the chassis and the
    # door are recoloured, and the fingers are not
    assert set(cfgs["glacier-white"]["component-attrs"]) == {
        f"evolution-hcm-base-{style}-{ru}u", f"evolution-hcm-door-{ru}u"}


@pytest.mark.parametrize("slug", ids)
def test_no_cable_capacity_is_stated_because_no_held_page_gives_one(slug):
    doc = load(slug)
    assert "performance" not in doc["attrs"]
    assert "capacity" not in doc["provenance"]
    assert "cable-capacity" in {g["what"] for g in doc["gaps"]}


@pytest.mark.parametrize("slug", ids)
def test_the_drawing_borrowed_from_the_evolution_part_is_declared(slug):
    doc = load(slug)
    gaps = {g["what"] for g in doc["gaps"]}
    assert {"drawing-borrowed", "mounting", "door-hinge", "door-features", "white-chassis-views"} <= gaps
    assert "Evolution horizontal" in doc["provenance"]["method"]["note"]
    assert doc["provenance"]["method"]["confidence"] == "estimated"
    for g in doc["gaps"]:
        assert g["reason"] and g.get("wanted"), g["what"]


# ---- the T-shaped fingers and the duct a cable runs along ----------------------------------

@pytest.mark.parametrize("slug", ids)
def test_each_device_publishes_its_finger_duct_and_ten_fingers_a_row(slug):
    ch = load(slug)["chassis"]
    v = load(slug)["views"]["front"]
    (duct,) = v["guides"]
    assert duct["kind"] == "duct" and duct["run"] == "x"
    assert (duct["finger-pitch"], duct["finger-gap"]) == (45.0, 24.0)
    assert duct["confidence"] == "estimated", "no document dimensions a finger"
    assert duct["at"][0] == 16.3 and duct["size"][0] == 450.0
    assert duct["size"][1] == pytest.approx(ch["height"] - 2 * 11.4, abs=0.01)
    fingers = [p for p in v["components"]["placements"] if p["group"] == "fingers"]
    assert len(fingers) == 20
    upper = sorted(p["at"][0] for p in fingers if p["at"][1] == 0.0)
    assert upper == [round(16.3 + 45.0 * i, 1) for i in range(10)], "a pitch of 45.0, ten a row"
    assert {p["at"][1] for p in fingers} == {0.0, round(ch["height"] - 11.4, 2)}
    assert not load(slug)["views"]["rear"].get("components")


@pytest.mark.parametrize("slug", ids)
def test_the_fingers_stand_in_the_back_plate_under_the_door(slug):
    v = load(slug)["views"]["front"]
    for p in (p for p in v["components"]["placements"] if p["group"] == "fingers"):
        assert p["in"] == "base" and p["under"] == "door"


# ---- the passes: two ports on the pass-through chassis, none on the solid one ----------------

@pytest.mark.parametrize("slug", ids)
def test_the_back_plate_declares_the_passes_its_chassis_style_has(slug):
    style = PARTS[slug][0]
    doc = load(slug)
    declared = {v: vw.get("passes") or [] for v, vw in doc["views"].items()}
    assert not declared["front"]
    assert all(v == [] for k, v in declared.items() if k != "rear")
    rear = declared["rear"]
    if style == "ports":
        assert len(rear) == 2 and all(p.get("cover", "open") == "open" for p in rear)
        assert "ports-size" in {g["what"] for g in doc["gaps"]}
    else:
        assert rear == []


# ---- the door: a removable part, and the fingers under it --------------------------------------

@pytest.mark.parametrize("slug", ids)
def test_the_door_is_a_removable_lid_on_every_device(slug):
    _, ru, _, _, _ = PARTS[slug]
    ref = f"chatsworth/evolution-hcm-door-{ru}u"
    placed = [p for p in load(slug)["views"]["front"]["components"]["placements"] if p["ref"] == f"{ref}@1"]
    assert [p["id"] for p in placed] == ["door"]
    c = yaml.safe_load((LIB / "components" / ref / "v1/contract.yaml").read_text())
    assert c["behaviour"] == "mounts" and c["lid"] is True


@pytest.mark.parametrize("slug", ids)
def test_the_drawing_with_the_door_off_shows_the_fingers(slug):
    root = front(slug)
    door = next(el for el in root.iter() if el.get("data-path") == "door")
    assert door.get("data-behaviour") == "mounts"
    fingers = [el for el in root.iter() if (el.get("data-path") or "").startswith("finger-") and el.get("data-path").count("/") == 0]
    assert len(fingers) == 20
    assert all("door" in (f.get("data-under") or "").split() for f in fingers), "declared under the door"
    for parent in root.iter():
        for child in list(parent):
            if child is door:
                parent.remove(child)
    left = [el for el in root.iter() if (el.get("data-path") or "").startswith("finger-")]
    assert {el.get("data-path") for el in left if "/" not in el.get("data-path")} == {f.get("data-path") for f in fingers}
    assert not any(el.get("data-path") == "door" for el in root.iter())


# ---- the DCIM types ----------------------------------------------------------------------------

def _types(kind):
    out = {}
    for f in (EXPORTS / kind / "device-types/Chatsworth Products").glob("*.yaml"):
        d = yaml.safe_load(f.read_text())
        if d["model"][:5] in FAMILIES:
            out[d["model"]] = d
    return out


@pytest.mark.parametrize("kind", ["netbox", "nautobot"])
def test_the_dcim_types_of_all_fourteen_part_numbers_export_zero_u_and_not_full_depth(kind):
    want = {f"{fam}-{c}{nn}" for _, _, _, fam, nn in PARTS.values() for c in "7E"}
    assert len(want) == 14
    types = _types(kind)
    assert set(types) == want
    for model, d in types.items():
        assert d["u_height"] == 0.0 and d["is_full_depth"] is False, model
        assert "occupies none" in d["comments"] or "occupies no rack unit" in d["comments"], model
