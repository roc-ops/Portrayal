"""A ring is solid round its opening (#968, docs/cable-lay-design.md section 3.3).

A ring's contract says what of its loop is solid: `wall` (each leg beside the
opening), `height` (the top of the loop over its base) and `slit` (the gap in
its far leg), with `sill`, `depth` and `aperture.at`. They compile to
`data-guide-wall`, `data-guide-height` and `data-guide-slit`, and rack.json
derives the loop's solids from them (`rack_solids.ring_solids`). L138 holds
each inside the part. The snap-in ring's relief is built to the same figures,
so the loop a router may not pass through is the loop that is drawn.
"""
import copy
import pathlib
import xml.etree.ElementTree as ET

import jsonschema
import pytest
import yaml

from portrayal import lint, rack_solids
from test_rack_trays import COMPONENT_SCHEMA, RING, SVG, _render

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _ring():
    return yaml.safe_load(RING.read_text())


def _l138(doc):
    with lint.collecting() as found:
        lint.lint_component_guide("c.yaml", doc)
    return [m for m in found.errors if "[L138]" in m]


# --- the contract and its relief --------------------------------------------------

def test_the_snap_in_ring_says_what_of_it_is_solid():
    doc = _ring()
    jsonschema.validate(doc, COMPONENT_SCHEMA)
    g = doc["guide"]
    assert (g["wall"], g["height"], g["slit"]) == (5.8, 41.0, [28.6, 30.8])
    for k in ("guide-wall", "guide-height", "guide-slit"):
        assert doc["provenance"][k].startswith("drawing - "), k
    # the legs and the opening fill the ring's 43.6 across the run, and the
    # bar over the opening is 5.9 thick, the 6.0 the drawing gives to a pixel
    assert 2 * g["wall"] + g["aperture"]["w"] == pytest.approx(doc["size"]["h"])
    assert g["aperture"]["at"][1] == pytest.approx(g["wall"])
    assert g["height"] - g["sill"] - g["aperture"]["h"] == pytest.approx(5.9)


def test_the_relief_is_built_to_the_guide():
    """The fault #968 found: the relief drew each leg 6.8 in the plane of the
    loop, so its opening was 30.0 where the guide's is 32.0, and the sill
    point of a route sat 1 mm into the rear leg. Each figure of the relief's
    loop now agrees with the guide's."""
    doc = _ring()
    g, el = doc["guide"], doc["elements"]
    feat = {f["node"]: f for f in doc["relief"]["features"]}
    rear, front, hook = el["leg-rear"], el["leg-front"], el["hook"]
    # across the run: the rear leg ends where the opening begins, the front
    # leg and the hook start where it ends, each `wall` thick
    assert rear["at"][1] + rear["size"][1] == pytest.approx(g["aperture"]["at"][1])
    assert front["at"][1] == pytest.approx(g["aperture"]["at"][1] + g["aperture"]["w"])
    assert hook["at"] == front["at"] and hook["size"] == front["size"]
    assert rear["size"][1] == front["size"][1] == pytest.approx(g["wall"])
    # along the run, the band
    for e in (rear, front, hook, el["top"]):
        assert e["at"][0] == pytest.approx(g["aperture"]["at"][0]) and e["size"][0] == pytest.approx(g["depth"])
    # out of the tray: the rear leg the full height, the front leg up to the
    # slit, the hook from the slit to the top
    assert feat["leg-rear"]["cyl"] == pytest.approx(g["height"])
    assert feat["leg-front"]["cyl"] == pytest.approx(g["slit"][0])
    assert feat["hook"]["lift"] == pytest.approx(g["slit"][1])
    assert feat["hook"]["lift"] + feat["hook"]["cyl"] == pytest.approx(g["height"])
    # and the skin draws the same rects the elements state
    skin = ET.parse(RING.parent / "skins" / "default.svg").getroot()
    rects = {r.get("id"): r for r in skin.iter() if r.get("id")}
    for name in ("leg-rear", "leg-front", "hook"):
        r = rects[name]
        assert [float(r.get(k)) for k in ("x", "y", "width", "height")] == pytest.approx(el[name]["at"] + el[name]["size"]), name


