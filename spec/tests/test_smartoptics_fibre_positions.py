"""On the Smartoptics chain, what the source measured stays put (B3, "The
Smartoptics axis").

`common/lc-duplex-adapter@6` moved its ferrule axis from 5.5 to 5.82 inside
its body so the bulkhead keyway fits. On a face that moves either the fibre or
the body, and each composer keeps the one its own source measured:

  * THE FIBRE, where the source is the fibre. The DCP-R devices are placed off
    the stencil's ShapeSheet connection points and the DCP-M32 off the
    photograph's channel positions; the A22 carrier likewise. Their placements
    moved the BODY 0.32 toward its latch side, so every optical point and every
    bore and duplex mate inside a placed lc-duplex-adapter equals the build
    before the move (origin/main at #509, with @4), to 1e-6.
  * THE BODY, where the source is the body. The eight PPM modules measured
    the adapter block on five renders, so their placements are @4's, and on
    the dcp-2 build their adapter bodies stand where they did while the fibres
    inside them move 0.32 away from the latch.

The expected figures are a fixture measured off origin/main's builds and
contracts, not derived here, so a second move of either fails this test.
"""
import json
import math
import pathlib
import shutil

import pytest
import xml.etree.ElementTree as ET

from test_nested_occupants import LIB, device_point
from test_slot_defaults import build
from portrayal.manifest import load_yaml

FIXTURE = pathlib.Path(__file__).parent / "fixtures" / "smartoptics_fibre_positions.json"
ADAPTER = "common/lc-duplex-adapter@"
PPM = "smartoptics/ppm-"
# (device, the drawing that shows the chain): the three that place the
# adapter directly, and dcp-2 in the configuration seating the A22 and a PPM
FACES = [("dcp-r-34d-cs", "dcp-r-34d-cs.front.svg"),
         ("dcp-r-9d-cs", "dcp-r-9d-cs.front.svg"),
         ("dcp-m32-cso-zr", "dcp-m32-cso-zr.front.svg"),
         ("dcp-2", "dcp-2.ila-node.front.svg")]


def _parse(svg_path):
    svg = ET.parse(svg_path).getroot()
    return svg, {c: p for p in svg.iter() for c in p}


def _chain(parents, el):
    """(the nearest data-path above `el`, the adapter group it is in or None,
    whether a PPM module holds that adapter)."""
    node, owner, adapter, ppm = parents.get(el), None, None, False
    while node is not None:
        if owner is None and node.get("data-path") is not None:
            owner = node.get("data-path")
        ref = node.get("data-ref") or ""
        if adapter is None and ref.startswith(ADAPTER):
            adapter = node
        elif adapter is not None and ref.startswith(PPM):
            ppm = True
        node = parents.get(node)
    return owner, adapter, ppm


def chain_points(svg_path, ppm=False):
    """{key: [x, y]} for every `optical` and `mate` connection point drawn
    inside a placed lc-duplex-adapter - outside a PPM module, or inside one
    when `ppm` - in the device frame. The key is the point's kind, the
    data-path of the part it belongs to and its order there."""
    svg, parents = _parse(svg_path)
    out, seen = {}, {}
    for el in svg.iter():
        cp = el.get("data-cp")
        if cp not in ("optical", "mate"):
            continue
        owner, adapter, in_ppm = _chain(parents, el)
        if adapter is None or in_ppm != ppm:
            continue
        # NOT A POINT OF THE ADAPTER'S: a cap seated in a bore (B3 task 8, the
        # adapter ships one per bore) is drawn inside the adapter's group and
        # carries its own `mate`, which lands on the bore's by construction
        # (test_shipped_caps.py) - it is the occupant's, not a fibre position
        if "-occupant" in owner:
            continue
        at = [float(v) for v in el.get("data-cp-at").split()]
        base = f"{cp} {owner}"
        n = seen[base] = seen.get(base, -1) + 1
        out[f"{base} #{n}"] = list(device_point(parents, el, at))
    return out


def ppm_bodies(svg_path):
    """{adapter data-path: its body's corner (the group's origin) in the
    device frame} for every lc-duplex-adapter a PPM module holds."""
    svg, parents = _parse(svg_path)
    out = {}
    for el in svg.iter():
        if (el.get("data-ref") or "").startswith(ADAPTER) and el.get("data-path") and \
                any((a.get("data-ref") or "").startswith(PPM) for a in _ancestors(parents, el)):
            out[el.get("data-path")] = list(device_point(parents, el, (0.0, 0.0)))
    return out


def _ancestors(parents, el):
    node = parents.get(el)
    while node is not None:
        yield node
        node = parents.get(node)


