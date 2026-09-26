"""generic/sfp-cable: the SFP+ direct-attach cable end - a head, a pull strap,
a strain relief and a stub of cable whose diameter is the `cable-od` field
(docs/pluggables-cables-design.md sections 2-4)."""
import json
import pathlib
import shutil
import xml.etree.ElementTree as ET

import jsonschema
import pytest
import yaml

from portrayal import lint
from portrayal import render as render_mod
from test_nested_occupants import (LIB, assert_same_turn, by_path, cage_mate,
                                   device_point, effective_lift, own_mate, run)

ROOT = pathlib.Path(__file__).resolve().parents[2]
REF = "generic/sfp-cable@1"
P = LIB / "components/generic/sfp-cable/v1/contract.yaml"
SKIN = P.parent / "skins/default.svg"
D = yaml.safe_load(P.read_text())
lint.STANDARDS.update(lint.load_yaml(ROOT / "spec/schemas/standards.yaml")["standards"])

HEAD_D, BOOT, STUB = 10.8, 27.9, 30.0


def errors(fn):
    with lint.collecting() as got:
        fn(P, D)
    return got.errors


def features():
    return {f["node"]: f for f in D["relief"]["features"]}


def test_it_validates_and_conforms_to_the_sfp_envelope():
    schema = json.loads((ROOT / "spec/schemas/component.schema.json").read_text())
    jsonschema.validate(D, schema)
    assert D["class"] == "transceiver" and D["behaviour"] == "occupies"
    assert D["conforms"] == "sfp-module" and D["mates"] == "sfp"
    assert D["size"] == {"w": 13.55, "h": 8.55, "d": 47.50}
    assert D["unplaced"].strip()


def test_the_head_is_molexs_and_says_what_it_exceeds():
    h = D["head"]
    assert {k: h[k] for k in ("at", "size", "node")} == {
        "at": [0.0, -1.40], "size": {"w": 13.55, "h": 11.50, "d": 10.8}, "node": "head"}
    assert h["size-confidence"] == {"w": "drawing", "h": "drawing", "d": "drawing"}
    # 1.55 below the 8.55 body (past SFF-8432's 1.40) and 10.8 long (past its
    # recommended 10.00); 1.40 above and 13.55 wide are inside the envelope
    assert {e["dimension"] for e in h["exceeds"]} == {"below", "length"}
    assert all(e["source"].strip() for e in h["exceeds"])
    assert not [e for e in errors(lint.lint_component_head) if "[L121]" in e]


def test_it_is_a_generic():
    assert not [e for e in errors(lint.lint_component_generic) if "[L99]" in e]
    for k in ("speed", "reach", "power-draw-max-w", "cable-kind"):
        assert k not in (D.get("attrs") or {})


def test_cable_od_is_lint_clean():
    assert not [e for e in errors(lint.lint_component_cable_od) if "[L122]" in e]


def test_the_fields_and_their_defaults():
    f = D["fields"]
    assert f["cable-od"]["type"] == "number" and f["cable-od"]["default"] == 4.8
    assert f["jacket-color"]["default"] == "#1c1c1c"
    assert f["latch-color"]["default"] == "#6f6f6f"


def _skin():
    root = ET.parse(SKIN).getroot()
    return {e.get("id"): e for e in root.iter() if e.get("id")}


def test_the_skin_binds_the_stub_and_the_strap_to_their_fields():
    n = _skin()
    stub = n["stub"]
    assert stub.tag.endswith("circle")
    assert stub.get("data-r-from") == "cable-od"
    assert stub.get("data-fill-from") == "jacket-color"
    assert float(stub.get("r")) == pytest.approx(D["fields"]["cable-od"]["default"] / 2)
    for s in ("strap", "strap-ring"):
        assert n[s].get("data-fill-from") == "latch-color", s
        assert n[s].get("data-stroke-derive") == "latch-color", s
    assert n["relief-boot"].tag.endswith("circle")
    assert n["head"].tag.endswith("rect")


def test_the_strap_lies_on_top_of_the_boot_and_the_cable():
    n = _skin()
    boot, strap = n["relief-boot"], n["strap"]
    boot_top = float(boot.get("cy")) - float(boot.get("r"))
    strap_bottom = float(strap.get("y")) + float(strap.get("height"))
    assert strap_bottom == pytest.approx(boot_top, abs=1e-6)
    # the boot and the stub are on the body axis (the rulings)
    for c in (boot, n["stub"]):
        assert (float(c.get("cx")), float(c.get("cy"))) == pytest.approx((6.775, 4.275))


def test_the_relief_chains_head_boot_stub_and_the_strap_starts_at_the_head_back():
    f = features()
    assert f["head"]["out"] == HEAD_D and "lift" not in f["head"]
    assert f["relief-boot"]["cyl"] == BOOT and f["relief-boot"]["lift"] == HEAD_D
    assert f["stub"]["cyl"] == STUB and f["stub"]["lift"] == pytest.approx(HEAD_D + BOOT)
    assert f["strap"]["lift"] == HEAD_D and f["strap"]["out"] == 53.9
    assert f["strap-ring"]["lift"] == 39.0 and f["strap-ring"]["out"] == 53.9
    for node, feat in f.items():
        assert feat["confidence"] and feat["source"].strip(), node


