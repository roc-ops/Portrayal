"""Adjustable positions, step 2: what the compiled drawing carries.

docs/adjustable-positions-design.md sections 5 and 6. The build writes the map
of a device's adjustments on the root of every face (`data-adjustments`), says
on each member what moves it and by how much per mm (`data-moves-with`,
`data-moves-by`), draws a configuration that sets a position moved, and lists
the map and each configuration's positions in `configs.json`.

The fixture device (spec/tests/fixtures/adjustments) is built once here, at
its default (60), at its front stop (20) and at the rear end of its travel
(180), and the box of every member is read at each. A device that states no
adjustment gains no attribute and no key.
"""
import hashlib
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest
import yaml

import adjustfixture as fx
import warmrender
from portrayal import adjustments as adj

AID = fx.AID
SVG = "{http://www.w3.org/2000/svg}"
# configuration -> the position it is built at
BUILT = {"base": 60.0, "forward": 20.0, "back": 180.0}
# configuration -> (adjustment, position): the ends of the part along x and along y
XY = {"x-min": ("block-offset", 22.0), "x-max": ("block-offset", 92.0),
      "y-min": ("shelf-height", 5.0), "y-max": ("shelf-height", 35.0)}
VIEWS = ("front", "rear", "top", "bottom", "left", "right")


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    def edit(d):
        # four more configurations, one at each end of the part along x and of
        # the part along y, so every axis is built at both ends
        for name, (aid, value) in XY.items():
            carrier = d["adjustments"][aid]["carrier"]
            d["configurations"][name] = {
                "kind": "example", "description": f"The same frame with {aid} at {value:g}.",
                "component-attrs": {carrier: {aid: f"{value:g}"}}}
    out, r = fx.render(tmp_path_factory.mktemp("adjust-build"), edit)
    assert r.returncode == 0, r.stderr[-2000:]
    return out


def face(out, cfg, view):
    return ET.parse(out / f"slider.{cfg}.{view}.svg").getroot()


def node(root, nid):
    return next(e for e in root.iter() if e.get("id") == nid)


def rows(out, cfg, view):
    doc = json.loads((out / f"slider.{cfg}.{view}.elements.json").read_text())
    return {r.get("path") or r.get("of"): r for r in doc["elements"]}


# --- the root map --------------------------------------------------------------------------

def test_every_face_carries_the_map_and_where_it_was_built(built):
    for cfg, at in BUILT.items():
        for view in VIEWS:
            raw = face(built, cfg, view).get("data-adjustments")
            got = json.loads(raw)
            assert set(got) == {AID, "block-offset", "shelf-height"}
            assert {k: v["at"] for k, v in got.items() if k != AID} == \
                {"block-offset": 30.0, "shelf-height": 20.0}
            assert {AID: got[AID]} == {AID: {
                "axis": "z", "carrier": "panel", "range": [20.0, 180.0], "default": 60.0,
                "stops": {"front": 20.0, "middle": 100.0, "rear": 180.0},
                "label": "Panel setback",
                "datum": "the front face of the panel, behind the front of the frame",
                "at": at}}, (cfg, view)
            # keys sorted and no spaces, the way data-positions is written
            assert raw == json.dumps(got, sort_keys=True, separators=(",", ":"))


# --- the two node attributes ---------------------------------------------------------------

# view -> (data-moves-by, the member nodes there)
MEMBERS = {
    "front": ("0 0 1", ["panel", "rail"]),
    "top": ("0 -1 0", ["panel", "rail"]),
    "bottom": ("0 -1 0", ["panel", "rail"]),
    "right": ("1 0 0", ["flange", "stud"]),
    "left": ("-1 0 0", ["flange", "stud"]),
}


