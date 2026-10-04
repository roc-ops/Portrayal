"""Each compiled face publishes its elements file (#727).

`<device>[.<config>].<view>.elements.json` beside every face lists each row the
face draws - address, class, ref, media, states, owners, box, connection points
and tree parent - so an embedder reads the tree instead of rebuilding it from
the SVG. Two halves are pinned here:

- the arithmetic, on drawings small enough to check by hand: boxes through
  rotations, arcs and curves, and the nesting fallbacks one by one;
- the published build: every face has its file, the default copy is the same
  bytes, the header is the face's own metadata, and each file is exactly what
  reading its SVG back gives - so the build's in-memory tree and the bytes on
  disk cannot have drifted apart.

Parity with the Explorer's own tree is test_face_elements_parity.py.
"""
import json
import os
import pathlib
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

from portrayal import elements as E

ROOT = pathlib.Path(__file__).resolve().parents[2]
DIST = ROOT / "library" / "dist"
NS = 'xmlns="http://www.w3.org/2000/svg"'


def doc(body, view="front", vb="0 0 100 50", meta=None):
    meta = meta or {"source-sha256": "ab", "device-version": "1.0.0",
                    "resolved-components": {"std/x@1": "1.2.3"},
                    "generator": {"tool": "portrayal-render", "version": "0.1.0"}}
    svg = ET.fromstring(f'<svg {NS} viewBox="{vb}" data-device="dev" data-view="{view}">'
                        f'<metadata>{json.dumps(meta)}</metadata>{body}</svg>')
    return E.face_elements(svg, "base", view, ["base"])


def rows(d):
    return {r.get("path", r.get("of")): r for r in d["elements"]}


# ---- boxes --------------------------------------------------------------

def box(shape, transform=""):
    t = f' transform="{transform}"' if transform else ""
    return rows(doc(f'<g data-path="p"{t}>{shape}</g>'))["p"]["box"]


def test_a_rect_through_a_rotation_takes_its_turned_corners():
    # 10 x 4 at the origin, turned a quarter about (0,0): x from -4 to 0
    assert box('<rect width="10" height="4"/>', "translate(20,5) rotate(90)") == \
        {"x": 16.0, "y": 5.0, "w": 4.0, "h": 10.0}


def test_a_circle_under_a_rotation_keeps_its_radius_not_its_square():
    # a 45-degree turn would put a corner-walked box out to r*sqrt(2)
    assert box('<circle cx="0" cy="0" r="2"/>', "rotate(45)") == \
        {"x": -2.0, "y": -2.0, "w": 4.0, "h": 4.0}


def test_a_scaled_ellipse():
    assert box('<ellipse cx="1" cy="1" rx="3" ry="1"/>', "scale(2)") == \
        {"x": -4.0, "y": 0.0, "w": 12.0, "h": 4.0}


def test_an_arc_counts_only_the_extremes_it_sweeps():
    # a quarter circle from (10,0) to (0,10) about the origin, sweeping through
    # positive angles: never left of 0 or above 0, out to 10 on both axes
    assert box('<path d="M10 0 A10 10 0 0 1 0 10"/>') == {"x": 0.0, "y": 0.0, "w": 10.0, "h": 10.0}
    # the same ends the long way round reach -10 on both axes
    assert box('<path d="M10 0 A10 10 0 1 0 0 10"/>') == {"x": -10.0, "y": -10.0, "w": 20.0, "h": 20.0}


def test_a_semicircle_bulges_past_its_chord():
    # the RJ45 latch shape: a chord from (0,5) to (10,5) and a half-disc above it
    assert box('<path d="M0 5 a5 5 0 0 1 10 0 Z"/>') == {"x": 0.0, "y": 0.0, "w": 10.0, "h": 5.0}


def test_packed_arc_flags_are_read_one_digit_each():
    assert box('<path d="M0 5a5 5 0 0110 0z"/>') == {"x": 0.0, "y": 0.0, "w": 10.0, "h": 5.0}


def test_a_cubic_box_is_its_curve_not_its_control_points():
    # control points at y=10 pull the curve only to y=7.5
    assert box('<path d="M0 0 C0 10 10 10 10 0"/>') == {"x": 0.0, "y": 0.0, "w": 10.0, "h": 7.5}


def test_relative_and_shorthand_commands():
    assert box('<path d="M1 1 h4 v2 H1 z"/>') == {"x": 1.0, "y": 1.0, "w": 4.0, "h": 2.0}
    assert box('<polygon points="0,0 4,0 2,3"/>') == {"x": 0.0, "y": 0.0, "w": 4.0, "h": 3.0}


