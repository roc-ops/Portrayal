"""The kit's Visio writer keeps every port findable in the .vsdx it writes.

The acceptance test of the exporter tab is one question: can a named port still
be found in the exported file? Here the file is a zip of XML, so the test opens
it as one, reads each part with an XML parser, and looks for the port by the
name the drawing gives it: as the shape's name and as a row of its Shape Data.

The script (js/visio-export.mjs) runs buildVsdx on hand-built zones and hands
the file back as base64. Reading a face out of an SVG and drawing it to a PNG
need a real DOM and canvas, and are the browser's to check; so is opening the
file in Visio.
"""
import base64
import io
import json
import posixpath
import shutil
import subprocess
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "tests/js/visio-export.mjs"

V = "http://schemas.microsoft.com/office/visio/2011/1/core"   # [MS-VSDX] 2.3.3
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG = "http://schemas.openxmlformats.org/package/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"
IN = 25.4          # millimetres to an inch: Visio draws in inches, y up

# the zones of the script, in its order of writing
PATHS = ["slot-1", "slot-2", "a&b <c> \"d\"", "port-1", "slot-1/module/p0"]
BAYS = ["slot-1", "slot-2"]


def near(v):
    # the file gives an inch to six places
    return pytest.approx(v, abs=2e-6)


@pytest.fixture(scope="module")
def out():
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    p = subprocess.run(["node", str(SCRIPT)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


@pytest.fixture(scope="module")
def zf(out):
    return zipfile.ZipFile(io.BytesIO(base64.b64decode(out["vsdx"])))


def xml(zf, name):
    return ET.fromstring(zf.read(name))


def shapes(zf, page=1):
    root = xml(zf, f"visio/pages/page{page}.xml")
    return {s.get("NameU"): s for s in root.iter(f"{{{V}}}Shape")}


def cell(shape, name):
    for c in shape.findall(f"{{{V}}}Cell"):
        if c.get("N") == name:
            return c
    return None


def data(shape):
    """A shape's Shape Data as {label: value}."""
    got = {}
    for sec in shape.findall(f"{{{V}}}Section"):
        if sec.get("N") != "Property":
            continue
        for row in sec.findall(f"{{{V}}}Row"):
            got[cell(row, "Label").get("V")] = cell(row, "Value").get("V")
    return got


def test_a_vsdx_is_a_stored_zip_that_opens_with_its_content_types(zf):
    assert zf.testzip() is None                       # every CRC holds
    assert zf.namelist()[0] == "[Content_Types].xml"
    assert {i.compress_type for i in zf.infolist()} == {zipfile.ZIP_STORED}


def test_the_parts_are_exactly_the_ones_the_drawing_needs(zf):
    # no master, no stencil: nothing but the drawing, its pages and their pictures
    assert sorted(zf.namelist()) == sorted([
        "[Content_Types].xml", "_rels/.rels", "docProps/core.xml",
        "visio/document.xml", "visio/_rels/document.xml.rels",
        "visio/pages/pages.xml", "visio/pages/_rels/pages.xml.rels",
        "visio/pages/page1.xml", "visio/pages/_rels/page1.xml.rels",
        "visio/pages/page2.xml", "visio/pages/_rels/page2.xml.rels",
        "visio/media/image1.png", "visio/media/image2.png",
    ])


def test_every_xml_part_parses_and_every_part_has_a_content_type(zf):
    types = xml(zf, "[Content_Types].xml")
    default = {d.get("Extension"): d.get("ContentType") for d in types.iter(f"{{{CT}}}Default")}
    override = {o.get("PartName"): o.get("ContentType") for o in types.iter(f"{{{CT}}}Override")}
    for name in zf.namelist():
        if name == "[Content_Types].xml":
            continue
        if name.endswith((".xml", ".rels")):
            ET.fromstring(zf.read(name))              # well formed
        ext = name.rsplit(".", 1)[1]
        assert "/" + name in override or ext in default, f"{name} has no content type"
    assert override["/visio/document.xml"] == "application/vnd.ms-visio.drawing.main+xml"
    assert override["/visio/pages/pages.xml"] == "application/vnd.ms-visio.pages+xml"
    assert override["/visio/pages/page1.xml"] == "application/vnd.ms-visio.page+xml"
    assert default["png"] == "image/png"


def test_every_relationship_points_at_a_part_that_is_there(zf):
    names = set(zf.namelist())
    for rels in [n for n in names if n.endswith(".rels")]:
        base = posixpath.dirname(posixpath.dirname(rels))
        for r in xml(zf, rels).iter(f"{{{PKG}}}Relationship"):
            target = posixpath.normpath(posixpath.join(base, r.get("Target")))
            assert target in names, f"{rels}: {r.get('Target')}"
    root = {r.get("Type").rsplit("/", 1)[1]: r.get("Target")
            for r in xml(zf, "_rels/.rels").iter(f"{{{PKG}}}Relationship")}
    assert root["document"] == "visio/document.xml"


def test_a_named_port_is_found_in_the_file(zf):
    # THE ACCEPTANCE TEST of the exporter tab: the shape is called by the port's
    # address, and the address is in its Shape Data too, for a script to read
    for page in (1, 2):
        got = shapes(zf, page)
        for path in PATHS:
            assert path in got, f"page {page}: no shape named {path!r}"
            assert data(got[path])["portrayal-path"] == path
            assert got[path].get("Name") == path


def test_draw_io_finds_nothing_that_visio_does_not(out, zf):
    # the ports draw.io writes cells for, by their address
    assert sorted(out["drawioNames"]) == sorted(p for p in PATHS if p not in BAYS)
    assert set(out["drawioNames"]) <= set(shapes(zf))


def test_a_shape_says_what_the_drawing_says_of_its_port(zf):
    d = data(shapes(zf)["port-1"])
    assert d == {"portrayal-path": "port-1", "portrayal-class": "port",
                 "portrayal-group": "uplink", "portrayal-media": "sfp+",
                 "portrayal-speed": "10G"}
    b = data(shapes(zf)["slot-1"])
    assert b["portrayal-class"] == "bay" and b["portrayal-model"] == "x/card@1"


def test_a_shape_is_where_its_zone_is_in_inches_with_y_up(zf):
    page = xml(zf, "visio/pages/pages.xml").find(f"{{{V}}}Page")
    sheet = {c.get("N"): float(c.get("V")) for c in page.find(f"{{{V}}}PageSheet").findall(f"{{{V}}}Cell")
             if c.get("N") in ("PageWidth", "PageHeight")}
    assert sheet == near({"PageWidth": 18 / IN, "PageHeight": 14 / IN})
    got = shapes(zf)
    # viewBox 0 -4.5 18 14: port-1 (0, -4.5, 4 x 2) is the top left corner
    p = got["port-1"]
    assert float(cell(p, "Width").get("V")) == near(4 / IN)
    assert float(cell(p, "Height").get("V")) == near(2 / IN)
    assert float(cell(p, "PinX").get("V")) == near(2 / IN)
    assert float(cell(p, "PinY").get("V")) == near((14 - 1) / IN)
    # slot-1 (10, 0, 8 x 9.5): its centre is 4.5 + 4.75 mm from the top
    s = got["slot-1"]
    assert float(cell(s, "PinX").get("V")) == near(14 / IN)
    assert float(cell(s, "PinY").get("V")) == near((14 - 9.25) / IN)


def test_each_shape_has_one_connection_point_dead_centre(zf):
    for name, s in shapes(zf).items():
        if s.get("Type") == "Foreign":              # the picture takes no cable
            continue
        sec = [x for x in s.findall(f"{{{V}}}Section") if x.get("N") == "Connection"]
        assert len(sec) == 1, name
        rows = sec[0].findall(f"{{{V}}}Row")
        assert len(rows) == 1, name
        x, y = cell(rows[0], "X"), cell(rows[0], "Y")
        # a formula, so the point stays centred when the shape is resized
        assert (x.get("F"), y.get("F")) == ("Width*0.5", "Height*0.5")
        assert float(x.get("V")) == near(float(cell(s, "Width").get("V")) / 2)
        assert float(y.get("V")) == near(float(cell(s, "Height").get("V")) / 2)


def test_the_face_is_the_picture_behind_bays_and_ports(zf):
    root = xml(zf, "visio/pages/page1.xml")
    order = [s.get("NameU") for s in root.iter(f"{{{V}}}Shape")]
    # Visio paints the first shape underneath: picture, bays, then ports
    assert order[0] == "S9510 front face"
    assert [n for n in order if n in BAYS] == BAYS
    assert max(order.index(b) for b in BAYS) < min(order.index(p) for p in PATHS if p not in BAYS)
    pic = shapes(zf)["S9510 front face"]
    assert pic.get("Type") == "Foreign"
    fd = pic.find(f"{{{V}}}ForeignData")
    assert (fd.get("ForeignType"), fd.get("CompressionType")) == ("Bitmap", "PNG")
    rid = fd.find(f"{{{V}}}Rel").get(f"{{{R}}}id")
    rels = {r.get("Id"): r.get("Target")
            for r in xml(zf, "visio/pages/_rels/page1.xml.rels").iter(f"{{{PKG}}}Relationship")}
    assert zf.read(posixpath.normpath(posixpath.join("visio/pages", rels[rid]))).startswith(b"\x89PNG")


def test_the_picture_says_which_drawing_it_is(zf):
    d = data(shapes(zf)["S9510 front face"])
    assert d == {"portrayal-device": "ufispace/s9510@1", "portrayal-face": "front",
                 "portrayal-version": "1.2.0", "portrayal-generated": "2026-10-02"}


def test_shape_ids_are_whole_numbers_that_do_not_repeat(zf):
    for page in (1, 2):
        ids = [s.get("ID") for s in xml(zf, f"visio/pages/page{page}.xml").iter(f"{{{V}}}Shape")]
        assert all(i.isdigit() and int(i) >= 4 for i in ids)   # [MS-VSDX] 2.3.4.2.88: 4 or more
        assert len(ids) == len(set(ids))


def test_a_page_a_drawing_named_by_its_label(zf):
    pages = xml(zf, "visio/pages/pages.xml").findall(f"{{{V}}}Page")
    assert [p.get("Name") for p in pages] == ["S9510 front", "second"]
    assert [shapes(zf, 2)[n].get("NameU") for n in ("second face",)] == ["second face"]


def test_the_same_drawing_is_the_same_bytes(out):
    assert out["stable"] is True


def test_the_module_exports_its_writer_and_the_browser_entry(out):
    assert {"buildVsdx", "toVisio"} <= set(out["exports"])