def test_each_member_says_what_moves_it_and_by_how_much(built):
    """The table of section 5 for `axis: z`, read off the drawing."""
    for cfg in BUILT:
        for view, (by, ids) in MEMBERS.items():
            root = face(built, cfg, view)
            marked = {e.get("id"): e.get("data-moves-by") for e in root.iter()
                      if e.get("data-moves-with") == AID}
            assert marked == {i: by for i in ids}, (cfg, view)
            assert all(node(root, i).get("data-moves-with") == AID for i in ids)
        # the rear view has no member of this adjustment, and it still has the map
        rear = face(built, cfg, "rear")
        assert not [e for e in rear.iter() if e.get("data-moves-with") == AID]
        assert rear.get("data-adjustments")


# EVERY ROW OF THE TABLE, WRITTEN OUT, WITH WHY. The sign of each axis on each
# face is what every saved position rests on: a flipped row moves parts the
# wrong way in every link and every rack that holds a value, with no edit to
# them. So the table is not derived here, it is stated, and the fixture is
# built along every axis below to hold the build to it.
# A face is drawn from outside the device, x to the right and y down the page.
TABLE = {
    # x runs from the left of the device as seen from its front
    ("x", "front"): ((1, 0, 0), "seen from the front, the left of the device is at the left"),
    ("x", "rear"): ((-1, 0, 0), "seen from behind, the left of the device is at the right"),
    ("x", "top"): ((1, 0, 0), "a plan has the rear at its top edge, so left is at the left"),
    ("x", "bottom"): ((-1, 0, 0), "seen from below with the rear at the top edge, left and right swap"),
    ("x", "left"): ((0, 0, 1), "the left face is at x = 0: further along x is deeper behind it"),
    ("x", "right"): ((0, 0, -1), "the right face is at the far end of x: further along is nearer it"),
    # y runs up from the bottom of the device
    ("y", "front"): ((0, -1, 0), "up the device is up the page, and y on a page runs down"),
    ("y", "rear"): ((0, -1, 0), "up is up from behind too"),
    ("y", "left"): ((0, -1, 0), "up is up on a side view"),
    ("y", "right"): ((0, -1, 0), "up is up on a side view"),
    ("y", "top"): ((0, 0, -1), "the top face is at the far end of y: higher is nearer it"),
    ("y", "bottom"): ((0, 0, 1), "the bottom face is at y = 0: higher is deeper behind it"),
    # z runs back from the front of the device
    ("z", "front"): ((0, 0, 1), "the front face is at z = 0: further back is deeper behind it"),
    ("z", "rear"): ((0, 0, -1), "the rear face is at the far end of z: further back is nearer it"),
    ("z", "top"): ((0, -1, 0), "a plan has the rear at its top edge (y = 0), so back is up the page"),
    ("z", "bottom"): ((0, -1, 0), "the plan from below keeps the rear at its top edge"),
    ("z", "right"): ((1, 0, 0), "the right view has the front at its left, so back is to the right"),
    ("z", "left"): ((-1, 0, 0), "the left view has the front at its right, so back is to the left"),
}


@pytest.mark.parametrize("axis, view", sorted(TABLE))
def test_each_row_of_the_table_is_as_stated(axis, view):
    want, why = TABLE[(axis, view)]
    assert adj.moves_by(axis, view) == want, why


def test_the_stated_table_is_the_whole_table():
    assert {(a, f) for a, faces in adj.MOVES_BY.items() for f in faces} == set(TABLE)
    assert len(TABLE) == 18


def test_the_table_covers_every_axis_and_face():
    """Each axis moves a part in the plane of four faces and along the depth
    of two, and opposite faces show it opposite ways or alike, never askew."""
    for axis, faces in adj.MOVES_BY.items():
        assert set(faces) == set(VIEWS)
        deep = [f for f, by in faces.items() if by[2]]
        assert len(deep) == 2 and faces[deep[0]][2] == -faces[deep[1]][2], axis
        for by in faces.values():
            assert sorted(abs(v) for v in by) == [0, 0, 1]
    assert adj.MOVES_BY["z"] == {"front": (0, 0, 1), "rear": (0, 0, -1), "top": (0, -1, 0),
                                 "bottom": (0, -1, 0), "right": (1, 0, 0), "left": (-1, 0, 0)}


