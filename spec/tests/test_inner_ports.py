"""The inner part of a composed port is marked `data-inner="1"` (#511).

A composed port - common/rj45-eth@1 around a std/rj45, common/qsfp28-cage@3
around a std/qsfp-ganged, common/sfp-plus-cage@2, common/rj45-ganged-eth@1 - draws its
std core as a `data-class="port"` element of its own, NESTED inside the outer
port. The facts (media, speed, group) sit on the outer port; the core carries
the generic housing's media and nothing else. So an audit selector such as
`[data-class=port]:not([data-speed])` matched every core and reported ports
missing a speed that were not ports at all - 199 of them on five devices.

The core keeps its class, so no selector that finds it today stops finding it;
it also says `data-inner="1"`. The rule is structural and is checked as one:

  - every data-class=port element with a data-class=port ANCESTOR is marked;
  - no data-class=port element without one is.
"""
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"
DIST = LIB / "dist"
RENDER = SPEC / "tools/portrayal/render.py"

# Picked for what they compose: rj45-eth and qsfp28/sfp-plus cages at device
# level (mx204, s9510-28dc), card ports in bays and a bay of a bay (mx10008,
# mx960), a ganged RJ45 pair on a route processor (asr-9903).
DEVICES = ["juniper/mx204", "ufispace/s9510-28dc", "juniper/mx10008",
           "juniper/mx960", "cisco/asr-9903"]


def _split(svg_root):
    """(inner, top) port elements of one drawing, by ancestry."""
    inner, top = [], []

    def walk(el, under_port):
        is_port = el.get("data-class") == "port"
        if is_port:
            (inner if under_port else top).append(el)
        for ch in el:
            walk(ch, under_port or is_port)
    walk(svg_root, False)
    return inner, top


def _check(svg_root, where):
    inner, top = _split(svg_root)
    for el in inner:
        assert el.get("data-inner") == "1", (where, el.get("data-path"))
    for el in top:
        assert el.get("data-inner") is None, (where, el.get("data-path"))
    return len(inner), len(top)


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    out = tmp_path_factory.mktemp("inner")
    svgs = []
    for dev in DEVICES:
        manifest = LIB / "devices" / dev / "device.yaml"
        r = subprocess.run([sys.executable, str(RENDER), str(manifest), "--library",
                            str(LIB), "--out", str(out / dev)],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        name = yaml.safe_load(manifest.read_text())["name"]
        svgs += sorted((out / dev).glob(f"{name}.*.svg"))
    return svgs


def test_inner_ports_are_marked_and_top_level_ports_are_not(built):
    n_inner = n_top = 0
    for svg in built:
        i, t = _check(ET.parse(svg).getroot(), svg.name)
        n_inner += i
        n_top += t
    # NOT VACUOUS: these five devices compose rj45-eth, qsfp28 and sfp-plus
    # cages and the RE/RP cards' ganged jacks, so both sides must be present.
    assert n_inner > 50, n_inner
    assert n_top > n_inner, (n_top, n_inner)


def test_the_marker_names_the_inner_part_only(built):
    """An inner port's id ends in the core's part id (`--jack`, `--aperture`,
    `--cage`, ...) and its parent port is the element that carries the
    facts: a marked element never carries a group its outer port lacks."""
    checked = 0
    for svg in built:
        root = ET.parse(svg).getroot()
        parent = {c: p for p in root.iter() for c in p}
        for el in root.iter():
            if el.get("data-inner") != "1":
                continue
            outer = parent[el]
            while outer.get("data-class") != "port":
                outer = parent[outer]
            if el.get("data-group"):
                assert outer.get("data-group") == el.get("data-group"), el.get("data-path")
            checked += 1
    assert checked > 0


def test_every_built_drawing_in_dist_follows_the_rule():
    """The whole library, when dist is built: the same two-sided rule over
    every compiled SVG. Skipped only when there is no dist at all, and then
    the built subset above still holds the rule."""
    svgs = sorted(DIST.glob("*.svg"))
    if not svgs:
        pytest.skip("library/dist not built - run ./publish.sh")
    total = 0
    for svg in svgs:
        i, _t = _check(ET.parse(svg).getroot(), svg.name)
        total += i
    assert total > 0
