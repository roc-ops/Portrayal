"""`speeds`: a multi-rate cage publishes every native rate (#512).

`speed` is the highest native rate, so a 1/10/25G SFP28 group says `25g` and
`[data-speeds~='10g']` could not find it. `speeds: [1g, 10g, 25g]` in a group's
attrs compiles to `data-speeds="1g 10g 25g"`. It is written per group from the
vendor's figure, so the library carries it on one device so far.
"""
import json
import pathlib
import xml.etree.ElementTree as ET

import jsonschema
import pytest

from portrayal import libwalk, lint, render
from portrayal.manifest import load_yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
DIST = LIB / "dist"

DEVICES_WITH_SPEEDS = {"s9600-72xc"}


@pytest.fixture
def errors(monkeypatch):
    got = []
    monkeypatch.setattr(lint, "ERRORS", got)
    return got


def _l110(errs):
    return [e for e in errs if "[L110]" in e]


def _device(speed, speeds, placement_attrs=None):
    return {
        "groups": {"ports": {"term": "Port", "role": "traffic",
                             "attrs": {"media": "sfp28", "speed": speed, "speeds": speeds}}},
        "views": {"front": {"components": {"placements": [
            {"ref": "std/sfp28@1", "id": "port-1", "at": [0, 0], "group": "ports",
             **({"attrs": placement_attrs} if placement_attrs else {})},
        ]}}},
    }


# --- the rule ----------------------------------------------------------------

def test_a_list_ending_at_speed_passes(errors):
    lint.lint_device_speed_vocabulary("d.yaml", _device("25g", ["1g", "10g", "25g"]))
    assert _l110(errors) == []


def test_a_member_outside_the_set_is_an_error(errors):
    lint.lint_device_speed_vocabulary("d.yaml", _device("25g", ["1000base-t", "10g", "25g"]))
    (msg,) = _l110(errors)
    assert "'1000base-t'" in msg and "groups/ports" in msg


def test_a_list_whose_highest_member_is_not_speed_is_an_error(errors):
    lint.lint_device_speed_vocabulary("d.yaml", _device("10g", ["1g", "10g", "25g"]))
    (msg,) = _l110(errors)
    assert "highest member" in msg


def test_a_list_without_speed_is_an_error(errors):
    d = _device("25g", ["1g", "10g", "25g"])
    del d["groups"]["ports"]["attrs"]["speed"]
    lint.lint_device_speed_vocabulary("d.yaml", d)
    (msg,) = _l110(errors)
    assert "no `speed`" in msg


def test_a_list_out_of_order_is_an_error(errors):
    lint.lint_device_speed_vocabulary("d.yaml", _device("25g", ["25g", "1g", "10g"]))
    (msg,) = _l110(errors)
    assert "ascending" in msg


def test_a_placement_speed_contradicting_its_groups_list_is_an_error(errors):
    d = _device("25g", ["1g", "10g", "25g"], {"speed": "10g"})
    lint.lint_device_speed_vocabulary("d.yaml", d)
    (msg,) = _l110(errors)
    assert "front/port-1" in msg and "highest member" in msg


def test_an_elements_row_carries_the_list():
    from portrayal import elements
    svg = ET.fromstring('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">'
                        '<g data-path="p" data-speed="25g" data-speeds="1g 10g 25g"/></svg>')
    doc = elements.face_elements(svg, "c", "front")
    (row,) = [r for r in doc["elements"] if r.get("path") == "p"]
    assert row["speed"] == "25g" and row["speeds"] == ["1g", "10g", "25g"]


def test_a_duplicate_is_an_error(errors):
    lint.lint_device_speed_vocabulary("d.yaml", _device("25g", ["1g", "10g", "10g", "25g"]))
    (msg,) = _l110(errors)
    assert "twice" in msg


def test_a_placement_list_is_held_to_its_groups_speed(errors):
    d = _device("25g", ["1g", "10g", "25g"], {"speeds": ["1g", "10g"]})
    lint.lint_device_speed_vocabulary("d.yaml", d)
    (msg,) = _l110(errors)
    assert "front/port-1" in msg


def test_a_component_group_list_is_read(errors):
    lint.lint_component_speed_vocabulary("c.yaml", {"groups": {"p": {
        "attrs": {"speed": "100g", "speeds": ["40g", "400g"]}}}})
    assert len(_l110(errors)) == 1


def test_the_schema_asks_for_two_or_more_distinct_rates():
    schema = json.loads((ROOT / "spec" / "schemas" / "device.schema.json").read_text())
    sp = schema["properties"]["groups"]["additionalProperties"]["properties"]["attrs"]["properties"]["speeds"]
    v = jsonschema.Draft202012Validator(sp)
    assert not list(v.iter_errors(["1g", "10g"]))
    assert list(v.iter_errors(["25g"]))              # a single rate adds nothing
    assert list(v.iter_errors(["10g", "10g"]))       # no duplicates


def test_a_list_compiles_to_a_space_separated_attribute():
    assert render.data_attrs({"speed": "25g", "speeds": ["1g", "10g", "25g"]}) == {
        "data-speed": "25g", "data-speeds": "1g 10g 25g"}


# --- the library -------------------------------------------------------------

def test_only_the_modelled_device_declares_speeds():
    got = set()
    for f in libwalk.iter_devices([LIB]):
        d = load_yaml(f) or {}
        if any("speeds" in ((g or {}).get("attrs") or {}) for g in (d.get("groups") or {}).values()):
            got.add(pathlib.Path(f).parent.name)
    assert got == DEVICES_WITH_SPEEDS


def _built_faces():
    if not (DIST / "devices.json").exists():
        pytest.skip("library/dist not built - run ./build.sh")
    return sorted(DIST.glob("*.svg"))


def _ports(svg):
    for el in ET.parse(svg).getroot().iter():
        if el.get("data-speed") is not None or el.get("data-speeds") is not None:
            yield el


def test_the_s9600_front_publishes_its_rates():
    fronts = [p for p in _built_faces() if p.name.startswith("s9600-72xc.") and p.name.endswith(".front.svg")]
    assert fronts
    for svg in fronts:
        sfp28 = [e for e in _ports(svg) if e.get("data-media") == "sfp28"]
        qsfp28 = [e for e in _ports(svg) if e.get("data-media") == "qsfp28"]
        assert len(sfp28) == 64 and len(qsfp28) == 8, svg.name
        assert {(e.get("data-speed"), e.get("data-speeds")) for e in sfp28} == {("25g", "1g 10g 25g")}
        assert {(e.get("data-speed"), e.get("data-speeds")) for e in qsfp28} == {("100g", "40g 100g")}


def test_no_other_port_in_the_library_carries_data_speeds():
    carrying = {}
    for svg in _built_faces():
        if any(True for e in _ports(svg) if e.get("data-speeds") is not None):
            carrying[svg.name] = True
    stray = [n for n in carrying if n.split(".")[0] not in DEVICES_WITH_SPEEDS]
    assert not stray, stray
    # and on the device itself, only the two groups carry it
    for svg in _built_faces():
        if svg.name.split(".")[0] in DEVICES_WITH_SPEEDS:
            for e in _ports(svg):
                if e.get("data-speeds") is not None:
                    assert e.get("data-media") in ("sfp28", "qsfp28"), (svg.name, e.get("data-path"))
