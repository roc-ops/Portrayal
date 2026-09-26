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


def _painted_box(ref, pad=10.0, pxmm=20):
    """The box a skin really paints, in its own mm frame: rasterised on a canvas
    `pad` mm wider than the viewBox on every side, so art past the viewBox is
    measured rather than clipped. A reading, not a parse - arcs, strokes and
    evenodd holes all count as they render."""
    import io
    import re
    cairosvg = pytest.importorskip("cairosvg")
    from PIL import Image
    doc = _contract(ref)
    w, h = doc["size"]["w"], doc["size"]["h"]
    src = _skin_path(ref).read_text()
    W, H = w + 2 * pad, h + 2 * pad
    src = re.sub(r'viewBox="[^"]*"', f'viewBox="{-pad} {-pad} {W} {H}"', src, count=1)
    src = re.sub(r'width="[^"]*mm"', f'width="{W}mm"', src, count=1)
    src = re.sub(r'height="[^"]*mm"', f'height="{H}mm"', src, count=1)
    png = cairosvg.svg2png(bytestring=src.encode(), output_width=int(W * pxmm),
                           output_height=int(H * pxmm))
    bb = Image.open(io.BytesIO(png)).getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
    assert bb, f"{ref} paints nothing"
    x0, y0, x1, y1 = (v / pxmm - pad for v in bb)
    return x0, y0, x1, y1


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
    """Its own skin AND its composed core, placed where the contract puts it.
    0.06 mm is one raster pixel of anti-aliasing at 20 px/mm."""
    tol = 0.06
    doc = _contract(ref)
    w, h = doc["size"]["w"], doc["size"]["h"]
    boxes = [_painted_box(ref)]
    for part in doc["parts"]:
        ax, ay = part["at"]
        x0, y0, x1, y1 = _painted_box(part["ref"])
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
