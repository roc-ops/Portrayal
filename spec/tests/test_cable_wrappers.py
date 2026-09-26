"""The six vendor cable ends: the library's first vendor wrappers
(docs/pluggables-design.md, "The vendor wrapper, once";
docs/pluggables-cables-design.md section 5).

A wrapper composes its generic whole, passes its product's colours and cable
diameter to the generic's fields, restates the generic's `mate` point, and
carries the product's facts in `attrs`. It draws nothing of its own.

It does NOT restate the generic's `cable` point. The composed generic already
emits its own `cable` marker inside the wrapper's group, pointing at the
wrapper's `body--stub`; a restated one would be a second, identical marker, and
L106 refuses it anyway, because `'on'` must name a relief feature of the SAME
contract and a wrapper has no relief. A test below holds both halves.
"""
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
from test_nested_occupants import _lib, by_path, cage_mate, device_point, own_mate

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
LIBS = [str(LIB)]
lint.STANDARDS.update(lint.load_yaml(ROOT / "spec/schemas/standards.yaml")["standards"])
SCHEMA = json.loads((ROOT / "spec/schemas/component.schema.json").read_text())

SFP, QSFP, DD2 = "generic/sfp-cable@1", "generic/qsfp-cable@1", "generic/qsfp-dd-cable-type2@1"
GENERICS = ["generic/sfp-cable@1", "generic/qsfp-cable@1",
            "generic/qsfp-dd-cable@1", "generic/qsfp-dd-cable-type2@1"]

# wrapper -> (the generic it wraps, cable-kind, speed, media, the agr560 cage it seats in)
WRAPPERS = {
    "molex/sfp-plus-passive-dac@1": (SFP, "dac", "10g", "sfp-plus", "port-0"),
    "amphenol/qsfp28-passive-dac@1": (QSFP, "dac", "100g", "qsfp28", "qsfp28-0"),
    "amphenol/qsfp56-linear-active@1": (QSFP, "acc", "200g", "qsfp56", "qsfp28-1"),
    "fs/qsfp28-aoc@1": (QSFP, "aoc", "100g", "qsfp28", "qsfp28-2"),
    "volex/qsfp-dd-passive-dac@1": (DD2, "dac", "400g", "qsfp-dd", "qsfpdd-0"),
    "credo/hiwire-shift-qsfp-dd@1": (DD2, "aec", "400g", "qsfp-dd", "qsfpdd-1"),
    "siemon/qsfp28-aoc@1": (QSFP, "aoc", "100g", "qsfp28", "qsfp28-4"),
}
# the field values each wrapper's own document gives it; a field absent here is
# one its document does not state, so the generic's default stands
FIELDS = {
    "molex/sfp-plus-passive-dac@1": {"latch-color": "#1c1c1c"},
    "amphenol/qsfp28-passive-dac@1": {"latch-color": "#009a44"},
    "amphenol/qsfp56-linear-active@1": {"latch-color": "#5b77cc", "jacket-color": "#1c1c1c"},
    "fs/qsfp28-aoc@1": {},
    "volex/qsfp-dd-passive-dac@1": {"cable-od": 9.0, "jacket-color": "#1c1c1c"},
    "credo/hiwire-shift-qsfp-dd@1": {"cable-od": 5.3, "jacket-color": "#6b3fa0"},
    "siemon/qsfp28-aoc@1": {"cable-od": 3.0, "jacket-color": "#49eaf8"},
}
EACH = pytest.mark.parametrize("ref", sorted(WRAPPERS))


def path_of(ref):
    ns, rest = ref.split("/")
    name, major = rest.split("@")
    return LIB / f"components/{ns}/{name}/v{major}/contract.yaml"


def doc(ref):
    return yaml.safe_load(path_of(ref).read_text())


def field_value(ref, key):
    """What the drawing should carry for `key`: the wrapper's value, else the
    generic's default."""
    if key in FIELDS[ref]:
        return FIELDS[ref][key]
    return doc(WRAPPERS[ref][0])["fields"][key]["default"]


# --- the contract --------------------------------------------------------------

