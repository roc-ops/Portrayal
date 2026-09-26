"""generic/qsfp-cable: the QSFP28/QSFP56 cable end - a head, a pull strap
ending in a ring, a strain relief and a stub whose diameter is the `cable-od`
field (docs/pluggables-cables-design.md sections 2-4)."""
import json
import pathlib
import shutil
import xml.etree.ElementTree as ET

import jsonschema
import pytest
import yaml

from portrayal import lint
from portrayal import render as render_mod
from test_nested_occupants import (_lib, assert_same_turn, cage_mate, device_point,
                                   effective_lift, own_mate, run)

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
P = LIB / "components/generic/qsfp-cable/v1/contract.yaml"
D = yaml.safe_load(P.read_text())
lint.STANDARDS.update(lint.load_yaml(ROOT / "spec/schemas/standards.yaml")["standards"])
REF = "generic/qsfp-cable@1"


def errors(fn):
    with lint.collecting() as got:
        fn(P, D)
    return got.errors


def features():
    return {f["node"]: f for f in D["relief"]["features"]}


def test_it_validates_and_conforms_to_the_qsfp_envelope():
    schema = json.loads((ROOT / "spec/schemas/component.schema.json").read_text())
    jsonschema.validate(D, schema)
    assert D["conforms"] == "qsfp-module" and D["mates"] == "qsfp"
    assert D["class"] == "transceiver" and D["behaviour"] == "occupies"
    assert D["size"] == {"w": 18.35, "h": 8.5, "d": 52.4}


def test_the_head_is_the_fci_backshell_and_fits_the_envelope():
    assert D["head"] == {
        "at": [0.0, -3.2],
        "size": {"w": 18.35, "h": 13.10, "d": 19.8},
        "size-confidence": {"w": "drawing", "h": "drawing", "d": "drawing"},
        "node": "head",
    }
    assert not [e for e in errors(lint.lint_component_head) if "[L121]" in e]


def test_it_is_a_generic():
    assert not [e for e in errors(lint.lint_component_generic) if "[L99]" in e]
    attrs = D.get("attrs") or {}
    for k in ("speed", "reach", "power-draw-max-w", "cable-kind"):
        assert k not in attrs


def test_the_fields_and_their_defaults():
    f = D["fields"]
    assert f["cable-od"]["default"] == 6.9
    assert f["jacket-color"]["default"] == "#1c1c1c"
    assert f["latch-color"]["default"] == "#6f6f6f"
    assert not [e for e in errors(lint.lint_component_cable_od) if "[L122]" in e]


def _skin():
    root = ET.parse(P.parent / "skins/default.svg").getroot()
    return {e.get("id"): e for e in root.iter() if e.get("id")}


def test_the_stub_is_bound_to_the_fields():
    s = _skin()["stub"]
    assert s.get("data-r-from") == "cable-od"
    assert s.get("data-fill-from") == "jacket-color"
    assert float(s.get("r")) == pytest.approx(6.9 / 2)
    for n in ("strap", "strap-ring"):
        assert _skin()[n].get("data-fill-from") == "latch-color"
        assert _skin()[n].get("data-stroke-derive") == "latch-color"


def _stub(attrs):
    g, _ = render_mod.instance_group(_lib, REF, "q", [0, 0], None, attrs, None, None)
    return next(e for e in g.iter() if (e.get("id") or "").endswith("--stub"))


def test_cable_od_sizes_the_stub():
    assert float(_stub({"cable-od": 3.0}).get("r")) == 1.5
    assert float(_stub({}).get("r")) == 3.45


def test_the_relief_stacks_head_boot_stub_and_strap():
    f = features()
    assert f["head"]["out"] == 19.8 and "lift" not in f["head"]
    assert (f["relief-boot"]["lift"], f["relief-boot"]["cyl"]) == (19.8, 15)
    # the stub starts at the boot's end and stops 45 behind the head's back,
    # Amphenol's 45 MIN to bend measured from the diecast end
    assert (f["stub"]["lift"], f["stub"]["cyl"]) == (34.8, 30)
    assert f["stub"]["lift"] + f["stub"]["cyl"] - D["head"]["size"]["d"] == pytest.approx(45)
    assert (f["strap"]["lift"], f["strap"]["out"]) == (19.8, 63.5)
    # the ring's far edge is the lanyard's 61.5 REF behind the head's back
    assert f["strap-ring"]["lift"] == f["strap"]["out"]
    assert f["strap-ring"]["out"] - D["head"]["size"]["d"] == pytest.approx(61.5)
    for x in f.values():
        assert x.get("confidence") and str(x.get("source") or "").strip()