# --- a configuration that sets a position is built moved --------------------------------------

def _rect(root, nid):
    r = node(root, nid)
    return [float(r.get(k)) for k in ("x", "y", "width", "height")]


def test_the_box_of_every_member_at_the_default_and_at_each_end(built):
    """`s` is the position. On a plan the rear is at y = 0, so the panel's
    front face is at y = 200 - s: its plate lies behind it and its rail in
    front. On the right view the front is at the left; the left view mirrors it."""
    for cfg, s in BUILT.items():
        for view in ("top", "bottom"):
            root = face(built, cfg, view)
            assert _rect(root, "panel") == [10, 200 - s - 1.5, 100, 1.5], (cfg, view)
            assert _rect(root, "rail") == [20, 200 - s, 80, 7.5], (cfg, view)
        assert _rect(face(built, cfg, "right"), "flange") == [s, 4, 12, 32], cfg
        assert _rect(face(built, cfg, "left"), "flange") == [200 - s - 12, 4, 12, 32], cfg
        # the studs are placements: their boxes come from the elements file
        assert rows(built, cfg, "right")["stud"]["box"] == \
            {"x": s + 3 + 0.1, "y": 17.1, "w": 5.8, "h": 5.8}, cfg
        assert rows(built, cfg, "left")["stud"]["box"] == \
            pytest.approx({"x": 200 - s - 9 + 0.1, "y": 17.1, "w": 5.8, "h": 5.8}), cfg
        # from the front nothing moves in the face: the same elevation
        front = rows(built, cfg, "front")
        assert front["panel"]["box"] == {"x": 10.0, "y": 0.0, "w": 100.0, "h": 40.0}
        assert front["rail"]["box"] == {"x": 20.0, "y": 15.0, "w": 80.0, "h": 10.0}


def test_what_does_not_move_is_drawn_the_same_in_every_configuration(built):
    for view, fixed in (("top", ["side-left", "side-right"]), ("right", [])):
        for nid in fixed:
            assert len({tuple(_rect(face(built, cfg, view), nid)) for cfg in BUILT}) == 1
    assert len({json.dumps(rows(built, cfg, "right")["side-right"]["box"]) for cfg in BUILT}) == 1
    assert len({json.dumps(rows(built, cfg, "rear")) for cfg in BUILT}) == 1


def test_the_depth_of_the_well_and_of_what_stands_in_it(built):
    """Section 6. From the front the motion is depth: the well's floor is the
    position, the rail stands on that floor (a lift of minus the position),
    and its 7.5 rises from there."""
    for cfg, s in BUILT.items():
        root = face(built, cfg, "front")
        assert float(node(root, "panel").get("data-depth")) == s, cfg
        assert float(node(root, "rail").get("data-z-lift")) == -s, cfg
        assert float(node(root, "rail--rail").get("data-z-out")) == 7.5 - s, cfg
        # a stud moves in the plane of its side view and keeps its own height
        stud = node(face(built, cfg, "right"), "stud")
        assert stud.get("data-z-lift") is None or float(stud.get("data-z-lift")) >= 0


def test_the_carrier_holds_the_value_only_where_a_configuration_set_it(built):
    """`data-<id>` on the carrier, in the one spelling: `front` is kept as 20."""
    got = {cfg: node(face(built, cfg, "front"), "panel").get(f"data-{AID}") for cfg in BUILT}
    assert got == {"base": None, "forward": "20", "back": "180"}


