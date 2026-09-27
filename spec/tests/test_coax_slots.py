"""Coax jacks are connector slots (#650, docs/connectors-coax-design.md).

A presented interface becomes a SLOT only when spec/schemas/connectors.yaml
lists it. These run against the real library and a components.json / device
build made here, never a possibly stale dist.

KNOWN mixes two kinds of real placement. `std/sma@1` and `std/smb@1` are each
placed directly on a device face (ufispace/s9500-30xs `pps-in`, juniper/mx304
`clk-1pps-in`), so those two go through render.py like the RJ45 device tests.
`std/f-type@1` and `std/mcx@1` are NOT placed directly on any device today -
every use found by
`grep -rn "ref: std/f-type@1\\|ref: std/mcx@1" library/devices/*/*/device.yaml`
is empty, and the real placements are inside bay-seated line cards
(casa/rfd@1, casa/ups-32x4@1), whose ports never reach a device's top-level
`cages` (a seated card's own ports are not expanded into its host's cages,
same as a bay's `bays` dict names only the seated ref). Those two go through
the indexer's components.json instead, same as the RJ45 census's `_card_slot`.
"""
import json
import sys
from pathlib import Path

import pytest
import yaml

import warmrender
from portrayal import render as render_mod

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
RENDER = ROOT / "spec/tools/portrayal/render.py"
INDEXER = ROOT / "spec/tools/portrayal/components_index.py"

EXISTING = {"f-type": "std/f-type", "sma": "std/sma", "smb": "std/smb", "mcx": "std/mcx"}


def test_each_existing_coax_interface_is_a_connector_with_a_standard():
    reg = render_mod._connector_registry()
    std = yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())["standards"]
    for iface in EXISTING:
        assert iface in reg, iface
        assert reg[iface]["standard"] in std, (iface, reg[iface])


def test_each_existing_jack_presents_its_interface():
    for iface, part in EXISTING.items():
        doc = yaml.safe_load((LIB / f"components/{part}/v1/contract.yaml").read_text())
        assert doc["interface"] == iface
        assert "mate" in doc["connection-points"]


