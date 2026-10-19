"""A body can be several boxes, and the riser's is.

One box the size of the face hid the chassis interior; a box cut to the plate
left the riser's PCB behind - in the top view, as a part of its own - when the
riser was ejected. `body.boxes` lists the pieces in the face's frame, the kit
resolves either form through one function, and L71 holds each box inside the
reach the part declares.
"""
import json
import pathlib
import shutil
import subprocess
import sys

import pytest
import yaml

SPEC = pathlib.Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"
from portrayal import lint


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_the_kit_resolves_both_body_forms_to_one_list():
    script = SPEC / "tests/js/body-boxes.mjs"
    p = subprocess.run(["node", str(script)], capture_output=True, text=True, cwd=str(script.parent))
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout.strip().splitlines()[-1])
    # the one-box body is the face, at the plane, its depth deep
    assert out["one"] == [{"id": "body", "x": 0, "y": 0, "w": 86.3, "h": 39.1,
                           "z0": 0, "z1": 195.5, "color": "#222"}]
    # a footprint trims it
    assert out["fp"][0]["w"] == 40 and out["fp"][0]["x"] == 2 and out["fp"][0]["z1"] == 60
    # the pieces keep their own place, start and colour, and inherit the body's
    pcb, c = out["riser"]
    assert (pcb["x"], pcb["z0"], pcb["z1"], pcb["color"]) == (-0.75, 13.9, 184.8, "#1f5138")
    assert (c["z0"], c["z1"], c["color"]) == (47.9, 138.9, "#4a5057")
    # placed through the module's own transform: riser 1's PCB lands at face
    # x 13.2, inside the chassis wall, not 13.4 further out where the bbox
    # of its brackets starts; mirrored, it lands on the other side, positive
    pl = out["plain"]
    assert (round(pl["x"], 2), round(pl["y"], 2), round(pl["w"], 2)) == (13.2, 2.6, 1.6)
    mr = out["mirrored"]
    assert round(mr["x"], 2) == round(13.95 + 107.59 + 0.75 - 1.6, 2) and round(mr["w"], 2) == 1.6


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_a_piece_can_be_round_and_can_show_the_part_s_own_drawing():
    """A splice tray riding in a drawer is a box, and what makes it a splice
    tray - two storage rings, two splice holders - was a colour. A piece can
    now be a ring or a cylinder, and a box can carry the patch of the part's
    plan or rear drawing it covers."""
    script = SPEC / "tests/js/body-boxes.mjs"
    p = subprocess.run(["node", str(script)], capture_output=True, text=True, cwd=str(script.parent))
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout.strip().splitlines()[-1])
    ring, post, tray, plainbox = out["pieces"]
    assert (ring["shape"], ring["axis"], ring["wall"]) == ("ring", "y", 2)
    assert (post["shape"], post["axis"]) == ("cylinder", "z") and "wall" not in post
    assert tray["shows"] == ["plan"] and "shape" not in tray
    # `shape: box` is the default spelled out, and resolves to a plain box
    assert set(plainbox) == {"id", "x", "y", "w", "h", "z0", "z1", "color"}
    # THE PLAN RUNS RIGHT TO LEFT AGAINST THE FACE AND DOWN INTO THE PART. The
    # tray's corner nearest the face and the face's left (u 0, v 0 on a box
    # top) is face x 118, 85 behind the plane: plan x 431 - 118 = 313, y 85.
    assert out["planNear"] == [313, 85]
    assert out["planFar"] == [118, 178.6]
    # THE REAR RUNS RIGHT TO LEFT TOO, and down the face. Seen from behind, the
    # block's top-left is the face's x 16, y 1: rear x 100 - 16 = 84.
    assert out["rearTopLeft"] == [84, 1]
    assert out["rearBottomRight"] == [96, 10]
    # A TURNED, MIRRORED OR TILTED HOST GETS THE PLAIN BOX. `axis` and `shows`
    # are in the part's frame; in a slot that turns its occupant a box's top
    # is not the part's top, so the piece is built as it was before either key.
    assert out["straight"] == [True, True, False, False, False, False]
    assert set(out["demoted"]) == {"id", "x", "y", "w", "h", "z0", "z1", "color"}


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_a_piece_carries_the_patch_of_a_side_drawing_it_lies_under():
    """A GPU's top edge is printed and its shroud is ribbed, and a body piece
    was a colour. A box now carries the patch of the part's own
    body-<side>.svg it lies under, in the frame the one-box body reads that
    drawing in, from a viewBox that need not start at zero."""
    script = SPEC / "tests/js/body-boxes.mjs"
    p = subprocess.run(["node", str(script)], capture_output=True, text=True, cwd=str(script.parent))
    assert p.returncode == 0, p.stderr
    s = json.loads(p.stdout.strip().splitlines()[-1])["sides"]
    # the top edge: across is mm behind the face, down the face's y
    assert s["rightFrontTop"] == [0.9, 14.4] and s["rightBackBottom"] == [140.93, 40]
    # the lower edge: across from the far end, 268.6 - 140.93
    assert s["leftBackTop"] == [127.67, 14.4]
    # the top: across the face's x, down from the far end
    assert s["topFrontLeft"] == [28.41, 267.7]
    # the broad side: across from the face's width, 120.02 - 28.41, and the
    # top edge at 126.31 lands at -6.29, inside the drawing's own origin
    assert s["bottomBackLeft"] == [91.61, 127.67] and s["bottomFrontRight"] == [-6.29, 267.7]


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_a_fitted_piece_stands_while_its_option_is_shown():
    """An extender bolted to a card's far end is a choice. The piece stands
    while the part's drawing shows a node for its option, which a
    configuration and a viewer both settle; hidden nodes show nothing, and a
    piece turned plain keeps its `when`."""
    script = SPEC / "tests/js/body-boxes.mjs"
    p = subprocess.run(["node", str(script)], capture_output=True, text=True, cwd=str(script.parent))
    assert p.returncode == 0, p.stderr
    out = json.loads(p.stdout.strip().splitlines()[-1])
    assert out["fitted"] == [True, False, False, True, False]
    assert out["keptWhen"]["when"] == {"extender": ["straight"]} and "shows" not in out["keptWhen"]
    assert out["shown"] == {"card": {"extender": ["straight"]},
                            "riser/module/slot-1/module": {"extender": ["long-offset"]}}


