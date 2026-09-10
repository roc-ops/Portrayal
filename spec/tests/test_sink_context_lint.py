"""L77 fires on a sink with no floor under it, and stays quiet on a real one.

The library sweep next door (`test_sink_sits_in_a_cavity`) can only say that
nothing is wrong TODAY. These are the cases the rule has to separate, written out
so a change to the predicate has to answer for each of them - and so the quiet
half is pinned as hard as the loud half. A rule that fires on every sink would
pass the sweep and be useless, because every correct sink in the library
(`common/screw-head@1`'s driver slots, `common/reset-button@1`'s pinhole, 3664
nodes in all) is one it must not touch.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "spec/tools/portrayal"))
import lint as L  # noqa: E402


def run(doc, path="t"):
    # L77 is an err, not a warn: publish.sh gates the build on lint errors, so a
    # contract cannot put an unbuildable recess into the dist at all.
    L.ERRORS.clear()
    L.lint_component_sink_context(path, doc)
    return [e for e in L.ERRORS if "L77" in e]


def part(**kw):
    doc = {"kind": "component", "size": {"w": 10.0, "h": 10.0}, "relief": {}}
    doc.update(kw)
    return doc


def test_a_sink_on_a_solid_face_is_caught():
    """`common/qsfp-pull-tab@1`'s speed cut: a recess declared through a solid
    crossbar, collected by nothing and drawn by nothing since the day it was
    written."""
    hits = run(part(relief={"features": [{"node": "speed-cut", "sink": 1.2,
                                          "lift": 34.8}]}))
    assert len(hits) == 1, hits
    assert "speed-cut" in hits[0] and "pocket" in hits[0]


def test_a_sink_in_a_part_that_is_itself_a_cavity_is_silent():
    """`common/screw-head@1`: an aperture part, so its own group carries
    `data-depth` and the driver slots have a floor to measure from."""
    assert run(part(size={"w": 5.0, "h": 5.0, "d": 1.2},
                    relief={"features": [{"node": "slot-h", "sink": 0.5},
                                         {"node": "slot-v", "sink": 0.5}]})) == []


def test_a_solid_module_that_says_it_has_a_cavity_is_silent():
    """A module is solid and gets `data-body-depth` instead - unless it says
    `relief.cavity`, which is a part insisting it really does have a recess."""
    module = {"kind": "module", "size": {"w": 40.0, "h": 40.0, "d": 60.0}}
    assert run(part(**module,
                    relief={"features": [{"node": "grille", "sink": 2.0}]})) != []
    assert run(part(**module,
                    relief={"cavity": "well",
                            "features": [{"node": "grille", "sink": 2.0}]})) == []


def test_a_part_that_mounts_is_solid_even_with_a_depth():
    """`mounts` means it stands ON the metal - a rack ear, a ground lug - so
    there is no hole behind it and no floor inside it."""
    assert run(part(behaviour="mounts", size={"w": 20.0, "h": 40.0, "d": 6.0},
                    relief={"features": [{"node": "recess", "sink": 1.0}]})) != []


def test_a_sink_inside_a_pocket_declared_by_the_same_part_is_silent(tmp_path):
    """The nesting the rule has to read out of the skin, because the relief block
    is a flat list and says nothing about what contains what. A pocket IS a
    cavity, so a step in its floor is a sink and is correct.
    """
    skins = tmp_path / "skins"
    skins.mkdir()
    (skins / "default.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
        '<g id="well"><rect id="step" x="1" y="1" width="2" height="2"/></g>'
        '<rect id="loose" x="5" y="5" width="2" height="2"/></svg>')
    doc = part(relief={"features": [{"node": "well", "pocket": 3.0},
                                    {"node": "step", "sink": 0.5}]})
    assert run(doc, str(tmp_path / "contract.yaml")) == []

    # and the same sink OUTSIDE that pocket still is not
    doc = part(relief={"features": [{"node": "well", "pocket": 3.0},
                                    {"node": "loose", "sink": 0.5}]})
    hits = run(doc, str(tmp_path / "contract.yaml"))
    assert len(hits) == 1 and "loose" in hits[0], hits


def test_a_skin_that_does_not_nest_it_is_not_excused_by_one_that_does(tmp_path):
    """The relief block is shared across skins and the drawing is not.

    `common/qsfp-pull-tab@1` has two skins; parts in this library routinely have
    several. A node inside the pocket on one and beside it on another has a floor
    under it on one drawing and nothing on the other, and the second drawing is
    exactly the defect. Checking `any` skin would let the good one excuse it.
    """
    skins = tmp_path / "skins"
    skins.mkdir()
    (skins / "white.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
        '<g id="well"><rect id="step" x="1" y="1" width="2" height="2"/></g></svg>')
    (skins / "blue.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
        '<g id="well"/><rect id="step" x="5" y="5" width="2" height="2"/></svg>')
    hits = run(part(relief={"features": [{"node": "well", "pocket": 3.0},
                                         {"node": "step", "sink": 0.5}]}),
               str(tmp_path / "contract.yaml"))
    assert len(hits) == 1 and "step" in hits[0], hits


def test_a_part_with_no_sinks_is_silent():
    assert run(part(relief={"features": [{"node": "body", "out": 3.0}]})) == []
    assert run(part()) == []
