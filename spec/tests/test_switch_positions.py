"""Switch positions: a choice field moves or shows a node (docs/switch-positions-design.md).

A position is a `choice` field. A skin node carries `data-move-from` with a
`data-move` table (an option, a translation in mm and optionally a turn about
the node's centre) or `data-show-from` with the options it is shown for. With
the field unset the skin draws the default. render.py's fill_from_attrs and
kit/fields.js paintFields apply the same two rules; the parity test below holds
them to one answer on one list of cases. These run against the real library
and device copies rendered here, never a possibly stale dist.
"""
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
import yaml

import warmrender
from portrayal import lint
from portrayal.manifest import parse_moves
from portrayal.render import check_positions, fill_from_attrs

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
RENDER = ROOT / "spec/tools/portrayal/render.py"
SCRIPT = ROOT / "spec/tests/js/switch-positions.mjs"
DIP = "common/dip-switch-2@1"
SVG = "http://www.w3.org/2000/svg"

PART = f'''<svg xmlns="{SVG}">
  <rect id="slider" x="1.1" y="6" width="2" height="2.8" data-move-from="sw-1" data-move="on: 0 -3.2"/>
  <rect id="drawn-moved" x="0" y="0" width="1" height="1" transform="translate(1 1)"
        data-move-from="sw-1" data-move="on: 0.5 0"/>
  <rect id="rocker" x="0" y="0" width="4" height="2" data-move-from="sw-1" data-move="on: 0 0 180"/>
  <rect id="placed-rocker" x="0" y="0" width="4" height="2" transform="translate(10 0)"
        data-move-from="sw-1" data-move="on: 1 0 180"/>
  <rect id="flag-on" x="0" y="0" width="1" height="1" data-show-from="state" data-show="on"/>
  <rect id="flag-off" x="0" y="0" width="1" height="1" display="none" data-show-from="state" data-show="off tripped"/>
  <text id="label" data-from="note" data-show-from="state" data-show="tripped" display="none">x</text>
</svg>'''
IDS = ("slider", "drawn-moved", "rocker", "placed-rocker", "flag-on", "flag-off", "label")

# One list, fed to the build and to the kit.
# A text node a position shows is shown by that field alone: writing its text
# (`note`) must not un-hide it, which the kit's data-from rule otherwise does.
CASES = [{}, {"sw-1": "on"}, {"sw-1": "off"}, {"sw-1": ""}, {"sw-1": " on "},
         {"state": "on"}, {"state": "off"}, {"state": "tripped"}, {"state": ""},
         {"sw-1": "on", "state": "tripped"}, {"note": "hello"}, {"note": "hello", "state": "on"},
         {"state": "tripped", "note": "hello"}]


def build_snap(vals):
    root = ET.fromstring(PART)
    fill_from_attrs(root, vals)
    by = {e.get("id"): e for e in root.iter()}
    return {i: {"transform": by[i].get("transform"), "display": by[i].get("display")} for i in IDS}


# --- the build ------------------------------------------------------------------------

def test_a_set_option_moves_its_node_and_the_default_draws_as_is():
    assert build_snap({})["slider"]["transform"] is None
    assert build_snap({"sw-1": "on"})["slider"]["transform"] == "translate(0 -3.2)"
    assert build_snap({"sw-1": "off"})["slider"]["transform"] is None


def test_a_move_goes_in_front_of_the_transform_the_node_was_drawn_with():
    assert build_snap({"sw-1": "on"})["drawn-moved"]["transform"] == "translate(0.5 0) translate(1 1)"
    assert build_snap({})["drawn-moved"]["transform"] == "translate(1 1)"


def test_a_turn_pivots_on_the_node_centre():
    assert build_snap({"sw-1": "on"})["rocker"]["transform"] == "rotate(180 2 1)"


def test_a_turn_on_a_drawn_offset_node_stays_in_place():
    """The turn runs first, in the node's own frame, then the drawn offset,
    then the move: a rocker drawn at x 10..14 turns in place and moves 1."""
    assert build_snap({"sw-1": "on"})["placed-rocker"]["transform"] == \
        "translate(1 0) translate(10 0) rotate(180 2 1)"


