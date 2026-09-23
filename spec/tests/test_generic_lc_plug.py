"""generic/lc-plug: the four-tier LC plug silhouette, front view, standing for
every LC plug - a body holding the ferrule, and a latch column that is NOT a
simple taper: a 3.3 stem off the body, a 4.3 shoulder proud of it, then the
2.3 tab (docs/pluggables-connectors-design.md).

SINCE @2 THE PLUG IS DRAWN SEATED: latch DOWN, in its bore's own unrotated
convention, and compressed so the tab ends at the bulkhead keyway's end, 5.71
from the ferrule axis (docs/pluggables-caps-design.md, "Seated plugs"). The
tier WIDTHS are SENKO's dimensioned ones; the tier HEIGHTS are SENKO's free
ones scaled in proportion, a modelling choice the contract declares.

It occupies an `lc` receptacle at its own `mate` point (behaviour: occupies,
mates: lc) and presents `lc-plug` so common/lc-boot@1 can seat on its `boot`
point - or a bare cable can land on its `cable` point when there is no boot.
Both rear points share the front `mate` point's (x, y): the fibre runs
straight through the plug on one axis, front to back.

NO DEPTH. The SENKO drawing gives an LC plug's overall length only as a
REFERENCE figure in parentheses, and three SENKO products disagree - (42),
(38.6), (43) - while the front profile and the latch length repeat with
tolerances. spec/tests/test_plug_envelopes.py already pins this on the
registry entry; the tests below pin it on the contract that reads the
registry.
"""
import json
import pathlib

import jsonschema
import pytest
import yaml

from portrayal import lint

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
P = LIB / "components/generic/lc-plug/v2/contract.yaml"

COMPONENT_SCHEMA = json.loads((ROOT / "spec/schemas/component.schema.json").read_text())

lint.STANDARDS.update(
    lint.load_yaml(ROOT / "spec/schemas/standards.yaml")["standards"])


def component_errors(path):
    d = yaml.safe_load(pathlib.Path(path).read_text())
    with lint.collecting() as got:
        lint.lint_component(path, jsonschema.Draft202012Validator(COMPONENT_SCHEMA))
        lint.lint_component_mating(path, d, [str(ROOT / "library")])
        lint.lint_component_generic(path, d)
        return list(got.errors)


def rule_errors(path, *rules):
    errs = component_errors(path)
    return [e for e in errs if any(f"[{r}]" in e for r in rules)]


def contract():
    return yaml.safe_load(P.read_text())


def tiers(d=None):
    """The silhouette's elements: everything but the fibre position `1`,
    which sits inside the body tier and is an address, not a tier."""
    return {k: v for k, v in (d or contract())["elements"].items()
            if v.get("class") != "fibre"}


def test_shape():
    d = contract()
    assert d["class"] == "port"
    assert d["mates"] == "lc"
    assert d["interface"] == "lc-plug"
    assert d["kind"] == "component"
    assert d["optical"]["positions"] == 1
    # NO `conforms:` since @2: `lc-plug` is SENKO's FREE 10.43 silhouette and
    # this part is drawn seated, so L9 would rightly refuse it
    assert "conforms" not in d
    assert "NO `conforms:`" in d["provenance"]["standard"]

def test_no_behaviour_despite_the_plan_table():
    """The plan's Task 4 table says `behaviour: occupies`, but this class is
    shared with std/lc-bore@3 (the aperture the plug enters), and
    test_behaviour.py::test_a_receptacle_does_not_move asserts every
    `class: port` contract carries no `behaviour` at all. std/lc-bore@3 itself
    seats a mate-to occupant with no `behaviour` set - the field only drives
    the 3D viewer's eject affordance, not the mate-to math - so omitting it
    keeps this part working and keeps that invariant intact. See
    provenance.behaviour for the full account."""
    d = contract()
    assert "behaviour" not in d
    assert "behaviour" in d["provenance"]


def test_size_has_no_depth():
    d = contract()
    assert d["size"] == {"w": 5.58, "h": 8.535}
    assert d["size-confidence"] == {"w": "drawing", "h": "borrowed"}
    assert "d" not in d["size"], (
        "an LC plug has no class-wide overall length - see the contract's "
        "provenance.size and spec/tests/test_plug_envelopes.py")