def test_text_and_inert_subtrees_have_no_box():
    """A glyph run's extent needs a font, and a clip path paints nothing where
    it stands. Neither is guessed."""
    r = rows(doc('<text data-path="silk:0" x="5" y="5">LINK</text>'
                 '<g data-path="g"><clipPath id="c"><rect width="99" height="99"/></clipPath>'
                 '<rect x="1" y="1" width="2" height="2"/></g>'))
    assert r["silk:0"]["box"] is None
    assert r["g"]["box"] == {"x": 1.0, "y": 1.0, "w": 2.0, "h": 2.0}


def test_a_row_box_holds_its_children():
    r = rows(doc('<g data-path="a" transform="translate(10,0)"><rect width="1" height="1"/>'
                 '<g data-path="a/b" transform="translate(5,5)"><rect width="2" height="2"/></g></g>'))
    assert r["a/b"]["box"] == {"x": 15.0, "y": 5.0, "w": 2.0, "h": 2.0}
    assert r["a"]["box"] == {"x": 10.0, "y": 0.0, "w": 7.0, "h": 7.0}


# ---- fields, connection points and seats ----------------------------------

def test_fields_are_the_svgs_own():
    r = rows(doc('<g data-path="port-1" id="port-1" data-class="port" data-ref="std/x@1:1.2.3" '
                 'data-media="sfp-plus" data-speed="10g" data-group="g" data-group-role="traffic" '
                 'data-rel-pos="1" data-inner="1" data-states="off link" data-for="a /rear/b">'
                 '<rect width="1" height="1"/></g>'))["port-1"]
    assert r == {"path": "port-1", "parent": None, "id": "port-1", "class": "port",
                 "ref": "std/x@1:1.2.3", "media": "sfp-plus", "speed": "10g", "group": "g",
                 "group-role": "traffic", "rel-pos": "1", "inner": True,
                 "states": ["off", "link"], "for": ["a", "/rear/b"],
                 "box": {"x": 0.0, "y": 0.0, "w": 1.0, "h": 1.0}}


def test_connection_points_land_on_the_face():
    r = rows(doc('<g data-path="p" transform="translate(10,20) rotate(90)">'
                 '<rect width="4" height="2"/>'
                 '<g data-cp="mate" data-cp-at="1 2" data-cp-dir="front"/></g>'))["p"]
    assert r["connection-points"] == {"mate": {"at": [1.0, 2.0], "face": [8.0, 21.0], "dir": "front"}}


def test_seated_rows_name_their_seat_and_the_chassis_names_none():
    r = rows(doc('<g data-path="chassis"><rect width="1" height="1"/></g>'
                 '<g data-path="slot-1" data-class="bay">'
                 '<g data-path="slot-1/module"><g data-path="slot-1/module/p0"/>'
                 '<g data-path="slot-1/module/p0-occupant" data-behaviour="occupies" '
                 'data-for="slot-1/module/p0"/></g></g>'))
    assert "seat" not in r["chassis"] and "seat" not in r["slot-1"]
    assert r["slot-1/module"]["seat"] == "slot-1"
    assert r["slot-1/module/p0"]["seat"] == "slot-1"
    assert r["slot-1/module/p0-occupant"]["seat"] == "slot-1/module/p0"


# ---- the tree ---------------------------------------------------------------

def parents(body):
    return {k: v["parent"] for k, v in rows(doc(body)).items()}


def test_nesting_by_prefix_then_each_fallback():
    p = parents(
        '<g data-path="chassis"/>'
        '<g data-path="port-1"/><g data-path="port-1/opening"/>'
        # a cutout something fills nests under it; one nothing names stays
        '<g data-path="cutout:port-1"/><g data-path="cutout:esd"/>'
        # one local owner; a placed part naming several is not its first one's
        '<g data-path="led-1" data-for="port-1"/>'
        '<g data-path="cover" data-ref="x@1:1.0.0" data-for="port-1 port-2"/>'
        '<g data-path="legend" data-for="port-1 port-2"/>'
        # a lamp whose only target is in another view is the chassis's
        '<g data-path="led-ps" data-for="/rear/psu-1"/>'
        # a projection lists under what it is seen through
        '<g data-path="cutout:back-1"><g data-of="bay-1/module" data-projection="1">'
        '<g data-of="bay-1/module/mtp1"/></g></g>')
    assert p == {"chassis": None, "port-1": None, "port-1/opening": "port-1",
                 "cutout:port-1": "port-1", "cutout:esd": None, "led-1": "port-1",
                 "cover": "chassis", "legend": "port-1", "led-ps": "chassis",
                 "cutout:back-1": None, "bay-1/module": "cutout:back-1",
                 "bay-1/module/mtp1": "bay-1/module"}