def test_the_profile_draws_the_same_slit():
    """The side view of the lacer draws one ring's loop with its slit: the
    gap it leaves in the front leg is the guide's, measured from the tray."""
    g = _ring()["guide"]
    for side, x in (("right", "2.65"), ("left", "107.35")):
        svg = (ROOT / f"library/components/fs/fhd-cmp5dr-profile/v1/skins/{side}.svg").read_text()
        path = next(el for el in ET.fromstring(svg).iter() if el.get("id") == "ring")
        d = path.get("d")
        # the tray's top is at y 41 of the view; the path starts on the front
        # leg's tip and ends on the hook's
        start, end = d.split()[0], d.split()[-1]
        assert start == f"M{x},{41 - g['slit'][0]:g}" and end == f"L{x},{41 - g['slit'][1]:g}", (side, d)


# --- L138 --------------------------------------------------------------------------

def test_L138_passes_the_snap_in_ring():
    assert not _l138(_ring())


@pytest.mark.parametrize("change", [
    {"wall": 6.0},                     # 5.8 + 32 + 6.0 runs off the 43.6
    {"height": 34.0},                  # below the opening's top, 35.1
    {"height": 42.0},                  # higher than the part's relief, 41
    {"slit": [3.0, 30.8]},             # starts below the sill, 5.6
    {"slit": [30.8, 28.6]},            # ends before it starts
    {"slit": [28.6, 42.0]},            # runs past the top of the loop
])
def test_L138_fails_a_loop_off_its_part(change):
    doc = copy.deepcopy(_ring())
    doc["guide"].update(change)
    assert _l138(doc), change


def test_L138_a_slit_needs_the_legs_and_a_loop_needs_a_run_in_the_face():
    doc = copy.deepcopy(_ring())
    del doc["guide"]["wall"]
    assert any("slit" in m for m in _l138(doc))
    doc = copy.deepcopy(_ring())
    doc["guide"] = {"kind": "ring", "aperture": {"w": 20.0, "h": 20.0}, "run": "z", "height": 30.0}
    assert any("runs out of the face" in m for m in _l138(doc))


def test_the_schema_refuses_a_malformed_slit():
    doc = copy.deepcopy(_ring())
    for bad in ([28.6], [28.6, 30.8, 33.0], ["a", 1], -1):
        doc["guide"]["slit"] = bad
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(doc, COMPONENT_SCHEMA)


# --- the compiled face, and rack.json ---------------------------------------------

def test_the_loop_reaches_the_drawing():
    root = _render({"size": {"w": 430.0, "h": 87.0}, "components": {"placements": [
        {"ref": "fs/d-ring-snap-in@1", "id": "guide-1", "at": [20.0, 20.0], "group": "tray", "rel-pos": 1}]}})
    el = next(el for el in root.iter() if el.get("id") == "guide-1")
    assert (el.get("data-guide-wall"), el.get("data-guide-height"), el.get("data-guide-slit")) == ("5.8", "41", "28.6 30.8")


RING_G = ('data-guide="ring" data-guide-run="x" data-guide-aperture="32 29.5" data-guide-depth="6.8" '
          'data-guide-sill="5.6" data-guide-aperture-at="12.75 5.8"')
LOOP = 'data-guide-wall="5.8" data-guide-height="41" data-guide-slit="28.6 30.8"'
SHEET = {"w": 483, "h": 44, "d": 110, "shell": "sheet", "thickness": 1.5}


def _parts(extra, transform="translate(19.55,66.4)"):
    top = f'<svg {SVG}><g id="guide-1" data-ref="r@1" {RING_G} {extra} data-z-lift="-41" transform="{transform}"/></svg>'
    return {s["part"]: s["box"] for s in rack_solids.ring_solids(ET.fromstring(top), rack_solids._Frame(483, 44, 110))}