def test_size_says_why_there_is_no_depth():
    """provenance.size must be actionable for a future reader, not just an
    absence - it should name the REF dimension and say it is not a class
    figure."""
    prov = contract()["provenance"]["size"]
    assert "REF" in prov or "reference" in prov.lower()
    assert "42" in prov, "should name at least one of the disagreeing REF figures"


def test_size_says_h_includes_the_latch_unlike_rj45_plug():
    """Fix round 1 on Tasks 6/7, finding 3: this part's h (10.43) is a
    silhouette INCLUDING its latch; generic/rj45-plug@1's h (7.93) is the body
    EXCLUDING its latch. Neither is wrong, but they measure different
    quantities and a reader comparing them needs to be told so - in both
    contracts and in both spec/schemas/standards.yaml entries."""
    prov = contract()["provenance"]
    text = " ".join(str(v) for v in prov.values()).lower()
    assert "rj45-plug" in text
    assert "includ" in text  # "including"/"includes"
    reg = yaml.safe_load(
        (ROOT / "spec/schemas/standards.yaml").read_text())["standards"]
    assert "includ" in reg["lc-plug"]["notes"].lower()
    assert "exclud" in reg["rj45-plug"]["notes"].lower()


FREE = {"tip": 2.66, "shoulder": 0.79, "stem": 1.33}      # SENKO, the free latch
SEATED_REACH = 5.71     # std/lc-bulkhead-bore@1's keyway end, from the ferrule


def test_the_four_tiers_are_the_part():
    d = contract()
    elems = tiers(d)
    assert set(elems) == {"tip", "shoulder", "stem", "body"}
    widths = {k: v["size"][0] for k, v in elems.items()}
    assert widths == {"tip": 2.3, "shoulder": 4.3, "stem": 3.3, "body": 5.58}
    heights = sum(v["size"][1] for v in elems.values())
    assert abs(heights - d["size"]["h"]) < 1e-9


def test_the_latch_tiers_are_the_free_ones_scaled_in_proportion():
    """THE DECLARED MODELLING CHOICE, held to its own arithmetic: the seated
    latch is 5.71 - 5.65/2 = 2.885 long against the free 4.78, and each tier
    is its free height scaled by the same ratio - so the three cannot be
    re-split without the contract's prose going stale."""
    elems = contract()["elements"]
    k = (SEATED_REACH - 5.65 / 2) / sum(FREE.values())
    for tier, free in FREE.items():
        assert elems[tier]["size"][1] == pytest.approx(free * k, abs=0.001), tier
    assert "NOT A READING" in contract()["provenance"]["keyway"]

def test_the_tiers_run_down_the_page_in_the_drawn_order():
    """THE ORDER IS A FACT ABOUT THE DRAWING, not a taper anyone chose - and
    since @2 it reads from the BODY down, because the latch is drawn below it.

    Reading out along the latch it is the 5.58 body, then 3.3, then 4.3, then
    the 2.3 tab: the 4.3 shoulder stands proud of BOTH its neighbours (see
    provenance.free-state for how the drawing fixed that).
    """
    elems = tiers()
    order = sorted(elems, key=lambda k: elems[k]["at"][1])
    assert order == ["body", "stem", "shoulder", "tip"]
    # tiers stack with no gap and no overlap
    y = 0.0
    for k in order:
        assert abs(elems[k]["at"][1] - y) < 1e-9, f"{k} does not start where the tier above ends"
        y += elems[k]["size"][1]
    assert abs(y - 8.535) < 1e-9
    # every tier is centred on the body's centreline
    for k, e in elems.items():
        assert abs(e["at"][0] + e["size"][0] / 2 - 5.58 / 2) < 1e-9, k
    # NOT a taper: the shoulder is wider than the tier on either side of it
    assert elems["shoulder"]["size"][0] > elems["stem"]["size"][0]
    assert elems["shoulder"]["size"][0] > elems["tip"]["size"][0]

