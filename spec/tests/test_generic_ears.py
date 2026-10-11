"""A generic L-bracket rack ear drawn from `chassis.ears` (roc-ops/Portrayal#909).

ears.py says which devices get one and what it is; render.py draws it on the
six faces under `--with ears`, the tag `common/rack-ear@1` is drawn under; the
kit's relief.js `genericEars` makes the same plan from configs.json and
viewer3d builds it when a host asks for `ears`. The default build draws no
ears, so nothing published moves - and the tests below hold that too.
"""
import json
import pathlib
import shutil
import subprocess
import xml.etree.ElementTree as ET

import pytest
import yaml

from portrayal import devicelock as dl
from portrayal import ears
from portrayal import lint
from portrayal import render

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
KIT = ROOT / "kit"
SCRIPT = ROOT / "spec/tests/js/generic-ears.mjs"
NS = {"s": "http://www.w3.org/2000/svg"}


def _device(w=440.0, h=44.0, **chassis):
    return {"format": 1, "kind": "device", "name": "d", "version": "1.0.0",
            "manufacturer": "M", "model": "M", "maturity": "modelled",
            "profile": "networking",
            "chassis": {"width": w, "height": h, "depth": 500.0, "ru": 1, **chassis},
            "views": {"front": {"size": {"w": w, "h": h}}}}


def _real(name):
    return yaml.safe_load((LIB / "devices" / name / "device.yaml").read_text())


# --- which devices get one -------------------------------------------------------

def test_a_plain_rack_box_gets_a_pair_reaching_the_rack_face():
    p = ears.plan(_device())
    assert p["flange"] == pytest.approx((482.6 - 440) / 2)
    assert p["w"] + 2 * p["flange"] == pytest.approx(482.6)
    assert (p["h"], p["y"], p["at"]) == (44.0, 0.0, 0.0)


@pytest.mark.parametrize("chassis", [
    {"mount": "din-rail"}, {"mount": "rack-face"}, {"mount": "rack-side"},
    {"ears": "behind"}, {"ears": {"behind": True}}, {"shell": "sheet"}])
def test_no_ear_where_the_device_says_it_has_none_or_is_its_ears(chassis):
    assert ears.plan(_device(**chassis)) is None


def test_an_ear_wide_face_already_has_its_ears():
    """L43's case: the R740xd's 482.6 mm front carries its VGA in an ear."""
    assert ears.plan(_device(w=482.6)) is None
    assert ears.plan(_real("dell/r740xd")) is None


def test_a_device_placing_rack_ear_gets_no_second_pair():
    doc = _device()
    doc["views"]["front"]["placements"] = [
        {"ref": "common/rack-ear@1", "id": "ear-left", "at": [-14, 0], "optional": "ears"}]
    assert ears.plan(doc) is None
    assert ears.plan(_real("edgecore/as5912-54x")) is None


@pytest.mark.parametrize("placement", [
    {"ref": "common/blank@1", "id": "x", "optional": "ears"},   # the include tag alone
    {"ref": "common/rack-ear@1", "id": "x"},                     # the ref alone
    {"ref": "common/blank@1", "id": "ear-right"},                # the id alone
])
def test_each_sign_of_its_own_ears_is_enough_alone(placement):
    """_places_own_ears answers yes to any ONE of the three signs, wherever in
    the views it sits; a placement with none of them leaves the generic pair."""
    doc = _device()
    doc["views"]["rear"] = {"components": {"placements": [placement]}}
    assert ears.plan(doc) is None
    doc["views"]["rear"]["components"]["placements"] = [{"ref": "common/blank@1", "id": "x"}]
    assert ears.plan(doc) is not None


def test_the_ear_is_silver_unless_the_device_says_otherwise():
    """Owner, 2026-10-09: most gear has silver ears even on a black face."""
    assert ears.plan(_device(color="#1b1e21"))["color"] == ears.SILVER == "#c8cacc"
    assert ears.plan(_device(ears={"color": "#2a2c2e"}))["color"] == "#2a2c2e"
    assert render.published_ears({"color": "#2a2c2e", "h": 40})["color"] == "#2a2c2e"
    assert "color" not in render.published_ears({"h": 40})


def test_changing_the_ears_colour_is_a_patch():
    before = dl.entry(_device(ears={"h": 43.5}))
    after = dl.entry(_device(ears={"h": 43.5, "color": "#1b1e21"}))
    assert before["shape"] == after["shape"]
    assert dl.required_bump(before, after) == "patch"


def test_stated_h_and_y_size_the_ear():
    p = ears.plan(_device(h=88.9, ru=2, ears={"h": 43.5, "y": 0.15}))
    assert (p["h"], p["y"]) == (43.5, 0.15)
    assert len(p["slots"]) == 2                 # one U of ear: two slots


def test_a_stated_y_alone_runs_the_ear_to_the_top():
    p = ears.plan(_device(h=88.9, ru=2, ears={"y": 10}))
    assert (p["y"], p["h"]) == (10.0, pytest.approx(78.9))


