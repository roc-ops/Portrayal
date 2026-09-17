"""Configurable fields: a part declares what a form can change on it.

A different shape is a different part; a different property is a field on
the same one. The skin fills text from attrs (`data-from`); `fields` says
which keys exist, so the index can offer a form, a configuration can set a
bay's occupant, and the kit can rewrite the text live.
"""
import json
import pathlib
import re
import sys

import pytest
import yaml

SPEC = pathlib.Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"
from portrayal import lint
from portrayal import render


def _caught(code, fn, *a):
    with lint.collecting() as got:
        fn(*a)
    return [m for m in got.warnings + got.errors if f"[{code}]" in m]


def test_a_configuration_writes_on_the_part_in_one_bay():
    lib = render.Library([str(LIB)])
    view = {"size": {"w": 434.0, "h": 86.8}, "components": {"bays": [
        {"id": "psu-1", "at": [251.3, 46.2], "size": {"w": 86.3, "h": 39.1},
         "accepts": ["dell/psu-1100w-ac-14g@1"], "default": "dell/psu-1100w-ac-14g@1"},
        {"id": "psu-2", "at": [341.1, 46.2], "size": {"w": 86.3, "h": 39.1},
         "accepts": ["dell/psu-1100w-ac-14g@1"], "default": "dell/psu-1100w-ac-14g@1"}]}}
    d = {"name": "f", "manufacturer": "F", "model": "F", "version": "0.1.0",
         "chassis": {"width": 434.0, "height": 86.8, "depth": 700.0}, "views": {"rear": view}}
    out = render.render_view(d, "rear", view, lib, config={"bay-attrs": {"psu-1": {"watts": "750W"}}})
    svg = out if isinstance(out, str) else render.ET.tostring(out, encoding="unicode")
    one = svg[svg.index('id="psu-1--module"'):svg.index('id="psu-2--module"')]
    two = svg[svg.index('id="psu-2--module"'):]
    assert 'data-watts="750W"' in one and ">750W<" in one, "the value did not reach the badge"
    assert 'data-watts="750W"' not in two and ">1100W<" in two, "the other supply must keep its drawing"


def test_every_field_prints_and_every_print_is_a_field():
    """Across the library: the promise L73 keeps, on the real files."""
    for p in sorted(LIB.glob("components/*/*/v*/contract.yaml")):
        c = yaml.safe_load(p.read_text())
        if not c.get("fields"):
            continue
        assert not _caught("L73", lint.lint_component_fields, p, c), p


def test_lint_refuses_a_field_that_prints_nowhere(tmp_path):
    d = tmp_path / "x"; (d / "skins").mkdir(parents=True)
    (d / "skins" / "default.svg").write_text('<svg><text data-from="watts">1W</text><text data-from="ghost">?</text></svg>')
    p = d / "contract.yaml"
    hits = _caught("L73", lint.lint_component_fields, p, {"skins": ["default"], "fields": {"watts": {}, "speed": {}}})
    assert any("speed has no data-from, data-fill-from or data-stroke-from node" in h for h in hits), hits
    assert any("ghost" in h for h in hits), hits
    hits = _caught("L73", lint.lint_component_fields, p, {"skins": ["default"], "fields": {"watts": {"type": "choice"}}})
    assert any("no options" in h for h in hits), hits


def test_the_index_offers_the_form():
    idx = LIB / "dist" / "components.json"
    if not idx.exists():
        pytest.skip("dist not built")
    comps = json.loads(idx.read_text())["components"]
    psu = next(c for c in comps if c["name"] == "psu-1100w-ac-14g")
    assert psu["fields"]["watts"]["default"] == "1100W"
    dimm = next(c for c in comps if c["name"] == "dimm-plan")
    assert set(dimm["fields"]) == {"capacity", "speed"}


def test_a_lamp_with_states_reads_the_variable(tmp_path):
    """L74: the R740xd control panel declared amber faults on lamps painted
    with literal colours, so nothing could ever light them."""
    d = tmp_path / "x"; (d / "skins").mkdir(parents=True)
    (d / "skins" / "default.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><rect id="lamp-a" fill="#123456"/>'
        '<g id="lamp-b" stroke="var(--led-color, #8b9299)"><path d="M0 0"/></g></svg>')
    c = {"skins": ["default"], "elements": {
        "lamp-a": {"class": "led", "states": ["off", {"name": "fault", "color": "#eab308"}]},
        "lamp-b": {"class": "led", "states": ["off", {"name": "fault", "color": "#eab308"}]}}}
    hits = _caught("L74", lint.lint_component_lamp_colour, d / "contract.yaml", c)
    assert len(hits) == 1 and "lamp-a" in hits[0], hits


def test_every_lit_lamp_in_the_library_reads_the_variable():
    for p in sorted(LIB.glob("components/*/*/v*/contract.yaml")):
        c = yaml.safe_load(p.read_text())
        assert not _caught("L74", lint.lint_component_lamp_colour, p, c), p