def _sided(tmp_path, box, svg=None, side="right"):
    """A part in tmp_path with one box and, unless `svg` is None, a side drawing."""
    (tmp_path / "skins").mkdir(exist_ok=True)
    if svg is not None:
        (tmp_path / "skins" / f"body-{side}.svg").write_text(svg)
    return tmp_path / "contract.yaml", {
        "size": {"w": 120.0, "h": 40.0, "d": 200.0},
        "body": {"depth": 200.0, "boxes": [{"id": "b", "at": [10, 5], "size": [100, 30],
                                            "from": 0, "depth": 200.0,
                                            "confidence": "estimated", **box}]}}


def test_a_shown_side_is_drawn_and_covers_the_piece(tmp_path):
    run = lambda p, d: _caught("L71", lint.lint_component_body_boxes, p, d)
    svg = lambda vb, w, h: (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}mm" '
                            f'height="{h}mm" viewBox="{vb}"/>')
    # the right side of a box 0..200 deep, y 5..35, inside a 0 0 200 40 drawing
    assert not run(*_sided(tmp_path, {"shows": ["right"]}, svg("0 0 200 40", 200, 40)))
    undrawn = tmp_path / "undrawn"
    undrawn.mkdir()
    assert any("there is no skins/body-right.svg" in m
               for m in run(*_sided(undrawn, {"shows": ["right"]})))
    assert any("viewBox covers" in m for m in
               run(*_sided(tmp_path, {"shows": ["right"]}, svg("0 10 200 30", 200, 30))))
    assert any("state it as 40mm" in m for m in
               run(*_sided(tmp_path, {"shows": ["right"]}, svg("0 0 200 40", 200, 45))))
    assert any("no viewBox" in m for m in
               run(*_sided(tmp_path, {"shows": ["right"]}, '<svg xmlns="http://www.w3.org/2000/svg"/>')))
    # the bottom is measured from the face's width: 120 - 110 .. 120 - 10
    assert not run(*_sided(tmp_path, {"shows": ["bottom"]}, svg("10 0 100 200", 100, 200), "bottom"))
    assert any("viewBox covers" in m for m in
               run(*_sided(tmp_path, {"shows": ["bottom"]}, svg("0 0 100 200", 100, 200), "bottom")))
    assert any("both `plan` and `top`" in m for m in
               run(*_sided(tmp_path, {"shows": ["plan", "top"]}, svg("10 0 100 200", 100, 200), "top")))


