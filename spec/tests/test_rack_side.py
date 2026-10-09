"""Vertical cable managers: the `rack-side` mount and `side` placements.

docs/vertical-cable-managers-design.md. A full-height vertical manager (the FS
CMV-SFD45U5W) bolts to the SIDE of a rack's upright and stands beside the
rack, outside the rails: `chassis.mount: rack-side`. It states the rack units
it runs beside and occupies none, it is drawn standing (its front is portrait,
L152), and a lab places it on a `side` of the rack from a bottom `ru` (L153,
L154). A rack-face part narrower than the opening (the 5U CMV-5U3W bracket on
one rail) may also say which `side` it bolts to, and then claims its rack unit
per face AND side (L142), so a bracket on each rail shares a unit.

Each check has a lab or a device that fails it, so a check that stops firing
fails here rather than passing quietly.
"""
import copy
import json
import pathlib
import sys

import pytest
import yaml

from portrayal import dcim_export as dx
from portrayal import labs, labs_index, lint

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DUCT = LIB / "devices/fs/cmv-sfd45u5w/device.yaml"
BRACKET = LIB / "devices/fs/cmv-5u3w/device.yaml"


# --- the mount ----------------------------------------------------------------

def test_the_schema_allows_rack_side():
    def enum(node):
        if isinstance(node, dict):
            m = node.get("mount")
            if isinstance(m, dict) and "enum" in m:
                return m["enum"]
            return next((e for e in map(enum, node.values()) if e), None)
        return None
    schema = json.loads((ROOT / "spec/schemas/device.schema.json").read_text())
    assert "rack-side" in (enum(schema) or [])


def test_a_rack_side_part_exports_no_rack_units_and_says_where_it_mounts():
    ch = {"mount": "rack-side", "ru": 45}
    assert dx.u_height(ch) == 0.0
    assert dx.is_full_depth(ch) is False
    body = dx.comments_for({"chassis": ch}, "base", {})
    assert "Mounts on the side of a rack's upright, beside the rack; occupies no rack unit." in body


def _l125(ch):
    with lint.collecting() as found:
        lint.lint_device_mount("device.yaml", {"chassis": ch})
    return [m for m in found.errors + found.warnings if "[L125]" in m]


def test_L125_a_rack_side_part_states_its_rack_units():
    with lint.collecting() as found:
        lint.lint_device_mount("device.yaml", {"chassis": {"mount": "rack-side"}})
    assert [m for m in found.warnings if "[L125]" in m and "rack-side" in m]
    assert not found.errors
    assert not _l125({"mount": "rack-side", "ru": 45})


@pytest.mark.parametrize("key,value", [
    ("full-depth", False), ("overhang", {"left": 10}), ("ears", "behind")])
def test_L125_rack_only_keys_stay_rack_only(key, value):
    with lint.collecting() as found:
        lint.lint_device_mount("device.yaml", {"chassis": {"mount": "rack-side", "ru": 45, key: value}})
    assert any("[L125]" in m and key in m for m in found.errors)


def _l152(doc):
    with lint.collecting() as found:
        lint.lint_rack_side_portrait("device.yaml", doc)
    return [m for m in found.warnings if "[L152]" in m]


def test_L152_a_rack_side_part_is_drawn_standing():
    standing = {"chassis": {"mount": "rack-side", "width": 138.8, "height": 2108.0},
                "views": {"front": {"size": {"w": 138.8, "h": 2108.0}}}}
    lying = copy.deepcopy(standing)
    lying["views"]["front"]["size"] = {"w": 2108.0, "h": 138.8}
    assert not _l152(standing)
    assert _l152(lying)
    # only a rack-side part: a horizontal manager is landscape by nature
    assert not _l152({"chassis": {"mount": "rack-face", "width": 483, "height": 44},
                      "views": {"front": {"size": {"w": 483, "h": 44}}}})


def test_the_library_duct_is_rack_side_and_standing():
    d = yaml.safe_load(DUCT.read_text())
    ch = d["chassis"]
    assert (ch["mount"], ch["ru"]) == ("rack-side", 45)
    assert not _l152(d)
    assert d["views"]["front"]["size"]["h"] > d["views"]["front"]["size"]["w"]
    guide = d["views"]["front"]["guides"][0]
    assert (guide["kind"], guide["run"]) == ("duct", "y")


@pytest.mark.parametrize("tree", ["netbox", "nautobot"])
@pytest.mark.parametrize("model", ["CMV-SFD45U5W", "CMV-5U3W"])
def test_the_exports_take_no_rack_unit(tree, model):
    doc = yaml.safe_load((LIB / "exports" / tree / "device-types" / "FS.com" / f"{model}.yaml").read_text())
    assert doc["u_height"] == 0.0
    assert doc["is_full_depth"] is False


# --- lab placement ------------------------------------------------------------

