"""How a part MOVES, which is what a renderer needs and a catalogue class cannot say.

The 3D viewer decided what could be ejected from a hardcoded list of class names,
so every new removable type meant editing that list - and a transceiver, which is
removable, was not on it. `behaviour` replaces the list with a fact the component
states about itself.
"""
import functools
import sys
from pathlib import Path

import pytest
import yaml

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"

CONTRACTS = sorted(LIB.glob("components/*/*/*/contract.yaml"))
VALID = {"fills", "occupies", "mounts"}


# 253 contracts, parsed once each rather than once per question. The set
# comprehension below calls this TWICE per file, and five tests here walk the
# whole library - which made this file 12.7s of a 38s suite, all of it re-reading
# bytes that had not changed since the last read a microsecond earlier.
@functools.lru_cache(maxsize=None)
def load(p):
    return yaml.safe_load(p.read_text()) or {}


def test_every_behaviour_is_one_of_three():
    for p in CONTRACTS:
        b = load(p).get("behaviour")
        assert b is None or b in VALID, (p, b)


def test_a_class_cannot_answer_this_which_is_why_the_field_exists():
    """Two classes are already mixed, and a class list cannot express either.

    `filter` holds five slide-out air filters and one snap-on cover; `inlet`
    holds three receptacles and one bolted panel. If these ever collapse to one
    behaviour each, either the library changed or somebody derived the field
    from the class again and lost the distinction.
    """
    for cls in ("filter", "inlet"):
        seen = {load(p).get("behaviour") for p in CONTRACTS if load(p).get("class") == cls}
        assert len(seen) > 1, f"{cls} came out uniform: {seen}"


def test_a_receptacle_does_not_move():
    """A cage, a lamp, a button and a printed mark do not come out, and saying
    nothing is how they say so. A `port` that gains a behaviour would be given a
    3D body and an eject control it has no business having."""
    for p in CONTRACTS:
        d = load(p)
        if d.get("class") in ("port", "led", "button", "silkscreen"):
            assert d.get("behaviour") is None, p


def test_the_transceiver_is_removable():
    """The gap this issue was filed for: removable, and not on the class list."""
    for name in ("common/sfp-lc-duplex", "common/qsfp-transceiver"):
        ns, n = name.split("/")
        p = next(iter(LIB.glob(f"components/{ns}/{n}/*/contract.yaml")))
        assert load(p).get("behaviour") == "occupies", p


def test_the_old_class_list_is_a_subset_of_fills():
    """Nothing that used to get a body may lose one. The five classes the viewer
    hardcoded must all still qualify, or the migration dropped a FRU."""
    for cls in ("psu", "fan", "tab", "power", "cooling"):
        for p in CONTRACTS:
            d = load(p)
            if d.get("class") == cls:
                assert d.get("behaviour") == "fills", (p, d.get("behaviour"))


# --- what the field is FOR, downstream of stating it -------------------------
#
# Declaring `behaviour` on 178 parts is worth nothing while no consumer can read
# it. Two things went wrong in exactly that way and both are pinned below: the
# component index never emitted the field, so `components.json` said `None` for
# every part; and the renderer drew every placement before every bay, so a part
# bolted across an opening painted UNDER the opening.

def needs_dist(name):
    """These read what the build EMITS, which is the only place the claim lives.

    Without the guard a fresh clone reports `FileNotFoundError` from inside
    pathlib and reads as a broken test rather than an unbuilt tree - which is
    exactly how it presented the first time it fired, during a build running
    alongside the suite.
    """
    p = LIB / "dist" / name
    if not p.exists():
        pytest.skip(f"{p} not built - run ./build.sh")
    return p


def test_the_component_index_actually_emits_behaviour():
    """It was in the contracts and on the SVG as data-behaviour, and absent from
    the one file most consumers read. A field nothing can see is not a field."""
    import json
    comps = json.loads(needs_dist("components.json").read_text())["components"]
    stated = {f"{c['ns']}/{c['name']}": c.get("behaviour") for c in comps}
    assert any(v for v in stated.values()), "components.json carries no behaviour at all"
    for p in CONTRACTS:
        d = load(p)
        key = f"{p.parents[2].name}/{d.get('name')}"
        if key in stated and d.get("behaviour"):
            assert stated[key] == d["behaviour"], (key, stated[key], d["behaviour"])


def test_mounted_parts_paint_after_bays():
    """A bay draws its opening, and an empty bay draws it dark. Anything mounted
    across that opening has to come later in document order or the hole paints
    over the thing physically in front of it.

    The C40G is the case that found it: a snap-on louvred filter cover spans all
    four PSU bays, which default to empty, so four dark rectangles landed on top
    of the cover. Checked on the rendered document rather than on the manifest,
    because document order is the whole claim.
    """
    svg = needs_dist("c40g.docsis-classic.front.svg").read_text()
    cover = svg.find('id="psu-cover"')
    assert cover != -1, "psu-cover is not in the C40G front view"
    for bay in ("psu-1", "psu-2", "psu-3", "psu-4"):
        at = svg.find(f'id="{bay}"')
        assert at != -1, f"{bay} is not in the C40G front view"
        assert at < cover, f"{bay} paints after the cover that covers it"


def test_a_mounted_part_under_an_opening_paints_before_it():
    """The second pass is for parts IN FRONT of openings. The R740xd's
    heatsinks are `mounts` because they lift off, and on a mid-tray
    configuration they are under the tray and its four drive bays - the
    drives sit at 55.49 and the heatsink tops at 40.8. Deferring them with
    the lids painted heatsinks over drives. A mounted part that says
    `under:` a bay or a well is drawn with the wells, in `under:` order."""
    svg = needs_dist("r740xd.lff12-mlff4-rlff2-rc0-noriser.top.svg").read_text()
    for hs in ("heatsink-1", "heatsink-2"):
        at = svg.find(f'id="{hs}"')
        assert at != -1, f"{hs} is not in the R740xd top view"
        for over in ("mid-lff-0", "mid-lff-3", "mid-drive-tray-lff", "system-cover"):
            o = svg.find(f'id="{over}"')
            assert o != -1, f"{over} is not in the R740xd top view"
            assert at < o, f"{hs} paints after {over}, which lies over it"


def test_a_part_in_a_well_is_sunk_to_its_floor():
    """The 3D reads a part's height off the face. A DIMM in the system board
    is not at the face: it stands on the PCB 79.9 down and rises its own
    31.3, so its plane is 48.6 down; a drive in the mid tray stands on a
    floor 31.31 down and rises 26.1, so its top is 5.21 down, where Dell's
    model has it. `in:` emits that as a negative data-z-lift, and a mounted
    part's `out` is pulled down by the well's depth so it rises from the
    floor rather than from the lid line."""
    import re
    svg = needs_dist("r740xd.lff12-mlff4-rlff2-rc0-noriser.top.svg").read_text()
    def lift(id_):
        m = re.search(rf'id="{id_}"[^>]*data-z-lift="([^"]+)"', svg)
        assert m, f"{id_} carries no data-z-lift"
        return float(m.group(1))
    assert lift("dimm-a1") == -48.6
    assert lift("heatsink-1") == -79.9
    assert lift("mid-lff-0") == -5.21
    assert lift("fan-0") == -3.48
    m = re.search(r'id="heatsink-1--block"[^>]*data-z-out="([^"]+)"', svg)
    assert m and float(m.group(1)) == -46.8, "the heatsink's out was not pulled down to the floor"
