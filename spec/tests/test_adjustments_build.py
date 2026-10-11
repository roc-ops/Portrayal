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
VIEWS = ("front", "rear", "top", "bottom", "left", "right")


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out, r = fx.render(tmp_path_factory.mktemp("adjust-build"))
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
            assert got == {AID: {
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
                      if e.get("data-moves-with") is not None}
            assert marked == {i: by for i in ids}, (cfg, view)
            assert all(node(root, i).get("data-moves-with") == AID for i in ids)
        # the rear view has no member: nothing on it moves, and it still has the map
        rear = face(built, cfg, "rear")
        assert not [e for e in rear.iter() if e.get("data-moves-with")]
        assert rear.get("data-adjustments")


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
    assert cfg["adjustments"] == {AID: {
        "axis": "z", "carrier": "panel", "range": [20.0, 180.0], "default": 60.0,
        "stops": {"front": 20.0, "middle": 100.0, "rear": 180.0}, "label": "Panel setback",
        "datum": "the front face of the panel, behind the front of the frame"}}
    assert {c["name"]: c["positions"] for c in cfg["configs"]} == \
        {"base": {}, "forward": {AID: 20.0}, "back": {AID: 180.0}}


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
