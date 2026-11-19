"""The Chatsworth Velocity single-sided horizontal cable managers 13930-701 and 13930-702 (#1093, part of #1091).

Two devices, 1U and 2U, from the Velocity Cable Management product data sheet (page 3): 19 in EIA wide,
5.9 in (150 mm) deep, black plastic, a row of T-shaped fingers along the top and the bottom, a snap-on
cover and two cable openings in the rear. What the data sheet does not dimension (the fingers, the
cover, the ears, the openings) is estimated, and these tests hold that it says so and that the part
still works: a finger duct a cable runs along, two openings a cable crosses the back by, a cover that
can be taken off, and the DCIM types of a part that bolts to the rail face.
"""
import pathlib
import xml.etree.ElementTree as ET

import pytest
import yaml

from portrayal import render

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DEVICES = LIB / "devices/chatsworth"
COMPONENTS = LIB / "components/chatsworth"
EXPORTS = LIB / "exports"

# directory -> (rack units, shipping weight in kg as printed)
PARTS = {"13930-701": (1, 0.9), "13930-702": (2, 1.4)}
RU_MM = 44.45
FINGERS_PER_ROW = 5
USABLE_LESS = 31.0       # the note: usable height is 1.2 in (31 mm) less than the overall height
ids = sorted(PARTS)


def load(slug):
    return yaml.safe_load((DEVICES / slug / "device.yaml").read_text())


def contract(name):
    return yaml.safe_load((COMPONENTS / name / "v1/contract.yaml").read_text())


def front(slug):
    doc = load(slug)
    svg = render.render_view(doc, "front", doc["views"]["front"], render.Library([str(LIB)]), config={})
    svg = svg[0] if isinstance(svg, tuple) else svg
    return ET.fromstring(svg) if isinstance(svg, (str, bytes)) else svg


def test_there_are_two_horizontal_devices_and_the_family_has_no_other():
    assert sorted(p.name for p in DEVICES.glob("1393*")) == ids


def test_the_horizontal_parts_are_their_own_components_and_borrow_none_of_another_line():
    names = sorted(p.name for p in COMPONENTS.glob("velocity-hcm-*"))
    assert names == ["velocity-hcm-base-1u", "velocity-hcm-base-2u", "velocity-hcm-door-1u",
                     "velocity-hcm-door-2u", "velocity-hcm-tguide", "velocity-hcm-tguide-end"]
    for slug in ids:
        refs = {p["ref"] for p in load(slug)["views"]["front"]["components"]["placements"]}
        assert all(r.startswith("chatsworth/velocity-hcm-") for r in refs), refs


@pytest.mark.parametrize("slug", ids)
def test_the_envelope_is_the_data_sheets_and_the_part_bolts_to_the_rail_face(slug):
    ru, kg = PARTS[slug]
    doc = load(slug)
    ch = doc["chassis"]
    assert doc["manufacturer"] == "Chatsworth Products" and doc["model"] == slug
    assert (ch["width"], ch["depth"]) == (482.6, 150.0), "19 in EIA by 5.9 in (150 mm)"
    assert ch["ru"] == ru and ch["mount"] == "rack-face" and ch["shell"] == "sheet"
    assert ch["height"] == pytest.approx(RU_MM * ru, abs=0.01)
    assert ch["weight-kg"] == kg == doc["attrs"]["physical"]["weight-kg"]
    for view, size in (("front", (482.6, ch["height"])), ("rear", (482.6, ch["height"])),
                       ("top", (482.6, 150.0)), ("left", (150.0, ch["height"]))):
        assert doc["views"][view]["size"] == {"w": size[0], "h": size[1]}


@pytest.mark.parametrize("slug", ids)
def test_each_device_has_one_orderable_configuration_with_its_part_number_and_only_black(slug):
    cfgs = load(slug)["configurations"]
    assert set(cfgs) == {"base", "black"}, "the table says Color is Black: no other colour is stated"
    assert cfgs["black"]["kind"] == "orderable"
    assert cfgs["black"]["part-numbers"] == {slug: {"part": slug}}
    assert cfgs["base"]["default"] is True and "part-numbers" not in cfgs["base"]


@pytest.mark.parametrize("slug", ids)
def test_the_estimates_are_declared_and_no_cable_capacity_is_stated(slug):
    doc = load(slug)
    gaps = {g["what"] for g in doc["gaps"]}
    assert {"rear-openings", "finger-count", "usable-split", "height-under-unit", "door-hinge",
            "ear-holes", "cable-capacity"} <= gaps
    assert "performance" not in doc["attrs"], "the data sheet points to a cable fill table and states no figure"
    for key in ("fingers", "door", "rear", "passes", "ears", "usable"):
        assert key in doc["provenance"], key
    assert doc["provenance"]["chassis"]["confidence"] == "datasheet"
    assert doc["provenance"]["fingers"]["confidence"] == "estimated"
    assert "G3" not in yaml.safe_dump(doc)


# ---- the T-shaped fingers and the duct a cable runs along ----------------------------------

