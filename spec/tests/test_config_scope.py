"""A configuration can change the sheet metal, not only what is fitted into it.

A C40G ordered for AC has one bolted panel across the bottom of the rear where a
DC chassis has two power-entry openings. That is different metal, not two empty
openings - and until `only-in` existed the format could say only what was FITTED,
so the AC rear drew two black rectangles and the bay picker offered a DC power
entry module on a chassis that cannot take one.
"""
from pathlib import Path

import pytest
import yaml

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"
C40G = yaml.safe_load((LIB / "devices/casa/c40g/device.yaml").read_text())


def rear_parts():
    c = C40G["views"]["rear"]["components"]
    return {q["id"]: q for q in (c.get("bays") or []) + (c.get("placements") or [])}


def test_the_two_power_entry_bays_are_dc_only():
    parts = rear_parts()
    cfgs = set(C40G["configurations"])
    for pem in ("pem-1", "pem-2"):
        only = set(parts[pem].get("only-in") or ())
        assert only, f"{pem} is present in every configuration, including AC"
        assert "ac-power" not in only, f"{pem} is present on an AC chassis"
        assert only < cfgs, f"{pem} scoped to {only}, which is not a subset of {cfgs}"


def test_the_ac_panel_is_ac_only_and_stands_where_the_bays_do():
    parts = rear_parts()
    panel = parts["ac-inlet-panel"]
    assert panel.get("only-in") == ["ac-power"]
    # it stands in for the two openings, so it starts on the same band top edge
    assert panel["at"][1] == parts["pem-1"]["at"][1] == parts["pem-2"]["at"][1]


def test_the_panel_and_the_openings_are_the_same_band():
    """One band carrying two heights is how this went wrong the first time.

    The panel was anchored to a top edge of 194.0, which the device's own
    `pem-band-top-edge` gap calls impossible, and the PEM bays were later moved to
    196.0 without the panel following. Both are now 68.5 tall. The gap may still
    move the band; what must not happen again is the two disagreeing.
    """
    panel = yaml.safe_load(
        (LIB / "components/casa/c40g-ac-inlet-panel/v1/contract.yaml").read_text())
    bay_h = rear_parts()["pem-1"]["size"]["h"]
    assert panel["size"]["h"] == bay_h, (panel["size"]["h"], bay_h)


def test_ac_and_dc_rears_render_different_metal():
    paths = [LIB / "dist/c40g.ac-power.rear.svg", LIB / "dist/c40g.docsis-classic.rear.svg"]
    for q in paths:
        if not q.exists():
            pytest.skip(f"{q} not built - run ./build.sh")
    ac, dc = (q.read_text() for q in paths)
    for bay in ('id="pem-1"', 'id="pem-2"'):
        assert bay not in ac, f"{bay} rendered on an AC chassis"
        assert bay in dc
    assert 'id="ac-inlet-panel"' in ac
    assert 'id="ac-inlet-panel"' not in dc, "the AC panel rendered on a DC chassis"


def test_scoping_never_silently_empties_a_view():
    """`only-in` is the one field that can delete geometry, and it is a list of
    free-text names. Every name in the library must be a real configuration."""
    for p in sorted(LIB.glob("devices/*/*/device.yaml")):
        d = yaml.safe_load(p.read_text()) or {}
        cfgs = set(d.get("configurations") or {})
        for vname, view in (d.get("views") or {}).items():
            comps = (view or {}).get("components") or {}
            for q in (comps.get("bays") or []) + (comps.get("placements") or []):
                only = q.get("only-in")
                if not only:
                    continue
                assert set(only) <= cfgs, (p.name, vname, q["id"], sorted(set(only) - cfgs))
                assert set(only) != cfgs, (
                    f"{p.name} {q['id']}: scoped to every configuration, which is "
                    "what omitting the field already means")


# --- a legend follows the opening it names ----------------------------------
#
# Exercised synthetically because nothing in the library needs it today. The
# C40G looked like the case for it and turned out not to be: `PEM 1`/`PEM 2` are
# a legend COLUMN on common metal and Figure 1-2 prints them on an AC chassis
# too. The rule is still right - a legend for an opening that is not there is not
# printed either - and without a test it would be an unexercised path waiting to
# be wrong the first time somebody scopes a bay whose label names it.

import sys

sys.path.insert(0, str(SPEC / "tools/portrayal"))
import render  # noqa: E402


class _Lib:
    def resolve(self, ref):
        return ({"name": "blank", "size": {"w": 10.0, "h": 10.0},
                 "skins": ["default"]}, None)


def _device(only_in):
    return {
        "name": "scope-fixture",
        "manufacturer": "Fixture", "model": "Scope", "version": "0.1.0",
        "chassis": {"width": 100.0, "height": 50.0, "depth": 10.0},
        "views": {"front": {
            "size": {"w": 100.0, "h": 50.0},
            "silkscreen": [
                {"at": [5.0, 20.0], "text": "SLOT A", "for": "bay-a"},
                {"at": [5.0, 30.0], "text": "SLOT B", "for": "bay-b"},
                {"at": [5.0, 40.0], "text": "MODEL X"},
            ],
            "components": {"bays": [
                {"id": "bay-a", "at": [20.0, 10.0], "size": {"w": 20.0, "h": 20.0},
                 "accepts": ["x/blank@1"], "only-in": only_in},
                {"id": "bay-b", "at": [50.0, 10.0], "size": {"w": 20.0, "h": 20.0},
                 "accepts": ["x/blank@1"]},
            ]},
        }},
    }


def _printed(only_in, config_name):
    """The words actually PRINTED, not the whole document.

    The rendered SVG embeds the source manifest in `<metadata>`, so a substring
    search on the file finds every legend whether it was drawn or not - which is
    how the first version of this test passed a rule that was working and failed
    one that was too. Read the text nodes.
    """
    d = _device(only_in)
    out = render.render_view(d, "front", d["views"]["front"], _Lib(),
                             config_name=config_name, config={})
    root = render.ET.fromstring(out) if isinstance(out, str) else out
    for md in root.iter(f"{{{render.SVG_NS}}}metadata"):
        for child in list(md):
            md.remove(child)
        md.text = None
    return {(t.text or "").strip() for t in root.iter(f"{{{render.SVG_NS}}}text")}


def test_a_legend_whose_only_owner_is_scoped_out_is_not_printed():
    printed = _printed(["dc"], "ac")
    assert "SLOT A" not in printed, "printed a legend for an opening that is not there"
    assert "SLOT B" in printed, "dropped a legend whose bay is still present"
    assert "MODEL X" in printed, "dropped a legend that names no owner at all"


def test_the_same_legend_prints_where_its_opening_exists():
    printed = _printed(["dc"], "dc")
    assert {"SLOT A", "SLOT B", "MODEL X"} <= printed, printed