# fhd-1ufce is a 1U fibre enclosure, cmv-sfd45u5w the 45U side duct, cmv-5u3w
# the 26 mm wide 5U rail bracket, fhd-cmp5dr the 483 mm wide rack-face manager.
GOOD = {
    "format": 1, "kind": "lab", "name": "vertical-managers",
    "rack": {"height-ru": 45},
    "devices": [
        {"id": "enc", "ref": "fhd-1ufce", "ru": 20},
        {"id": "duct-l", "ref": "cmv-sfd45u5w", "side": "left"},
        {"id": "duct-r", "ref": "cmv-sfd45u5w", "side": "right", "ru": 1, "face": "front"},
        {"id": "bkt-l", "ref": "cmv-5u3w", "ru": 10, "side": "left"},
        {"id": "bkt-r", "ref": "cmv-5u3w", "ru": 10, "side": "right"},
        {"id": "bkt-on", "ref": "cmv-5u3w", "on": "enc", "side": "left"},
    ],
    "links": [],
}


def lab(**changes):
    d = copy.deepcopy(GOOD)
    by_id = {p["id"]: i for i, p in enumerate(d["devices"])}
    for pid, p in changes.items():
        pid = pid.replace("_", "-")
        if pid in by_id:
            d["devices"][by_id[pid]] = p
        else:
            d["devices"].append(p)
    d["devices"] = [p for p in d["devices"] if p is not None]
    return d


def run(d):
    found, placed = labs.check(d, [LIB])
    return found, {p["id"]: p for p in placed}


def codes(d):
    return [c for c, sev, _ in run(d)[0] if sev == "error"]


def test_the_good_lab_validates_and_raises_nothing():
    assert labs.schema_errors(GOOD) == []
    assert run(GOOD)[0] == []


def test_positions_are_resolved_with_their_side():
    _, p = run(GOOD)
    # a rack-side part: its bottom unit defaults to 1, its face to front
    assert {k: p["duct-l"][k] for k in ("ru", "face", "side", "mount", "host")} == \
        {"ru": 1, "face": "front", "side": "left", "mount": "rack-side", "host": None}
    assert p["duct-r"]["side"] == "right"
    # a bracket on each rail of one unit and face: both stand
    assert (p["bkt-l"]["ru"], p["bkt-l"]["side"], p["bkt-r"]["side"]) == (10, "left", "right")
    assert (p["bkt-on"]["ru"], p["bkt-on"]["host"], p["bkt-on"]["side"]) == (20, "enc", "left")
    # a placement with no side resolves to None
    assert p["enc"]["side"] is None


FAILING = {
    "L153 a rack-side part with no side":
        ("L153", lab(duct_l={"id": "duct-l", "ref": "cmv-sfd45u5w"})),
    "L153 a rack-side part on a host":
        ("L153", lab(duct_l={"id": "duct-l", "ref": "cmv-sfd45u5w", "side": "left", "on": "enc"})),
    "L153 a side on a rack-face part as wide as the rack":
        ("L153", lab(mgr={"id": "mgr", "ref": "fhd-cmp5dr", "ru": 30, "side": "left"})),
    "L153 a side on a rack device":
        ("L153", lab(enc={"id": "enc", "ref": "fhd-1ufce", "ru": 20, "side": "left"}, bkt_on=None)),
    "L154 two rack-side parts on one side":
        ("L154", lab(duct_r={"id": "duct-r", "ref": "cmv-sfd45u5w", "side": "left"})),
    "L154 a rack-side part taller than the rack":
        ("L154", {**lab(duct_r=None), "rack": {"height-ru": 42}}),
    "L154 a rack-side part that runs off the top":
        ("L154", lab(duct_r={"id": "duct-r", "ref": "cmv-sfd45u5w", "side": "right", "ru": 2})),
    "L142 two brackets on one side of one unit":
        ("L142", lab(bkt_r={"id": "bkt-r", "ref": "cmv-5u3w", "ru": 12, "side": "left"})),
    "L142 a full-width manager over a sided bracket":
        ("L142", lab(mgr={"id": "mgr", "ref": "fhd-cmp5dr", "ru": 11})),
    "L142 a bracket with no side takes both":
        ("L142", lab(bkt_x={"id": "bkt-x", "ref": "cmv-5u3w", "ru": 14})),
}


@pytest.mark.parametrize("case", sorted(FAILING))
def test_each_check_fails_its_lab(case):
    code, d = FAILING[case]
    assert labs.schema_errors(d) == [], "the fixture should fail the check, not the schema"
    assert codes(d) == [code], run(d)[0]


def test_a_bracket_on_each_rail_does_not_conflict_but_two_on_one_do():
    both = lab(bkt_on=None)
    assert codes(both) == []
    same = lab(bkt_on=None, bkt_r={"id": "bkt-r", "ref": "cmv-5u3w", "ru": 10, "side": "left"})
    found = [m for c, _, m in run(same)[0] if c == "L142"]
    assert len(found) == 1 and "left side" in found[0]


def test_a_rear_bracket_does_not_meet_a_front_one():
    assert codes(lab(bkt_r={"id": "bkt-r", "ref": "cmv-5u3w", "ru": 10, "side": "left",
                            "face": "rear"})) == []