def test_a_ring_that_says_what_is_solid_is_five_boxes_round_its_opening():
    parts = _parts(LOOP)
    assert parts == {
        # the band, 6.8 along x from 32.3; the plan's y from the back, so the
        # rear leg is nearest the rail, at the far end of z
        "ring/guide-1/rear-leg": {"x": 32.3, "y": 3.0, "z": 37.8, "w": 6.8, "h": 41.0, "d": 5.8},
        "ring/guide-1/front-leg": {"x": 32.3, "y": 3.0, "z": 0.0, "w": 6.8, "h": 28.6, "d": 5.8},
        "ring/guide-1/hook": {"x": 32.3, "y": 33.8, "z": 0.0, "w": 6.8, "h": 10.2, "d": 5.8},
        "ring/guide-1/bar": {"x": 32.3, "y": 38.1, "z": 5.8, "w": 6.8, "h": 5.9, "d": 32.0},
        "ring/guide-1/seat": {"x": 32.3, "y": 3.0, "z": 5.8, "w": 6.8, "h": 5.6, "d": 32.0},
    }


def test_the_opening_is_the_one_way_through_and_matches_the_trays_reading():
    """The five boxes close the opening rack.json's `trays` reads off the same
    ring on every side but along the run, and overlap it nowhere."""
    parts = _parts(LOOP)
    top = f'''<svg {SVG}><g data-ref="t@1"><rect data-class="tray" data-tray="tray" data-tray-height="3" data-tray-run="x"
              x="0" y="48.8" width="483" height="61.2"/></g>
      <g id="guide-1" data-ref="r@1" {RING_G} {LOOP} data-z-lift="-41" transform="translate(19.55,66.4)"/></svg>'''
    (t,) = rack_solids.trays({"top": ET.fromstring(top)}, SHEET)
    o = t["rings"][0]["box"]
    hi = lambda b, k, s: b[k] + b[s]
    assert parts["ring/guide-1/rear-leg"]["z"] == pytest.approx(o["z"] + o["d"])           # the rear leg behind the opening
    assert hi(parts["ring/guide-1/front-leg"], "z", "d") == pytest.approx(o["z"])          # the front leg in front of it
    assert hi(parts["ring/guide-1/seat"], "y", "h") == pytest.approx(o["y"])               # the seat under it, its top the sill
    assert parts["ring/guide-1/bar"]["y"] == pytest.approx(o["y"] + o["h"])                # the bar over it
    assert rack_solids._overlaps(parts["ring/guide-1/seat"], o) is False
    assert not any(rack_solids._overlaps(b, o) for b in parts.values())


def test_without_a_slit_the_far_leg_is_whole_and_without_a_wall_the_ring_is_open():
    parts = _parts('data-guide-wall="5.8" data-guide-height="41"')
    assert sorted(p.split("/")[2] for p in parts) == ["bar", "front-leg", "rear-leg", "seat"]
    assert parts["ring/guide-1/front-leg"]["h"] == 41.0
    assert _parts('data-guide-height="41"') == {}
    assert _parts('data-guide-wall="5.8"') == {}


def test_a_ring_turned_across_the_device_names_its_legs_left_and_right():
    # turned a quarter: the loop now stands across x, its legs either side
    parts = _parts(LOOP, transform="translate(200,20) rotate(90)")
    assert sorted(p.split("/")[2] for p in parts) == ["bar", "hook", "left-leg", "right-leg", "seat"]
    left, right = parts["ring/guide-1/left-leg"], parts["ring/guide-1/right-leg"]
    assert left["x"] < right["x"]
    # the slit is in the far leg, which the turn puts on the left
    assert left["h"] == 28.6 and right["h"] == 41.0


def test_a_box_device_carries_no_ring_solids(tmp_path):
    """A ring on a box device's plan is inside its envelope, which is solid
    whole until step 6; only a sheet part's rings are added."""
    top = f'<svg {SVG}><g id="guide-1" data-ref="r@1" {RING_G} {LOOP} data-z-lift="-41" transform="translate(19.55,66.4)"/></svg>'
    assert rack_solids.solids({"top": ET.fromstring(top)}, {"w": 483, "h": 44, "d": 110}) is None
    out = rack_solids.solids({"top": ET.fromstring(top)}, SHEET)
    assert [s["part"].split("/")[2] for s in out] == ["rear-leg", "front-leg", "hook", "bar", "seat"]
