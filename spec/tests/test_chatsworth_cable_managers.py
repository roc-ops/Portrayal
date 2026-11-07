"""The Chatsworth Evolution horizontal cable managers (#1093, part of #1091).

Thirteen devices, one per part number family and height, each with a black and a Glacier
White configuration. What the maker advertises has to WORK in the library, not only be drawn:
a finger duct a cable runs along, a pass-through port, a brush or a grommet a cable crosses
the back plate by, a door that can be taken off, and the DCIM types of a part that bolts to the
rail face. The sizes are the Evolution Cable Management System data sheet's ordering table
(page 3); the rack kit's side, the cable that runs and crosses, is
spec/tests/js/rack-chatsworth-managers.mjs.
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
    "35441-x01": ("solid", 1, 1.4, "35441", "01"),
    "35441-x02": ("ports", 2, 1.8, "35441", "02"),
    "35441-x03": ("ports", 3, 2.3, "35441", "03"),
    "35441-x04": ("ports", 4, 3.2, "35441", "04"),
    "35442-x02": ("solid", 2, 1.8, "35442", "02"),
    "35442-x03": ("solid", 3, 2.3, "35442", "03"),
    "35442-x04": ("solid", 4, 3.2, "35442", "04"),
    "33548-x02": ("brush", 2, 1.8, "33548", "02"),
    "33548-x03": ("brush", 3, 2.3, "33548", "03"),
    "33548-x04": ("brush", 4, 3.2, "33548", "04"),
    "33549-x02": ("grommet", 2, 1.8, "33549", "02"),
    "33549-x03": ("grommet", 3, 2.3, "33549", "03"),
    "33549-x04": ("grommet", 4, 3.2, "33549", "04"),
}
# what each chassis style declares on its back plate: (cover, how many)
PASSES = {"solid": [], "ports": [("open", 2)], "brush": [("brush", 1)], "grommet": [("open", 3)]}
# the maker's CPI Cable Fill Table, Cat 6 (0.250 in OD) at the maximum fill, by rack units
CAPACITY = {1: 56, 2: 173, 3: 285, 4: 403}
RECOMMENDED = {1: 28, 2: 87, 3: 143, 4: 202}
RU_MM = 44.45

ids = sorted(PARTS)


def load(slug):
    return yaml.safe_load((DEVICES / slug / "device.yaml").read_text())


def front(slug):
    doc = load(slug)
    svg = render.render_view(doc, "front", doc["views"]["front"], render.Library([str(LIB)]), config={})
    svg = svg[0] if isinstance(svg, tuple) else svg
    return ET.fromstring(svg) if isinstance(svg, (str, bytes)) else svg


def test_there_are_thirteen_devices_and_no_other():
    assert sorted(p.name for p in DEVICES.iterdir() if p.is_dir()) == ids


@pytest.mark.parametrize("slug", ids)
def test_the_envelope_is_the_data_sheets_and_the_part_bolts_to_the_rail_face(slug):
    style, ru, kg, _, _ = PARTS[slug]
    doc = load(slug)
    ch = doc["chassis"]
    assert doc["manufacturer"] == "Chatsworth Products"
    assert (ch["width"], ch["depth"]) == (482.6, 208.0), "19 in EIA by 8.2 in (208 mm)"
    assert ch["ru"] == ru and ch["mount"] == "rack-face" and ch["shell"] == "sheet"
    assert ch["height"] == pytest.approx(RU_MM * ru, abs=0.01)
    assert ch["weight-kg"] == kg == doc["attrs"]["physical"]["weight-kg"]
    assert doc["views"]["front"]["size"] == {"w": 482.6, "h": ch["height"]}


@pytest.mark.parametrize("slug", ids)
def test_each_device_has_a_black_and_a_glacier_white_configuration_with_its_part_number(slug):
    _, _, _, family, nn = PARTS[slug]
    cfgs = load(slug)["configurations"]
    assert cfgs["black"]["kind"] == cfgs["glacier-white"]["kind"] == "orderable"
    assert cfgs["black"]["part-numbers"] == {f"{family}-7{nn}": {"part": f"{family}-7{nn}"}}
    assert cfgs["glacier-white"]["part-numbers"] == {f"{family}-E{nn}": {"part": f"{family}-E{nn}"}}
    assert cfgs["base"]["default"] is True and "part-numbers" not in cfgs["base"]
    # Glacier White recolours the plate, the fingers and the door and nothing else
    assert set(cfgs["glacier-white"]["component-attrs"]) >= {"evolution-hcm-finger", "evolution-hcm-finger-end"}


@pytest.mark.parametrize("slug", ids)
def test_the_cable_capacity_is_the_makers_with_its_basis_and_none_is_estimated(slug):
    _, ru, _, _, _ = PARTS[slug]
    doc = load(slug)
    perf = doc["attrs"]["performance"]
    assert perf["cable-capacity"] == CAPACITY[ru] and perf["cable-capacity-media"] == "cat6"
    assert str(RECOMMENDED[ru]) in perf["cable-capacity-basis"], "the recommended fill is in the basis"
    assert "cable-capacity-estimated" not in perf, "the maker states it; nothing here is an estimate"
    assert doc["provenance"]["capacity"]["confidence"] == "datasheet"


# ---- the T-shaped fingers and the duct a cable runs along ----------------------------------

@pytest.mark.parametrize("slug", ids)
def test_each_device_publishes_its_finger_duct_and_ten_fingers_a_row(slug):
    ch = load(slug)["chassis"]
    v = load(slug)["views"]["front"]
    (duct,) = v["guides"]
    assert duct["kind"] == "duct" and duct["run"] == "x"
    assert (duct["finger-pitch"], duct["finger-gap"]) == (45.0, 24.0)
    assert duct["confidence"] == "estimated", "no document dimensions a finger"
    # the channel between the two finger plates, over the 450 between the ears
    assert duct["at"][0] == 16.3 and duct["size"][0] == 450.0
    assert duct["size"][1] == pytest.approx(ch["height"] - 2 * 11.4, abs=0.01)
    fingers = [p for p in v["components"]["placements"] if p["group"] == "fingers"]
    assert len(fingers) == 20
    upper = sorted(p["at"][0] for p in fingers if p["at"][1] == 0.0)
    assert upper == [round(16.3 + 45.0 * i, 1) for i in range(10)], "a pitch of 45.0, ten a row"
    assert {p["at"][1] for p in fingers} == {0.0, round(ch["height"] - 11.4, 2)}
    # the fingers are on the front only: the rear view places none
    assert not load(slug)["views"]["rear"].get("components")


@pytest.mark.parametrize("slug", ids)
def test_the_fingers_stand_in_the_back_plate_under_the_door(slug):
    v = load(slug)["views"]["front"]
    for p in (p for p in v["components"]["placements"] if p["group"] == "fingers"):
        assert p["in"] == "base" and p["under"] == "door"


# ---- the passes: ports, a brush, grommets, and none on the solid ones ------------------------

@pytest.mark.parametrize("slug", ids)
def test_the_back_plate_declares_the_passes_its_chassis_style_has(slug):
    style = PARTS[slug][0]
    doc = load(slug)
    declared = {v: vw.get("passes") or [] for v, vw in doc["views"].items()}
    assert not declared["front"]
    rear = declared["rear"]
    assert sorted((c, sum(1 for p in rear if p.get("cover", "open") == c)) for c in {p.get("cover", "open") for p in rear}) \
        == sorted(PASSES[style])
    assert all(v == [] for k, v in declared.items() if k != "rear")
    if style == "brush":
        decor = [d for d in doc["views"]["rear"]["panel"]["decor"] if d.get("pattern") == "brush"]
        assert len(decor) == 1, "the brush is drawn where its pass is declared"
    if style == "grommet":
        # round openings, declared as the square of their bore: an obround of equal sides is a
        # hole of no width in rack.json, which no cable crosses
        assert all(p["shape"] == "rect" and p["size"][0] == p["size"][1] for p in rear)
    if style == "solid":
        assert rear == []


# ---- the door: a removable part, and the fingers under it --------------------------------------

@pytest.mark.parametrize("slug", ids)
def test_the_door_is_a_removable_lid_on_every_device(slug):
    _, ru, _, _, _ = PARTS[slug]
    ref = f"chatsworth/evolution-hcm-door-{ru}u"
    placed = [p for p in load(slug)["views"]["front"]["components"]["placements"] if p["ref"] == f"{ref}@1"]
    assert [p["id"] for p in placed] == ["door"]
    c = yaml.safe_load((LIB / "components" / ref / "v1/contract.yaml").read_text())
    # `mounts` is what the explorer's tree pulls, and `lid` what lets a pass lie under it
    assert c["behaviour"] == "mounts" and c["lid"] is True
    assert "opens up or down" in c["provenance"]["lid"] and "can be removed" in c["provenance"]["lid"]


@pytest.mark.parametrize("slug", ids)
def test_the_drawing_with_the_door_off_shows_the_fingers(slug):
    root = front(slug)
    door = next(el for el in root.iter() if el.get("data-path") == "door")
    assert door.get("data-behaviour") == "mounts"
    fingers = [el for el in root.iter() if (el.get("data-path") or "").startswith("finger-") and el.get("data-path").count("/") == 0]
    assert len(fingers) == 20
    assert all("door" in (f.get("data-under") or "").split() for f in fingers), "declared under the door"
    # taking the door off the tree leaves every finger drawn
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
        out[d["model"]] = d
    return out


@pytest.mark.parametrize("kind", ["netbox", "nautobot"])
def test_the_dcim_types_of_all_twenty_six_part_numbers_export_zero_u_and_not_full_depth(kind):
    want = {f"{fam}-{c}{nn}" for _, _, _, fam, nn in PARTS.values() for c in "7E"}
    assert len(want) == 26
    types = _types(kind)
    assert set(types) == want
    for model, d in types.items():
        assert d["u_height"] == 0.0 and d["is_full_depth"] is False, model
        assert "occupies none" in d["comments"] or "occupies no rack unit" in d["comments"], model