def test_a_fitted_piece_may_reach_past_the_bare_part():
    part = {"size": {"w": 100.0, "h": 40.0, "d": 200.0},
            "body": {"depth": 200.0, "boxes": [
                {"id": "ext", "at": [0, 0], "size": [10, 10], "from": 200.0, "depth": 40.0,
                 "confidence": "estimated", "when": {"extender": ["straight"]}}]}}
    assert not _caught("L71", lint.lint_component_body_boxes, pathlib.Path("x.yaml"), part)
    del part["body"]["boxes"][0]["when"]
    assert _caught("L71", lint.lint_component_body_boxes, pathlib.Path("x.yaml"), part)


def test_a_fitted_piece_names_a_choice_the_drawing_can_show(tmp_path):
    (tmp_path / "skins").mkdir()
    skin = tmp_path / "skins" / "default.svg"
    part = lambda when, field=None: {
        "skins": ["default"],
        "fields": {"extender": field or {"type": "choice", "options": ["none", "straight", "long"],
                                         "drawn-by-absence": ["none"]}},
        "body": {"depth": 10, "boxes": [{"id": "ext", "at": [0, 0], "size": [1, 1],
                                         "depth": 1, "when": when}]}}
    run = lambda d: _caught("L148", lint.lint_component_fitted_pieces, tmp_path / "contract.yaml", d)
    skin.write_text('<svg xmlns="http://www.w3.org/2000/svg">'
                    '<g data-show-from="extender" data-show="straight" display="none"/></svg>')
    assert not run(part({"extender": ["straight"]}))
    assert any("not an option" in m for m in run(part({"extender": ["sideways"]})))
    assert any("not a choice" in m for m in run(part({"colour": ["red"]})))
    assert any("not a choice" in m for m in run(part({"extender": ["straight"]}, {"type": "text"})))
    hits = run(part({"extender": ["long"]}))
    assert hits and "never built" in hits[0], hits


def test_a_round_piece_says_how_it_stands_and_a_shown_drawing_exists():
    def part(box, faces=None):
        d = {"size": {"w": 100.0, "h": 20.0, "d": 100.0},
             "body": {"depth": 100.0, "boxes": [{"at": [0, 0], "depth": 10.0,
                                                 "confidence": "estimated", **box}]}}
        if faces:
            d["faces"] = faces
        return d
    run = lambda p: _caught("L71", lint.lint_component_body_boxes, pathlib.Path("x.yaml"), p)
    ok = {"id": "r", "size": [10, 4], "shape": "ring", "axis": "y", "wall": 1.5}
    assert not run(part(ok))
    assert any("no `axis`" in m for m in run(part({**ok, "axis": None})))
    assert any("no `wall`" in m for m in run(part({**ok, "wall": None})))
    assert any("that is a cylinder" in m for m in run(part({**ok, "wall": 5})))
    # across a y axis the cross-section is width by depth: 10 x 10 here
    assert any("as wide as it is deep" in m for m in run(part({**ok, "size": [12, 4]})))
    assert any("not round" in m for m in run(part({"id": "b", "size": [10, 4], "axis": "y"})))
    shown = {"id": "t", "size": [10, 4], "shows": ["plan"]}
    assert any("declares no `faces.plan`" in m for m in run(part(shown)))
    assert not run(part(shown, {"plan": {"ref": "x/y-plan@1"}}))
    assert any("only a box" in m for m in
               run(part({**ok, "shows": ["plan"]}, {"plan": {"ref": "x/y-plan@1"}})))


def _caught(code, fn, *a):
    with lint.collecting() as got:
        fn(*a)
    return [m for m in got.warnings + got.errors if f"[{code}]" in m]


def test_a_box_cannot_reach_past_the_part_s_own_depth():
    part = lambda d, bd, frm: {"size": {"w": 100.0, "h": 60.0, "d": d},
                               "body": {"depth": bd, "boxes": [
                                   {"id": "pcb", "at": [0, 0], "size": [1.6, 77.0],
                                    "from": frm, "depth": 170.9, "confidence": "measured"}]}}
    hits = _caught("L71", lint.lint_component_body_boxes, pathlib.Path("x.yaml"), part(170.9, 170.9, 13.9))
    assert hits and "184.8" in hits[0], hits
    assert not _caught("L71", lint.lint_component_body_boxes, pathlib.Path("x.yaml"), part(184.8, 184.8, 13.9))
    # and the pull distance is read from body.depth, so that has to be the reach too
    hits = _caught("L71", lint.lint_component_body_boxes, pathlib.Path("x.yaml"), part(184.8, 20.0, 13.9))
    assert hits and "body.depth" in hits[0], hits


