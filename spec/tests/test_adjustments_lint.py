"""Adjustable positions, step 1: the keys and the rules that hold them.

docs/adjustable-positions-design.md sections 3 and 9. A device declares a part
that slides in `adjustments:`, and every placement, bay and decor entry that
slides with it says `moves-with`. Eleven rules, L173 to L183, hold what a
reader of the drawing would otherwise have to guess. Each is shown here on the
fixture device (spec/tests/fixtures/adjustments), with one edit that breaks it
as written and the finding that edit must raise.
"""
import json
import pathlib

import pytest
from jsonschema import Draft202012Validator

import adjustfixture as fx
from portrayal import adjustments as adj
from portrayal import lint

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "spec/schemas/device.schema.json").read_text())
AID = fx.AID


def broken(edit):
    doc = fx.device()
    edit(doc)
    return fx.findings(doc)


def only(found, code, *words):
    """`found` holds `code` and no other adjustment rule, and one of its
    messages has every one of `words`."""
    assert set(found) == {code}, found
    assert any(all(w in m for w in words) for m in found[code]), found[code]


# --- the fixture itself ---------------------------------------------------------------

def test_the_fixture_validates_and_lints_clean():
    """The whole of lint, not only the eleven rules: a fixture that another
    rule refuses would show the tests below nothing about a clean device."""
    assert fx.findings(fx.device()) == {}
    with lint.collecting() as got:
        lint.lint_device(fx.DEVICE, Draft202012Validator(SCHEMA), fx.ROOTS)
    assert got.errors == [] and got.warnings == []


def test_the_fixture_is_measured_and_not_skipped():
    """A rule that returns early passes every test above. The fixture states
    one adjustment with members on five views, and the rules walk them."""
    doc = fx.device()
    assert adj.members(doc) == {AID: [
        "bottom/decor/panel", "bottom/decor/rail", "front/placements/panel",
        "front/placements/rail", "left/decor/flange", "left/placements/stud",
        "right/decor/flange", "right/placements/stud", "top/decor/panel", "top/decor/rail"]}


# --- the schema -----------------------------------------------------------------------

def _schema_errors(edit):
    return broken(edit).get("L1") or []


@pytest.mark.parametrize("key", ["label", "carrier", "axis", "default", "datum"])
def test_an_adjustment_states_each_required_key(key):
    assert _schema_errors(lambda d: d["adjustments"][AID].pop(key))


def test_an_adjustment_states_a_range_or_stops():
    def edit(d):
        del d["adjustments"][AID]["range"], d["adjustments"][AID]["stops"]
    assert _schema_errors(edit)


@pytest.mark.parametrize("edit", [
    lambda d: d["adjustments"][AID].update(axis="w"),
    lambda d: d["adjustments"][AID].update(range=[20.0]),
    lambda d: d["adjustments"][AID].update(range=[20.0, 100.0, 180.0]),
    lambda d: d["adjustments"][AID].update(default=-1),
    lambda d: d["adjustments"][AID].update(stops={"Front": 20.0}),
    lambda d: d["adjustments"][AID].update(travel=5),
    lambda d: d["adjustments"].update({"Panel Setback": d["adjustments"][AID]}),
    lambda d: fx.decor(d, "top", "panel").pop("id"),
    lambda d: fx.placement(d, "front", "rail").update({"moves-with": ["a", "b"]}),
], ids=["axis", "short-range", "long-range", "negative", "stop-name", "unknown-key",
        "id-spelling", "decor-member-without-id", "two-adjustments"])
def test_the_schema_refuses(edit):
    assert _schema_errors(edit)


def test_every_new_key_has_a_description():
    props = SCHEMA["properties"]["adjustments"]
    assert len(props["description"]) > 80
    for key, spec in props["additionalProperties"]["properties"].items():
        assert len(spec.get("description", "")) > 40, key
    view = SCHEMA["properties"]["views"]["additionalProperties"]["properties"]
    comps = view["components"]["properties"]
    for where in (view["panel"]["properties"]["decor"], comps["placements"], comps["bays"]):
        assert len(where["items"]["properties"]["moves-with"]["description"]) > 40


# --- L173: an adjustment is well formed ------------------------------------------------