def test_the_strap_lies_on_the_boot_not_in_it():
    s = _skin()
    boot, strap = s["relief-boot"], s["strap"]
    boot_top = float(boot.get("cy")) - float(boot.get("r"))
    underside = float(strap.get("y")) + float(strap.get("height"))
    assert underside == pytest.approx(boot_top, abs=1e-6)
    # and both lie above the body, on the tab side
    assert float(strap.get("y")) < 0


def test_the_cable_point_sits_on_the_stub():
    cp = D["connection-points"]
    assert cp["mate"] == {"at": [9.175, 4.25], "direction": "front"}
    assert cp["cable"]["on"] == "stub" and cp["cable"]["direction"] == "front"
    s = _skin()["stub"]
    assert cp["cable"]["at"] == [float(s.get("cx")), float(s.get("cy"))]
    assert not [e for e in errors(lint.lint_component_seat_point) if "[L106]" in e]


# --- seated in a real QSFP28 cage ---------------------------------------------

AGR560 = LIB / "devices/edgecore/agr560"
PORT = "qsfp28-4"


@pytest.fixture(scope="module")
def seated(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("qc")
    dev = tmp / "agr560" / "device.yaml"
    shutil.copytree(AGR560, dev.parent)
    d = yaml.safe_load(dev.read_text())
    for cfg in d["configurations"].values():
        cfg["occupants"] = {PORT: {"ref": REF, "attrs": {"cable-od": 3.0}}}
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    r = run(dev, tmp / "o")
    assert r.returncode == 0, r.stderr[-800:]
    svg = sorted((tmp / "o").glob("agr560*front.svg"))[0]
    root = ET.parse(svg).getroot()
    return root, {c: p for p in root.iter() for c in p}


def _one(root, suffix):
    hits = [e for e in root.iter() if (e.get("id") or "").endswith(suffix)]
    assert len(hits) == 1, (suffix, [h.get("id") for h in hits])
    return hits[0]


def test_it_seats_in_an_agr560_qsfp28_cage(seated):
    root, parents = seated
    occ = _one(root, f"{PORT}-occupant")
    assert occ.get("data-ref", "").startswith(REF)
    host = next(e for e in root.iter() if e.get("data-path") == occ.get("data-for"))
    hx, hy = device_point(parents, host, cage_mate(host))
    ox, oy = device_point(parents, occ, own_mate(occ))
    assert abs(hx - ox) < 1e-6 and abs(hy - oy) < 1e-6, ((hx, hy), (ox, oy))
    assert_same_turn(parents, occ, host)


def test_the_placements_cable_od_reaches_the_stub(seated):
    root, _ = seated
    assert float(_one(root, f"{PORT}-occupant--stub").get("r")) == 1.5


def test_every_solid_builds_right_way_out(seated):
    """relief.js: a raised node runs from its summed lift to its absolute out;
    a cyl from its summed lift for its length."""
    root, parents = seated
    seen = {}
    for n in ("head", "relief-boot", "stub", "strap", "strap-ring"):
        el = _one(root, f"{PORT}-occupant--{n}")
        lift = effective_lift(parents, el)
        if el.get("data-z-out"):
            depth = float(el.get("data-z-out")) - lift
        else:
            depth = float(el.get("data-z-cyl"))
        assert depth > 0, (n, depth)
        seen[n] = (lift, lift + depth)
    assert seen["head"][1] == pytest.approx(seen["relief-boot"][0])
    assert seen["relief-boot"][1] == pytest.approx(seen["stub"][0])
    assert seen["strap"][0] == pytest.approx(seen["head"][1])
    assert seen["strap"][1] == pytest.approx(seen["strap-ring"][0])


def test_the_head_buries_nothing(seated):
    """2D: document order is paint order. The head is the skin's base plate,
    so the boot, the stub and the strap all paint after it."""
    root, parents = seated
    head = _one(root, f"{PORT}-occupant--head")
    kids = list(parents[head])
    assert kids.index(head) == min(kids.index(_one(root, f"{PORT}-occupant--{n}"))
                                   for n in ("head", "relief-boot", "stub", "strap", "strap-ring"))


def test_the_cable_marker_points_at_the_stub(seated):
    root, _ = seated
    marks = [e for e in root.iter() if e.get("data-cp") == "cable"
             and (e.get("data-cp-on") or "").endswith(f"{PORT}-occupant--stub")]
    assert len(marks) == 1
