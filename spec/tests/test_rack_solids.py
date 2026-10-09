"""The `solids` rack.json carries (docs/cable-lay-design.md section 1.1, #949),
derived by rack_solids.py from the compiled faces and never stated: a sheet
part is its plates, a zero-U duct its walls and back, each with its declared
pass-throughs as holes. Any other device carries none: the kit takes its
envelope."""
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from portrayal import rack_index, rack_solids

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist"
FIXTURE = Path(__file__).resolve().parent / "js" / "cable-solids-catalogue.json"
CAT = json.loads(FIXTURE.read_text())["devices"]

SVG = 'xmlns="http://www.w3.org/2000/svg"'


def _dist(tmp_path, name, chassis, faces, device=None):
    (tmp_path / "devices.json").write_text(json.dumps({"devices": [
        {"name": name, "manufacturer": "FS.com", "model": name.upper(), "profile": "optical", **(device or {})}]}))
    (tmp_path / f"{name}.configs.json").write_text(json.dumps({
        "chassis": chassis, "default": "base", "configs": [{"name": "base"}], "attrs": {}}))
    for view, text in faces.items():
        (tmp_path / f"{name}.base.{view}.svg").write_text(text)
    return tmp_path


def test_a_box_device_is_its_envelope_whatever_its_plan_marks(tmp_path):
    """A device with cable space inside its envelope waits for step 6 of the
    note: until then a box device carries no solids, even with a ring on its
    plan and a grommet in its back."""
    faces = {"rear": f'<svg {SVG}><rect id="pass--grommet-1" data-class="pass" x="358" y="10" width="40" height="24"/></svg>',
             "top": f'<svg {SVG}><g id="guide-1" data-guide="ring" data-ref="fs/d-ring-snap-in@1:1.1.0"/></svg>'}
    e = rack_index.build(_dist(tmp_path, "encl", {"w": 448, "h": 44, "d": 432.8}, faces))["devices"]["encl"]
    assert "solids" not in e and e["passes"] == {"rear": ["grommet-1"]}


def test_a_plain_box_device_carries_no_solids(tmp_path):
    e = rack_index.build(_dist(tmp_path, "sw", {"w": 440, "h": 44, "d": 300}, {}))["devices"]["sw"]
    assert "solids" not in e


def test_a_sheet_part_through_rack_index(tmp_path):
    top = f'''<svg {SVG}><g id="tray" data-ref="t@1" data-depth="41">
      <rect id="tray--floor" data-class="bezel" x="0" y="0" width="100" height="50"/></g></svg>'''
    rear = f'<svg {SVG}><rect id="pass--window-1" data-class="pass" x="10" y="5" width="30" height="20"/></svg>'
    e = rack_index.build(_dist(tmp_path, "mgr", {"w": 100, "h": 44, "d": 50, "shell": "sheet", "thickness": 1.5},
                               {"top": top, "rear": rear}))["devices"]["mgr"]
    assert e["solids"] == [{"part": "tray--floor", "box": {"x": 0.0, "y": 1.5, "z": 0.0, "w": 100.0, "h": 1.5, "d": 50.0}}]


def test_the_cmp5dr_floor_outline_is_cut_into_its_strip_and_two_arms():
    d = ("M0,15.4 H10.5 V34.8 Q10.5,48.8 24.5,48.8 H423.9 Q437.9,48.8 437.9,34.8 V15.4 H448.4 V107 "
         "Q448.4,110 445.4,110 H3 Q0,110 0,107 Z M54.85,95 h22.5 v3 h-22.5 Z")
    rings = rack_solids.path_rings(d)
    # the outline and one tie slot; the slot is not taken out of the plate
    assert len(rings) == 2
    assert sorted(rack_solids.rect_pieces(rings[0])) == [(0.0, 15.4, 10.5, 33.4), (0.0, 48.8, 448.4, 61.2),
                                                         (437.9, 15.4, 10.5, 33.4)]


def test_an_outline_that_is_not_rectilinear_is_its_bounding_box():
    assert rack_solids.rect_pieces([(0, 0), (10, 0), (5, 8)]) is None


def test_a_ring_is_never_a_plate_a_tie_slot_never_an_opening_and_decor_never_a_plate():
    top = f'''<svg {SVG}>
      <rect id="ear-left-edge" data-kind="ear" x="0" y="0" width="17.3" height="1.5"/>
      <g id="tray" data-ref="t@1" data-depth="41" transform="translate(17.3,0)">
        <path id="tray--floor" data-class="bezel" d="M0,0 H448.4 V110 H0 Z M54.85,95 h22.5 v3 h-22.5 Z"/>
        <rect id="tray--seam" x="0" y="50" width="448.4" height="0.6"/></g>
      <g id="guide-1" data-ref="r@1" data-guide="ring" data-z-lift="-41" transform="translate(19.55,66.4)">
        <rect id="guide-1--band" x="0" y="0" width="6.8" height="40" data-z-out="0"/></g></svg>'''
    out = rack_solids.solids({"top": ET.fromstring(top)}, {"w": 483, "h": 44, "d": 110, "shell": "sheet", "thickness": 1.5})
    assert out == [{"part": "tray--floor", "box": {"x": 17.3, "y": 1.5, "z": 0.0, "w": 448.4, "h": 1.5, "d": 110.0}}]