@pytest.mark.parametrize("slug", ids)
def test_each_device_publishes_its_finger_duct_and_the_fingers_stand_under_the_cover(slug):
    ch = load(slug)["chassis"]
    v = load(slug)["views"]["front"]
    (duct,) = v["guides"]
    assert duct["kind"] == "duct" and duct["run"] == "x" and duct["confidence"] == "estimated"
    # the channel between the two finger plates: the usable height of the note, over the 450 between the ears
    assert duct["at"][0] == 16.3 and duct["size"][0] == 450.0
    assert duct["size"][1] == pytest.approx(ch["height"] - USABLE_LESS, abs=0.01)
    fingers = [p for p in v["components"]["placements"] if p["group"] == "fingers"]
    assert len(fingers) == 2 * FINGERS_PER_ROW
    upper = sorted(p["at"][0] for p in fingers if p["at"][1] == 0.0)
    assert upper == [round(16.3 + 90.0 * i, 1) for i in range(FINGERS_PER_ROW)], "a pitch of 90.0"
    assert {p["at"][1] for p in fingers} == {0.0, round(ch["height"] - USABLE_LESS / 2, 2)}
    assert all(p["in"] == "base" and p["under"] == "door" for p in fingers)
    assert not load(slug)["views"]["rear"].get("components"), "the fingers are on the front only"


@pytest.mark.parametrize("name", ["velocity-hcm-tguide", "velocity-hcm-tguide-end"])
def test_a_finger_stands_inside_the_150_mm_the_table_gives(name):
    c = contract(name)
    assert c["size"] == {"w": 90.0, "h": 15.5}
    assert c["size-confidence"] == {"w": "estimated", "h": "estimated"}
    outs = [x.get("out") for x in c["relief"]["features"]]
    assert max(o for o in outs if o) <= 150.0 and 144.0 in outs
    assert all(x["confidence"] == "estimated" for x in c["relief"]["features"])
    assert "94" in c["provenance"]["relief"], "the usable depth the slot ends are read from"


# ---- the two openings in the back ---------------------------------------------------------------

@pytest.mark.parametrize("slug", ids)
def test_the_back_declares_two_open_passes_and_the_other_views_none(slug):
    doc = load(slug)
    rear = doc["views"]["rear"]["passes"]
    assert [p["cover"] for p in rear] == ["open", "open"] and all(p["shape"] == "obround" for p in rear)
    h = doc["chassis"]["height"]
    assert all(p["size"][1] <= h - 1 for p in rear), "an opening fits in the back plate"
    assert all(0 <= p["at"][0] and p["at"][0] + p["size"][0] <= 482.6 for p in rear)
    decor = {d["id"] for d in doc["views"]["rear"]["panel"]["decor"]}
    assert {"port-1", "port-2"} <= decor, "each opening is drawn where it is declared"
    assert all(not vw.get("passes") for k, vw in doc["views"].items() if k != "rear")


# ---- the cover: a removable part, and the fingers under it ---------------------------------------

@pytest.mark.parametrize("slug", ids)
def test_the_cover_is_a_removable_lid_on_every_device(slug):
    ru, _ = PARTS[slug]
    placed = [p for p in load(slug)["views"]["front"]["components"]["placements"]
              if p["ref"] == f"chatsworth/velocity-hcm-door-{ru}u@1"]
    assert [p["id"] for p in placed] == ["door"]
    c = contract(f"velocity-hcm-door-{ru}u")
    assert c["behaviour"] == "mounts" and c["lid"] is True
    assert "snaps onto" in c["provenance"]["lid"] and "opened position" in c["provenance"]["lid"]


@pytest.mark.parametrize("slug", ids)
def test_the_drawing_with_the_cover_off_shows_the_fingers(slug):
    root = front(slug)
    door = next(el for el in root.iter() if el.get("data-path") == "door")
    assert door.get("data-behaviour") == "mounts"
    fingers = [el for el in root.iter() if (el.get("data-path") or "").startswith("finger-") and "/" not in el.get("data-path")]
    assert len(fingers) == 2 * FINGERS_PER_ROW
    assert all("door" in (f.get("data-under") or "").split() for f in fingers)
    for parent in root.iter():
        for child in list(parent):
            if child is door:
                parent.remove(child)
    left = {el.get("data-path") for el in root.iter() if (el.get("data-path") or "").startswith("finger-") and "/" not in el.get("data-path")}
    assert left == {f.get("data-path") for f in fingers}


# ---- the DCIM types ----------------------------------------------------------------------------

@pytest.mark.parametrize("kind", ["netbox", "nautobot"])
def test_the_dcim_types_export_zero_u_and_not_full_depth(kind):
    types = {}
    for f in (EXPORTS / kind / "device-types/Chatsworth Products").glob("1393*.yaml"):
        d = yaml.safe_load(f.read_text())
        types[d["model"]] = d
    assert sorted(types) == ids
    for model, d in types.items():
        assert d["u_height"] == 0.0 and d["is_full_depth"] is False, model
        assert "occupies none" in d["comments"] or "occupies no rack unit" in d["comments"], model