@EACH
def test_it_is_a_wrapper_of_its_generic(ref):
    d, generic = doc(ref), WRAPPERS[ref][0]
    g = doc(generic)
    jsonschema.validate(d, SCHEMA)
    assert d["kind"] == "module" and d["class"] == "transceiver"
    assert d["behaviour"] == "occupies"
    assert d["mates"] == g["mates"]
    assert d["size"] == g["size"]
    assert d["size-confidence"] == {"w": "borrowed", "h": "borrowed", "d": "borrowed"}
    assert d["provenance"]["size"].startswith(f"borrowed - {generic}")
    assert d["parts"] == [{"ref": generic, "id": "body", "at": [0, 0],
                           **({"attrs": FIELDS[ref]} if FIELDS[ref] else {})}]
    # it restates mate, exactly, and not cable (see the module docstring)
    assert d["connection-points"] == {"mate": g["connection-points"]["mate"]}
    # no relief and no elements: every drawn thing is the generic's
    assert "relief" not in d and not d.get("elements")


@EACH
def test_its_attrs_are_the_products(ref):
    _generic, kind, speed, media, _cage = WRAPPERS[ref]
    a = doc(ref)["attrs"]
    assert a["cable-kind"] == kind and a["speed"] == speed and a["media"] == media
    assert a.get("model")
    # a power figure, or a sourced statement that there is none
    assert a.get("power-draw-max-w") or a.get("power-draw-typical-w") or a.get("power-absent")
    assert doc(ref)["provenance"]["power"].strip()


@EACH
def test_it_lints_clean(ref):
    """L1 (schema), L9, L11, L97, L99, L106, L122, L27/L52 on the wrapper, and
    L121 on the generic it wraps - no error and no warning."""
    p, d = path_of(ref), doc(ref)
    with lint.collecting() as got:
        lint.lint_component(p, jsonschema.Draft202012Validator(SCHEMA))
        lint.lint_component_parts(p, d, LIBS)
        lint.lint_component_mating(p, d, LIBS)
        lint.lint_component_generic(p, d)
        lint.lint_component_head(p, d)
        lint.lint_component_cable_od(p, d)
        lint.lint_component_seat_point(p, d)
        lint.lint_component_power(p, d)
        lint.lint_component_size_confidence(p, d)
        lint.lint_component_speed_vocabulary(p, d)
        lint.lint_component_relief_confidence(p, d, LIBS)
        gen = WRAPPERS[ref][0]
        lint.lint_component_head(path_of(gen), doc(gen))
    assert got.errors == [] and got.warnings == []


@EACH
def test_a_cable_od_is_a_number_or_absent_never_empty(ref):
    """L122 errors on `cable-od: ""`; a document that gives no diameter leaves
    the key out, and the generic's default stands."""
    attrs = doc(ref)["parts"][0].get("attrs") or {}
    if "cable-od" in attrs:
        assert isinstance(attrs["cable-od"], (int, float)) and 2 <= attrs["cable-od"] <= 15
    else:
        assert "NOT STATED" in doc(ref)["provenance"]["cable-od"]


@pytest.mark.parametrize("ref", GENERICS)
def test_no_generic_provenance_line_opens_borrowed(ref):
    """`borrowed` is kept for a figure its origin part measured (L36). The
    generics' figures come from drawings and data sheets, so no provenance line
    opens with it; `borrowed` there would claim a measurement nobody made."""
    prov = doc(ref)["provenance"]
    assert prov, ref
    assert [k for k, v in prov.items() if str(v).lstrip().startswith("borrowed")] == []


def test_a_restated_cable_point_is_refused_and_is_not_needed():
    ref = "volex/qsfp-dd-passive-dac@1"
    d = doc(ref)
    d["connection-points"]["cable"] = {"at": [9.175, 4.25], "direction": "front",
                                       "on": "body--stub"}
    with lint.collecting() as got:
        lint.lint_component_seat_point(path_of(ref), d)
    assert any("L106" in e for e in got.errors)
    # and the composed generic's own marker is already there, on the stub
    g, _ = render_mod.instance_group(_lib, ref, "t", [0, 0], None, {}, None, None)
    cps = [e for e in g.iter() if e.get("data-cp") == "cable"]
    assert len(cps) == 1 and cps[0].get("data-cp-on") == "t--body--stub"


# --- seated in the AGR560 -------------------------------------------------------