def test_two_boxes_cannot_share_a_face_plane_where_they_overlap():
    """Coplanar faces z-fight: the A100's connector housing ended at y 14.4,
    the plane of the cover's bottom, and the ceiling under it shimmered."""
    part = lambda *boxes: {"size": {"w": 100.0, "h": 60.0, "d": 50.0},
                           "body": {"depth": 50.0, "boxes": [
                               dict(b, confidence="measured") for b in boxes]}}
    cover = {"id": "cover", "at": [0, 6.01], "size": [100, 8.39], "from": 0, "depth": 50}
    flush = {"id": "housing", "at": [10, 3.5], "size": [18, 10.9], "from": 10, "depth": 20}
    lifted = dict(flush, size=[18, 10.85])
    run = lambda *b: _caught("L71", lint.lint_component_body_boxes, pathlib.Path("x.yaml"), part(*b))
    hits = run(cover, flush)
    assert hits and "cover" in hits[0] and "housing" in hits[0] and "y 14.4" in hits[0], hits
    assert not run(cover, lifted)
    # boxes that abut, or only touch at an edge, are not coplanar overlaps
    assert not run(cover, {"id": "next", "at": [0, 14.4], "size": [100, 5], "from": 0, "depth": 50})
    assert not run(cover, {"id": "beside", "at": [100, 6.01], "size": [5, 8.39], "from": 0, "depth": 50})
    # options that are never drawn together are not compared
    a = dict(flush, when={"extender": ["straight"]})
    b = dict(cover, when={"extender": ["long-offset"]})
    assert not run(a, b)


def test_no_library_part_has_coplanar_body_boxes():
    for f in sorted((LIB / "components").glob("**/contract.yaml")):
        boxes = ((yaml.safe_load(f.read_text()) or {}).get("body") or {}).get("boxes") or []
        assert not lint.coplanar_box_faces(boxes), (f, lint.coplanar_box_faces(boxes)[:3])


def test_every_riser_carries_its_pcb_and_a_connector_per_card_slot():
    """The point of the exercise: the riser IS its PCB, and a slot that takes
    a card has a connector behind it while one that takes only a filler has
    none - riser 1A's middle opening."""
    risers = sorted((LIB / "components/dell").glob("riser-[123][a-f]-14g/v*/contract.yaml"))
    # EVERY MAJOR, AND COUNTED: the glob named v1, and when the full-height
    # risers moved to v2 it went on passing over the two that had not.
    assert len(risers) >= 11, [str(r) for r in risers]
    for p in risers:
        c = yaml.safe_load(p.read_text())
        boxes = {b["id"]: b for b in c["body"]["boxes"]}
        assert "pcb" in boxes, p
        pcb = boxes["pcb"]
        assert abs(pcb["from"] + pcb["depth"] - c["size"]["d"]) < 0.05, (p, "the PCB is the reach")
        assert c["body"]["depth"] == c["size"]["d"], p
        for slot, b in (c.get("bays") or {}).items():
            takes_card = any("bracket" in a for a in b["accepts"])
            assert (f"{slot}-connector" in boxes) == takes_card, (p, slot)


def test_a_configuration_can_seat_a_riser_slot():
    """A card goes into a riser's slot from the device file: the
    configuration's bay map takes a nested key, `riser-1/slot-1`, and it
    wins over the module bay's default. Rendered on a fixture that seats
    riser 1B in a bay and the generic card in its top slot."""
    import re
    from portrayal import render
    lib = render.Library([str(LIB)])
    view = {"size": {"w": 434.0, "h": 86.8}, "components": {"bays": [
        {"id": "riser-1", "at": [13.95, 4.0], "size": {"w": 107.59, "h": 62.0},
         "accepts": ["dell/riser-1b-14g@2"], "default": "dell/riser-1b-14g@2"}]}}
    d = {"name": "f", "manufacturer": "F", "model": "F", "version": "0.1.0",
         "chassis": {"width": 434.0, "height": 86.8, "depth": 700.0},
         "views": {"rear": view}}
    def render_with(bays):
        out = render.render_view(d, "rear", view, lib, config={"bays": bays})
        return out if isinstance(out, str) else render.ET.tostring(out, encoding="unicode")
    plain = render_with({})
    assert re.search(r'data-path="riser-1/module/slot-1/module"[^>]*data-ref="dell/pcie-filler-fh-14g@2', plain)
    seated = render_with({"riser-1/slot-1": "common/pcie-card-fh@2", "riser-1/slot-3": ""})
    assert re.search(r'data-path="riser-1/module/slot-1/module"[^>]*data-ref="common/pcie-card-fh@2', seated)
    assert re.search(r'data-path="riser-1/module/slot-2/module"[^>]*data-ref="dell/pcie-filler-fh-14g@2', seated)
    assert not re.search(r'data-path="riser-1/module/slot-3/module"', seated), "an empty string empties the slot"