def test_a_2u_ear_has_two_slots_a_u():
    p = ears.plan(_device(h=87.0, ru=2))
    assert len(p["slots"]) == 4
    assert p["slots"] == sorted(p["slots"]) and 0 < p["slots"][0] and p["slots"][-1] < 87


def test_the_default_position_sets_the_flange_plane():
    p = ears.plan(_device(ears={"positions": [{"name": "flush", "at": 0},
                                              {"name": "proud", "at": 40, "default": True}]}))
    assert p["at"] == 40.0
    assert ears.leg_span(p) == (40.0, 70.0)
    # a bracket reaching forward still bolts LEG of itself onto the body
    assert ears.leg_span({**p, "at": -25.4}) == (-25.4, 30.0)


# --- the six faces ----------------------------------------------------------------

def test_front_and_rear_show_the_flanges_beyond_the_body_mirrored():
    p = ears.plan(_device())
    front = {(s, k): (x, y, w, h) for s, k, x, y, w, h in ears.rects(p, "front", 440, 44)
             if k == "flange"}
    rear = {(s, k): (x, y, w, h) for s, k, x, y, w, h in ears.rects(p, "rear", 440, 44)
            if k == "flange"}
    assert front[("ear-left", "flange")][0] == pytest.approx(-21.3)
    assert front[("ear-right", "flange")][0] == 440
    assert rear[("ear-left", "flange")][0] == 440     # seen from behind
    slots = [r for r in ears.rects(p, "front", 440, 44) if r[1] == "slot"]
    # each slot sits on the rail hole: 465.1 mm apart across the rack
    lx = min(r[2] + r[4] / 2 for r in slots)
    rx = max(r[2] + r[4] / 2 for r in slots)
    assert rx - lx == pytest.approx(465.1)


def test_the_sides_show_the_leg_at_the_front_end():
    p = ears.plan(_device())
    left = {k: (x, w) for _s, k, x, _y, w, _h in ears.rects(p, "left", 500, 44)}
    right = {k: (x, w) for _s, k, x, _y, w, _h in ears.rects(p, "right", 500, 44)}
    assert left["leg"] == (470.0, 30.0)         # the front is the left view's right end
    assert right["leg"] == (0.0, 30.0)
    assert right["edge"] == (-2.0, 2.0)         # the flange, edge on, ahead of the plane


def test_the_top_and_underside_are_mirrored():
    """The underside is authored mirrored, so the device's left ear is at the
    drawing's right there, and at its left on the top."""
    p = ears.plan(_device())
    top = {(s, k): x for s, k, x, _y, _w, _h in ears.rects(p, "top", 440, 500)}
    bottom = {(s, k): x for s, k, x, _y, _w, _h in ears.rects(p, "bottom", 440, 500)}
    assert top[("ear-left", "leg")] == -2.0 and top[("ear-left", "edge")] == pytest.approx(-21.3)
    assert top[("ear-right", "leg")] == 440 and top[("ear-right", "edge")] == 440
    assert bottom[("ear-left", "leg")] == 440 and bottom[("ear-left", "edge")] == 440
    assert bottom[("ear-right", "leg")] == -2.0


def test_a_narrow_flange_narrows_the_slot():
    """A slot never runs off a flange narrower than the 8 mm slot plus a
    millimetre: a 470 mm face leaves 6.3 mm a side, so the slot is 5.3 wide."""
    p = ears.plan(_device(w=470.0))
    assert p["flange"] == pytest.approx(6.3)
    assert p["slot"] == [pytest.approx(5.3), 5.0]


def test_stated_y_lifts_the_ear_on_every_face():
    p = ears.plan(_device(h=88.9, ru=2, ears={"h": 43.5, "y": 0.15}))
    for view in ("front", "rear", "left", "right"):
        for _s, kind, _x, y, _w, h in ears.rects(p, view, 440 if view in ("front", "rear") else 500, 88.9):
            if kind in ("flange", "leg", "edge"):
                assert (y, h) == (pytest.approx(88.9 - 0.15 - 43.5), 43.5)


def _render(name, view, include):
    doc = _real(name)
    return render.render_view(doc, view, doc["views"][view], render.Library([str(LIB)]),
                              include=include)


def test_with_ears_draws_the_pair_and_grows_the_viewbox():
    svg = _render("edgecore/dcs240", "front", ("ears",))
    ids = {g.get("id") for g in svg.iter() if g.get("data-generic") == "ear"}
    assert ids == {"ear-left", "ear-right"}
    vb = [float(v) for v in svg.get("viewBox").split()]
    assert vb[0] == pytest.approx(-22.1) and vb[2] == pytest.approx(482.6)
    assert svg.get("data-face-w") == "438.4"


@pytest.mark.parametrize("view", ["front", "rear", "left", "right", "top", "bottom"])
def test_the_default_build_draws_no_ears(view):
    """THE PUBLISHED FACES DO NOT MOVE: no `ears` tag, no ear."""
    svg = _render("edgecore/dcs240", view, ())
    assert not [g for g in svg.iter() if g.get("data-generic")]
    assert not svg.get("data-face-w")


