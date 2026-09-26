"""generic/qsfp-dd-cable@1 (Type 1) and generic/qsfp-dd-cable-type2@1: the QSFP-DD
cable ends (docs/pluggables-cables-design.md sections 2 and 3).

The two share everything but the head's length and the strap. Type 2's head is the
Volex drawing's 28.3 outside the cage; Type 1's is the MSA's 20 MAX, because no held
drawing dimensions a Type 1 cable head. L121 holding the Type 1 part to 20 is what
makes the split worth having, and a test below proves it does.
"""
import copy
import json
import pathlib
import shutil
import sys
import xml.etree.ElementTree as ET

import jsonschema
import pytest
import yaml

import warmrender
from portrayal import lint
from portrayal import render as render_mod
from test_nested_occupants import _lib, by_path, device_point, own_mate, cage_mate
from test_head_3d import lift_of

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
lint.STANDARDS.update(lint.load_yaml(ROOT / "spec/schemas/standards.yaml")["standards"])

T1 = "generic/qsfp-dd-cable@1"
T2 = "generic/qsfp-dd-cable-type2@1"


def path_of(ref):
    ns, rest = ref.split("/")
    name, major = rest.split("@")
    return LIB / f"components/{ns}/{name}/v{major}/contract.yaml"


DOCS = {ref: yaml.safe_load(path_of(ref).read_text()) for ref in (T1, T2)}
BOTH = pytest.mark.parametrize("ref", [T1, T2])

# the heads, as the rulings fix them
HEAD = {
    T1: {"at": [0.0, -3.4], "size": {"w": 18.35, "h": 13.5, "d": 20.0}, "type": 1},
    T2: {"at": [0.0, -3.4], "size": {"w": 18.35, "h": 13.5, "d": 28.3}, "type": 2},
}
BOOT_CYL, BOOT_DIA, STUB_CYL = 15.0, 11.0, 30.0
# (lift, out), absolute from the cage face
STRAP = {T1: (20.0, 70.0), T2: (28.3, 68.3)}
RING = {T1: (53.5, 70.0), T2: (58.3, 68.3)}


def errors(ref, fn, doc=None):
    with lint.collecting() as got:
        fn(path_of(ref), doc if doc is not None else DOCS[ref])
    return got.errors


def feature(ref, node):
    return next(f for f in DOCS[ref]["relief"]["features"] if f["node"] == node)


def skin(ref):
    return ET.parse(path_of(ref).parent / "skins/default.svg").getroot()


def node(root, nid):
    return next(e for e in root.iter() if e.get("id") == nid)


@BOTH
def test_it_validates_and_conforms_to_the_qsfp_dd_envelope(ref):
    schema = json.loads((ROOT / "spec/schemas/component.schema.json").read_text())
    jsonschema.validate(DOCS[ref], schema)
    d = DOCS[ref]
    assert d["conforms"] == "qsfp-dd-module" and d["mates"] == "qsfp-dd"
    assert d["class"] == "transceiver" and d["behaviour"] == "occupies"
    assert d["size"] == {"w": 18.35, "h": 8.5, "d": 58.26}


@BOTH
def test_the_head_is_the_ruled_one_and_l121_is_clean(ref):
    h = DOCS[ref]["head"]
    assert {k: h[k] for k in ("at", "size", "type")} == HEAD[ref]
    assert h["node"] == "head"
    assert not [e for e in errors(ref, lint.lint_component_head) if "[L121]" in e]


def test_type_1_is_registry_and_type_2_is_drawing():
    assert DOCS[T1]["head"]["size-confidence"]["d"] == "registry"
    assert DOCS[T2]["head"]["size-confidence"]["d"] == "drawing"


def test_l121_fails_the_type_1_generic_given_the_type_2_length():
    """THE SPLIT MATTERS: the Volex 28.3 is inside Type 2's 35 MAX and over Type 1's
    20 MAX, so the same head on the Type 1 part is refused."""
    doc = copy.deepcopy(DOCS[T1])
    doc["head"]["size"]["d"] = 28.3
    got = [e for e in errors(T1, lint.lint_component_head, doc) if "[L121]" in e]
    assert any("length 28.3" in e and "20" in e for e in got), got