def test_the_elements_file_says_which_rows_move(built):
    for cfg in BUILT:
        front = rows(built, cfg, "front")
        for path in ("panel", "panel/panel", "rail", "rail/rail"):
            assert front[path]["moves-with"] == AID, path
            assert front[path]["moves-by"] == [0.0, 0.0, 1.0], path
        assert "moves-with" not in front["chassis"]
        right = rows(built, cfg, "right")
        assert right["stud"]["moves-by"] == [1.0, 0.0, 0.0]
        assert "moves-with" not in right["side-right"]
        assert rows(built, cfg, "left")["stud"]["moves-by"] == [-1.0, 0.0, 0.0]


def test_configs_json_carries_the_map_and_each_configuration_positions(built):
    cfg = json.loads((built / "slider.configs.json").read_text())
    assert {AID: cfg["adjustments"][AID]} == {AID: {
        "axis": "z", "carrier": "panel", "range": [20.0, 180.0], "default": 60.0,
        "stops": {"front": 20.0, "middle": 100.0, "rear": 180.0}, "label": "Panel setback",
        "datum": "the front face of the panel, behind the front of the frame"}}
    assert {c["name"]: c["positions"] for c in cfg["configs"]} == \
        {"base": {}, "forward": {AID: 20.0}, "back": {AID: 180.0},
         **{name: {aid: value} for name, (aid, value) in XY.items()}}


def test_every_face_names_the_manifest_as_written(built):
    """A moved configuration is drawn from a copy of the manifest; the digest a
    face carries is still that of the one source file."""
    want = hashlib.sha256((built / "slider.source.json").read_bytes()).hexdigest()
    for cfg in BUILT:
        for view in VIEWS:
            meta = json.loads(face(built, cfg, view).find(f"{SVG}metadata").text)
            assert meta["source-sha256"] == want, (cfg, view)


# --- a value that is not a position fails the build -------------------------------------------

@pytest.mark.parametrize("value, sentence", [
    ("300", "panel-setback on SLIDER takes 20 to 180 mm. 300 is outside it."),
    ("back", "panel-setback on SLIDER takes a number in mm, or one of: front, middle, rear."),
])
def test_a_configuration_that_sets_no_position_fails_the_build(tmp_path, value, sentence):
    def edit(d):
        d["configurations"]["back"]["component-attrs"]["panel"][AID] = value
    _out, r = fx.render(tmp_path, edit)
    assert r.returncode != 0 and sentence in r.stderr, r.stderr[-600:]


def test_stops_alone_take_a_stop_and_refuse_the_space_between(tmp_path):
    def stops(value):
        def edit(d):
            a = d["adjustments"][AID]
            del a["range"]
            a["stops"] = {"near": 60.0, "far": 180.0}
            d["configurations"]["back"]["component-attrs"]["panel"][AID] = value
            del d["configurations"]["forward"]
        return edit
    out, r = fx.render(tmp_path / "ok", stops("far"))
    assert r.returncode == 0, r.stderr[-600:]
    assert json.loads(face(out, "back", "top").get("data-adjustments"))[AID]["at"] == 180.0
    _out, r = fx.render(tmp_path / "bad", stops("120"))
    assert r.returncode != 0
    assert "panel-setback on SLIDER takes one of: near (60), far (180)." in r.stderr


# --- a device that states none ---------------------------------------------------------------

def test_a_device_with_no_adjustment_gains_no_attribute_and_no_key(tmp_path):
    def edit(d):
        del d["adjustments"], d["provenance"][AID]
        for view in d["views"].values():
            for _kind, item in adj._items(view):
                item.pop("moves-with", None)
        for name in ("forward", "back"):
            del d["configurations"][name]
    out, r = fx.render(tmp_path, edit)
    assert r.returncode == 0, r.stderr[-600:]
    for f in out.glob("*.svg"):
        assert "moves-" not in f.read_text() and "data-adjustments" not in f.read_text(), f.name
    for f in out.glob("*.elements.json"):
        assert "moves-" not in f.read_text(), f.name
    cfg = json.loads((out / "slider.configs.json").read_text())
    assert "adjustments" not in cfg and all("positions" not in c for c in cfg["configs"])