def test_a_proud_node_steps_along_its_profile():
    top = f'''<svg {SVG}><g id="web" data-ref="w@1" data-z-lift="-41" data-behaviour="mounts">
      <rect id="web--plate" x="0" y="0" width="1.5" height="66" data-z-out="0" data-z-profile-y="0:0,8:0,31:-30.5,66:-41"/></g></svg>'''
    out = rack_solids.solids({"top": ET.fromstring(top)}, {"w": 483, "h": 44, "d": 110, "shell": "sheet"})
    # 41 high for the first 8 mm, then as high as the higher end of each step;
    # the last step, 0 high at its higher end, is no plate
    assert [(s["box"]["z"], s["box"]["d"], s["box"]["h"]) for s in out] == [(102.0, 8.0, 41.0), (79.0, 23.0, 41.0),
                                                                           (44.0, 35.0, 10.5)]


def test_a_ducts_fingers_and_clips_are_not_plates():
    front = f'''<svg {SVG}>
      <rect id="guide--duct" data-class="guide" data-guide="duct" x="22.7" y="0" width="93.4" height="2108"/>
      <g id="base" data-ref="b@1" data-depth="138.2"><rect id="base--floor" data-class="bezel" x="6.7" y="0" width="125.4" height="2108"/>
        <rect id="base--seam" x="6.7" y="1053.7" width="125.4" height="0.6"/></g>
      <g id="wall-left" data-ref="w@1" data-z-lift="-138.2"><rect id="wall-left--root" x="6.7" y="0" width="16" height="2108" data-z-out="-121.7"/></g>
      <g id="finger-1" data-ref="f@1" data-behaviour="mounts" data-z-lift="-138.2"><rect id="finger-1--arm" x="6.7" y="0" width="16" height="20" data-z-out="-21"/></g>
    </svg>'''
    chassis = {"w": 138.8, "h": 2108, "d": 165.1, "mount": "rack-side", "shell": "sheet", "thickness": 1.5}
    out = rack_solids.solids({"front": ET.fromstring(front)}, chassis, lane=True)
    assert [s["part"] for s in out] == ["base--floor", "wall-left--root"]


def test_anything_inside_a_duct_guides_footprint_is_open_whatever_its_behaviour():
    """The CMV-5U3W: its fingers are part of its own body, not mounted on it,
    and stand inside the duct's footprint; they bound the channel, so a cable
    through the duct does not go round them. The flange behind, wider than the
    duct, stays a plate."""
    front = f'''<svg {SVG}>
      <rect id="guide--duct" data-class="guide" data-guide="duct" x="0" y="0" width="14.6" height="222"/>
      <g id="flange" data-ref="b@1" data-depth="79.2"><rect id="flange--floor" data-class="bezel" x="0" y="0" width="26" height="222"/></g>
      <g id="fingers" data-ref="f@1" data-z-lift="-79.2"><rect id="fingers--spine" x="0" y="0" width="3.6" height="222" data-z-out="-71.1"/>
        <rect id="fingers--bar-1" x="3.6" y="0" width="11" height="17.1" data-z-out="-3.7"/></g>
    </svg>'''
    out = rack_solids.solids({"front": ET.fromstring(front)}, {"w": 26, "h": 222, "d": 84, "mount": "rack-face", "shell": "sheet"})
    assert [s["part"] for s in out] == ["flange--floor"]


@pytest.mark.parametrize("name, count", [("fhd-cmp5dr", 15), ("cmv-sfd45u5w", 3), ("cmv-5u3w", 1)])
def test_the_library_fixture_is_what_rack_index_derives_from_the_build(name, count):
    """The kit test's FHD-CMP5DR and ducts are copies of rack.json; the build
    must still derive exactly them, and they are not vacuous."""
    rack = DIST / "rack.json"
    assert rack.is_file(), "no library/dist/rack.json: run ./build.sh first (the suite reads the build)"
    built = json.loads(rack.read_text())["devices"].get(name)
    assert built is not None, f"{name} is not in library/dist/rack.json: run ./build.sh"
    assert built["solids"] == CAT[name]["solids"]
    assert len(built["solids"]) == count


def test_no_decor_is_a_plate_anywhere_in_the_build():
    rack = DIST / "rack.json"
    assert rack.is_file(), "no library/dist/rack.json: run ./build.sh first (the suite reads the build)"
    parts = [(n, s["part"]) for n, e in json.loads(rack.read_text())["devices"].items() for s in e.get("solids", [])]
    assert len(parts) > 50
    assert not [p for p in parts if any(w in p[1] for w in ("seam", "window", "-edge", "keyhole"))]


def test_the_cmp5dr_floor_sits_3_mm_up_its_envelope_and_the_sheet_thick():
    floor = [s["box"] for s in CAT["fhd-cmp5dr"]["solids"] if s["part"] == "tray/floor"]
    assert len(floor) == 3
    assert {(b["y"], b["h"]) for b in floor} == {(1.5, 1.5)}
    strip = max(floor, key=lambda b: b["w"])
    assert (strip["x"], strip["w"], strip["z"], strip["d"]) == (17.3, 448.4, 0.0, 61.2)