def test_the_schema_rejects_a_side_that_is_neither():
    assert labs.schema_errors(lab(duct_l={"id": "duct-l", "ref": "cmv-sfd45u5w", "side": "middle"}))


def test_lint_reports_the_new_lab_codes():
    with lint.collecting() as found:
        lint.lint_lab("library/labs/x/lab.yaml", FAILING["L154 two rack-side parts on one side"][1], [LIB])
        lint.lint_lab("library/labs/x/lab.yaml", FAILING["L153 a rack-side part with no side"][1], [LIB])
    assert len(found.errors) == 2
    assert any("[L154]" in m for m in found.errors) and any("[L153]" in m for m in found.errors)


def test_labs_json_carries_the_side(tmp_path, monkeypatch):
    (tmp_path / "lib/labs/t").mkdir(parents=True)
    (tmp_path / "lib/labs/t/lab.yaml").write_text(json.dumps(GOOD))
    out = tmp_path / "dist"
    monkeypatch.setattr(sys, "argv", ["labs_index", "--library", str(tmp_path / "lib"),
                                      "--library", str(LIB), "--out", str(out)])
    assert labs_index.main() == 0
    got = {l["name"]: l for l in json.loads((out / "labs.json").read_text())["labs"]}
    p = {q["id"]: q for q in got["vertical-managers"]["devices"]}
    assert {k: p["duct-l"][k] for k in ("ru", "face", "side", "mount")} == \
        {"ru": 1, "face": "front", "side": "left", "mount": "rack-side"}
    assert p["bkt-r"]["side"] == "right" and p["enc"]["side"] is None


def test_the_bracket_is_narrower_than_the_opening_and_the_manager_is_not():
    b = yaml.safe_load(BRACKET.read_text())["chassis"]
    assert b["mount"] == "rack-face" and b["width"] < labs.RACK_OPENING_MM
    m = yaml.safe_load((LIB / "devices/fs/fhd-cmp5dr/device.yaml").read_text())["chassis"]
    assert m["width"] >= labs.RACK_OPENING_MM


# --- attachment points (#934, docs/pdu-model-design.md section 6.4) ------------

def _four(**changes):
    return lab(**{"duct_l": {"id": "duct-l", "ref": "cmv-sfd45u5w", "side": "left-front"},
                  "duct_r": {"id": "duct-r", "ref": "cmv-sfd45u5w", "side": "left-rear"},
                  **changes})


def test_front_and_rear_points_on_one_side_never_meet():
    """Two 45U parts a side, one at each four-post point: the names alone decide."""
    d = _four()
    assert labs.schema_errors(d) == [] and codes(d) == []
    _, p = run(d)
    assert (p["duct-l"]["side"], p["duct-r"]["side"]) == ("left-front", "left-rear")


@pytest.mark.parametrize("case, code, d", [
    ("two parts at one four-post point", "L154",
     _four(duct_r={"id": "duct-r", "ref": "cmv-sfd45u5w", "side": "left-front"})),
    ("a side mixing the two-post and a four-post name", "L154",
     _four(duct_r={"id": "duct-r", "ref": "cmv-sfd45u5w", "side": "left", "ru": 1})),
    ("a rack-face bracket at a four-post point", "L153",
     lab(bkt_l={"id": "bkt-l", "ref": "cmv-5u3w", "ru": 10, "side": "left-front"})),
])
def test_attachment_point_checks(case, code, d):
    assert labs.schema_errors(d) == []
    assert code in codes(d), (case, run(d)[0])


def test_the_mixed_side_names_both_kinds():
    d = _four(duct_r={"id": "duct-r", "ref": "cmv-sfd45u5w", "side": "left"})
    msgs = [m for c, _, m in run(d)[0] if c == "L154"]
    assert any("two-post" in m and "duct-r" in m and "duct-l" in m for m in msgs), msgs


def test_the_right_side_is_judged_apart_from_the_left():
    d = lab(duct_l={"id": "duct-l", "ref": "cmv-sfd45u5w", "side": "left"},
            duct_r={"id": "duct-r", "ref": "cmv-sfd45u5w", "side": "right-rear"})
    assert codes(d) == []


def test_labs_json_publishes_the_point_as_written(tmp_path, monkeypatch):
    (tmp_path / "lib/labs/t").mkdir(parents=True)
    (tmp_path / "lib/labs/t/lab.yaml").write_text(json.dumps(_four()))
    out = tmp_path / "dist"
    monkeypatch.setattr(sys, "argv", ["labs_index", "--library", str(tmp_path / "lib"),
                                      "--library", str(LIB), "--out", str(out)])
    assert labs_index.main() == 0
    got = {l["name"]: l for l in json.loads((out / "labs.json").read_text())["labs"]}
    p = {q["id"]: q for q in got["vertical-managers"]["devices"]}
    assert (p["duct-l"]["side"], p["duct-r"]["side"]) == ("left-front", "left-rear")