def test_show_follows_the_field_and_unset_leaves_the_drawing():
    assert build_snap({})["flag-on"]["display"] is None and build_snap({})["flag-off"]["display"] == "none"
    s = build_snap({"state": "tripped"})
    assert s["flag-on"]["display"] == "none" and s["flag-off"]["display"] is None
    assert s["label"]["display"] is None


def test_the_table_parses_and_a_bad_entry_is_loud():
    assert parse_moves("on: 0 -3.2, off: 1 2 90") == {"on": (0.0, -3.2, 0.0), "off": (1.0, 2.0, 90.0)}
    with pytest.raises(ValueError):
        parse_moves("on: up")


def test_an_unquoted_on_or_off_fails_the_build():
    """YAML 1.1 reads `sw-1: on` as True. Taken as unset it would draw the
    default and look set; the build says to quote it."""
    root = ET.fromstring(PART)
    contract = {"name": "dip", "fields": {"sw-1": {"type": "choice", "options": ["off", "on"]}}}
    for v, word in ((True, "'on'"), (False, "'off'")):
        with pytest.raises(ValueError, match=f"quote it: {word}"):
            check_positions(root, {"sw-1": v}, contract, "dip")


def test_an_option_the_field_does_not_declare_fails_the_build():
    root = ET.fromstring(PART)
    contract = {"name": "dip", "fields": {"sw-1": {"type": "choice", "options": ["off", "on"]},
                                          "state": {"type": "choice", "options": ["on", "off", "tripped"]}}}
    check_positions(root, {"sw-1": "on"}, contract, "dip")
    with pytest.raises(ValueError, match="up.*is not a position"):
        check_positions(root, {"sw-1": "up"}, contract, "dip")


# --- the kit agrees -------------------------------------------------------------------