def test_every_riser_slot_says_what_it_is():
    """A card feature reads `slot:`: connector, lanes, height, length. Every
    wired slot on every R740xd riser carries it, agreeing with its prose."""
    wired = 0
    for p in sorted(LIB.glob("components/dell/riser-[123][a-f]-14g/v1/contract.yaml")):
        c = yaml.safe_load(p.read_text())
        for bid, b in c["bays"].items():
            prose = c["attrs"].get(bid, "")
            if prose.startswith("no connector"):
                assert "slot" not in b, (p, bid, "a blanked opening is not a slot")
                continue
            assert "slot" in b, (p, bid)
            wired += 1
        assert not _caught("L75", lint.lint_component_slots, p, c), p
    assert wired == 26, wired


def test_lint_holds_a_slot_to_its_prose_and_its_connector():
    c = {"attrs": {"slot-1": "x8, full height, full length, processor 1"},
         "bays": {"slot-1": {"at": [0, 0], "size": [1, 1], "accepts": ["x/y@1"],
                             "slot": {"connector": "x16", "lanes": 16, "height": "full", "length": "full", "processor": 1}}}}
    hits = _caught("L75", lint.lint_component_slots, pathlib.Path("x.yaml"), c)
    assert hits and "attr reads" in hits[0], hits
    c["bays"]["slot-1"]["slot"] = {"connector": "x8", "lanes": 16, "height": "full", "length": "full", "processor": 1}
    hits = _caught("L75", lint.lint_component_slots, pathlib.Path("x.yaml"), c)
    assert any("16 lanes on an x8" in h for h in hits), hits


# A SHELL IS A PROPERTY, NOT A SHAPE. The RJ45 family is one drawing whose
# shield is bright metal on some boxes and black plastic on others, so the
# finish is a field like a DIMM's capacity - `data-fill-from` sets a fill the
# way `data-from` sets text. These pin the mechanism, the default and the one
# device measured dark, because a silent regression here repaints 758 jacks.

RJ45_FAMILY = ["std/rj45@2", "std/rj45-ganged@2",
               "common/rj45-eth@1", "common/rj45-ganged-eth@1"]


def _skin_of(ref):
    ns, major = ref.rsplit("@", 1)
    return (LIB / "components" / ns / f"v{major}" / "skins" / "default.svg").read_text()


def _contract_of(ref):
    ns, major = ref.rsplit("@", 1)
    return yaml.safe_load(
        (LIB / "components" / ns / f"v{major}" / "contract.yaml").read_text())


@pytest.mark.parametrize("ref", RJ45_FAMILY)
def test_every_rj45_shell_is_painted_from_its_finish_field(ref):
    """The shell reads the attr, declares the field, and still draws alone."""
    skin, contract = _skin_of(ref), _contract_of(ref)
    assert 'data-fill-from="finish"' in skin
    assert contract["fields"]["finish"]["default"] == "#b0b5bb"
    # the node keeps a literal fill, so the skin is a valid standalone drawing
    assert re.search(r'fill="#b0b5bb" data-fill-from="finish"', skin)


def test_the_finish_attr_repaints_the_shell_and_absence_leaves_the_default():
    root = render.ET.fromstring(
        '<g xmlns="http://www.w3.org/2000/svg">'
        '<path id="housing" fill="#b0b5bb" data-fill-from="finish"/></g>')
    render.fill_from_attrs(root, {})
    assert root[0].get("fill") == "#b0b5bb", "no attr leaves the drawn default"
    render.fill_from_attrs(root, {"finish": "#2b2f33"})
    assert root[0].get("fill") == "#2b2f33"


def test_an_empty_finish_does_not_delete_the_housing():
    """For text an empty attr deletes the node; a shape with no fill is not a
    quieter drawing, it is an invisible one."""
    root = render.ET.fromstring(
        '<g xmlns="http://www.w3.org/2000/svg">'
        '<path id="housing" fill="#b0b5bb" data-fill-from="finish"/></g>')
    render.fill_from_attrs(root, {"finish": ""})
    assert len(root) == 1 and root[0].get("fill") == "#b0b5bb"


def test_the_s8901_jacks_carry_the_black_finish_they_were_measured_at():
    """Its shells read 46 and 39 against the S9701-82DC's 183-185, and the
    zoomed render shows black plastic in a white bezel plate."""
    d = yaml.safe_load((LIB / "devices/ufispace/s8901-54xc/device.yaml").read_text())
    got = {p["id"]: (p.get("attrs") or {}).get("finish")
           for p in d["views"]["front"]["components"]["placements"]
           if p["id"] in ("mgmt", "console")}
    assert got == {"mgmt": "#2b2f33", "console": "#2b2f33"}


def test_a_field_wired_by_fill_satisfies_l73(tmp_path):
    """L73 asks whether the drawing is wired to the field, not which attribute
    carries it - so a fill-painted node keeps the promise a text node does."""
    (tmp_path / "skins").mkdir()
    (tmp_path / "skins" / "default.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg"><path data-fill-from="finish"/></svg>')
    data = {"format": 1, "kind": "component", "name": "x", "version": "1.0.0",
            "class": "port", "size": {"w": 1.0, "h": 1.0},
            "fields": {"finish": {"label": "Shell finish", "type": "text",
                                  "default": "#b0b5bb"}}}
    assert _caught("L73", lint.lint_component_fields,
                   tmp_path / "contract.yaml", data) == []
