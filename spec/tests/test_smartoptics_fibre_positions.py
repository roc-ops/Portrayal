"""The Smartoptics fibres stay where the sources put them (B3, "The Smartoptics
axis").

`common/lc-duplex-adapter@5` moved its ferrule axis from 5.5 to 5.82 inside
its body, so the bulkhead keyway fits. The fibre positions are what the
devices resolved from a source - the stencil ShapeSheet connection points -
so the ferrules keep them and every placement of the adapter moved its BODY
0.32 toward its own latch side instead. This pins the outcome, on real
builds: every optical point and every bore and duplex mate inside a placed
lc-duplex-adapter, on the four devices that draw one, equals the figure the
build gave before the move (origin/main at #509, with @4), to 1e-6.

The expected figures are a fixture measured off those builds, not derived
here, so a second move of the axis - or of a body without its ferrules -
fails this test instead of passing through it.
"""
import json
import math
import pathlib
import shutil

import pytest
import xml.etree.ElementTree as ET

from test_nested_occupants import LIB, device_point
from test_slot_defaults import build

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "smartoptics_fibre_positions.json"
ADAPTER = "common/lc-duplex-adapter@"
# (device, the drawing that shows the chain): the three that place the
# adapter directly, and dcp-2 in the configuration seating the A22 and a PPM
FACES = [("dcp-r-34d-cs", "dcp-r-34d-cs.front.svg"),
         ("dcp-r-9d-cs", "dcp-r-9d-cs.front.svg"),
         ("dcp-m32-cso-zr", "dcp-m32-cso-zr.front.svg"),
         ("dcp-2", "dcp-2.ila-node.front.svg")]


def chain_points(svg_path):
    """{key: [x, y]} for every `optical` and `mate` connection point drawn
    inside a placed lc-duplex-adapter, in the device frame. The key is the
    point's kind, the data-path of the part it belongs to, and its order
    there - stable across builds, since ids do not change."""
    svg = ET.parse(svg_path).getroot()
    parents = {c: p for p in svg.iter() for c in p}
    out, seen = {}, {}
    for el in svg.iter():
        cp = el.get("data-cp")
        if cp not in ("optical", "mate"):
            continue
        node, owner, inside = parents.get(el), None, False
        while node is not None:
            if owner is None and node.get("data-path") is not None:
                owner = node.get("data-path")
            if (node.get("data-ref") or "").startswith(ADAPTER):
                inside = True
                break
            node = parents.get(node)
        if not inside:
            continue
        at = [float(v) for v in el.get("data-cp-at").split()]
        base = f"{cp} {owner}"
        n = seen[base] = seen.get(base, -1) + 1
        out[f"{base} #{n}"] = list(device_point(parents, el, at))
    return out


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("so")
    for name, _svg in FACES:
        src = LIB / "devices" / "smartoptics" / name
        dev = shutil.copytree(src, out / "src" / name) / "device.yaml"
        build(dev, out / "o", LIB)
    return out / "o"


def test_the_fixture_holds_every_fibre_on_the_chain():
    want = json.loads(FIXTURE.read_text())
    assert sorted(want) == sorted(n for n, _ in FACES)
    for name, pts in want.items():
        optical = [k for k in pts if k.startswith("optical ")]
        mates = [k for k in pts if k.startswith("mate ")]
        # one optical point per adapter and its two bores' mates (@4 had no
        # mate of its own: the pair's seat is B3's, and is checked below)
        assert len(optical) > 0 and len(mates) == 2 * len(optical), (name, len(optical), len(mates))


@pytest.mark.parametrize("name,svg", FACES)
def test_every_smartoptics_fibre_is_where_it_was_before_the_axis_moved(built, name, svg):
    want = json.loads(FIXTURE.read_text())[name]
    got = chain_points(built / svg)
    assert set(want) <= set(got), sorted(set(want) - set(got))[:6]
    assert len(want) > 0
    off = {k: round(math.dist(got[k], want[k]), 6) for k in want
           if math.dist(got[k], want[k]) > 1e-6}
    assert off == {}, dict(list(off.items())[:6])
    # WHAT THE BUILD HAS THAT @4 DID NOT: each adapter's own duplex seat,
    # which must sit on that adapter's fibre midpoint - its optical point
    extra = sorted(set(got) - set(want))
    assert len(extra) == sum(k.startswith("optical ") for k in want), extra[:6]
    for k in extra:
        assert k.startswith("mate ") and k.endswith(" #0"), k
        owner = k[len("mate "):-len(" #0")]
        assert math.dist(got[k], got[f"optical {owner} #0"]) < 1e-6, k


def test_the_xc_rows_ferrule_lines_are_the_row_pitch_apart(built):
    """The two XC rows of the DCP-R-34D-CS stand 11.5 apart on the stencil,
    and so do their ferrule lines - the rows are turned 180 about the gap
    between them, so this holds only if each body moved toward its OWN latch
    side."""
    got = chain_points(built / "dcp-r-34d-cs.front.svg")
    top = {round(v[1], 6) for k, v in got.items() if k.startswith("optical xc") and int(k.split()[1][2:]) <= 17}
    bot = {round(v[1], 6) for k, v in got.items() if k.startswith("optical xc") and int(k.split()[1][2:]) >= 18}
    assert len(top) == 1 and len(bot) == 1, (top, bot)
    assert bot.pop() - top.pop() == pytest.approx(11.5, abs=1e-6)