@pytest.fixture(scope="module")
def kit():
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    p = subprocess.run(["node", str(SCRIPT), json.dumps(CASES)], capture_output=True, text=True,
                       cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_the_kit_agrees_on_every_case(kit):
    assert len(kit["cases"]) == len(CASES)
    for vals, got in zip(CASES, kit["cases"]):
        assert got == build_snap(vals), vals


def test_unpaint_puts_every_position_back(kit):
    assert kit["painted"]["slider"]["transform"] == "translate(0 -3.2)"
    assert kit["unpainted"] == build_snap({})
    assert kit["stashLeft"] is False


def test_setting_the_default_after_a_move_draws_as_drawn(kit):
    assert kit["backToDefault"] == build_snap({})


def test_the_build_records_what_a_moved_node_was_drawn_with():
    root = ET.fromstring(PART)
    fill_from_attrs(root, {"sw-1": "on"})
    by = {e.get("id"): e for e in root.iter()}
    assert by["slider"].get("data-move-base") == ""
    assert by["drawn-moved"].get("data-move-base") == "translate(1 1)"
    root = ET.fromstring(PART)
    fill_from_attrs(root, {})
    assert all(e.get("data-move-base") is None for e in root.iter())


def test_the_kit_moves_a_built_position_back_to_the_default(kit):
    """A configuration set the switch on, so the build moved it. Setting it
    off at runtime puts it where the skin drew it; clearing the field leaves
    it as built, and so does unpaint."""
    assert kit["builtOff"] == [None, "translate(1 1)"]
    assert kit["builtUnpainted"] == ["translate(0 -3.2)", "translate(0.5 0) translate(1 1)"]
    assert kit["builtEmpty"] == ["translate(0 -3.2)", "translate(0.5 0) translate(1 1)"]
    assert kit["builtOn"] == ["translate(0 -3.2)", "translate(0.5 0) translate(1 1)"]


def test_a_number_that_is_not_one_is_refused_in_both_halves(kit):
    """'.' and '1.2.3' match the entry pattern; neither half may draw NaN (#874)."""
    for s in ("on: . 0", "on: 1.2.3 0", "on: 0 0 ."):
        with pytest.raises(ValueError, match="is not 'option: dx dy"):
            parse_moves(s)
    assert kit["badNumber"] == ["threw", "threw", "threw"]


def test_a_part_says_which_fields_are_positions_before_a_hidden_node_goes(kit):
    """The viewer rebuilds when a changed field moves or shows a node, reading
    the face text - from which a hidden SHOW node has been removed. A part whose
    only SHOW node starts hidden must still say so, on its own group (#874)."""
    assert kit["marks"] == {"brk": "state", "dip": "sw-1 sw-2", "plain": None}
    assert kit["flagGone"] is True


def test_the_kit_reads_the_table_alike(kit):
    assert kit["parse"] == {"on": [0, -3.2, 0], "off": [1, 2, 90]}
    assert kit["badParse"] == "threw"


# --- the first user, seated on a real device ------------------------------------------

def _render(tmp, device, edit):
    name = device.split("/")[1]
    dev = tmp / name / "device.yaml"
    shutil.copytree(LIB / "devices" / device, dev.parent)
    d = yaml.safe_load(dev.read_text())
    edit(d)
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    o = tmp / name / "o"
    r = warmrender.run([sys.executable, str(RENDER), str(dev), "--library", str(LIB), "--out", str(o)],
                       capture_output=True, text=True)
    return name, o, r


def _set_dip(value):
    def edit(d):
        for p in d["views"]["front"]["components"]["placements"]:
            if p["id"] == "dip":
                p["attrs"] = {**(p.get("attrs") or {}), "sw-1": value}
    return edit


def test_a_placement_sets_switch_1_on_and_the_slider_moves(tmp_path):
    name, o, r = _render(tmp_path, "aurcore/ais4001p", _set_dip("on"))
    assert r.returncode == 0, r.stderr[-800:]
    svg = (o / f"{name}.front.svg").read_text()
    root = ET.fromstring(svg)
    by = {e.get("id"): e for e in root.iter() if e.get("id")}
    assert by["dip--slider-1"].get("transform") == "translate(0 -3.2)"
    assert by["dip--slider-2"].get("transform") is None
    # THE ELEMENT BOX FOLLOWS the move: the two sliders were drawn side by side,
    # 2.8 apart across the part and level along it; switch 1 is now 3.2 further
    # along the slot. The part is turned 90 on this face, so measure both axes.
    els = json.loads((o / f"{name}.front.elements.json").read_text())
    rows = {e["id"]: e["box"] for e in els.get("elements") or els.get("components") or []
            if isinstance(e, dict) and e.get("id") in ("dip--slider-1", "dip--slider-2")}
    assert set(rows) == {"dip--slider-1", "dip--slider-2"}, sorted(rows)
    c1 = (rows["dip--slider-1"]["x"] + rows["dip--slider-1"]["w"] / 2, rows["dip--slider-1"]["y"] + rows["dip--slider-1"]["h"] / 2)
    c2 = (rows["dip--slider-2"]["x"] + rows["dip--slider-2"]["w"] / 2, rows["dip--slider-2"]["y"] + rows["dip--slider-2"]["h"] / 2)
    d = sorted([abs(c1[0] - c2[0]), abs(c1[1] - c2[1])])
    assert d == pytest.approx([2.8, 3.2], abs=0.01), d


def test_an_undeclared_option_fails_the_render(tmp_path):
    _name, _o, r = _render(tmp_path, "aurcore/ais4001p", _set_dip("up"))
    assert r.returncode != 0
    assert "is not a position" in r.stderr


def test_an_unquoted_on_fails_the_render(tmp_path):
    _name, _o, r = _render(tmp_path, "aurcore/ais4001p", _set_dip(True))
    assert r.returncode != 0
    assert "quote it: 'on'" in r.stderr


def test_the_ten_placements_draw_as_before():
    """The default is the drawn position, so nothing that places the part moves."""
    for dev in sorted(LIB.glob("devices/aurcore/*/device.yaml")):
        d = yaml.safe_load(dev.read_text())
        for v in (d.get("views") or {}).values():
            for p in ((v or {}).get("components") or {}).get("placements") or []:
                if p.get("ref") == DIP:
                    assert not {"sw-1", "sw-2"} & set(p.get("attrs") or {}), (dev, p["id"])


# --- lint -------------------------------------------------------------------------------

def _caught(code, fn, *a):
    with lint.collecting() as got:
        fn(*a)
    return [m for m in got.warnings + got.errors if f"[{code}]" in m]


def _component(tmp_path, svg, fields, size=(7.0, 10.0)):
    (tmp_path / "skins").mkdir(exist_ok=True)
    (tmp_path / "skins" / "default.svg").write_text(svg)
    return tmp_path / "contract.yaml", {"skins": ["default"], "fields": fields,
                                        "size": {"w": size[0], "h": size[1]}}


SW = {"sw-1": {"type": "choice", "options": ["off", "on"], "default": "off"}}


def test_the_dip_switch_lints_clean():
    p = LIB / "components/common/dip-switch-2/v1/contract.yaml"
    c = yaml.safe_load(p.read_text())
    for code in ("L73", "L148", "L149"):
        assert not _caught(code, lint.lint_component_fields, p, c), code


def test_l148_refuses_an_option_the_field_lacks(tmp_path):
    p, c = _component(tmp_path, f'<svg xmlns="{SVG}"><rect id="s" x="1" y="6" width="2" height="2" '
                                'data-move-from="sw-1" data-move="up: 0 -3"/></svg>', SW)
    hits = _caught("L148", lint.lint_component_fields, p, c)
    assert any("'up'" in h for h in hits), hits


def test_l148_refuses_a_position_on_a_field_that_is_not_a_choice(tmp_path):
    p, c = _component(tmp_path, f'<svg xmlns="{SVG}"><rect id="s" x="1" y="6" width="2" height="2" '
                                'data-show-from="sw-1" data-show="on"/></svg>',
                      {"sw-1": {"type": "text"}})
    assert _caught("L148", lint.lint_component_fields, p, c)


def test_l148_refuses_an_unreadable_table(tmp_path):
    p, c = _component(tmp_path, f'<svg xmlns="{SVG}"><rect id="s" x="1" y="6" width="2" height="2" '
                                'data-move-from="sw-1" data-move="on: far"/></svg>', SW)
    assert _caught("L148", lint.lint_component_fields, p, c)


def test_l149_refuses_a_move_off_the_part(tmp_path):
    p, c = _component(tmp_path, f'<svg xmlns="{SVG}"><rect id="s" x="1" y="6" width="2" height="2" '
                                'data-move-from="sw-1" data-move="on: 0 -7"/></svg>', SW)
    hits = _caught("L149", lint.lint_component_fields, p, c)
    assert any("outside the part" in h for h in hits), hits
    p, c = _component(tmp_path, f'<svg xmlns="{SVG}"><rect id="s" x="1" y="6" width="2" height="2" '
                                'data-move-from="sw-1" data-move="on: 0 -3"/></svg>', SW)
    assert not _caught("L149", lint.lint_component_fields, p, c)


STATE = {"state": {"type": "choice", "options": ["on", "off", "tripped"], "default": "on"}}
FLAGS = (f'<svg xmlns="{SVG}"><rect id="f1" x="1" y="1" width="2" height="2" data-show-from="state" '
         'data-show="off"/><rect id="f2" x="1" y="1" width="2" height="2" display="none" '
         'data-show-from="state" data-show="tripped"/></svg>')


def test_l148_asks_every_show_option_to_show_something(tmp_path):
    """`on` shows no node and the field does not say it is drawn by absence."""
    p, c = _component(tmp_path, FLAGS, STATE)
    hits = _caught("L148", lint.lint_component_fields, p, c)
    assert any("no node is shown for state=on" in h for h in hits), hits


def test_l148_accepts_an_option_drawn_by_absence(tmp_path):
    fields = {"state": {**STATE["state"], "drawn-by-absence": ["on"]}}
    p, c = _component(tmp_path, FLAGS, fields)
    assert not _caught("L148", lint.lint_component_fields, p, c)


def test_l148_refuses_an_absence_that_is_not_an_option(tmp_path):
    fields = {"state": {**STATE["state"], "drawn-by-absence": ["on", "unknown"]}}
    p, c = _component(tmp_path, FLAGS, fields)
    hits = _caught("L148", lint.lint_component_fields, p, c)
    assert any("'unknown'" in h for h in hits), hits


def test_l73_counts_a_position_as_wiring(tmp_path):
    p, c = _component(tmp_path, f'<svg xmlns="{SVG}"><rect id="s" x="1" y="6" width="2" height="2" '
                                'data-move-from="sw-1" data-move="on: 0 -3"/></svg>', SW)
    assert not _caught("L73", lint.lint_component_fields, p, c)


def test_a_placement_may_say_what_a_position_means():
    schema = json.loads((ROOT / "spec/schemas/device.schema.json").read_text())
    pl = (schema["properties"]["views"]["additionalProperties"]["properties"]["components"]
          ["properties"]["placements"]["items"]["properties"])
    assert pl["positions"]["additionalProperties"]["additionalProperties"] == {"type": "string"}


# --- the 300CB08 family's alarm DIPs -----------------------------------------------------

ALARM = "amphenol-ns/alarm-dip-8@1"
PANELS = sorted(p.parent.name for p in (LIB / "devices/amphenol-ns").glob("*/device.yaml")
                if ALARM in p.read_text())


def test_the_alarm_dip_lints_clean():
    p = LIB / "components/amphenol-ns/alarm-dip-8/v1/contract.yaml"
    c = yaml.safe_load(p.read_text())
    assert set(c["fields"]) == {f"sw-{i}" for i in range(1, 9)}
    assert all(f["options"] == ["up", "down"] and f["default"] == "up" for f in c["fields"].values())
    for code in ("L73", "L148", "L149"):
        assert not _caught(code, lint.lint_component_fields, p, c), code


def test_every_panel_says_what_its_switches_mean_and_its_examples_set_them():
    """Eleven panels place the part. Each states a meaning for every switch of
    both blocks, the nrgILS its own, and every example configuration sets the
    switch of each fitted breaker position down - the guide's rule."""
    assert len(PANELS) == 11, PANELS
    for name in PANELS:
        d = yaml.safe_load((LIB / "devices/amphenol-ns" / name / "device.yaml").read_text())
        dips = {p["id"]: p for v in d["views"].values()
                for p in ((v or {}).get("components") or {}).get("placements") or [] if p.get("ref") == ALARM}
        assert set(dips) == {"dip-a", "dip-b"}, name
        for pid, p in dips.items():
            assert set(p["positions"]) == {f"sw-{i}" for i in range(1, 9)}, (name, pid)
            words = p["positions"]["sw-3"]["up"]
            assert ("software" in words) == name.startswith("nrgils"), (name, words)
        for cfg, c in d["configurations"].items():
            fitted = {k for k, v in (c.get("bays") or {}).items() if v and "blank" not in v}
            want = {}
            for side in "ab":
                sw = {f"sw-{i}": "down" for i in range(1, 9) if f"breaker-{side}{i}" in fitted}
                if sw:
                    want[f"dip-{side}"] = sw
            assert (c.get("component-attrs") or {}) == want, (name, cfg)


def test_a_populated_panel_draws_its_switches_down(tmp_path):
    name, o, r = _render(tmp_path, "amphenol-ns/300cb08", lambda d: None)
    assert r.returncode == 0, r.stderr[-800:]
    for cfg, want in (("base", None), ("populated", "translate(0 1.5)"), ("with-fuses", "translate(0 1.5)")):
        f = o / (f"{name}.front.svg" if cfg == "base" else f"{name}.{cfg}.front.svg")
        root = ET.parse(f).getroot()
        got = [e.get("transform") for e in root.iter()
               if (e.get("id") or "").startswith(("dip-a--slider-", "dip-b--slider-"))]
        assert len(got) == 16 and set(got) == {want}, (cfg, got)
        dip = next(e for e in root.iter() if e.get("id") == "dip-a")
        assert json.loads(dip.get("data-positions"))["sw-1"]["down"] == "alarm enabled for breaker position A1"
