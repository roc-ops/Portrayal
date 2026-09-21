"""A hole through a part is not part of it.

L21, L44 and L64 measured a placed component by its box, so a part with windows
cut through it was treated as solid. maiaedge/pbc-2000-bezel@1 is the case that
showed it: one plate across the PBC-2000's face with two octagonal windows, and
the ports, legends and louvres of the faceplate seen through them. By the
bezel's box both louvre fields were 100% buried (L44) and CON, MGMT and CTRL
were painted over (L21); and the two QSFP cages read as bolted to the louvres
(L64), because a cutout that is exactly a cage's opening could not contain the
cage's flange.

The holes are read from the relief feature with `shape: true`, the same art the
kit cuts them from in 3D - so each test below that says "quiet" has a twin that
takes the openings away and gets the false positive back.
"""
import copy
from pathlib import Path

import pytest
import yaml

from portrayal import lint

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"
PBC = LIB / "devices" / "maiaedge" / "pbc-2000" / "device.yaml"
BEZEL = "maiaedge/pbc-2000-bezel@2"


class _NoSchema:
    def iter_errors(self, _data):
        return iter(())


def _run(path, rule):
    with lint.collecting() as got:
        lint.lint_device(path, _NoSchema(), [str(LIB)])
    return [w for w in got.warnings if f"[{rule}]" in w]


def _decor(view):
    with lint.collecting() as got:
        lint.lint_device_decor("t", "front", view, [str(LIB)])
    return [w for w in got.warnings if "[L44]" in w]


def _air(doc):
    with lint.collecting() as got:
        lint.lint_device_air_aperture("t", doc, [str(LIB)])
    return [w for w in got.warnings if "[L64]" in w]


@pytest.fixture
def pbc():
    return yaml.safe_load(PBC.read_text())


@pytest.fixture
def no_openings(monkeypatch):
    """The rules as they were: every part solid to its box."""
    monkeypatch.setattr(lint, "component_openings", lambda *a, **k: [])


def _write(tmp_path, doc):
    p = tmp_path / "device.yaml"
    p.write_text(yaml.safe_dump(doc, sort_keys=False))
    return p


# ------------------------------------------------------------ the reading ---

def test_the_bezel_has_its_two_windows():
    """Two octagons as the face-on photograph measured them: 36.04 tall, with
    chamfers 19.0 (left) and 17.6 (right) across by 13.0 down - not 45 degrees."""
    holes = lint.component_openings(BEZEL, "default", [str(LIB)])
    assert len(holes) == 2
    want = ((17.0, 131.2, 19.0), (241.6, 128.0, 17.6))
    for h, (x, w, cx) in zip(sorted(holes, key=lambda r: min(p[0] for p in r)), want):
        assert lint._poly_area(h) == pytest.approx(w * 36.04 - 2 * cx * 13.0, abs=0.05)
        assert min(p[0] for p in h) == pytest.approx(x)
        assert min(p[1] for p in h) == pytest.approx(2.46)


def test_a_part_without_a_shaped_relief_has_no_openings():
    assert lint.component_openings("common/qsfp-cage@2", "default", [str(LIB)]) == []


def test_curves_are_not_guessed_at():
    """A path this reader cannot follow answers no openings - the box - so it
    can cost a false positive and never a missed one."""
    assert lint._subpaths("M0 0 L10 0 L10 10 Z") == [[(0, 0), (10, 0), (10, 10)]]
    assert lint._subpaths("M0 0 h10 v10 h-10 z m2 2 h2 v2 h-2 z") == [
        [(0, 0), (10, 0), (10, 10), (0, 10)], [(2, 2), (4, 2), (4, 4), (2, 4)]]
    assert lint._subpaths("M0 0 C1 1 2 2 3 3 Z") is None


def test_a_rotated_placement_turns_its_openings_about_its_centre():
    """translate(at) rotate(deg w/2 h/2), the way render.py draws it."""
    flat = lint.placed_openings({"ref": BEZEL, "at": [0, 0]}, [str(LIB)])
    half = lint.placed_openings({"ref": BEZEL, "at": [0, 0], "rotate": 180}, [str(LIB)])
    lo = lambda hs: sorted(round(min(p[0] for p in h), 6) for h in hs)
    # 372 wide: the window at 17.0..148.2 lands at 223.8..355.0, and the one at
    # 241.6..369.6 at 2.4..130.4
    assert lo(flat) == [17.0, 241.6]
    assert lo(half) == [2.4, 223.8]


def test_open_area_clips_a_hole_to_the_box():
    square = [(0, 0), (10, 0), (10, 10), (0, 10)]
    assert lint.open_area((5, 5, 20, 20), [square]) == pytest.approx(25.0)
    assert lint.open_area((20, 20, 30, 30), [square]) == 0.0