@pytest.fixture(scope="module")
def seated(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("cablewrappers")
    dev = tmp / "agr560" / "device.yaml"
    shutil.copytree(LIB / "devices/edgecore/agr560", dev.parent)
    d = yaml.safe_load(dev.read_text())
    d["configurations"]["base"]["occupants"] = {w[4]: ref for ref, w in WRAPPERS.items()}
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    r = warmrender.run([sys.executable, str(ROOT / "spec/tools/portrayal/render.py"), str(dev),
                        "--library", str(LIB), "--out", str(tmp / "o")],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    root = ET.parse(tmp / "o" / "agr560.base.front.svg").getroot()
    configs = json.loads((tmp / "o" / "agr560.configs.json").read_text())
    return root, {c: p for p in root.iter() for c in p}, configs


@EACH
def test_it_seats_in_a_cage_of_its_family(seated, ref):
    root, parents, _ = seated
    cage = WRAPPERS[ref][4]
    host = by_path(root, cage)
    occ = by_path(root, f"{cage}-occupant")
    assert occ.get("data-ref", "").startswith(ref)
    hx, hy = device_point(parents, host, cage_mate(host))
    ox, oy = device_point(parents, occ, own_mate(occ))
    assert abs(hx - ox) < 1e-6 and abs(hy - oy) < 1e-6


@EACH
def test_the_stub_takes_the_wrappers_cable_od_and_jacket(seated, ref):
    root, _, _ = seated
    occ = by_path(root, f"{WRAPPERS[ref][4]}-occupant")
    stub = next(e for e in occ.iter() if e.get("id") == f"{occ.get('id')}--body--stub")
    assert float(stub.get("r")) == pytest.approx(field_value(ref, "cable-od") / 2)
    assert stub.get("fill") == field_value(ref, "jacket-color")
    strap = next(e for e in occ.iter() if e.get("id") == f"{occ.get('id')}--body--strap")
    assert strap.get("fill") == field_value(ref, "latch-color")


def test_the_accept_lists_offer_the_generics_and_the_wrappers(seated):
    _, _, configs = seated
    accepts = {c["id"]: c["accepts"] for c in configs["cages"]["front"]}
    sfp, qsfp, dd = accepts["port-0"], accepts["qsfp28-0"], accepts["qsfpdd-0"]
    assert "generic/sfp-cable@1" in sfp and "molex/sfp-plus-passive-dac@1" in sfp
    assert "generic/qsfp-cable@1" in qsfp
    for ref in ("amphenol/qsfp28-passive-dac@1", "amphenol/qsfp56-linear-active@1",
                "fs/qsfp28-aoc@1", "siemon/qsfp28-aoc@1"):
        assert ref in qsfp and ref in dd          # a QSFP-DD cage also accepts QSFP
        assert ref not in sfp
    for ref in GENERICS[1:]:
        assert ref in dd
    for ref in ("volex/qsfp-dd-passive-dac@1", "credo/hiwire-shift-qsfp-dd@1"):
        assert ref in dd and ref not in qsfp and ref not in sfp
    assert "molex/sfp-plus-passive-dac@1" not in qsfp + dd
    # generics first, then the wrappers
    for lst in (sfp, qsfp, dd):
        ns = [r.split("/")[0] == "generic" for r in lst]
        assert ns == sorted(ns, reverse=True)


def test_the_thin_aoc_is_visibly_thinner_than_a_default_sized_cable(seated):
    """The reason the Siemon end exists: a 3.0 mm fibre cable has to LOOK thin
    beside a copper one. Read from the compiled drawing, not the contracts, so
    it fails if the field stops reaching the stub. The Amphenol ACC states no
    diameter and keeps the generic's 6.9 default; the AOC's stub diameter must
    be less than half of that."""
    root, _, _ = seated

    def stub_d(ref):
        occ = by_path(root, f"{WRAPPERS[ref][4]}-occupant")
        assert occ.get("data-ref", "").startswith(ref)
        stub = next(e for e in occ.iter() if e.get("id") == f"{occ.get('id')}--body--stub")
        return 2 * float(stub.get("r"))

    thin, acc = stub_d("siemon/qsfp28-aoc@1"), stub_d("amphenol/qsfp56-linear-active@1")
    assert thin == pytest.approx(3.0)
    assert acc == pytest.approx(doc(QSFP)["fields"]["cable-od"]["default"])
    assert thin < acc / 2
