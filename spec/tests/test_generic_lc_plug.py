"""generic/lc-plug: the four-tier LC plug silhouette, front view, standing for
every LC plug - a body holding the ferrule, and above it a latch column that
is NOT a simple taper: a 3.3 stem off the body, a 4.3 shoulder proud of it,
then the 2.3 tab (docs/superpowers/plans/
2026-09-19-pluggables-b2-connector-parts.md, Task 4).

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
import yaml

from portrayal import lint

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
P = LIB / "components/generic/lc-plug/v1/contract.yaml"

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


def test_shape():
    d = contract()
    assert d["class"] == "port"
    assert d["mates"] == "lc"
    assert d["interface"] == "lc-plug"
    assert d["conforms"] == "lc-plug"
    assert d["kind"] == "component"
    assert d["optical"]["positions"] == 1


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
    assert d["size"] == {"w": 5.58, "h": 10.43}
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


def test_the_four_tiers_are_the_part():
    d = contract()
    elems = d["elements"]
    assert set(elems) == {"tip", "shoulder", "stem", "body"}
    widths = {k: v["size"][0] for k, v in elems.items()}
    assert widths == {"tip": 2.3, "shoulder": 4.3, "stem": 3.3, "body": 5.58}
    heights = sum(v["size"][1] for v in elems.values())
    assert abs(heights - 10.43) < 0.01, "the four tiers must sum to the drawn 10.43"


def test_the_tiers_run_down_the_page_in_the_drawn_order():
    """THE ORDER IS A FACT ABOUT THE DRAWING, not a taper anyone chose.

    The first cut of this contract put the 3.3 tier ABOVE the 4.3 one and
    described a monotonic narrowing toward the tab. The drawing shows the 4.3
    shoulder standing proud of BOTH its neighbours: reading down from the tab
    it is 2.3, then 4.3, then 3.3, then the 5.58 body. Each width's extension
    lines land on a different tier and the three figures are far enough apart
    that the assignment cannot be mistaken - see provenance.keyway.
    """
    elems = contract()["elements"]
    order = sorted(elems, key=lambda k: elems[k]["at"][1])
    assert order == ["tip", "shoulder", "stem", "body"]
    # tiers stack with no gap and no overlap
    y = 0.0
    for k in order:
        assert abs(elems[k]["at"][1] - y) < 1e-9, f"{k} does not start where the tier above ends"
        y += elems[k]["size"][1]
    assert abs(y - 10.43) < 1e-9
    # every tier is centred on the body's centreline
    for k, e in elems.items():
        assert abs(e["at"][0] + e["size"][0] / 2 - 5.58 / 2) < 1e-9, k
    # NOT a taper: the shoulder is wider than the tier below it as well as above
    assert elems["shoulder"]["size"][0] > elems["stem"]["size"][0]


def test_the_body_tier_is_the_dimensioned_5_65():
    """Summing to 10.43 does not pin a SPLIT - any four numbers can do that.

    This is the assertion the first cut was missing: it checked only the sum,
    so a body of 4.48 (1.17 short) satisfied it. The body is the one tier the
    drawing DIMENSIONS - 5.65 on the side view, the same figure
    common/lc-boot@1 cites for the body it wraps - so it is the one tier that
    can be pinned against a callout rather than against a proportion.
    """
    d = contract()
    body = d["elements"]["body"]
    assert body["size"][1] == 5.65, (
        "the body tier must be the drawing's dimensioned body height, not a "
        "share of the overall silhouette")
    assert abs(body["at"][1] - (10.43 - 5.65)) < 1e-9
    # and the latch column is what is left of the dimensioned overall
    latch = sum(v["size"][1] for k, v in d["elements"].items() if k != "body")
    assert abs(latch - (10.43 - 5.65)) < 1e-9

    # THE AXIS IS THE BODY TIER'S CENTRE, and that is a DERIVED relation the
    # contract holds exactly - see provenance.axis. The drawn centreline
    # measures 7.617, which corroborates it to 0.007 but is NOT the stated
    # figure: at 45.686 px/mm half a pixel is 0.011, so the artwork cannot
    # resolve the 0.012 between them, and the tier centre is the one the
    # geometry fixes. The tolerance here is tight enough to tell the two
    # apart - swap in the measured 7.617 and this fails - because the whole
    # point is that the point and the tier it stands in cannot drift.
    axis = d["connection-points"]["mate"]["at"][1]
    assert abs(axis - (body["at"][1] + 5.65 / 2)) <= 0.005, (
        f"the mate point sits at {axis}, but the centre of the body tier the "
        f"ferrule stands in is {body['at'][1] + 5.65 / 2}")

    prov = " ".join(str(v) for v in d["provenance"].values())
    assert "5.65" in prov, "provenance must cite the dimension the body is pinned to"


def test_the_axis_provenance_does_not_claim_a_reading_for_a_derived_figure():
    """The heading and the body must agree about what 7.61 IS.

    An earlier draft opened "drawing - MEASURED, not derived" over prose that
    then did the arithmetic honestly: the stated value is the body tier's
    centre, 4.78 + 5.65/2 = 7.605, and the drawn centreline measures 7.617.
    Presenting a derived figure as a measurement is the one mislabel this
    library treats as cardinal, and a heading is where a reader stops.
    """
    d = contract()
    axis_prov = d["provenance"]["axis"]
    head = axis_prov.lstrip().split(".")[0]
    assert head.upper().startswith("DERIVED"), (
        f"the heading must say what the number is before the prose explains "
        f"it; it opens {head!r}")
    assert "measured" not in head.lower(), (
        f"the heading must not claim a reading for a derived figure; it opens "
        f"{head!r}")
    assert "It is NOT the measured figure" in axis_prov, (
        "say outright that the stated value is not the measurement - the "
        "earlier draft's prose was honest and its heading was not, and a "
        "reader who stops at the heading is the one this protects")
    # both figures named, so a reader can check the claim either way round
    assert "7.605" in axis_prov and "7.617" in axis_prov
    # and the stated value is the derived one, not the measured one
    assert d["connection-points"]["mate"]["at"][1] == 7.61


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
    for el, e in contract()["elements"].items():
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