def test_type_1_provenance_says_no_held_drawing_dimensions_its_head():
    head = " ".join(DOCS[T1]["provenance"]["head"].split())
    assert "No held drawing dimensions a Type 1 cable head" in head
    assert "FS 400G QSFP-DD DAC" in head        # depicted there, per the rulings


@BOTH
def test_it_is_a_generic(ref):
    assert not [e for e in errors(ref, lint.lint_component_generic) if "[L99]" in e]
    attrs = DOCS[ref].get("attrs") or {}
    for k in ("speed", "reach", "power-draw-max-w", "cable-kind", "media"):
        assert k not in attrs


@BOTH
def test_the_fields_and_their_defaults(ref):
    f = DOCS[ref]["fields"]
    assert set(f) == {"cable-od", "jacket-color", "latch-color"}
    assert f["cable-od"]["default"] == 9.0 and f["cable-od"]["type"] == "number"
    assert f["jacket-color"]["default"] == "#1c1c1c"
    assert f["latch-color"]["default"] == "#6f6f6f"


@BOTH
@pytest.mark.parametrize("rule", ["lint_component_cable_od", "lint_component_fields",
                                  "lint_component_seat_point"])
def test_the_cable_rules_are_clean(ref, rule):
    assert not errors(ref, getattr(lint, rule))


@BOTH
def test_the_stub_is_sized_and_painted_by_the_fields(ref):
    stub = node(skin(ref), "stub")
    assert stub.tag.endswith("circle")
    assert stub.get("data-r-from") == "cable-od"
    assert stub.get("data-fill-from") == "jacket-color"
    assert float(stub.get("r")) == 4.5          # half the 9.0 default
    for nid in ("strap", "strap-ring"):
        s = node(skin(ref), nid)
        assert s.get("data-fill-from") == "latch-color"
        assert s.get("data-stroke-derive") == "latch-color"


@BOTH
def test_a_cable_od_of_3_gives_the_stub_r_1_5(ref):
    g, _ = render_mod.instance_group(_lib, ref, "t", [0, 0], None, {"cable-od": 3.0},
                                     None, None)
    stub = next(e for e in g.iter() if e.get("id") == "t--stub")
    assert float(stub.get("r")) == 1.5


@BOTH
def test_the_cable_point_sits_on_the_stub(ref):
    cp = DOCS[ref]["connection-points"]
    assert cp["mate"] == {"at": [9.175, 4.25], "direction": "front"}
    assert cp["cable"]["on"] == "stub" and cp["cable"]["direction"] == "front"
    stub = node(skin(ref), "stub")
    assert cp["cable"]["at"] == [float(stub.get("cx")), float(stub.get("cy"))]


@BOTH
def test_the_relief_chain_runs_head_boot_stub(ref):
    d = HEAD[ref]["size"]["d"]
    assert feature(ref, "head")["out"] == d
    boot = feature(ref, "relief-boot")
    assert boot["cyl"] == BOOT_CYL and boot["lift"] == d
    # borrowed in substance, `estimated` in the token: L36 keeps `borrowed` for a
    # figure the origin MEASURED, and the QSFP generic did not measure its boot
    assert boot["confidence"] == "estimated" and "generic/qsfp-cable@1" in boot["source"]
    assert float(node(skin(ref), "relief-boot").get("r")) * 2 == BOOT_DIA
    stub = feature(ref, "stub")
    assert stub["cyl"] == STUB_CYL and stub["lift"] == pytest.approx(d + BOOT_CYL)
    assert "out" not in stub        # a cyl's rear is lift + cyl; no square stub
    # 45 past the head's back, as generic/qsfp-cable@1's stub ends
    assert stub["lift"] + stub["cyl"] - d == pytest.approx(45.0)