# --- a member bay carries its projection ------------------------------------------------------

def _library_copy(tmp, device, edit):
    """A library device copied and edited, as test_switch_positions.py does."""
    name = device.split("/")[1]
    dev = tmp / name / "device.yaml"
    shutil.copytree(fx.LIB / "devices" / device, dev.parent)
    d = yaml.safe_load(dev.read_text())
    edit(d)
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    out = tmp / name / "o"
    r = warmrender.run([sys.executable, str(fx.RENDER), str(dev), "--library", str(fx.LIB),
                        "--out", str(out)], capture_output=True, text=True)
    return name, out, r


def _translate(g):
    args = g.get("transform").split("translate(")[1].split(")")[0].replace(",", " ").split()
    return [float(a) for a in args]


def test_the_plan_of_a_member_bay_moves_with_it(tmp_path):
    """NOT A MODEL OF THIS PANEL: its drawer is the smallest bay in the
    library with a `plan`, and that is all it is used for. A bay that moves
    along z is drawn deeper from the front, and its plan, on the top view,
    moves toward the rear, marked as a member there."""
    def edit(d):
        d["adjustments"] = {"reach": {"label": "Reach", "carrier": "shell-top", "axis": "z",
                                      "range": [0.0, 20.0], "default": 0.0,
                                      "datum": "a test"}}
        d["views"]["front"]["components"]["bays"][0]["moves-with"] = "reach"
        next(p for p in d["views"]["top"]["components"]["placements"]
             if p["id"] == "shell-top")["moves-with"] = "reach"
        d["configurations"] = {
            "base": d["configurations"]["base"],
            "deep": {**d["configurations"]["base"], "default": False, "kind": "example",
                     "component-attrs": {"shell-top": {"reach": "20"}}}}
    name, out, r = _library_copy(tmp_path, "fibrain/xcu", edit)
    assert r.returncode == 0, r.stderr[-1500:]
    at = {}
    for cfg in ("base", "deep"):
        top = ET.parse(out / f"{name}.{cfg}.top.svg").getroot()
        plan = node(top, "drawer-plan")
        assert plan.get("data-projection") == "1"
        assert (plan.get("data-moves-with"), plan.get("data-moves-by")) == ("reach", "0 -1 0")
        assert plan.get("data-z-lift") is None      # a projection is flat
        at[cfg] = _translate(plan)
        bay = node(ET.parse(out / f"{name}.{cfg}.front.svg").getroot(), "drawer")
        assert (bay.get("data-moves-with"), bay.get("data-moves-by")) == ("reach", "0 0 1")
        assert float(bay.get("data-z-lift") or 0) == (-20.0 if cfg == "deep" else 0.0)
    assert at["deep"][0] == at["base"][0] and at["deep"][1] == at["base"][1] - 20.0, at


def test_the_back_of_a_module_in_a_member_bay_moves_with_it(tmp_path):
    """NOT A MODEL OF THIS ENCLOSURE either: it is the smallest device whose
    bays show their occupant's back through a hole (`rear:`). That projection
    is placed from the hole and not from the bay, so the build moves it
    itself, and marks it, inside the hole it is drawn in."""
    def edit(d):
        d["adjustments"] = {"slide": {"label": "Slide", "carrier": "ear-left", "axis": "y",
                                      "range": [0.0, 2.0], "default": 0.0, "datum": "a test"}}
        next(b for b in d["views"]["front"]["components"]["bays"]
             if b["id"] == "bay-1")["moves-with"] = "slide"
        d["configurations"]["raised"] = {
            **d["configurations"]["populated"],
            "component-attrs": {"ear-left": {"slide": "2"}}}
    name, out, r = _library_copy(tmp_path, "fs/fhd-1ufce", edit)
    assert r.returncode == 0, r.stderr[-1500:]
    at = {}
    for cfg in ("populated", "raised"):
        rear = ET.parse(out / f"{name}.{cfg}.rear.svg").getroot()
        back = node(rear, "bay-1-rear")
        assert (back.get("data-moves-with"), back.get("data-moves-by")) == ("slide", "0 -1 0")
        assert back in list(node(rear, "cutout--back-1"))
        at[cfg] = _translate(back)
        # the bay beside it is not a member, and its back is not marked
        assert node(rear, "bay-2-rear").get("data-moves-with") is None
    assert at["raised"] == [at["populated"][0], at["populated"][1] - 2.0], at