@pytest.mark.parametrize("edit, words", [
    (lambda a: a.update(range=[180.0, 20.0]), ["does not run"]),
    (lambda a: a.update(default=10.0), ["default 10", "outside the range"]),
    (lambda a: a["stops"].update(far=190.0), ["stop 'far'", "outside the range"]),
    (lambda a: a["stops"].update(centre=100.0), ["'middle' and 'centre'", "both at 100"]),
    (lambda a: a["stops"].update({"100": 100.0}), ["named with a number"]),
], ids=["reversed", "default-outside", "stop-outside", "two-stops-one-place", "numeric-name"])
def test_l173_refuses_a_malformed_adjustment(edit, words):
    found = broken(lambda d: edit(d["adjustments"][AID]))
    assert any(all(w in m for w in words) for m in found.get("L173", [])), found


def _stops_only(d, default=20.0, stops=None):
    a = d["adjustments"][AID]
    del a["range"]
    a["default"] = default
    a["stops"] = stops or {"front": 20.0, "middle": 100.0, "rear": 180.0}
    # the panel is drawn at 20 now: the well, and every view, would follow in a
    # real device. These tests read L173 alone.


def test_l173_asks_stops_alone_for_two_and_a_default_among_them():
    found = broken(lambda d: _stops_only(d, default=60.0))
    assert any("not one of the stops" in m for m in found.get("L173", [])), found
    found = broken(lambda d: _stops_only(d, stops={"front": 20.0}))
    assert any("is not a choice" in m for m in found.get("L173", [])), found
    found = broken(lambda d: _stops_only(d))
    assert "L173" not in found, found


# --- L174: the carrier ----------------------------------------------------------------

def test_l174_refuses_a_carrier_that_is_no_placement():
    # `flange` is decor on both side views and a placement on none
    only(broken(lambda d: d["adjustments"][AID].update(carrier="flange")),
         "L174", "'flange' is no placement")


def test_l174_refuses_a_carrier_that_is_not_a_member():
    def edit(d):
        d["adjustments"][AID]["carrier"] = "side-left"
    assert any("does not say `moves-with" in m for m in broken(edit).get("L174", []))


@pytest.mark.parametrize("key, value", [("only-in", ["base"]), ("optional", "extras")])
def test_l174_refuses_a_carrier_some_build_leaves_out(key, value):
    found = broken(lambda d: fx.placement(d, "front", "panel").update({key: value}))
    only(found, "L174", f"`{key}`")


# --- L175: membership resolves --------------------------------------------------------

def test_l175_refuses_a_moves_with_that_names_nothing():
    found = broken(lambda d: fx.decor(d, "top", "rail").update({"moves-with": "panel-setbak"}))
    only(found, "L175", "top/decor/rail", "names no adjustment", AID)


def test_l175_refuses_an_adjustment_nothing_moves_with():
    def edit(d):
        d["adjustments"]["lid"] = {"label": "Lid", "carrier": "panel", "axis": "y",
                                   "range": [0.0, 10.0], "default": 0.0, "datum": "the lid"}
        d["provenance"]["lid"] = {"confidence": "estimated", "note": "a test"}
    found = broken(edit)
    assert any("nothing says `moves-with: lid`" in m for m in found.get("L175", [])), found


def test_l175_refuses_a_member_on_a_view_that_is_not_a_face():
    def edit(d):
        d["views"]["inside"] = d["views"].pop("rear")
        d["views"]["inside"]["panel"]["decor"][0]["moves-with"] = AID
    found = broken(edit)
    assert any("inside/decor/panel-back" in m and "six" in m for m in found.get("L175", [])), found


def test_a_variant_view_is_the_face_it_stands_in_for():
    def edit(d):
        d["views"]["front-b"] = {**d["views"]["front"], "face": "front"}
    assert "L175" not in broken(edit)


# --- L176: what stands on a member moves with it ---------------------------------------

def test_l176_refuses_a_part_left_on_a_floor_that_moves():
    found = broken(lambda d: fx.placement(d, "front", "rail").pop("moves-with"))
    only(found, "L176", "front/placements/rail", "`in: panel`")


def test_l176_refuses_a_mated_part_left_behind():
    def edit(d):
        d["views"]["front"]["components"]["placements"].append(
            {"ref": "fixture/slide-stud@1", "id": "cap", "mate-to": "rail"})
    found = broken(edit)
    assert any("front/placements/cap" in m and "`mate-to: rail`" in m
               for m in found.get("L176", [])), found