# -------------------------------------------------- the PBC-2000, as it is ---

def test_pbc_louvres_are_not_buried_under_the_bezel():
    assert _run(PBC, "L44") == []


def test_pbc_louvres_were_buried_by_the_bezels_box(no_openings):
    ws = _run(PBC, "L44")
    # one field per louvre column and band - 14 in the left window, 10 in the right
    assert len(ws) == 24 and all("slots-h" in w and "100% buried" in w for w in ws), ws


def test_pbc_legends_in_the_window_are_not_painted_over():
    assert _run(PBC, "L21") == []


def test_pbc_legends_were_painted_over_by_the_bezels_box(no_openings):
    ws = _run(PBC, "L21")
    assert sorted(w.split("silkscreen ")[1].split(" at")[0] for w in ws) == [
        "'0'", "'1'", "'100G'", "'100G'", "'1G'", "'1G'", "'CON'", "'CTRL'", "'MGMT'"], ws
    assert all("inside bezel" in w for w in ws)


def test_pbc_cages_are_punched_through_their_cutouts():
    """port-1 and port-2 go quiet because their cutouts are their openings.
    Since v5 the legends are quiet too, for a different reason: the photograph
    showed the louvres stop at the ports, and the fields were re-laid to match."""
    ws = _run(PBC, "L64")
    assert not any("'port-1'" in w or "'port-2'" in w for w in ws), ws


# ---------------------------------------- and the rules still see the plate ---

def test_a_mark_on_the_plate_between_the_windows_is_still_painted_over(tmp_path, pbc):
    doc = copy.deepcopy(pbc)
    doc["views"]["front"]["silkscreen"].append({"at": [186.0, 22.0], "text": "X"})
    ws = _run(_write(tmp_path, doc), "L21")
    assert any("'X'" in w and "inside bezel" in w for w in ws), ws


def test_a_mark_straddling_a_window_edge_is_still_painted_over(tmp_path, pbc):
    """Wholly inside a window or it is covered: half a legend under the plate is
    half a legend nobody reads."""
    doc = copy.deepcopy(pbc)
    doc["views"]["front"]["silkscreen"].append(
        {"at": [238.0, 22.0], "text": "EDGE", "font-size": 3})   # across 241.6
    ws = _run(_write(tmp_path, doc), "L21")
    assert any("'EDGE'" in w and "inside bezel" in w for w in ws), ws


def test_a_part_the_bezel_composes_is_not_a_window(tmp_path, pbc, monkeypatch):
    """The bezel's status lamp is one of its `parts:`. Open the whole plate and
    a mark on the plate goes quiet, but a mark under the lamp does not: a hole
    in the skin is not a hole in the hardware composed on top of it."""
    monkeypatch.setattr(lint, "component_openings", lambda *a, **k: [
        [(0.0, 0.0), (372.0, 0.0), (372.0, 41.27), (0.0, 41.27)]])
    doc = copy.deepcopy(pbc)
    doc["views"]["front"]["silkscreen"] += [
        {"at": [186.0, 22.0], "text": "X"},
        {"at": [364.0, 34.4], "text": "L", "font-size": 2}]   # on the lamp at 362.6..366.6
    ws = _run(_write(tmp_path, doc), "L21")
    assert not any("'X'" in w for w in ws), ws
    assert any("'L'" in w and "inside bezel" in w for w in ws), ws


def test_a_field_behind_the_plate_is_still_buried(pbc):
    view = copy.deepcopy(pbc["views"]["front"])
    view["panel"]["decor"].append(
        {"id": "hidden", "at": [150.0, 8.0], "size": [70.0, 24.0], "pattern": "honeycomb"})
    ws = _decor(view)
    assert len(ws) == 1 and "[150.0, 8.0]" in ws[0], ws


def test_a_field_half_in_a_window_is_not_buried(pbc):
    """Across the left window's right end: 30 of 60 mm in the window, less its
    chamfer - comfortably under the 80% line."""
    view = copy.deepcopy(pbc["views"]["front"])
    view["panel"]["decor"] = [d for d in view["panel"]["decor"] if not d.get("pattern")]
    view["panel"]["decor"].append(
        {"id": "straddle", "at": [110.0, 8.0], "size": [60.0, 24.0], "pattern": "honeycomb"})
    assert _decor(view) == []


# ----------------------------------------------- L64: aperture, not flange ---

VENT = {"at": [10.0, 10.0], "size": [60.0, 30.0], "pattern": "vent", "vent": 25}
CAGE = {"ref": "common/qsfp-cage@2", "id": "q1", "at": [30.0, 15.0]}   # 19.5 x 10.18