def test_lint_walks_a_nested_configuration_key():
    dev = lambda bays: {"views": {"rear": {"size": {"w": 434.0, "h": 86.8}, "components": {"bays": [
                            {"id": "riser-1", "at": [13.95, 4.0], "size": {"w": 107.59, "h": 62.0},
                             "accepts": ["dell/riser-1b-14g@2"], "default": "dell/riser-1b-14g@2"}]}}},
                        "configurations": {"c": {"bays": bays}}}
    run = lambda bays: _caught("L8", lint.lint_device_configuration_bays, pathlib.Path("x.yaml"), dev(bays), [str(LIB)])
    assert not run({"riser-1/slot-1": "common/pcie-card-fh@2", "riser-1/slot-2": ""})
    hits = run({"riser-1/slot-9": "common/pcie-card-fh@2"})
    assert hits and "unknown nested bay" in hits[0], hits
    hits = run({"riser-1/slot-1": "common/pcie-card-lp@1"})
    assert hits and "does not accept" in hits[0], hits
    hits = run({"riser-9": "dell/riser-1b-14g@2"})
    assert hits and "unknown bay" in hits[0], hits


def test_a_seated_part_is_projected_into_another_view_once():
    """The rear bay says where its occupant's plan lands in the top view;
    the occupant's contract says what draws it from above. The top view gets
    a PROJECTION - `data-of` the rear path, `data-projection`, no data-path
    of its own and no relief - and the cards in the riser's slots come along
    at their declared offsets, mirrored with the riser."""
    import re
    from portrayal import render
    lib = render.Library([str(LIB)])
    rear = {"size": {"w": 434.0, "h": 86.8}, "components": {"bays": [
        {"id": "riser-1", "at": [13.95, 4.0], "size": {"w": 107.59, "h": 62.0},
         "accepts": ["dell/riser-1b-14g@2"], "default": "dell/riser-1b-14g@2",
         "plan": {"view": "top", "at": [408.0, 13.9], "in": "board", "under": ["lid"]}},
        {"id": "riser-3", "at": [309.085, 4.0], "size": {"w": 107.59, "h": 41.68},
         "accepts": ["dell/riser-3a-14g@2"], "default": "dell/riser-3a-14g@2",
         "plan": {"view": "top", "at": [14.1, 13.9], "in": "board", "mirror": True}}]}}
    top = {"size": {"w": 434.0, "h": 737.5}, "components": {"placements": [
        {"ref": "dell/system-board-14g@1", "id": "board", "at": [5.5, 6.2]},
        {"ref": "dell/system-cover-14g@1", "id": "lid", "at": [0.0, 0.0]}]}}
    d = {"name": "f", "manufacturer": "F", "model": "F", "version": "0.1.0",
         "chassis": {"width": 434.0, "height": 86.8, "depth": 737.5},
         "views": {"rear": rear, "top": top}}
    out = render.render_view(d, "top", top, lib, config={"bays": {"riser-1/slot-1": "common/pcie-card-fh@2"}})
    svg = out if isinstance(out, str) else render.ET.tostring(out, encoding="unicode")
    g = re.search(r'<g id="riser-1-plan"[^>]*>', svg)
    assert g, "the riser's plan is not in the top view"
    assert 'data-projection="1"' in g.group(0) and 'data-of="riser-1/module"' in g.group(0)
    assert 'data-path=' not in g.group(0), "a projection is not a second part in the tree"
    assert 'data-in="board"' in g.group(0)
    # the projection carries no relief for the kit to build
    body = svg[g.end():svg.index("</g>", g.end())]
    assert "data-z-" not in body and "data-ref" not in body
    # the seated card came along, inboard of the PCB, under the riser's plan
    c = re.search(r'<g id="riser-1-slot-1-plan"[^>]*>', svg)
    assert c and 'data-of="riser-1/module/slot-1/module"' in c.group(0), "the card's plan is missing"
    assert re.search(r'translate\(310\.1,0(\.0)?\)', c.group(0)), c.group(0)
    # the fillers in slots 2 and 3 have no plan and draw nothing
    assert 'id="riser-1-slot-2-plan"' not in svg
    # riser 3 is mirrored: its slot-7 filler draws nothing, and its own plan flips
    r3 = re.search(r'<g id="riser-3-plan"[^>]*>', svg)
    assert r3 and "scale(-1,1)" in r3.group(0)
