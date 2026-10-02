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
