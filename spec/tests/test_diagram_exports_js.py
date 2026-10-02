"""The kit's draw.io and OmniGraffle writers put each port where its picture is.

Both exports are a picture of the face with one connectable shape over every
port and bay, so the one thing that must hold is that the shape and the
picture agree. They did not for a face whose viewBox does not start at 0,0:
draw.io measured ports from the origin, OmniGraffle from the viewBox's corner.
Every device face starts at the origin, so nothing showed it - but an optic's
face stands its bail above y=0, and a cropped export is a viewBox over the
middle of a faceplate.

The script (js/diagram-exports.mjs) runs the writers on hand-built zones; what
needs a real DOM - reading those zones out of an SVG - is the browser's to check.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "tests/js/diagram-exports.mjs"

PT = 72 / 25.4


@pytest.fixture(scope="module")
def out():
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_drawio_measures_from_the_viewbox_corner(out):
    # viewBox 0 -4.5 18 14 at 2 px/mm: a port at y=-4.5 is the top of the picture
    assert out["cells"]["d-port-1"] == [0, 0, 8, 4]
    assert out["cells"]["d-slot-1"] == [20, 9, 16, 19]
    assert out["cells"]["d-slot-2"] == [8, 19, 8, 8]


def test_a_cards_ports_sit_in_their_bay(out):
    # relative to the bay's own corner: (12 - 10) * 2, (2 - 0) * 2
    assert out["parents"]["d-slot-1--module--p0"] == "d-slot-1"
    assert out["cells"]["d-slot-1--module--p0"] == [4, 4, 4, 4]
    assert out["parents"]["d-port-1"] == "d"


def test_bays_are_written_before_ports(out):
    # draw.io stacks a later sibling on top, and a bay over its own card's ports
    # takes every click meant for them
    assert out["order"] == ["slot-1", "slot-2", "port-1", "slot-1--module--p0"]


def test_omnigraffle_and_drawio_agree(out):
    b = out["graffle"]["bounds"]
    assert b["port-1"] == "{{0, 0}, {11.3386, 5.6693}}"
    x, y = round(10 * PT, 4), round(4.5 * PT, 4)
    assert b["slot-1"].startswith(f"{{{{{x}, {y}}}")


def test_a_crop_drops_what_it_misses_and_clips_what_it_cuts(out):
    assert out["within"] == [
        ["slot-1", 10, 0, 3, 6],
        ["slot-1--module--p0", 12, 2, 1, 2],
        ["slot-2", 4, 5, 4, 1],
    ]


def test_a_library_is_well_formed(out):
    lib = out["library"]
    assert lib["head"] == "<!--\nmade - here\n-->\n"   # `--` would close the comment
    assert lib["rawAngle"] is False
    assert lib["json"] == "A <b> & c"


def test_a_diagram_is_one_page_of_named_ports(out):
    d = out["diagram"]
    assert d["head"] == ('<mxfile host="portrayal"><diagram name="one &quot;device&quot;" '
                         'id="page0"><mxGraphModel grid="0" page="0">')
    assert sorted(d["paths"]) == ["port-1", "slot-1/module/p0"]
    assert d["tail"].endswith("</diagram></mxfile>")


def test_a_stencil_is_a_stored_zip_of_its_plist_and_image(out):
    g = out["graffle"]
    assert out["crc"] == "cbf43926"           # the CRC-32 check value
    assert g["files"] == ["data.plist", "image1.png"]
    assert g["crcOk"] is True
    assert g["png"] == [0x89, 0x50, 0x4E, 0x47]
    assert g["device"] is True


def test_a_rack_diagram_keeps_its_defaults(out):
    r = out["rack"]["plain"]
    assert r["pages"] == ["P"]
    assert r["racks"] == [["g0r0-front", "ascend"]]
    assert r["device"] == "A-g0r0-front"


def test_a_rack_builder_sets_faces_ids_and_numbering_per_rack(out):
    r = out["rack"]["opts"]
    assert r["pages"] == ["Front", "Rear"]
    # each page draws only its own face, not the call's front-and-rear default
    assert r["racks"] == [["g0r0-front", "descend"], ["g1r0-rear", "ascend"]]
    # two devices with one name get two cells, named by their ids
    assert r["devices"] == ["dev-1-g0r0-front", "dev-2-g0r0-front", "dev-1-g1r0-rear"]


# ---------------------------------------------------------------- cables
# A cable plan written as draw.io edges between the port cells (#728).

def _edges(out, page):
    return {e["id"]: e for e in out["cables"]["pages"][page]["edges"]}


def test_a_cable_on_one_page_is_an_edge_between_its_port_cells(out):
    e = _edges(out, 0)["cable-c1"]
    # a port on a card seated in slot-2 resolves by its data-path
    assert e["source"] == "sw-1-g0r0-front-slot-2--module--p0"
    assert e["target"] == "srv-1-g0r0-front-p0"
    assert e["label"] == "up-1 · 2 m"
    assert e["attrs"] == {"portrayal-cable": "c1", "portrayal-media": "dac",
                          "portrayal-purpose": "uplink", "portrayal-length": "2 m"}


def test_two_racks_on_one_page_are_one_edge(out):
    e = _edges(out, 0)["cable-c-6"]
    assert (e["source"], e["target"]) == ("sw-1-g0r0-front-p0", "pp-1-g0r1-front-p0")
    # a plan's text is escaped, and the edge is not an html label
    assert e["label"] == "a &lt;b&gt;"


def test_every_edge_ends_on_a_cell_of_its_own_page(out):
    assert [p["dangling"] for p in out["cables"]["pages"]] == [[], []]


def test_a_front_to_rear_cable_is_a_stub_on_each_page(out):
    front, rear = _edges(out, 0), _edges(out, 1)
    assert "cable-c2" not in front and "cable-c2" not in rear
    a, b = front["cable-c2-a"], rear["cable-c2-b"]
    assert (a["source"], a["target"]) == ("sw-1-g0r0-front-p0", "cable-c2-a-far")
    assert (b["source"], b["target"]) == ("srv-1-g1r0-rear-nic-1--p0", "cable-c2-b-far")
    assert a["attrs"]["portrayal-end"] == "a" and b["attrs"]["portrayal-end"] == "b"
    assert out["cables"]["far"] == {"front": "→ rack-2 · r740 · rear/nic-1/p0",
                                    "rear": "→ rack-2 · sw · front/p0"}
    # in the gutter right of the cabinet (180 + 4), level with its port
    assert out["cables"]["farGeom"] == [184, 51.81, 84, 10]


def test_an_end_with_no_cell_is_a_note_not_a_half_edge(out):
    c = out["cables"]
    ids = {e["id"] for p in c["pages"] for e in p["edges"]}
    assert not any(i.startswith(("cable-c3", "cable-c4", "cable-c5")) for i in ids)
    assert c["notes"] == [
        "Cable c3 is not drawn: b (srv-1 front/p99) is not a port in its device's drawing.",
        "Cable c4 is not drawn: a (ghost front/p0) names no mounted device.",
        "Cable c5 is not drawn: a (blank-1 front/p0) is on a face no page draws.",
    ]
    # one comment inside <mxfile>, the caller's notes first
    assert c["commentInside"] is True
    assert c["comment"] == "Notes:\n- caller note\n" + "\n".join(f"- {n}" for n in c["notes"])


def test_edge_ids_come_from_cable_ids_and_never_repeat(out):
    # "c 6" and "c-6" slug alike; the second is numbered, not dropped
    assert list(_edges(out, 0)) == ["cable-c1", "cable-c2-a", "cable-c-6", "cable-c-6-2"]


def test_numbered_and_stub_ids_never_collide_with_another_cable(out):
    c = out["clash"]
    # every cell a cable writes has an id no other cell has
    assert len(c["ids"]) == len(set(c["ids"])), c["ids"]
    # and every cable is in the file
    assert sorted(c["cables"]) == sorted(["c 6", "c-6", "c-6-2", "x", "x-a", "y-b", "y"])
    assert c["notes"] == []
    ids = set(c["ids"])
    # where nothing clashes the plain names stand; where something does, the
    # later cable is numbered on, and a stub pair keeps one suffix
    assert {"cable-c-6", "cable-c-6-2", "cable-c-6-2-2"} <= ids
    assert {"cable-x-a", "cable-x-a-far", "cable-x-b", "cable-x-b-far", "cable-x-a-2"} <= ids
    assert {"cable-y-b", "cable-y-2-a", "cable-y-2-a-far", "cable-y-2-b", "cable-y-2-b-far"} <= ids


def test_cable_style_is_the_callers(out):
    c = out["cables"]
    assert c["styleFn"] == ["#ABCDEF"]
    # a map merges over the default palette; an unknown media is the default grey
    assert dict(c["styleMap"]) == {"cable-c1": "#4D4D4D", "cable-c2-a": "#D4A017",
                                   "cable-c-6": "#123456", "cable-c-6-2": "#808080",
                                   "cable-c2-b": "#D4A017"}


def test_cables_are_byte_stable_and_absent_cables_change_nothing(out):
    assert out["cables"]["stable"] is True
    assert out["cables"]["none"] is True


def test_one_device_diagram_takes_cables_between_its_own_ports(out):
    o = out["oneDevice"]
    assert [(e["id"], e["source"], e["target"]) for e in o["edges"]] == [
        ("cable-k1", "S-p0", "S-slot-2--module--p0")]
    assert o["comment"] == (
        "Notes:\n"
        "- Cable k2 is not drawn: b (other p0) names a device this file does not draw.\n"
        "- Cable k3 is not drawn: a (rear/p0) is on a face this file does not draw.")