def test_l176_refuses_a_bay_whose_plan_stands_in_a_member():
    def edit(d):
        # a well on the plan that moves, and a rear bay whose plan stands in it
        d["views"]["top"]["components"] = {"placements": [
            {"ref": "fixture/slide-well@1", "id": "tray", "at": [10.0, 100.0],
             "moves-with": AID}]}
        d["views"]["rear"]["components"] = {"bays": [
            {"id": "slot", "at": [10.0, 0.0], "size": {"w": 20.0, "h": 10.0},
             "interface": "test-card", "plan": {"view": "top", "at": [12.0, 102.0], "in": "tray"}}]}
    found = broken(edit)
    assert any("rear/bays/slot" in m and "its plan on top" in m for m in found.get("L176", [])), found


# --- L177: the default is the position drawn --------------------------------------------

def test_l177_refuses_a_default_the_well_is_not_drawn_at():
    found = broken(lambda d: d["adjustments"][AID].update(default=70.0))
    assert any("default 70" in m and "a well 60 deep" in m for m in found.get("L177", [])), found


def test_l177_reads_only_what_it_can_tell():
    """On another axis the depth of the front well says nothing of the default."""
    def edit(d):
        d["adjustments"][AID].update(axis="y", range=[0.0, 0.0001], default=0.0)
        d["adjustments"][AID].pop("stops")
    assert "L177" not in broken(edit)


# --- L178: a member stays inside the device ---------------------------------------------

def test_l178_refuses_a_range_that_carries_a_member_out_of_its_view():
    found = broken(lambda d: d["adjustments"][AID].update(
        range=[20.0, 199.0], stops={"front": 20.0}))
    # at 199 the panel's plate on the plan runs past the rear, y = 0
    assert any("top/decor/panel" in m and "= 199" in m and "outside the 120 x 200 view" in m
               for m in found.get("L178", [])), found


def test_l178_refuses_a_range_longer_than_the_device():
    found = broken(lambda d: d["adjustments"][AID].update(range=[20.0, 240.0]))
    assert any("beyond the 200 mm the device has along z" in m for m in found.get("L178", [])), found
    assert any("its floor is 240 behind the face" in m for m in found["L178"]), found


def test_l178_is_asked_at_both_ends():
    found = broken(lambda d: d["adjustments"][AID].update(
        range=[1.0, 180.0], stops={"rear": 180.0}))
    # at 1 the rail, 7.5 in front of the panel, is through the front of the plan
    assert any("top/decor/rail" in m and "= 1 " in m for m in found.get("L178", [])), found


# --- L179: no new collision ---------------------------------------------------------------

def _post(d, x):
    """A fixed post on the right side view, 6 wide from `x`: not a member."""
    d["views"]["right"]["components"]["placements"].append(
        {"ref": "fixture/slide-stud@1", "id": "post", "at": [x, 17.0], "group": "studs",
         "rel-pos": 9})
    fx.placement(d, "right", "side-right")["under"] = ["stud", "post"]


def test_l179_refuses_a_member_that_lands_on_a_part_that_stays():
    """The post stands clear of the stud at the default and under it at the
    rear stop, 180: the default hides the collision."""
    found = broken(lambda d: _post(d, 183.0))
    only(found, "L179", "at panel-setback = 180", "right: stud and post overlap")


def test_l179_reads_a_stop_between_the_ends():
    found = broken(lambda d: _post(d, 103.0))
    only(found, "L179", "at panel-setback = 100", "stud and post overlap")


def test_l179_refuses_a_cover_that_slides_off_what_it_covers():
    """The stud is drawn over the side plate. A plate too short to reach the
    rear end of the travel is no longer under it there."""
    def edit(d):
        fx.placement(d, "right", "side-right")["at"] = [-130.0, 0.0]
    found = broken(edit)
    assert any("stud no longer lies over side-right" in m and "= 180" in m
               for m in found.get("L179", [])), found


def test_l179_is_quiet_about_a_collision_the_default_already_has():
    """A fault at the default is L13's to report, once."""
    found = broken(lambda d: _post(d, 63.0))
    assert "L179" not in found, found


# --- L180: the id is free on the carrier ---------------------------------------------------

def _rename(d, new):
    d["adjustments"][new] = d["adjustments"].pop(AID)
    d["provenance"][new] = d["provenance"].pop(AID)
    for view in d["views"].values():
        for kind, item in adj._items(view):
            if item.get("moves-with") == AID:
                item["moves-with"] = new
    for cfg in d["configurations"].values():
        for vals in (cfg.get("component-attrs") or {}).values():
            if AID in vals:
                vals[new] = vals.pop(AID)
    d["attrs"] = {}