# --- a part that moves along x, and one along y ------------------------------------------------



def test_a_part_along_x_is_drawn_at_both_ends_on_every_view_that_shows_it(built):
    """`v` is the left edge of the block from the left of the frame. The front
    and the plan show it at x = v; the rear and the plan from below are seen
    the other way round, at 120 - v - 6. The side views show x as depth, and
    nothing on them moves in the plane."""
    for cfg, v in (("base", 30.0), ("x-min", 22.0), ("x-max", 92.0)):
        assert rows(built, cfg, "front")["block"]["box"] == \
            pytest.approx({"x": v + 0.1, "y": 30.1, "w": 5.8, "h": 5.8}), cfg
        assert _rect(face(built, cfg, "top"), "block") == [v, 194, 6, 4], cfg
        assert _rect(face(built, cfg, "rear"), "block-back") == [120 - v - 6, 30, 6, 6], cfg
        assert _rect(face(built, cfg, "bottom"), "block") == [120 - v - 6, 194, 6, 4], cfg
    by = {view: node(face(built, "base", view), nid).get("data-moves-by")
          for view, nid in (("front", "block"), ("top", "block"), ("rear", "block-back"),
                            ("bottom", "block"))}
    assert by == {"front": "1 0 0", "top": "1 0 0", "rear": "-1 0 0", "bottom": "-1 0 0"}
    # and the block alone moved: the panel and the shelf stand where they were
    for cfg in ("x-min", "x-max"):
        assert rows(built, cfg, "front")["shelf"]["box"] == rows(built, "base", "front")["shelf"]["box"]
        assert _rect(face(built, cfg, "top"), "panel") == _rect(face(built, "base", "top"), "panel")


def test_a_part_along_y_is_drawn_at_both_ends_on_every_view_that_shows_it(built):
    """`v` is the centre of the shelf stud above the bottom of the frame. Up
    the device is up the page on the front, the rear and both sides: the top
    of the 6 mm stud is at y = 40 - v - 3 on each. The plans show y as depth."""
    for cfg, v in (("base", 20.0), ("y-min", 5.0), ("y-max", 35.0)):
        y = 40 - v - 3
        assert rows(built, cfg, "front")["shelf"]["box"] == \
            pytest.approx({"x": 2.1, "y": y + 0.1, "w": 5.8, "h": 5.8}), cfg
        assert _rect(face(built, cfg, "rear"), "shelf-back") == [112, y, 6, 6], cfg
        assert _rect(face(built, cfg, "left"), "shelf") == [190, y, 4, 6], cfg
        assert _rect(face(built, cfg, "right"), "shelf") == [6, y, 4, 6], cfg
    by = {view: node(face(built, "base", view), nid).get("data-moves-by")
          for view, nid in (("front", "shelf"), ("rear", "shelf-back"), ("left", "shelf"),
                            ("right", "shelf"))}
    assert by == {view: "0 -1 0" for view in ("front", "rear", "left", "right")}
    for cfg in ("y-min", "y-max"):
        assert rows(built, cfg, "front")["block"]["box"] == rows(built, "base", "front")["block"]["box"]