def test_a_projection_of_a_part_this_face_draws_is_that_part():
    r = rows(doc('<g data-path="psu-1"/><g data-of="psu-1" data-projection="1"/>'))
    assert list(r) == ["psu-1"] and "of" not in r["psu-1"]


def test_the_header_is_the_faces_metadata():
    d = doc("", vb="-2 0 104.5 50")
    assert {k: v for k, v in d.items() if k != "elements"} == {
        "device": "dev", "device-version": "1.0.0", "view": "front", "config": "base",
        "configs": ["base"], "viewBox": [-2.0, 0.0, 104.5, 50.0], "source-sha256": "ab",
        "components": {"std/x@1": "1.2.3"},
        "generator": {"tool": "portrayal-render", "version": "0.1.0"}}


def test_the_bytes_are_deterministic():
    body = '<g data-path="b"/><g data-path="a"><rect width="1.23456789" height="-0"/></g>'
    assert E.dumps(doc(body)) == E.dumps(doc(body))
    assert E.dumps(doc(body)).endswith("}\n")
    assert [r["path"] for r in doc(body)["elements"]] == ["b", "a"], "rows are document order"


# ---- --if-stale -------------------------------------------------------------

def test_if_stale_writes_a_missing_elements_file(tmp_path):
    """A dist from before #727 has every SVG and no elements file. `--fast`
    must see that as stale, or the files never appear until a full build."""
    yml = next(ROOT.glob("library/devices/*/agr110/device.yaml"))
    cmd = [sys.executable, str(ROOT / "spec/tools/portrayal/render.py"), str(yml),
           "--library", str(ROOT / "library"), "--out", str(tmp_path)]
    env = {**os.environ, "PYTHONPATH": str(ROOT / "spec/tools")}
    subprocess.run(cmd, check=True, capture_output=True, env=env)
    target = tmp_path / "agr110.ac.front.elements.json"
    first = target.read_bytes()
    target.unlink()
    out = subprocess.run(cmd + ["--if-stale"], check=True, capture_output=True, text=True, env=env)
    assert "up to date" not in out.stdout
    assert target.read_bytes() == first, "a rebuild must write the same bytes"
    out = subprocess.run(cmd + ["--if-stale"], check=True, capture_output=True, text=True, env=env)
    assert "up to date" in out.stdout


# ---- the published build ---------------------------------------------------

def _indexes():
    found = sorted(DIST.glob("*.configs.json"))
    if not found:
        pytest.skip("library/dist not built - run ./build.sh")
    return [json.loads(p.read_text()) for p in found]


def test_every_face_has_its_elements_file_and_the_default_copy_is_the_same_bytes():
    checked = 0
    for idx in _indexes():
        dev = idx["device"]
        for c in idx["configs"]:
            for view, name in c["files"].items():
                ej = DIST / E.elements_name(name)
                assert ej.exists(), f"{name} has no {ej.name}"
                d = json.loads(ej.read_text())
                assert c["name"] in d["configs"], f"{ej.name} does not list {c['name']}"
                assert d["view"] == view and d["device"] == dev
                if c["name"] == idx["default"]:
                    copy = DIST / f"{dev}.{view}.elements.json"
                    assert copy.read_bytes() == ej.read_bytes(), copy.name
                checked += 1
    assert checked > 1000, f"only {checked} faces checked; the build is not the library"


def test_no_elements_file_without_its_face():
    orphans = sorted(p.name for p in DIST.glob("*.elements.json")
                     if not (DIST / (p.name[:-len(".elements.json")] + ".svg")).exists())
    _indexes()
    assert not orphans, f"elements files with no SVG beside them: {orphans[:5]}"


def test_each_file_is_what_its_svg_says():
    """Read every published face back with xml.etree and compare bytes. The
    build writes from the tree in memory; this proves the file a consumer
    holds agrees with the SVG a consumer holds."""
    _indexes()
    faces = sorted(p for p in DIST.glob("*.svg") if len(p.name.split(".")) == 4)
    assert faces, "no faces in dist - run ./build.sh"
    rows_seen = 0
    for svg in faces:
        ej = DIST / E.elements_name(svg.name)
        pub = ej.read_text()
        head = json.loads(pub)
        again = E.face_elements(ET.parse(svg).getroot(), head["config"], head["view"],
                                head["configs"])
        assert E.dumps(again) == pub, f"{ej.name} differs from reading {svg.name}"
        meta = json.loads(next(e for e in ET.parse(svg).getroot()
                               if e.tag.endswith("metadata")).text)
        assert head["source-sha256"] == meta["source-sha256"]
        assert head["components"] == meta["resolved-components"]
        rows_seen += len(head["elements"])
    assert rows_seen > 100000, f"only {rows_seen} rows across {len(faces)} faces"