def ppm_placements():
    """{'<module>/<id>': at} for every lc-duplex-adapter a PPM contract places."""
    out = {}
    for f in sorted((LIB / "components" / "smartoptics").glob("ppm-*/v*/contract.yaml")):
        for q in load_yaml(f).get("parts") or []:
            if q["ref"].startswith(ADAPTER):
                out[f"{f.parts[-3]}/{q['id']}"] = list(q["at"])
    return out


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("so")
    for name, _svg in FACES:
        src = LIB / "devices" / "smartoptics" / name
        dev = shutil.copytree(src, out / "src" / name) / "device.yaml"
        build(dev, out / "o", LIB)
    return out / "o"


def fixture():
    return json.loads(FIXTURE.read_text())


def test_the_fixture_holds_every_fibre_and_every_ppm_body():
    want = fixture()
    assert sorted(want["fibres"]) == sorted(n for n, _ in FACES)
    for name, pts in want["fibres"].items():
        optical = [k for k in pts if k.startswith("optical ")]
        mates = [k for k in pts if k.startswith("mate ")]
        # one optical point per adapter and its two bores' mates (@4 had no
        # mate of its own: the pair's seat is B3's, and is checked below)
        assert len(optical) > 0 and len(mates) == 2 * len(optical), (name, len(optical), len(mates))
    assert len(want["ppm-placements"]) == 14
    assert len(want["dcp-2-ppm-bodies"]) > 0 and len(want["dcp-2-ppm-fibres"]) > 0


@pytest.mark.parametrize("name,svg", FACES)
def test_where_the_source_is_the_fibre_the_fibre_stays(built, name, svg):
    want = fixture()["fibres"][name]
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


def test_where_the_source_is_the_body_the_ppm_placements_are_at4s():
    want = fixture()["ppm-placements"]
    got = ppm_placements()
    assert sorted(got) == sorted(want) and len(got) == 14
    assert {k: v for k, v in got.items() if v != want[k]} == {}


def test_on_dcp2_the_ppm_bodies_stay_and_their_fibres_move_inside_them(built):
    """The PPM seated in the dcp-2's A22: each adapter body's corner is where
    it was, and each fibre on it is exactly 0.32 further from the latch - down
    the face, since no PPM adapter is turned."""
    want = fixture()
    svg = built / "dcp-2.ila-node.front.svg"
    bodies = ppm_bodies(svg)
    assert sorted(bodies) == sorted(want["dcp-2-ppm-bodies"]) and len(bodies) > 0
    assert {k: v for k, v in bodies.items()
            if math.dist(v, want["dcp-2-ppm-bodies"][k]) > 1e-6} == {}
    fibres = chain_points(svg, ppm=True)
    was = want["dcp-2-ppm-fibres"]
    assert set(was) <= set(fibres) and len(was) > 0
    moved = {k: (round(fibres[k][0] - was[k][0], 6), round(fibres[k][1] - was[k][1], 6)) for k in was}
    assert set(moved.values()) == {(0.0, 0.32)}, moved


# --- the Tx/Rx caption frames the bodies moved toward ---------------------------------

@pytest.mark.parametrize("name", ["dcp-r-34d-cs", "dcp-r-9d-cs"])
def test_every_caption_frame_clears_the_adapter_it_labels(name):
    """The frames were generated 5.85 from the ferrule; once the bodies moved
    to keep the fibres on the connection points they met them. They now stand
    where the stencil draws them (the device's provenance.tx-rx-positions),
    and each frame - its 0.14 stroke included - clears its adapter body and
    that body's 0.2 outline stroke. Every adapter has exactly one frame, at
    its own x, on its latch side."""
    d = load_yaml(LIB / "devices" / "smartoptics" / name / "device.yaml")
    front = d["views"]["front"]
    ads = [p for p in front["components"]["placements"] if p["ref"].startswith(ADAPTER)]
    frames = [dc for dc in front["panel"]["decor"] if dc.get("size") == [13.2, 2.5]]
    assert len(ads) == len(frames) > 0
    for p in ads:
        x, y = p["at"]
        mine = [f for f in frames if abs(f["at"][0] - x) < 1e-6
                and (f["at"][1] < y) == ((p.get("rotate") or 0) % 360 == 0)]
        assert len(mine) == 1, (p["id"], len(mine))
        fy, half = mine[0]["at"][1], mine[0]["stroke-width"] / 2
        clear = (y - 0.1) - (fy + 2.5 + half) if fy < y else fy - half - (y + 11 + 0.1)
        assert clear > 0, (p["id"], round(clear, 3))