def test_each_configuration_moves_only_its_own_adjustment(built):
    for cfg, (aid, value) in XY.items():
        got = json.loads(face(built, cfg, "front").get("data-adjustments"))
        want = {AID: 60.0, "block-offset": 30.0, "shelf-height": 20.0, aid: value}
        assert {k: v["at"] for k, v in got.items()} == want, cfg


# --- the kit's move and the build's are one move -----------------------------------------------

def _spec(el):
    """An SVG element as the fake DOM's JSON tree (spec/tests/js/fake-dom.mjs)."""
    return {"t": el.tag.rsplit("}", 1)[-1], "a": dict(el.attrib),
            "c": [_spec(c) for c in el if isinstance(c.tag, str)]}


def _stands(attrs):
    """Where a node stands and how deep: the point its own `x`,`y` (or its
    origin) lands at through its transform, and its depth keys as numbers."""
    from portrayal.elements import _apply, parse_transform
    x, y = _apply(parse_transform(attrs.get("transform")), float(attrs.get("x", 0)),
                  float(attrs.get("y", 0)))
    out = {"at": (round(x, 3), round(y, 3))}
    for k in ("data-depth", "data-z-lift", "data-z-out"):
        if k in attrs:
            out[k] = round(float(attrs[k]), 3)
    # a profile is `t:height,...`: every height is a depth key too
    for k in ("data-z-profile", "data-z-profile-y"):
        if k in attrs:
            out[k] = [tuple(round(float(v), 3) for v in pair.split(":"))
                      for pair in attrs[k].split(",")]
    return out


PARITY = [("forward", {"panel": {AID: "20"}}), ("back", {"panel": {AID: "rear"}}),
          ("x-min", {"block": {"block-offset": "22"}}), ("x-max", {"block": {"block-offset": "92"}}),
          ("y-min", {"shelf": {"shelf-height": "5"}}), ("y-max", {"shelf": {"shelf-height": "35"}})]


@pytest.mark.parametrize("cfg, fields", PARITY, ids=[c for c, _ in PARITY])
def test_the_kit_moves_the_default_build_to_where_the_build_draws_it(built, tmp_path, cfg, fields):
    """ONE MOVE, WRITTEN TWICE: `mark_member` in render.py draws a
    configuration moved, and `moveMember` in kit/fields.js moves a drawing a
    reader holds. The faces built at the default, moved by the kit to a
    position, stand exactly where the build draws that position: every node,
    on every face, in the plane and in depth."""
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    faces = {view: _spec(face(built, "base", view)) for view in VIEWS}
    arg = tmp_path / "parity.json"
    arg.write_text(json.dumps({"faces": faces, "fields": fields}))
    script = fx.ROOT / "spec/tests/js/adjustments-parity.mjs"
    p = subprocess.run(["node", str(script), str(arg)], capture_output=True, text=True,
                       cwd=str(script.parent), timeout=60)
    assert p.returncode == 0, p.stderr
    kit = json.loads(p.stdout.strip().splitlines()[-1])
    moved = 0
    for view in VIEWS:
        want = {e.get("id"): _stands(e.attrib) for e in face(built, cfg, view).iter() if e.get("id")}
        got = {i: _stands(a) for i, a in kit[view]["nodes"].items()}
        assert got == want, (cfg, view)
        was = {e.get("id"): _stands(e.attrib) for e in face(built, "base", view).iter() if e.get("id")}
        moved += sum(1 for i in want if want[i] != was[i])
    assert moved >= 4, "nothing moved: the comparison measured nothing"
    if cfg in ("forward", "back"):
        # the rail's lip is a profile, and its heights went with the floor
        s = BUILT[cfg]
        lip = _stands(kit["front"]["nodes"]["rail--lip"])
        assert lip["data-z-profile"] == [(0.0, 3.0 - s), (80.0, 1.0 - s)], cfg


# --- two things the build promises, each with a drawing that breaks it ---------------------------

def _svg(text):
    return ET.fromstring(f'<svg xmlns="http://www.w3.org/2000/svg">{text}</svg>')