@pytest.mark.parametrize("name", ["depth", "path", "ref", "in", "under", "group"])
def test_l180_refuses_a_name_the_build_writes(name):
    only(broken(lambda d: _rename(d, name)), "L180", f"`data-{name}`", "the build")


def test_l180_reads_the_names_from_the_build():
    """Not a list kept here: every `data-` name render.py spells."""
    names = lint.build_data_names()
    assert {"depth", "path", "ref", "in", "under", "group", "z-lift"} <= names
    src = (ROOT / "spec/tools/portrayal/render.py").read_text()
    assert all(f'"data-{n}"' in src for n in names) and len(names) > 60


def test_l180_refuses_an_attr_of_the_carrier():
    def edit(d):
        _rename(d, "tier")
        fx.placement(d, "front", "panel")["attrs"] = {"tier": "upper"}
    only(broken(edit), "L180", "front/panel", "its attr `tier`")


# --- L181: a position a configuration sets ---------------------------------------------------

@pytest.mark.parametrize("value, sentence", [
    ("300", "panel-setback on SLIDER takes 20 to 180 mm. 300 is outside it."),
    ("back", "panel-setback on SLIDER takes a number in mm, or one of: front, middle, rear."),
    ("-20", "panel-setback on SLIDER takes a number in mm, or one of: front, middle, rear."),
])
def test_l181_refuses_a_value_that_is_not_a_position(value, sentence):
    def edit(d):
        d["configurations"]["back"]["component-attrs"]["panel"][AID] = value
    only(broken(edit), "L181", "configuration back", sentence)


# --- L182: provenance --------------------------------------------------------------------

def test_l182_asks_for_the_source_of_the_range():
    only(broken(lambda d: d["provenance"].pop(AID)), "L182", "provenance.panel-setback")


# --- L183: an attr that restates the adjustment ----------------------------------------------

@pytest.mark.parametrize("key, value, words", [
    ("slide-panel-setback-mm", 61, ["is 61", "the default of panel-setback is 60"]),
    ("slide-panel-setback-min-mm", 25, ["is 25", "the min of panel-setback is 20"]),
    ("slide-panel-setback-max-mm", 175.5, ["is 175.5", "the max of panel-setback is 180"]),
    ("slide-panel-setback-mm", "sixty", ["is not a number"]),
])
def test_l183_refuses_an_attr_that_disagrees(key, value, words):
    only(broken(lambda d: d["attrs"]["physical"].update({key: value})), "L183", *words)


def test_l183_pairs_an_attr_by_its_name_and_names_no_maker():
    """The pairing is the name: the id, with any words before it, then `-mm`,
    `-min-mm` or `-max-mm`. A key that does not end in the id is not paired."""
    flat = {"panel-setback-mm": 1, "slide-panel-setback-max-mm": 1, "x-panel-setback-min-mm": 1,
            "panel-setback": 1, "panel-setback-in": 1, "spanel-setback-mm": 1,
            "panel-setback-depth-mm": 1, "min-mm": 1}
    assert adj.restating_attrs("panel-setback", flat) == {
        "panel-setback-mm": "default", "slide-panel-setback-max-mm": "max",
        "x-panel-setback-min-mm": "min"}


def test_l183_says_stops_alone_have_no_end_to_restate():
    def edit(d):
        _stops_only(d, default=60.0, stops={"near": 60.0, "far": 180.0})
    found = broken(edit)
    msgs = found.get("L183", [])
    assert len(msgs) == 2 and all("has stops and no `range`" in m for m in msgs), found
    # the default is still restated, and still agrees
    assert not any("slide-panel-setback-mm:" in m for m in msgs)


def test_an_attr_is_not_required():
    assert "L183" not in broken(lambda d: d.update(attrs={}))


# --- one test for the table -------------------------------------------------------------------

def test_each_rule_has_a_fixture_that_fails_as_written():
    """The eleven codes, each raised somewhere above; this holds the list to
    the catalogue so a twelfth rule cannot arrive without its fixture."""
    src = pathlib.Path(__file__).read_text()
    for code in fx.CODES:
        assert code in lint.RULES and lint.RULES[code][0] == "device", code
        assert lint.RULES[code][4] == lint.ERROR
        assert f'"{code}"' in src, f"{code} has no failing fixture in this file"