def test_the_cable_point_sits_on_the_stub():
    cps = D["connection-points"]
    assert cps["mate"] == {"at": [6.775, 4.275], "direction": "front"}
    assert cps["cable"] == {"at": [6.775, 4.275], "direction": "front", "on": "stub"}


def _group(attrs):
    lib = render_mod.Library([str(LIB)])
    g, _ = render_mod.instance_group(lib, REF, "t", [0, 0], None, attrs, None, None,
                                     skin_name="default", palette={}, resolved={})
    return g


def _compiled(attrs):
    return {n.get("id"): n for n in _group(attrs).iter() if n.get("id")}


def test_a_cable_od_sizes_the_stub():
    assert float(_compiled({"cable-od": 3.0})["t--stub"].get("r")) == 1.5


def test_no_cable_od_leaves_the_default_stub():
    assert float(_compiled(None)["t--stub"].get("r")) == 2.4


def test_the_head_is_the_base_plate_and_buries_nothing():
    """2D: document order is paint order, and the head is drawn first so the
    boot, strap and stub paint over it. 3D: the head's solid ends at 10.8, where
    every other feature begins - none of them starts inside it."""
    g = _group(None)
    n = {k.get("id"): k for k in g.iter() if k.get("id")}
    kids = [k.get("id") for k in g if k.get("id")]
    order = [kids.index(f"t--{s}") for s in ("head", "relief-boot", "strap", "strap-ring", "stub")]
    assert order == sorted(order), kids
    head_out = float(n["t--head"].get("data-z-out"))
    assert head_out == HEAD_D
    for s in ("relief-boot", "strap", "strap-ring", "stub"):
        assert float(n[f"t--{s}"].get("data-z-lift")) >= head_out - 1e-9, s


# --- seated in an SFP cage on a real device ----------------------------------

AGR560 = LIB / "devices/edgecore/agr560"


@pytest.fixture(scope="module")
def seated(tmp_path_factory):
    """agr560's port-0 (upright) and port-1 (rotate 180), each seating the
    cable end, built from a copy."""
    tmp = tmp_path_factory.mktemp("sfpcable")
    dev = tmp / "agr560" / "device.yaml"
    shutil.copytree(AGR560, dev.parent)
    d = yaml.safe_load(dev.read_text())
    d["configurations"]["base"]["occupants"] = {"port-0": REF, "port-1": REF}
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    out = tmp / "o"
    r = run(dev, out)
    assert r.returncode == 0, r.stderr[-800:]
    svg = out / "agr560.front.svg"
    if not svg.exists():
        svg = out / "agr560.base.front.svg"
    root = ET.parse(svg).getroot()
    return root, {c: p for p in root.iter() for c in p}


@pytest.mark.parametrize("port", ["port-0", "port-1"])
def test_it_seats_in_an_sfp_cage_on_the_agr560(seated, port):
    root, parents = seated
    host = by_path(root, port)
    occ = by_path(root, f"{port}-occupant")
    assert occ.get("data-ref", "").startswith(REF)
    hx, hy = device_point(parents, host, cage_mate(host))
    ox, oy = device_point(parents, occ, own_mate(occ))
    assert abs(hx - ox) < 1e-6 and abs(hy - oy) < 1e-6, ((hx, hy), (ox, oy))
    assert_same_turn(parents, occ, host)


def test_seated_no_solid_is_built_inside_out_and_the_cable_leaves_the_stub(seated):
    root, parents = seated
    occ = by_path(root, "port-0-occupant")
    pre = occ.get("id")
    ids = {e.get("id"): e for e in occ.iter() if e.get("id")}
    seen = 0
    for el in occ.iter():
        if el.get("data-z-out"):
            seen += 1
            assert float(el.get("data-z-out")) - effective_lift(parents, el) >= -1e-6, el.get("id")
    assert seen == 3, seen                      # head, strap, strap-ring
    stub = ids[f"{pre}--stub"]
    end = effective_lift(parents, stub) + float(stub.get("data-z-cyl"))
    assert end == pytest.approx(HEAD_D + BOOT + STUB)
    mk = next(e for e in occ if e.get("data-cp") == "cable")
    assert mk.get("data-cp-on") == f"{pre}--stub"
    assert mk.get("data-cp-dir") == "front"


def test_the_cable_leaves_the_stubs_far_end():
    """The `cable` point is 'on' the stub, a `cyl`: its rear is lift + cyl, 68.7
    from the cage face (manifest._seat_out, which the build and L106 share)."""
    from portrayal.manifest import _seat_out
    assert _seat_out(D, D["connection-points"]["cable"]) == pytest.approx(HEAD_D + BOOT + STUB)
    assert not [e for e in errors(lint.lint_component_seat_point) if "[L106]" in e]