def test_the_build_refuses_a_member_inside_a_member():
    from portrayal import render
    with pytest.raises(ValueError, match="would move twice"):
        render._check_members(_svg(
            '<g id="outer" data-moves-with="a" data-moves-by="1 0 0">'
            '<g id="inner" data-moves-with="a" data-moves-by="1 0 0"/></g>'))


def test_the_build_refuses_a_member_under_a_group_that_is_turned():
    from portrayal import render
    with pytest.raises(ValueError, match="not in the frame of the face"):
        render._check_members(_svg(
            '<g id="turned" transform="rotate(90)">'
            '<g id="inner" data-moves-with="a" data-moves-by="1 0 0"/></g>'))
    # a member with a transform of its own, under plain groups, is what every
    # placement is
    render._check_members(_svg(
        '<g id="--decor"><rect id="d" data-moves-with="a" data-moves-by="1 0 0"/></g>'
        '<g id="p" transform="translate(1,2)" data-moves-with="a" data-moves-by="1 0 0"/>'))


def test_every_face_of_a_device_that_slides_is_checked(monkeypatch):
    """And the build asks: with the check made to refuse everything, drawing a
    face of the fixture stops; a device that declares no adjustment is not asked."""
    from portrayal import render
    lib = render.Library([str(fx.FIXTURE_LIB), str(fx.LIB)])

    def refuse(_svg):
        raise ValueError("checked")
    monkeypatch.setattr(render, "_check_members", refuse)
    doc = fx.device()
    with pytest.raises(ValueError, match="checked"):
        render.render_view(doc, "top", doc["views"]["top"], lib, config_name="base",
                           config=doc["configurations"]["base"])
    del doc["adjustments"]
    for view in doc["views"].values():
        for _kind, item in adj._items(view):
            item.pop("moves-with", None)
    render.render_view(doc, "top", doc["views"]["top"], lib, config_name="base",
                       config=doc["configurations"]["base"])


def test_a_part_seated_on_a_member_moves_with_it(tmp_path):
    """NOT A MODEL OF THIS ROUTER: it has a cage a configuration can seat an
    optic in. The optic is a placement the build makes, with no entry to say
    `moves-with` on, so the build marks it as a member of its cage's
    adjustment and draws it moved with the cage."""
    def edit(d):
        d["adjustments"] = {"slide": {"label": "Slide", "carrier": "port-0", "axis": "y",
                                      "range": [0.0, 1.0], "default": 0.0, "datum": "a test"}}
        next(p for p in d["views"]["front"]["components"]["placements"]
             if p["id"] == "port-0")["moves-with"] = "slide"
        base = d["configurations"]["ac"]
        d["configurations"] = {
            "ac": {**base, "occupants": {"port-0": "generic/sfp-lc@1", "port-1": "generic/sfp-lc@1"}},
            "up": {**base, "default": False, "kind": "example",
                   "occupants": {"port-0": "generic/sfp-lc@1", "port-1": "generic/sfp-lc@1"},
                   "component-attrs": {"port-0": {"slide": "1"}}}}
    name, out, r = _library_copy(tmp_path, "edgecore/agr110", edit)
    assert r.returncode == 0, r.stderr[-1500:]
    at = {}
    for cfg in ("ac", "up"):
        front = ET.parse(out / f"{name}.{cfg}.front.svg").getroot()
        for nid in ("port-0", "port-0-occupant"):
            g = node(front, nid)
            assert (g.get("data-moves-with"), g.get("data-moves-by")) == ("slide", "0 -1 0"), nid
            at[cfg, nid] = _translate(g)
        # the optic in the cage beside it is no member
        assert node(front, "port-1-occupant").get("data-moves-with") is None
    for nid in ("port-0", "port-0-occupant"):
        assert at["up", nid] == pytest.approx([at["ac", nid][0], at["ac", nid][1] - 1.0]), nid