def test_a_rack_ear_device_draws_its_own_pair_and_no_generic_one():
    svg = _render("edgecore/as5912-54x", "front", ("ears",))
    assert not [g for g in svg.iter() if g.get("data-generic")]
    assert len([g for g in svg.iter() if g.get("data-class") == "ear"]) == 2


# --- the kit's plan is ears.py's ---------------------------------------------------

CASES = [_device(), _device(w=220.0), _device(h=88.9, ru=2, ears={"h": 43.5, "y": 0.15}),
         _device(h=87.0, ru=2), _device(ears={"y": 4}),
         _device(ears={"positions": [{"name": "mid", "at": 228, "default": True}]}),
         _device(w=482.6), _device(ears="behind"), _device(mount="wall"),
         _device(w=478.0), _device(ears={"color": "#1b1e21", "y": 2}),
         # a flange narrower than a slot (the slot-width clamp), and a shell
         _device(w=470.0), _device(shell="sheet")]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_the_kit_draws_the_same_ear_as_ears_py():
    cases = [{"chassis": {"w": d["chassis"]["width"], "h": d["chassis"]["height"],
                          "d": d["chassis"]["depth"],
                          "mount": d["chassis"].get("mount", "rack"),
                          **({"shell": d["chassis"]["shell"]} if "shell" in d["chassis"] else {}),
                          **({"ears": render.published_ears(d["chassis"]["ears"])}
                             if "ears" in d["chassis"] else {})},
              "faceW": d["views"]["front"]["size"]["w"]} for d in CASES]
    p = subprocess.run(["node", str(SCRIPT)], input=json.dumps(cases), capture_output=True,
                       text=True, cwd=str(SCRIPT.parent), timeout=60)
    assert p.returncode == 0, p.stderr
    got = json.loads(p.stdout.strip().splitlines()[-1])
    want = [ears.plan(d) for d in CASES]
    assert [g is None for g in got] == [w is None for w in want]
    assert sum(w is not None for w in want) == 8     # the comparison compares something
    # the colour too: silver by default, the stated one where there is one
    assert [w["color"] for w in want if w] == [ears.SILVER] * 6 + ["#1b1e21", ears.SILVER]
    for g, w in zip(got, want):
        if w is None:
            continue
        assert set(g) == set(w)
        for k in w:
            if isinstance(w[k], str):
                assert g[k] == w[k], k
            else:
                assert g[k] == pytest.approx(w[k]), k


def _code(name):
    return "\n".join(line.split("//")[0] for line in (KIT / name).read_text().splitlines())


def test_the_viewer_builds_the_ears_after_the_chassis_and_off_by_default():
    code = _code("viewer3d.js")
    assert "let EARS = !!opts.ears;" in code
    build = code[code.index("async function build(cfg)"):code.index("function buildEars()")]
    assert "buildEars();" in build
    assert "genericEars(devIndex.chassis, (FACE_MM.front || [])[0])" in code
    assert "setEars, ears:" in code


# --- the lock: h and y stay a patch ------------------------------------------------

def test_changing_the_ears_h_or_y_is_a_patch():
    """The ear drawn from them is drawn only when asked for, never in a
    published face or export (devicelock CHASSIS_SURFACE)."""
    before = dl.entry(_device(ears={"h": 43.5, "y": 0.15}))
    for ears_ in ({"h": 40.0, "y": 0.15}, {"h": 43.5, "y": 2.0}):
        after = dl.entry(_device(ears=ears_))
        assert before["shape"] == after["shape"]
        assert dl.required_bump(before, after) == "patch"


# --- L164 and L165 -----------------------------------------------------------------

def _warns(doc):
    with lint.collecting() as found:
        lint.lint_device_ear_span(pathlib.Path("d.yaml"), doc)
    return found.warnings


@pytest.mark.parametrize("ears_,fires", [
    ({"h": 43.5, "y": 0.15}, False), ({"h": 44.0, "y": 0.0}, False),
    ({"h": 44.0, "y": 0.04}, False), ({"h": 44.0, "y": 1.0}, True),
    ({"h": 60.0}, True), ({"h": 30.0, "y": 14.1}, True),
    ({"y": 10.0}, False), ("behind", False), ({"positions": [{"name": "flush"}]}, False)])
def test_L164_the_ears_fit_the_chassis(ears_, fires):
    assert any("[L164]" in w for w in _warns(_device(ears=ears_))) is fires


@pytest.mark.parametrize("positions,fires", [
    ([{"name": "flush", "label": "chassis flush"},
      {"name": "flush", "label": "transponder flush"}], False),
    ([{"name": "flush"}, {"name": "recessed"}], False),
    ([{"name": "flush"}, {"name": "flush", "at": 0}], True),
    ([{"name": "mid", "label": "x"}, {"name": "mid", "label": "x"}], True)])
def test_L165_no_position_is_written_twice(positions, fires):
    doc = _device(ears={"positions": positions})
    assert any("[L165]" in w for w in _warns(doc)) is fires


def test_the_library_raises_neither():
    for path in sorted((LIB / "devices").glob("*/*/device.yaml")):
        found = _warns(yaml.safe_load(path.read_text()))
        assert not found, (path, found)
