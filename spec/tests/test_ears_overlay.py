"""The kit's 2D rack-ear overlay is render.py's `--with ears` (#909).

A published face has no ears, so a page that offers them as a choice (the
Explorer and Annotate off by default, the Rack Builder on) draws them itself,
with kit/ears2d.js, over the face it holds. These tests draw a real device's
six faces twice in Python - as published, and `--with ears` - hand the
published ones to the kit, and require the kit's overlay to carry the same
shapes, with the same attributes, and to grow the viewBox to the same box.
"""
import copy
import json
import pathlib
import shutil
import subprocess
import xml.etree.ElementTree as ET

import pytest
import yaml

from portrayal import ears
from portrayal import render

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
KIT = ROOT / "kit"
SCRIPT = ROOT / "spec/tests/js/ears-overlay.mjs"
SVG = "{http://www.w3.org/2000/svg}"
VIEWS = ("front", "rear", "left", "right", "top", "bottom")
ROOT_KEYS = ("viewBox", "width", "height", "data-face-w", "data-face-h")


def _doc(name, ears_=None):
    doc = yaml.safe_load((LIB / "devices" / name / "device.yaml").read_text())
    if ears_ is not None:
        doc = copy.deepcopy(doc)
        doc["chassis"]["ears"] = ears_
    return doc


# a 1U switch; a 2U router whose sizes are not round numbers; and the 1U with
# its ears stated - a part-height ear lifted off the bottom, its flange set
# back - so the leg and the edge views move off the front
DEVICES = {
    "dcs240": ("edgecore/dcs240", None),
    "asr-9901": ("cisco/asr-9901", None),
    "dcs240-stated": ("edgecore/dcs240", {"h": 40.0, "y": 2.5, "positions": [
        {"name": "flush", "at": 0}, {"name": "proud", "at": 25.4, "default": True}]}),
}


def _chassis(doc):
    """configs.json's `chassis`, the part of it genericEars reads."""
    ch = doc["chassis"]
    out = {"w": ch.get("width"), "h": ch.get("height"), "d": ch.get("depth"),
           "ru": ch.get("ru"), "mount": ch.get("mount", "rack")}
    if ch.get("shell"):
        out["shell"] = ch["shell"]
    if ch.get("ears"):
        out["ears"] = render.published_ears(ch["ears"])
    return out


def _spec(el):
    """An element as fake-dom's JSON tree."""
    return {"t": el.tag.replace(SVG, ""), "a": dict(el.attrib),
            "c": [_spec(c) for c in el if isinstance(c.tag, str)]}


def _render(doc, view, include):
    return render.render_view(doc, view, doc["views"][view], render.Library([str(LIB)]),
                              include=include)


@pytest.fixture(scope="module")
def drawn():
    """Every case's six faces, published and `--with ears`, and the kit's
    overlay over each published one."""
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    cases, want, bare = [], {}, {}
    for key, (name, ears_) in DEVICES.items():
        doc = _doc(name, ears_)
        assert ears.plan(doc), key          # a device the ear is drawn for
        front = ET.tostring(_render(doc, "front", ()), encoding="unicode")
        for view in VIEWS:
            plain = _render(doc, view, ())
            withe = _render(doc, view, ("ears",))
            case = f"{key}/{view}"
            # the overlay needs only the root: it reads the viewBox and the
            # declared face, and appends after whatever the drawing holds
            cases.append({"name": case, "meta": {"chassis": _chassis(doc)}, "front": front,
                          "view": view, "root": {"t": "svg", "a": dict(plain.attrib), "c": []}})
            want[case] = withe
            bare[case] = plain
    p = subprocess.run(["node", str(SCRIPT)], input=json.dumps({"cases": cases}),
                       capture_output=True, text=True, cwd=str(SCRIPT.parent), timeout=120)
    assert p.returncode == 0, p.stderr
    got = json.loads(p.stdout.strip().splitlines()[-1])
    return got, want, bare


def _overlay(spec):
    hosts = [c for c in spec["c"] if c["a"].get("data-overlay") == "ears"]
    assert len(hosts) <= 1
    return hosts[0]["c"] if hosts else []