@BOTH
def test_the_strap_lies_behind_the_head_on_top_of_the_cable(ref):
    strap, ring = feature(ref, "strap"), feature(ref, "strap-ring")
    assert (strap["lift"], strap["out"]) == pytest.approx(STRAP[ref])
    assert (ring["lift"], ring["out"]) == pytest.approx(RING[ref])
    root = skin(ref)
    s, b = node(root, "strap"), node(root, "relief-boot")
    boot_top = float(b.get("cy")) - float(b.get("r"))
    # the strap's underside sits on the boot's top, so the boot does not pierce it
    assert float(s.get("y")) + float(s.get("height")) == pytest.approx(boot_top)


@BOTH
def test_the_head_is_drawn_first_so_it_buries_nothing(ref):
    """In 2D the head is the part furthest from the viewer: everything else is
    drawn after it, or the head rect would paint over the boot, strap and stub."""
    ids = [e.get("id") for e in skin(ref) if e.get("id")]
    assert ids[0] == "head"
    assert set(ids[1:]) >= {"relief-boot", "stub", "strap", "strap-ring"}


# --- seated in a QSFP-DD cage on the AGR560 -----------------------------------

OCC = {"qsfpdd-0": T2, "qsfpdd-1": T1}      # qsfpdd-1 is the turned lower cage


@pytest.fixture(scope="module")
def seated(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("qsfpddcable")
    dev = tmp / "agr560" / "device.yaml"
    shutil.copytree(LIB / "devices/edgecore/agr560", dev.parent)
    d = yaml.safe_load(dev.read_text())
    d["configurations"]["base"]["occupants"] = OCC
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    r = warmrender.run([sys.executable, str(ROOT / "spec/tools/portrayal/render.py"), str(dev),
                        "--library", str(LIB), "--out", str(tmp / "o")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    root = ET.parse(tmp / "o" / "agr560.base.front.svg").getroot()
    return root, {c: p for p in root.iter() for c in p}


@pytest.mark.parametrize("cage", sorted(OCC))
def test_each_seats_in_a_qsfp_dd_cage(seated, cage):
    root, parents = seated
    host = by_path(root, cage)
    occ = by_path(root, f"{cage}-occupant")
    assert occ.get("data-ref", "").startswith(OCC[cage])
    hx, hy = device_point(parents, host, cage_mate(host))
    ox, oy = device_point(parents, occ, own_mate(occ))
    assert abs(hx - ox) < 1e-6 and abs(hy - oy) < 1e-6


@pytest.mark.parametrize("cage", sorted(OCC))
def test_seated_it_builds_as_solids_of_the_ruled_lengths(seated, cage):
    """Read off the compiled relief attributes the way kit/relief.js reads them:
    a raised node runs from its summed lift to its absolute out, a cyl from its
    summed lift for its length. Measured from the head's own base, so the
    cage's seat depth drops out."""
    root, parents = seated
    occ = by_path(root, f"{cage}-occupant")
    ref, oid = OCC[cage], occ.get("id")
    names = ("head", "relief-boot", "stub", "strap", "strap-ring")
    el = {n: next(e for e in occ.iter() if e.get("id") == f"{oid}--{n}") for n in names}
    d = HEAD[ref]["size"]["d"]
    head_lift = lift_of(parents, el["head"])
    base = float(el["head"].get("data-z-out")) - d
    for n in ("head", "strap", "strap-ring"):
        lo, hi = lift_of(parents, el[n]), float(el[n].get("data-z-out"))
        assert hi - lo > 0, (n, lo, hi)                       # never inside out
    assert head_lift == pytest.approx(base)
    assert lift_of(parents, el["relief-boot"]) - base == pytest.approx(d)
    assert float(el["relief-boot"].get("data-z-cyl")) == BOOT_CYL
    assert lift_of(parents, el["stub"]) - base == pytest.approx(d + BOOT_CYL)
    assert float(el["stub"].get("data-z-cyl")) == STUB_CYL
    for n, (lo, hi) in (("strap", STRAP[ref]), ("strap-ring", RING[ref])):
        assert lift_of(parents, el[n]) - base == pytest.approx(lo)
        assert float(el[n].get("data-z-out")) - base == pytest.approx(hi)
    # the head is not moved over its cable in 2D: it stays the first drawn
    order = [e.get("id") for e in occ.iter() if e in el.values()]
    assert order[0] == f"{oid}--head"
