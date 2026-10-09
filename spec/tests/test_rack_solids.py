"""The `solids` rack.json carries (docs/cable-lay-design.md section 1.1, #949),
derived by rack_solids.py from the compiled faces and never stated: a sheet
part is its plates, a zero-U duct its walls and back, a device with cable space
inside its envelope its shell, plate and what is inside, with its declared
pass-throughs as the only openings. A plain box device carries none: the kit
takes its envelope."""
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
# A closed enclosure with cable space: a ring on its plan (inside the body),
# one grommet in its rear wall, 40 x 24 at rear-view x 358 (device x 50 to 90).
ENCL = {
    "chassis": {"w": 448, "h": 44, "d": 432.8, "ru": 1, "mount": "rack"},
    "faces": {
        "front": f'<svg {SVG}><rect id="chassis-faceplate" data-class="chassis" x="0" y="0" width="448" height="44"/></svg>',
        "rear": f'<svg {SVG}><rect id="pass--grommet-1" data-class="pass" data-pass="grommet-1" x="358" y="10" width="40" height="24"/></svg>',
        "top": f'<svg {SVG}><g id="guide-1" data-guide="ring" data-ref="fs/d-ring-snap-in@1:1.1.0"/></svg>',
    },
}


def _dist(tmp_path, name, chassis, faces, device=None):
    (tmp_path / "devices.json").write_text(json.dumps({"devices": [
        {"name": name, "manufacturer": "FS.com", "model": name.upper(), "profile": "optical", **(device or {})}]}))
    (tmp_path / f"{name}.configs.json").write_text(json.dumps({
        "chassis": chassis, "default": "base", "configs": [{"name": "base"}], "attrs": {}}))
    for view, text in faces.items():
        (tmp_path / f"{name}.base.{view}.svg").write_text(text)
    return tmp_path


def _roots(faces):
    return {v: ET.fromstring(t) for v, t in faces.items()}


def test_the_enclosure_fixture_is_what_rack_index_derives(tmp_path):
    e = rack_index.build(_dist(tmp_path, "fhd-encl", ENCL["chassis"], ENCL["faces"]))["devices"]["fhd-encl"]
    assert e["solids"] == CAT["fhd-encl"]["solids"]
    parts = [s["part"] for s in e["solids"]]
    # five shell walls and the patch plate, and nothing for the ring: it is an opening
    assert parts == ["shell/top", "shell/bottom", "shell/left", "shell/right", "shell/rear", "plate"]
    rear = e["solids"][4]
    assert rear["holes"] == [{"via": "grommet-1", "box": {"x": 50.0, "y": 10.0, "z": 431.8, "w": 40.0, "h": 24.0, "d": 1.0},
                              "size": [40.0, 24.0]}]
    # the grommet cuts the rear wall only, never the plate at the front
    assert all("holes" not in s for s in e["solids"] if s["part"] != "shell/rear")


def test_a_box_device_whose_pathways_are_only_on_its_faces_is_its_envelope(tmp_path):
    faces = dict(ENCL["faces"], top=f'<svg {SVG}/>')
    e = rack_index.build(_dist(tmp_path, "encl", ENCL["chassis"], faces))["devices"]["encl"]
    assert "solids" not in e and e["passes"] == {"rear": ["grommet-1"]}


def test_a_plain_box_device_carries_no_solids(tmp_path):
    e = rack_index.build(_dist(tmp_path, "sw", {"w": 440, "h": 44, "d": 300}, {}))["devices"]["sw"]
    assert "solids" not in e


def test_seated_modules_are_solid_behind_the_plate():
    faces = dict(ENCL["faces"], front=f'''<svg {SVG}>
      <g id="bay-1" data-class="bay"><g id="bay-1--module" data-body-depth="117.86" transform="translate(60.5,22) translate(-54.5,-17.5)">
        <rect x="0" y="0" width="109" height="35"/></g></g></svg>''')
    out = rack_solids.solids(_roots(faces), {"w": 448, "h": 44, "d": 432.8})
    mod = [s for s in out if s["part"] == "bay-1--module"]
    assert mod == [{"part": "bay-1--module", "box": {"x": 6.0, "y": 4.5, "z": 1.0, "w": 109.0, "h": 35.0, "d": 117.86}}]


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


def test_a_ring_is_never_a_plate_and_a_tie_slot_never_an_opening():
    top = f'''<svg {SVG}>
      <g id="tray" data-ref="t@1" data-depth="41" transform="translate(17.3,0)">
        <path id="tray--floor" d="M0,0 H448.4 V110 H0 Z M54.85,95 h22.5 v3 h-22.5 Z"/></g>
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
      <g id="base" data-ref="b@1" data-depth="138.2"><rect id="base--floor" x="6.7" y="0" width="125.4" height="2108"/></g>
      <g id="wall-left" data-ref="w@1" data-z-lift="-138.2"><rect id="wall-left--root" x="6.7" y="0" width="16" height="2108" data-z-out="-121.7"/></g>
      <g id="finger-1" data-ref="f@1" data-behaviour="mounts" data-z-lift="-138.2"><rect id="finger-1--arm" x="6.7" y="0" width="16" height="20" data-z-out="-21"/></g>
    </svg>'''
    chassis = {"w": 138.8, "h": 2108, "d": 165.1, "mount": "rack-side", "shell": "sheet", "thickness": 1.5}
    out = rack_solids.solids({"front": ET.fromstring(front)}, chassis, lane=True)
    assert [s["part"] for s in out] == ["base--floor", "wall-left--root"]


@pytest.mark.parametrize("name", ["fhd-cmp5dr", "cmv-sfd45u5w"])
def test_the_library_fixture_is_what_rack_index_derives_from_the_build(name):
    """The kit test's FHD-CMP5DR and vertical duct are copies of rack.json; the
    build must still derive exactly them."""
    rack = DIST / "rack.json"
    if not rack.is_file():
        pytest.skip("no library/dist/rack.json: run ./build.sh first")
    built = json.loads(rack.read_text())["devices"].get(name)
    if built is None:
        pytest.skip(f"{name} is not in this build")
    assert built["solids"] == CAT[name]["solids"]
    # and they are not vacuous: the counts measured when the fixture was taken
    assert len(built["solids"]) == {"fhd-cmp5dr": 17, "cmv-sfd45u5w": 4}[name]


def test_the_cmp5dr_floor_sits_3_mm_up_its_envelope_and_the_sheet_thick():
    floor = [s["box"] for s in CAT["fhd-cmp5dr"]["solids"] if s["part"] == "tray/floor"]
    assert len(floor) == 3
    assert {(b["y"], b["h"]) for b in floor} == {(1.5, 1.5)}
    strip = max(floor, key=lambda b: b["w"])
    assert (strip["x"], strip["w"], strip["z"], strip["d"]) == (17.3, 448.4, 0.0, 61.2)