def _vent_doc(placements, cutouts=()):
    return {"views": {"front": {
        "panel": {"decor": [VENT], "cutouts": list(cutouts)},
        "components": {"placements": list(placements)}}}}


def test_a_cage_on_a_vent_with_no_cutout_is_caught():
    assert len(_air(_vent_doc([CAGE]))) == 1


def test_a_cutout_that_is_the_cages_opening_answers_the_rule():
    """The opening std/qsfp-ganged presents, 0.575 in and 0.6 down: exactly
    what L63 derives, and not big enough to contain the cage's flange."""
    cut = {"id": "q1", "at": [30.575, 15.6], "size": [18.5, 9.58]}
    assert _air(_vent_doc([CAGE], [cut])) == []


def test_a_cutout_elsewhere_does_not():
    cut = {"id": "q1", "at": [45.0, 30.0], "size": [18.5, 9.58]}
    assert len(_air(_vent_doc([CAGE], [cut]))) == 1


def test_a_rotated_cage_is_punched_through_its_rotated_opening():
    turned = dict(CAGE, rotate=90)
    # the 19.5 x 10.18 box turned about its centre (39.75, 20.09): the opening
    # 18.5 x 9.58 at local (0.575, 0.6) lands at x 34.66..44.24, y 10.915..29.415
    cut = {"id": "q1", "at": [34.66, 10.915], "size": [9.58, 18.5]}
    assert _air(_vent_doc([turned], [cut])) == []
    assert len(_air(_vent_doc([turned]))) == 1


# --------------------------------------- a skin L21 can read, holes and all ---

def test_a_readable_skin_opens_its_own_paint_and_not_its_parts(tmp_path):
    """When the skin can be read node by node, the hole goes with the node it
    is cut in - not with the parts composed over it, and not with another node
    the skin paints inside the window. Either still covers the legend under it."""
    comp = tmp_path / "lib" / "components" / "t" / "plate" / "v1"
    (comp / "skins").mkdir(parents=True)
    (comp / "contract.yaml").write_text(yaml.safe_dump({
        "format": 1, "kind": "component", "name": "plate", "version": "1.0.0",
        "class": "bezel", "size": {"w": 40.0, "h": 20.0}, "skins": ["default"],
        "relief": {"features": [{"node": "plate", "out": 3, "shape": True}]},
        "parts": [{"ref": "common/led-dot@1", "id": "lamp", "at": [30.0, 8.0]}]}))
    (comp / "skins" / "default.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 40 20">'
        '<path id="plate" fill-rule="evenodd" fill="#222" '
        'd="M0 0 L40 0 L40 20 L0 20 Z M4 3 L36 3 L36 17 L4 17 Z"/>'
        '<rect id="tag" x="6" y="5" width="6" height="4" fill="#fff"/></svg>')
    roots = [str(tmp_path / "lib"), str(LIB)]
    assert lint.paint_boxes("t/plate@1", "default", roots) is not None, \
        "the point of this test is the readable-skin branch"
    dev = tmp_path / "device.yaml"
    dev.write_text(yaml.safe_dump({
        "format": 1, "kind": "device", "name": "t", "version": "0.1.0",
        "maturity": "draft", "manufacturer": "T", "model": "T",
        "chassis": {"width": 100, "height": 50, "depth": 100},
        "views": {"front": {
            "size": {"w": 100, "h": 50},
            "silkscreen": [{"at": [22, 20], "text": "IN", "font-size": 3},
                           {"at": [41, 15], "text": "L", "font-size": 2},
                           {"at": [19, 13], "text": "T", "font-size": 2}],
            "components": {"placements": [
                {"ref": "t/plate@1", "id": "plate", "at": [10, 5]}]}}}}))
    with lint.collecting() as got:
        lint.lint_device(dev, _NoSchema(), roots)
    ws = [w for w in got.warnings if "[L21]" in w]
    assert not any("'IN'" in w for w in ws), ws
    assert any("'L'" in w and "inside plate" in w for w in ws), ws
    # and a node the skin paints INSIDE the window is not the window
    assert any("'T'" in w and "inside plate" in w for w in ws), ws


def test_a_letter_glued_to_its_number_does_not_shift_the_extent():
    """`M0 0 L40 0` read by splitting on spaces dropped `M0` and `L40` and
    paired what was left, so a 40 x 20 plate measured 20 x 20."""
    import xml.etree.ElementTree as ET
    el = ET.fromstring('<path xmlns="http://www.w3.org/2000/svg" fill="#222" '
                       'd="M0 0 L40 0 L40 20 L0 20 Z"/>')
    assert lint._paint_box(el) == (0.0, 0.0, 40.0, 20.0)