@pytest.mark.parametrize("case", [f"{k}/{v}" for k in DEVICES for v in VIEWS])
def test_the_overlay_is_what_render_py_draws_with_ears(drawn, case):
    got, want, _bare = drawn
    g = got[case]
    assert "error" not in g, g.get("error")
    py = [el for el in want[case] if el.get("data-generic") == "ear"]
    js = _overlay(g["drawn"])
    # the comparison compares something: both ears, every shape
    assert [e.get("id") for e in py] == [e["a"]["id"] for e in js]
    assert py and g["n"] == sum(len(list(e)) for e in py) > 0
    for pe, je in zip(py, js):
        assert je["a"]["data-generic"] == "ear"
        kids = [_spec(k) for k in pe]
        assert [k["t"] for k in kids] == [k["t"] for k in je["c"]]
        for pk, jk in zip(kids, je["c"]):
            assert pk["a"] == jk["a"], (pk["a"].get("id"), pk["a"], jk["a"])
    # the root grows to the same box, and still names its face
    for k in ROOT_KEYS:
        assert g["drawn"]["a"].get(k) == want[case].get(k), k


@pytest.mark.parametrize("case", [f"{k}/{v}" for k in DEVICES for v in VIEWS])
def test_the_overlay_is_no_part_and_comes_off_cleanly(drawn, case):
    got, _want, bare = drawn
    g = got[case]
    host = [c for c in g["drawn"]["c"] if c["a"].get("data-overlay") == "ears"]
    assert host and host[0]["a"]["pointer-events"] == "none"

    def walk(n):
        yield n
        for c in n["c"]:
            yield from walk(c)
    # nothing in it is a part a reader can pick, list or wire to
    for n in walk(host[0]):
        assert "data-path" not in n["a"] and "data-class" not in n["a"]
    assert g["again"] == g["n"] and g["twice"] == 1
    assert g["cleared"]["c"] == []
    assert {k: g["cleared"]["a"].get(k) for k in ROOT_KEYS} == \
        {k: bare[case].get(k) for k in ROOT_KEYS}


def test_the_stated_ear_moved_the_side_views():
    """The third case is not the first again: its leg starts at the setback."""
    p = ears.plan(_doc(*DEVICES["dcs240-stated"]))
    assert (p["at"], p["h"], p["y"]) == (25.4, 40.0, 2.5)


def test_a_device_without_a_generic_ear_gets_no_overlay():
    """The R740xd's front is ear-wide: its ears are in the face, always shown."""
    doc = _doc("dell/r740xd")
    assert ears.plan(doc) is None
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    front = ET.tostring(_render(doc, "front", ()), encoding="unicode")
    case = {"name": "r740xd", "meta": {"chassis": _chassis(doc)}, "front": front,
            "view": "rear", "root": {"t": "svg", "a": {"viewBox": "0 0 434 86.8"}, "c": []}}
    p = subprocess.run(["node", str(SCRIPT)], input=json.dumps({"cases": [case]}),
                       capture_output=True, text=True, cwd=str(SCRIPT.parent), timeout=60)
    assert p.returncode == 0, p.stderr
    got = json.loads(p.stdout.strip().splitlines()[-1])["r740xd"]
    # the REAR is 434 wide; only the front's 482.6 says the ears are built in
    assert got["plan"] is None and got["n"] == 0 and got["drawn"]["c"] == []


def test_the_explorer_wires_the_toggle():
    """kit/index.html: off unless the reader turned it on, remembered per
    viewer, shown only for a device that gets an ear, and handed to both
    stages."""
    page = (KIT / "index.html").read_text()
    assert "from './ears2d.js'" in page
    assert "localStorage.getItem(EARS_KEY)" in page and "EARS_KEY = 'portrayal.ears'" in page
    assert "let earsOn = false" in page
    assert "createViewer(host3d, { dist: DIST, background: shell.stage(), ears: earsOn })" in page
    assert "viewer.setEars(" in page
    assert "drawEars(svg, plan, state.view)" in page