def test_the_body_tier_is_the_dimensioned_5_65():
    """The body is the one tier the drawing DIMENSIONS - 5.65 on the side
    view, the figure common/lc-boot@1 cites for the body it wraps - so it is
    pinned against the callout, and the latch is what the seated reach leaves.
    """
    d = contract()
    body = d["elements"]["body"]
    assert body["size"][1] == 5.65
    assert body["at"][1] == 0.0
    latch = sum(v["size"][1] for k, v in tiers(d).items() if k != "body")
    assert abs(latch - (SEATED_REACH - 5.65 / 2)) < 1e-9

    # THE AXIS IS THE BODY TIER'S CENTRE, a DERIVED relation the contract
    # holds exactly - see provenance.axis.
    axis = d["connection-points"]["mate"]["at"][1]
    assert axis == pytest.approx(body["at"][1] + 5.65 / 2, abs=1e-9)
    # and the tab ends at the seated reach below it
    assert d["size"]["h"] - axis == pytest.approx(SEATED_REACH, abs=1e-9)

    prov = " ".join(str(v) for v in d["provenance"].values())
    assert "5.65" in prov, "provenance must cite the dimension the body is pinned to"

def test_the_axis_provenance_does_not_claim_a_reading_for_a_derived_figure():
    """The heading and the body must agree about what 2.825 IS: the body
    tier's centre, derived, corroborated against SENKO's drawn centreline (on
    the free plug, where @1 measured it) - not a reading of its own."""
    d = contract()
    axis_prov = d["provenance"]["axis"]
    head = axis_prov.lstrip().split(":")[0].split(".")[0]
    assert head.upper().startswith("DERIVED"), head
    assert "measured" not in head.lower(), head
    assert "2.825" in axis_prov and "0.012" in axis_prov
    assert d["connection-points"]["mate"]["at"][1] == 2.825

def test_connection_points_share_the_optical_axis():
    cps = contract()["connection-points"]
    assert set(cps) == {"mate", "boot", "cable"}
    assert cps["mate"]["direction"] == "front"
    assert cps["boot"]["direction"] == "rear"
    assert cps["cable"]["direction"] == "rear"
    # front and rear are the same physical axis, seen from two directions
    assert cps["mate"]["at"] == cps["boot"]["at"] == cps["cable"]["at"]


def test_it_lints_clean_alone():
    """L9 (size against the registry), L11 (mating - both `mates` and
    `interface` need a usable 'mate' point) and L99 (a generic under
    class: transceiver stays generic - not applicable here since class is
    `port`, but run it anyway so a future reclass is still checked)."""
    assert rule_errors(P, "L9", "L11", "L99") == []


def test_skin_matches_the_four_elements():
    svg = (P.parent / "skins/default.svg").read_text()
    for el in ("tip", "shoulder", "stem", "body"):
        assert f'id="{el}"' in svg, el


def test_the_skin_draws_the_tiers_where_the_contract_puts_them():
    """A skin that kept the old split would draw a plug the contract denies."""
    import re
    svg = (P.parent / "skins/default.svg").read_text()
    for el, e in tiers().items():
        m = re.search(rf'<rect id="{el}"[^>]*>', svg)
        assert m, el
        got = {k: float(re.search(rf'\b{k}="([-\d.]+)"', m.group(0)).group(1))
               for k in ("x", "y", "width", "height")}
        assert (got["x"], got["y"], got["width"], got["height"]) == (
            e["at"][0], e["at"][1], e["size"][0], e["size"][1]), (el, got, e)
    # the ferrule sits on the optical axis
    axis = contract()["connection-points"]["mate"]["at"]
    for cid in ("ferrule", "ferrule-bore"):
        m = re.search(rf'<circle id="{cid}"[^>]*>', svg)
        assert m, cid
        cx = float(re.search(r'cx="([-\d.]+)"', m.group(0)).group(1))
        cy = float(re.search(r'cy="([-\d.]+)"', m.group(0)).group(1))
        assert [cx, cy] == axis, (cid, cx, cy, axis)


def test_the_fibre_position_is_the_ferrule_on_the_axis():
    """L112: the plug's one fibre is node `1`, the group around the ferrule
    end, and its element box is centred on the optical axis."""
    import re
    fibres = {k: v for k, v in contract()["elements"].items() if v.get("class") == "fibre"}
    assert set(fibres) == {"1"}
    e = fibres["1"]
    axis = contract()["connection-points"]["mate"]["at"]
    centre = [round(e["at"][i] + e["size"][i] / 2, 6) for i in (0, 1)]
    assert centre == axis, (centre, axis)
    svg = (P.parent / "skins/default.svg").read_text()
    g = svg[svg.index('<g id="1">'):]
    g = g[:g.index("</g>")]
    assert 'id="ferrule"' in g and 'id="ferrule-bore"' in g