@pytest.fixture(scope="module")
def comps(tmp_path_factory):
    out = tmp_path_factory.mktemp("components")
    r = warmrender.run([sys.executable, str(INDEXER), "--library", str(LIB),
                        "--out", str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads((out / "components.json").read_text())
    got = {f"{e['ns']}/{e['name']}@{e['major'][1:]}": e for e in doc["components"]}
    assert got, "the indexer published no component at all"
    return got


def _device_configs(device, tmp_path):
    src = LIB / f"devices/{device}/device.yaml"
    r = warmrender.run([sys.executable, str(RENDER), str(src), "--library", str(LIB),
                        "--out", str(tmp_path)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    name = src.parent.name
    return json.loads((tmp_path / f"{name}.configs.json").read_text())


def _device_slot(device, view, cage_id, tmp_path):
    cfg = _device_configs(device, tmp_path)
    return next(c for c in cfg["cages"][view] if c["id"] == cage_id)


def _card_slot(comps, ref, cage_id):
    return next(c for c in comps[ref]["cages"] if c["id"] == cage_id)


# One real placement per existing family. sma/smb are direct device
# placements (view, placement id); f-type/mcx are card ports (component ref,
# port id) - see the module docstring for why.
KNOWN_DEVICE = {
    "sma": ("ufispace/s9500-30xs", "front", "pps-in"),
    "smb": ("juniper/mx304", "rear", "clk-1pps-in"),
}
KNOWN_CARD = {
    "f-type": ("casa/rfd@1", "p0"),
    "mcx": ("casa/ups-32x4@1", "p0"),
    # a Cisco T3/E3 SPA port, a common/din-1-0-2-3-jack@1 placement (Task 6,
    # "THE STAND-IN MOVES" below)
    "din-1-0-2-3": ("cisco/spa-4xt3e3@1", "p0-tx"),
}


@pytest.mark.parametrize("iface", sorted(EXISTING))
def test_a_known_coax_port_publishes_a_connector_slot(iface, comps, tmp_path):
    if iface in KNOWN_DEVICE:
        device, view, pid = KNOWN_DEVICE[iface]
        slot = _device_slot(device, view, pid, tmp_path)
    else:
        ref, cage_id = KNOWN_CARD[iface]
        slot = _card_slot(comps, ref, cage_id)
    assert slot["kind"] == "connector"
    assert slot["interface"] == iface


# THE PLUGS (#650 Task 4). Each known port offers its generic plug; the port
# is reached the same way the slot test above reaches it - a device placement
# for sma/smb, the indexer's card entry for mcx.
PLUG_FOR = {"sma": "generic/sma-plug@1", "smb": "generic/smb-plug@1",
            "mcx": "generic/mcx-plug@1", "f-type": "generic/f-type-plug@1",
            "din-1-0-2-3": "generic/din-1-0-2-3-plug@1"}


@pytest.mark.parametrize("iface,plug", sorted(PLUG_FOR.items()))
def test_a_known_port_offers_its_plug(iface, plug, comps, tmp_path):
    if iface in KNOWN_DEVICE:
        device, view, pid = KNOWN_DEVICE[iface]
        slot = _device_slot(device, view, pid, tmp_path)
    else:
        ref, cage_id = KNOWN_CARD[iface]
        slot = _card_slot(comps, ref, cage_id)
    assert plug in slot["accepts"], slot


# THE BNC PLUG (#650 Task 5; a real device since #673). The bezel's own
# components.json entry carries neither `cages` (it is not a card) nor
# `presents` (it mates nothing), so the accept list is read where the build
# publishes it. Two real placements of common/bnc-jack@1 carry it: the
# ReadyLinks GL-12xB-240D's SYNC IN jack, a device placement read from the
# device's configs.json, and RL1 on the GL-x 12-port BNC line card that device
# seats, read from the indexer's card entry. The 1.0/2.3 plug is read off a
# real SPA port instead (KNOWN_CARD, PLUG_FOR).
BNC_DEVICE = {
    "bnc": ("readylinks/gl-12xb-240d", "front", "sync-in", "common/bnc-jack@1",
            "generic/bnc-plug@1"),
}
BNC_CARD = {"bnc": ("readylinks/gl-x-lc-12xb@1", "rl1", "generic/bnc-plug@1")}


@pytest.mark.parametrize("iface", sorted(BNC_DEVICE))
def test_a_bezel_placement_offers_its_plug(iface, tmp_path):
    device, view, pid, bezel, plug = BNC_DEVICE[iface]
    d = yaml.safe_load((LIB / "devices" / device / "device.yaml").read_text())
    hits = [p for p in d["views"][view]["components"]["placements"] if p.get("id") == pid]
    assert len(hits) == 1 and hits[0]["ref"] == bezel, hits
    slot = _device_slot(device, view, pid, tmp_path)
    assert slot["kind"] == "connector" and slot["interface"] == iface, slot
    assert plug in slot["accepts"], slot


@pytest.mark.parametrize("iface", sorted(BNC_CARD))
def test_a_card_bezel_port_offers_its_plug(iface, comps):
    ref, cage_id, plug = BNC_CARD[iface]
    part = next(p for p in _contract(ref)["parts"] if p["id"] == cage_id)
    assert part["ref"] == "common/bnc-jack@1", part
    slot = _card_slot(comps, ref, cage_id)
    assert slot["kind"] == "connector" and slot["interface"] == iface, slot
    assert plug in slot["accepts"], slot


# The two new jacks (#650, Task 3). The 1.0/2.3 interface is spelled
# `din-1-0-2-3`: component.schema.json's segment pattern refuses a dot in an
# interface, the same as in a component name (L2).
NEW = {"bnc": "std/bnc", "din-1-0-2-3": "std/din-1-0-2-3"}


@pytest.mark.parametrize("iface", sorted(NEW))
def test_each_new_jack_exists_presents_and_conforms(iface):
    part = NEW[iface]
    doc = yaml.safe_load((LIB / f"components/{part}/v1/contract.yaml").read_text())
    std = yaml.safe_load((ROOT / "spec/schemas/standards.yaml").read_text())["standards"]
    assert doc["interface"] == iface
    assert doc["class"] == "port" and "behaviour" not in doc
    assert doc["conforms"] in std
    assert "mate" in doc["connection-points"]
    reg = render_mod._connector_registry()
    assert reg[iface]["standard"] == doc["conforms"]


# The bezels (#650 review): the flange and lugs of a front-mount BNC and the
# spanner nut of a rear-mount 1.0/2.3 are wider than the panel hole, so they
# are a common/ bezel around the std/ core, as common/sma-jack is around
# std/sma. The bezel's size box is what L13 and the hit box read, so it must
# hold everything drawn in front of the panel.
BEZELS = {"common/bnc-jack@1": ("bnc", "std/bnc@1"),
          "common/din-1-0-2-3-jack@1": ("din-1-0-2-3", "std/din-1-0-2-3@1")}


def _contract(ref):
    ns, rest = ref.split("/")
    name, major = rest.split("@")
    return yaml.safe_load((LIB / f"components/{ns}/{name}/v{major}/contract.yaml").read_text())


def _skin_path(ref):
    ns, rest = ref.split("/")
    name, major = rest.split("@")
    return LIB / f"components/{ns}/{name}/v{major}/skins/default.svg"


def _arc_extent(x0, y0, rx, ry, phi, large, sweep, x1, y1):
    """The exact box of one SVG elliptical arc (SVG 1.1 appendix F.6.5): the
    two endpoints plus every axis extreme of the ellipse that the sweep passes.
    Only unrotated arcs are handled - a rotated one raises, so a skin that grows
    one fails here rather than being measured wrong."""
    import math
    if phi % 360:
        raise AssertionError("rotated arc - extend _arc_extent")
    rx, ry = abs(rx), abs(ry)
    xs, ys = [x0, x1], [y0, y1]
    if rx == 0 or ry == 0:
        return xs, ys
    dx, dy = (x0 - x1) / 2, (y0 - y1) / 2
    lam = (dx / rx) ** 2 + (dy / ry) ** 2
    if lam > 1:
        rx, ry = rx * math.sqrt(lam), ry * math.sqrt(lam)
    num = rx * rx * ry * ry - rx * rx * dy * dy - ry * ry * dx * dx
    den = rx * rx * dy * dy + ry * ry * dx * dx
    k = math.sqrt(max(num, 0) / den) if den else 0.0
    if large == sweep:
        k = -k
    cxp, cyp = k * rx * dy / ry, -k * ry * dx / rx
    cx, cy = cxp + (x0 + x1) / 2, cyp + (y0 + y1) / 2
    def ang(ux, uy, vx, vy):
        a = math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)
        return a
    t1 = ang(1, 0, (dx - cxp) / rx, (dy - cyp) / ry)
    dt = ang((dx - cxp) / rx, (dy - cyp) / ry, (-dx - cxp) / rx, (-dy - cyp) / ry)
    if not sweep and dt > 0:
        dt -= 2 * math.pi
    elif sweep and dt < 0:
        dt += 2 * math.pi
    for q in range(-8, 9):
        a = q * math.pi / 2
        rel = (a - t1) if dt >= 0 else (t1 - a)
        if 0 <= rel <= abs(dt):
            xs.append(cx + rx * math.cos(a))
            ys.append(cy + ry * math.sin(a))
    return xs, ys


def _path_points(d):
    """Absolute M/L/H/V/A/Z path data to the x and y extents it can reach.
    Anything else raises: a new command is extended here, never skipped."""
    import re
    toks = re.findall(r"[A-Za-z]|-?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?", d)
    xs, ys = [], []
    i, cmd, x, y = 0, None, 0.0, 0.0
    while i < len(toks):
        if toks[i].isalpha():
            cmd = toks[i]
            i += 1
            if cmd in "Zz":
                continue
        if cmd == "M" or cmd == "L":
            x, y = float(toks[i]), float(toks[i + 1]); i += 2
        elif cmd == "H":
            x = float(toks[i]); i += 1
        elif cmd == "V":
            y = float(toks[i]); i += 1
        elif cmd == "A":
            rx, ry, phi, large, sweep, nx, ny = (float(t) for t in toks[i:i + 7]); i += 7
            ax, ay = _arc_extent(x, y, rx, ry, phi, int(large), int(sweep), nx, ny)
            xs += ax; ys += ay
            x, y = nx, ny
        else:
            raise AssertionError(f"path command {cmd!r} - extend _path_points")
        xs.append(x); ys.append(y)
    return xs, ys


def _drawn_box(ref):
    """The box a skin draws, in its own mm frame, read from its geometry:
    every circle, ellipse, rect, line, polygon and path, each widened by half
    its stroke. Exact for the shapes these skins use, with no rasteriser (the
    CI runners install none). A transform, or a shape this does not read,
    raises - so the check cannot pass by ignoring part of the drawing."""
    import xml.etree.ElementTree as ET
    root = ET.parse(_skin_path(ref)).getroot()
    x0 = y0 = float("inf")
    x1 = y1 = float("-inf")
    for el in root.iter():
        tag = el.tag.rsplit("}", 1)[-1]
        if el.get("transform"):
            raise AssertionError(f"{ref}: a transform on <{tag}> - extend _drawn_box")
        a = {k: el.get(k) for k in el.keys()}
        sw = float(a.get("stroke-width") or 0) if a.get("stroke") not in (None, "none") else 0.0
        h = sw / 2
        if tag == "circle":
            cx, cy, r = float(a["cx"]), float(a["cy"]), float(a["r"])
            xs, ys = [cx - r, cx + r], [cy - r, cy + r]
        elif tag == "ellipse":
            cx, cy, rx, ry = (float(a[k]) for k in ("cx", "cy", "rx", "ry"))
            xs, ys = [cx - rx, cx + rx], [cy - ry, cy + ry]
        elif tag == "rect":
            x, y, w, hh = (float(a.get(k) or 0) for k in ("x", "y", "width", "height"))
            xs, ys = [x, x + w], [y, y + hh]
        elif tag == "line":
            xs = [float(a.get("x1") or 0), float(a.get("x2") or 0)]
            ys = [float(a.get("y1") or 0), float(a.get("y2") or 0)]
        elif tag in ("polygon", "polyline"):
            nums = [float(v) for v in a["points"].replace(",", " ").split()]
            xs, ys = nums[0::2], nums[1::2]
        elif tag == "path":
            xs, ys = _path_points(a["d"])
        elif tag in ("svg", "g", "title", "desc", "defs", "metadata"):
            continue
        else:
            raise AssertionError(f"{ref}: <{tag}> - extend _drawn_box")
        x0, y0 = min(x0, min(xs) - h), min(y0, min(ys) - h)
        x1, y1 = max(x1, max(xs) + h), max(y1, max(ys) + h)
    assert x0 < x1, f"{ref} draws nothing"
    return x0, y0, x1, y1


def test_the_drawn_box_reads_a_known_skin_exactly():
    """The reader is exact on shapes whose extent is known without it: the BNC
    bezel's flange is a full 6.35 circle, drawn as two arcs, filling its 12.7
    box; the core's D-hole is an arc cut by a flat at 8.85, so its box ends
    there and not at the full circle's 9.7."""
    x0, y0, x1, y1 = _drawn_box("common/bnc-jack@1")
    assert (x0, y0, x1, y1) == pytest.approx((0, 0, 12.7, 12.7), abs=1e-9)
    # the D-hole's endpoints are written to 3 decimals, so the arc's centre
    # sits a fraction of a micron off (4.85, 4.85): hold it to the skin's own
    # precision, not float noise
    ox0, oy0, ox1, oy1 = _path_points_box("std/bnc@1", "opening")
    assert (ox0, oy0, ox1, oy1) == pytest.approx((0, 0, 9.7, 8.85), abs=1e-3)


def _path_points_box(ref, node_id):
    import xml.etree.ElementTree as ET
    root = ET.parse(_skin_path(ref)).getroot()
    el = next(e for e in root.iter() if e.get("id") == node_id)
    xs, ys = _path_points(el.get("d"))
    return min(xs), min(ys), max(xs), max(ys)


@pytest.mark.parametrize("ref", sorted(BEZELS))
def test_each_bezel_presents_its_interface_through_its_core(ref):
    from portrayal import manifest
    iface, core = BEZELS[ref]
    doc = _contract(ref)
    assert "interface" not in doc, "a bezel presents through its core, as common/sma-jack"
    assert [p["ref"] for p in doc["parts"]] == [core]
    got, mate_at, _lift = manifest.presented_interface(doc, _contract)
    assert got == iface
    # the core's collar centre is the bezel's centre
    assert mate_at == [doc["size"]["w"] / 2, doc["size"]["h"] / 2]
    assert render_mod._connector_registry()[got]["standard"] == _contract(core)["conforms"]


@pytest.mark.parametrize("ref", sorted(BEZELS))
def test_each_bezel_box_holds_everything_it_draws(ref):
    """Its own skin AND its composed core, placed where the contract puts it,
    read from the skins' geometry (strokes included) - exact, so the only
    tolerance is float noise."""
    tol = 1e-9
    doc = _contract(ref)
    w, h = doc["size"]["w"], doc["size"]["h"]
    boxes = [_drawn_box(ref)]
    for part in doc["parts"]:
        ax, ay = part["at"]
        x0, y0, x1, y1 = _drawn_box(part["ref"])
        boxes.append((x0 + ax, y0 + ay, x1 + ax, y1 + ay))
    for x0, y0, x1, y1 in boxes:
        assert x0 >= -tol and y0 >= -tol and x1 <= w + tol and y1 <= h + tol, (ref, boxes)


def _stack(ref):
    """Every relief feature of a bezel and its core as (node, start, end) in
    absolute mm from the panel: `out` is absolute, a `cyl` runs `lift` to
    `lift + cyl`. The core is composed with no lift of its own."""
    doc = _contract(ref)
    feats = list(doc["relief"]["features"])
    for part in doc["parts"]:
        assert not part.get("lift")
        feats += _contract(part["ref"])["relief"]["features"]
    out = []
    for f in feats:
        lift = f.get("lift", 0.0)
        end = f["out"] if "out" in f else lift + f["cyl"]
        out.append((f["node"], round(lift, 3), round(end, 3)))
    return out


# PINNED, so an edit that opens a gap, reorders the stack or moves the lugs
# fails here. Figures: see each contract's provenance.
STACKS = {
    "common/bnc-jack@1": [("flange", 0.0, 1.4), ("collar", 1.4, 12.2)],
    "common/din-1-0-2-3-jack@1": [("nut", 0.0, 2.41), ("collar", 2.41, 3.25),
                                  ("barrel", 3.25, 7.2), ("groove", 7.2, 8.0),
                                  ("ring", 8.0, 9.4)],
}


@pytest.mark.parametrize("ref", sorted(STACKS))
def test_each_jack_relief_stack_is_continuous_and_pinned(ref):
    cyls = sorted((s for s in _stack(ref) if not s[0].startswith("lug")), key=lambda s: s[1])
    assert cyls == STACKS[ref]
    for (_a, _s, end), (_b, start, _e) in zip(cyls, cyls[1:]):
        assert start == end, ("gap or overlap in the stack", cyls)
    assert all(end > start for _n, start, end in _stack(ref)), "a solid built inside out"


def test_the_bnc_lugs_sit_where_mil_std_348_puts_them():
    """Stud H 1.985 centred 4.24 behind the 12.2 front (F 5.23 less H/2):
    7.96 in front of the panel, on the collar, both lugs alike."""
    lugs = [s for s in _stack("common/bnc-jack@1") if s[0].startswith("lug")]
    assert [n for n, *_ in lugs] == ["lug-l", "lug-r"]
    for _n, start, end in lugs:
        assert (start, end) == (6.97, 8.96)
        assert abs((start + end) / 2 - (12.2 - 4.2375)) < 0.01
        assert abs((end - start) - 1.985) < 0.01


# THE STAND-IN MOVES (#650 Task 6, docs/connectors-coax-design.md section 6).
# The Cisco clear channel T3/E3 SPAs drew their 1.0/2.3 jacks as skin art; they
# now place common/din-1-0-2-3-jack@1 (the bezel, never the bare core) at the
# centres the skin drew. The Juniper DS3/E3 MIC does not move: its faceplate
# jack is 75-ohm mini-SMB, which no modelled interface fits.
SPA_JACKS = {
    "cisco/spa-4xt3e3@1": {
        "p0-tx": 10.29, "p0-rx": 22.77, "p1-tx": 53.26, "p1-rx": 65.38,
        "p2-tx": 96.24, "p2-rx": 108.0, "p3-tx": 138.85, "p3-rx": 151.34,
    },
    "cisco/spa-2xt3e3@1": {
        "p0-tx": 10.29, "p0-rx": 22.77, "p1-tx": 53.26, "p1-rx": 65.38,
    },
    # Fix round 1: the two channelized T3 cards the guide also gives 1.0/2.3
    # (Siemax / DIN 1.0/2.3) jacks.
    "cisco/spa-4xct3-ds0@1": {
        "p0-tx": 10.29, "p0-rx": 22.77, "p1-tx": 53.26, "p1-rx": 65.38,
        "p2-tx": 96.24, "p2-rx": 108.0, "p3-tx": 138.85, "p3-rx": 151.34,
    },
    "cisco/spa-2cht3-ce-atm@1": {
        "p0-tx": 15.43, "p0-rx": 27.92, "p1-tx": 49.59, "p1-rx": 61.34,
    },
}
SPA_JACK_X = {"cisco/spa-2cht3-ce-atm@1": 8.64}  # every other card: 9.88


def test_the_known_din_card_port_publishes_a_connector_slot(comps):
    ref, cage_id = KNOWN_CARD["din-1-0-2-3"]
    slot = _card_slot(comps, ref, cage_id)
    assert (slot["kind"], slot["interface"]) == ("connector", "din-1-0-2-3"), slot


@pytest.mark.parametrize("ref", sorted(SPA_JACKS))
def test_each_t3e3_spa_jack_is_a_placed_din_bezel_at_the_drawn_centre(ref, comps):
    doc = _contract(ref)
    parts = {p["id"]: p for p in doc.get("parts") or []}
    for pid, cy in SPA_JACKS[ref].items():
        p = parts[pid]
        assert p["ref"] == "common/din-1-0-2-3-jack@1", p
        assert p["attrs"] == {"impedance": 75, "media": "coax-din-1-0-2-3"}, p
        # the bezel box is the 7.01 nut, so its centre is at + 3.505
        cx = SPA_JACK_X.get(ref, 9.88)
        assert abs(p["at"][0] + 3.505 - cx) < 1e-6 and abs(p["at"][1] + 3.505 - cy) < 1e-6, p
        slot = _card_slot(comps, ref, pid)
        assert (slot["kind"], slot["interface"]) == ("connector", "din-1-0-2-3"), slot


@pytest.mark.parametrize("ref", sorted(SPA_JACKS))
def test_each_t3e3_spa_jack_accepts_the_din_plug(ref, comps):
    for pid in SPA_JACKS[ref]:
        assert "generic/din-1-0-2-3-plug@1" in _card_slot(comps, ref, pid)["accepts"]


def test_the_t3e3_skins_no_longer_draw_the_jacks():
    for ref, jacks in SPA_JACKS.items():
        svg = _skin_path(ref).read_text()
        for pid in jacks:
            assert f'id="{pid}"' not in svg, (ref, pid)
        assert 'id="silkscreen"' in svg and 'id="status"' in svg, ref


CORE_BEZEL = {"std/bnc@1": "common/bnc-jack@1",
              "std/din-1-0-2-3@1": "common/din-1-0-2-3-jack@1"}


def _refs(node, out):
    if isinstance(node, dict):
        if isinstance(node.get("ref"), str):
            out.append(node["ref"])
        for v in node.values():
            _refs(v, out)
    elif isinstance(node, list):
        for v in node:
            _refs(v, out)
    return out


def test_no_device_or_card_places_a_bare_bnc_or_din_core():
    """The BNC and 1.0/2.3 cores paint past their own box (the BNC collar over
    its D-flat, and neither draws the flange or nut a panel shows), so every
    placement goes through the common/*-jack bezel. Walks every device.yaml and
    every contract in the real library, not a list."""
    seen, bad, bezel_places, din_placers = 0, [], set(), set()
    for f in sorted((LIB / "devices").glob("*/*/device.yaml")):
        seen += 1
        bad += [(str(f.relative_to(LIB)), r) for r in _refs(yaml.safe_load(f.read_text()), [])
                if r in CORE_BEZEL]
    for f in sorted((LIB / "components").glob("*/*/v*/contract.yaml")):
        seen += 1
        doc = yaml.safe_load(f.read_text())
        me = f"{f.parts[-4]}/{f.parts[-3]}@{f.parts[-2][1:]}"
        for r in _refs(doc.get("parts") or [], []) + _refs(doc.get("bays") or {}, []):
            if r == "common/din-1-0-2-3-jack@1":
                din_placers.add(me)
            if r in CORE_BEZEL:
                if CORE_BEZEL[r] == me:
                    bezel_places.add(me)
                else:
                    bad.append((str(f.relative_to(LIB)), r))
    assert seen > 1000, f"walked only {seen} files"
    assert bezel_places == set(CORE_BEZEL.values()), bezel_places  # the walk sees the cores
    # and it reaches every moved card, each through the bezel
    assert set(SPA_JACKS) <= din_placers, set(SPA_JACKS) - din_placers
    assert not bad, bad
