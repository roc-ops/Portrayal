"""Rack PDUs: the derived class, the input rating, `lines`, `through` on a fixed
breaker, `feed_leg` and the mount points (#934, docs/pdu-model-design.md).

Fixtures are small documents built from the real Eaton G4 parts, so a rule that
reads a part's class or a PART_POWER slug reads the library's answer.
"""
import copy
from pathlib import Path

import pytest

from portrayal import dcim_export as dx
from portrayal import devicelock as dl
from portrayal import lint
from portrayal import manifest
from portrayal import render
from portrayal.manifest import load_yaml

ROOT = Path(__file__).resolve().parents[2]
LIB = ROOT / "library"
EVMI = LIB / "devices/eaton/evmi2130x/device.yaml"
EVMA = LIB / "devices/eaton/evma8365x/device.yaml"

C13 = "std/c13-outlet@1"
CORD = "eaton/g4-cord-l21-30p@1"
BREAKER = "eaton/g4-breaker-20a-2p@1"


def pdu(power=None, management=None, breaker_lines=("L1", "L2"), **outlet_keys):
    """One cord, one fixed breaker and two outlets through it."""
    brk = {"id": "breaker-a", "ref": BREAKER, "at": [0, 100]}
    if breaker_lines:
        brk["lines"] = list(breaker_lines)
    outlets = [{"id": f"outlet-a{n}", "ref": C13, "at": [0, 20 * n], "group": "outlets",
                "fed-by": "input", "through": "breaker-a", **outlet_keys} for n in (1, 2)]
    attrs = {}
    if power is not None:
        attrs["power"] = power
    if management is not None:
        attrs["management"] = management
    return {"format": 1, "kind": "device", "name": "p", "version": "1.0.0",
            "manufacturer": "Acme", "model": "P1", "profile": "power",
            "maturity": "modelled", "attrs": attrs,
            "chassis": {"width": 52, "height": 400, "depth": 53, "ru": 9,
                        "mount": "rack-side"},
            "groups": {"outlets": {"term": "Outlet"}},
            "views": {"front": {"size": {"w": 52, "h": 400},
                                "components": {"placements": [brk, *outlets]}},
                      "bottom": {"size": {"w": 52, "h": 53}, "components": {"placements": [
                          {"id": "input", "ref": CORD, "at": [7.55, 10.05]}]}}}}


WYE = {"input-phase": "three", "input-wiring": "wye"}


def found(fn, doc, code, *args):
    with lint.collecting() as got:
        fn("device.yaml", doc, *args)
    return ([m for m in got.errors if f"[{code}]" in m],
            [m for m in got.warnings if f"[{code}]" in m])


# --- the class -----------------------------------------------------------------

def test_every_pair_has_its_name():
    assert len(manifest.PDU_CLASSES) == 8 == len(set(manifest.PDU_CLASSES.values()))
    for (scope, switching), name in manifest.PDU_CLASSES.items():
        doc = {"attrs": {"management": {"metering-scope": scope,
                                        "outlet-switching": switching}}}
        assert manifest.pdu_class(doc) == name
    assert manifest.pdu_class({"attrs": {"management": {"metering-scope": "branch"}}}) is None
    assert manifest.pdu_class({}) is None


def test_L166_the_two_facts_are_stated_together():
    errs, _ = found(lint.lint_device_pdu_capability, pdu(management={"metering-scope": "input"}),
                    "L166")
    assert len(errs) == 1 and "outlet-switching" in errs[0]


def test_L166_a_switched_pdu_declares_the_vocabulary_on_every_outlet():
    doc = pdu(management={"metering-scope": "outlet", "outlet-switching": True})
    _, warns = found(lint.lint_device_pdu_capability, doc, "L166")
    assert len(warns) == 1 and "outlet-a1" in warns[0] and "outlet-a2" in warns[0]
    doc["groups"]["outlets"]["states"] = ["on", "off"]
    assert found(lint.lint_device_pdu_capability, doc, "L166") == ([], [])


def test_L166_an_unswitched_pdu_declares_no_outlet_state():
    doc = pdu(management={"metering-scope": "branch", "outlet-switching": False})
    assert found(lint.lint_device_pdu_capability, doc, "L166") == ([], [])
    doc["groups"]["outlets"]["states"] = ["on", "off"]
    errs, _ = found(lint.lint_device_pdu_capability, doc, "L166")
    assert len(errs) == 1


# --- the input rating ----------------------------------------------------------

def test_L167_input_plug_is_the_slug_the_input_exports():
    assert found(lint.lint_device_input_rating, pdu({"input-plug": "nema-l21-30p", **WYE}),
                 "L167") == ([], [])
    errs, _ = found(lint.lint_device_input_rating, pdu({"input-plug": "cs8365c", **WYE}), "L167")
    assert len(errs) == 1 and "nema-l21-30p" in errs[0]


@pytest.mark.parametrize("power", [{"input-phase": "single", "input-wiring": "wye"},
                                   {"input-phase": "three"}])
def test_L167_wiring_is_stated_exactly_when_three_phase(power):
    errs, _ = found(lint.lint_device_input_rating, pdu(power), "L167")
    assert len(errs) == 1


def test_L168_a_pdu_does_not_state_both_voltage_keys():
    _, warns = found(lint.lint_device_input_rating,
                     pdu({"input-voltage": "208 V", "input-voltage-v": 208}), "L168")
    assert len(warns) == 1
    assert found(lint.lint_device_input_rating, pdu({"input-voltage-v": 208}), "L168") == ([], [])


def test_the_rating_sentence_reads_the_numbers_only():
    doc = pdu({"input-voltage-v": 208, "input-current-a": 24, "plug-rating-a": 30, **WYE})
    assert manifest.input_rating(doc) == "208 V three-phase wye, 24 A input (30 A plug)"
    assert manifest.input_rating(pdu({"input-ac": "prose only"})) is None


# --- through, lines and feed_leg -----------------------------------------------

def test_L133_through_may_name_a_fixed_breaker_and_L135_reads_bays_only():
    doc = pdu(WYE)
    for code in ("L133", "L135"):
        assert found(lint.lint_device_power_outlets, doc, code, [LIB]) == ([], []), code
    # the cord is a placement and not a breaker, so it is still refused
    bad = pdu(WYE)
    bad["views"]["front"]["components"]["placements"][1]["through"] = "input"
    errs, _ = found(lint.lint_device_power_outlets, bad, "L133", [LIB])
    assert len(errs) == 1


def test_L169_lines_stand_on_a_breaker_or_an_outlet():
    doc = pdu(WYE)
    assert found(lint.lint_device_lines, doc, "L169", [LIB]) == ([], [])
    doc["views"]["bottom"]["components"]["placements"][0]["lines"] = ["L1", "L2"]
    errs, _ = found(lint.lint_device_lines, doc, "L169", [LIB])
    assert len(errs) == 1 and "input" in errs[0]


def test_L169_a_three_phase_pdu_with_no_lines_is_warned():
    _, warns = found(lint.lint_device_lines, pdu(WYE, breaker_lines=None), "L169", [LIB])
    assert len(warns) == 1 and "outlet-a1" in warns[0]
    # single phase: the plug decides the leg, nothing is owed
    assert found(lint.lint_device_lines, pdu({"input-phase": "single"}, breaker_lines=None),
                 "L169", [LIB]) == ([], [])


@pytest.mark.parametrize("power, lines, leg", [
    (WYE, ("L1", "N"), "A"),
    (WYE, ("L3", "N"), "C"),
    (WYE, ("L1", "L2"), None),                      # line to line: two legs
    ({"input-phase": "three", "input-wiring": "delta"}, ("L1", "N"), None),
    ({"input-phase": "single"}, ("L1", "N"), None),  # the installation's leg
])
def test_feed_leg_only_for_line_to_neutral_on_wye(power, lines, leg):
    rows = dx.build(pdu(power, breaker_lines=lines), "default", {}, None)["power-outlets"]
    assert [r.get("feed_leg") for r in rows] == [leg, leg]
    # the outlet reaches the lines through its breaker and says so
    assert rows[0]["description"] == f"Through breaker-a, lines {'-'.join(lines)}"


@pytest.mark.parametrize("attrs, said", [
    ({"section": "A", "section-color": "#f4d440"}, "Through breaker A"),  # the G4 tile letter
    ({"label": "CB1", "section": "A"}, "Through breaker CB1"),            # a printed label first
    ({"section": "  "}, "Through breaker-a"),                             # blank is unstated
    ({}, "Through breaker-a"),                                            # nothing printed: the id
])
def test_an_outlet_names_its_breaker_as_printed(attrs, said):
    """Decided 2026-10-09: the description names the breaker as the unit
    prints it, so a reader finds it on the PDU; the id is the fallback."""
    doc = pdu(WYE)
    doc["views"]["front"]["components"]["placements"][0]["attrs"] = attrs
    rows = dx.build(doc, "default", {}, None)["power-outlets"]
    assert [r["description"] for r in rows] == [f"{said}, lines L1-L2"] * 2


def test_an_outlet_with_its_own_lines_and_no_breaker():
    doc = pdu(WYE, breaker_lines=None, lines=["L2", "N"])
    for o in doc["views"]["front"]["components"]["placements"][1:]:
        del o["through"]
    rows = dx.build(doc, "default", {}, None)["power-outlets"]
    assert [(r["description"], r["feed_leg"]) for r in rows] == [("Lines L2-N", "B")] * 2


def test_the_input_port_carries_the_rating():
    doc = pdu({"input-voltage-v": 208, "input-current-a": 24, "plug-rating-a": 30, **WYE},
              management={"metering-scope": "branch", "outlet-switching": False})
    out = dx.build(doc, "default", {}, None)
    assert out["power-ports"] == [{"name": "input", "type": "nema-l21-30p",
                                   "description": "208 V three-phase wye, 24 A input (30 A plug)"}]
    assert "PDU class: metered-branch (metering-scope branch, outlet-switching false)." \
        in out["comments"]
    # a boolean fact is spelled as JSON spells it, as the drawing's data-* is
    assert "- management.outlet-switching: false" in out["comments"]


@pytest.mark.parametrize("before, after, need", [
    (None, ["L1", "L2"], "minor"),           # stated where there was none
    (["L1", "L2"], ["L2", "L3"], "major"),   # changed
    (["L1", "L2"], None, "major"),           # dropped
])
def test_lines_are_addressing(before, after, need):
    assert "lines" in dl.PLACEMENT_ADDRESSING
    old, new = pdu(breaker_lines=before), pdu(breaker_lines=after)
    assert dl.required_bump(dl.entry(old), dl.entry(new)) == need


# --- the pilot, and its mount points -------------------------------------------

def test_the_evmi2130x_states_the_model():
    d = load_yaml(EVMI)
    assert manifest.pdu_class(d) == "metered-branch"
    placed = manifest.device_placements(d)
    want = {"a": ["L1", "L2"], "b": ["L2", "L3"], "c": ["L3", "L1"]}
    outlets = {k: p for k, p in placed.items() if k.startswith("outlet-")}
    assert len(outlets) == 42
    assert all(manifest.outlet_lines(p, placed) == want[k[len("outlet-")]]
               for k, p in outlets.items())
    rows = dx.build(d, "base", d["configurations"]["base"], None)["power-outlets"]
    assert not any("feed_leg" in r for r in rows), "every outlet is line to line"
    by = {r["name"]: r["description"] for r in rows}
    assert by["A1"] == "Through breaker A, lines L1-L2"
    assert by["C42"] == "Through breaker C, lines L3-L1"


@pytest.mark.parametrize("target", dx.TARGETS)
def test_the_evma8365x_outlets_say_which_breaker_and_lines(target):
    """The delta G4: 42 outlets named by their printed labels, seven behind
    each of six two-pole breakers, A to F round the delta twice. B8 is the
    first outlet behind the second breaker and F42 the last behind the sixth;
    their sentences are written out here, not derived."""
    d = load_yaml(EVMA)
    built = dx.build(d, "base", d["configurations"]["base"], None)
    rows = dx.for_target(copy.deepcopy(built), target)["power-outlets"]
    by = {r["name"]: r for r in rows}
    assert len(rows) == 42
    assert by["B8"]["description"] == "Through breaker B, lines L2-L3"
    assert by["F42"]["description"] == "Through breaker F, lines L3-L1"
    assert by["A7"]["description"] == "Through breaker A, lines L1-L2"
    for name in ("B8", "F42"):
        assert by[name]["type"] == "iec-60320-c13"
        assert by[name]["power_port"] == "input"
    assert not any("feed_leg" in r for r in rows), "every outlet is line to line"


def test_mount_points_are_derived_from_the_buttons():
    d = load_yaml(EVMI)
    got = render.mount_points(d, "base", d["configurations"]["base"],
                              render.Library([LIB]))
    assert got == [{"mates": "pdu-button", "at": 72.0}, {"mates": "pdu-button", "at": 1627.8}]
    # the pitch the drawing dimensions, and no manifest states
    assert round(got[1]["at"] - got[0]["at"], 2) == 1555.8


def test_a_device_without_buttons_publishes_none():
    d = copy.deepcopy(load_yaml(EVMI))
    d["views"]["rear"]["components"]["placements"] = []
    assert render.mount_points(d, "base", {}, render.Library([LIB])) == []


# --- slots and states in configs.json (rack file version 4, part 4) -------------

KEYHOLE = """format: 1
kind: component
name: keyhole
version: 1.0.0
class: mount
interface: pdu-button
profile: power
description: A fixture keyhole slot, for the test of configs[].slots.
size: {w: 12, h: 20}
connection-points:
  mate: {at: [6, 14]}
"""


def _bracket(tmp_path):
    """A fixture bracket with keyholes: two on its front option, and a third
    that only its side option has."""
    part = tmp_path / "components/fixture/keyhole/v1"
    part.mkdir(parents=True)
    (part / "contract.yaml").write_text(KEYHOLE)
    device = {"views": {"front": {"size": {"w": 40, "h": 100}, "components": {"placements": [
        {"id": "slot-1", "ref": "fixture/keyhole@1", "at": [14, 10]},
        {"id": "slot-2", "ref": "fixture/keyhole@1", "at": [14, 60]},
        {"id": "slot-3", "ref": "fixture/keyhole@1", "at": [14, 35], "only-in": ["side"]}]}}},
        "configurations": {"front": {}, "side": {}}}
    return device, render.Library([tmp_path, LIB])


def test_a_part_with_keyholes_publishes_its_slots_and_each_configuration_its_own(tmp_path):
    d, lib = _bracket(tmp_path)
    # at: from the bottom of the 100 mm view to each mate point, 14 below the top of its part
    assert render.config_slots(d, "front", d["configurations"]["front"], lib) == [
        {"interface": "pdu-button", "at": 26.0}, {"interface": "pdu-button", "at": 76.0}]
    assert render.config_slots(d, "side", d["configurations"]["side"], lib) == [
        {"interface": "pdu-button", "at": 26.0}, {"interface": "pdu-button", "at": 51.0},
        {"interface": "pdu-button", "at": 76.0}]
    # a slot is not a mount point, and a button is not a slot
    assert render.mount_points(d, "front", {}, lib) == []
    evmi = load_yaml(EVMI)
    assert render.config_slots(evmi, "base", evmi["configurations"]["base"], render.Library([LIB])) == []
    # two brackets 35 units apart meet the G4 pitch to 0.05 mm, as section 5 of the note says
    points = render.mount_points(evmi, "base", evmi["configurations"]["base"], render.Library([LIB]))
    assert abs((points[1]["at"] - points[0]["at"]) - 35 * 44.45) <= 0.051


def test_the_evma8365x_lists_its_switchable_outlets_under_states():
    """The list form on a real device: each outlet states `['on', 'off']` on its
    placement. The 42 lamps beside them, which take the two colours from their
    group, are not listed: a state is set on the outlet and follows `for:`."""
    d = load_yaml(EVMA)
    assert manifest.pdu_class(d) == "managed"
    got = render.config_states(d, "base", d["configurations"]["base"], render.Library([LIB]))
    assert len(got) == 42 and all(k.startswith("outlet-") for k in got)
    assert set(map(tuple, got.values())) == {("on", "off")}
    assert got["outlet-a1"] == ["on", "off"] and got["outlet-f42"] == ["on", "off"]
    assert list(got) == sorted(got)


def test_the_evma8365x_names_its_outlets_as_its_device_type_export_does():
    """`configs[].names` and the device-type export read one source, so a rack
    comment that says which outlets are off names them as the DCIM lists
    them: A1, not outlet-a1."""
    d = load_yaml(EVMA)
    states = render.config_states(d, "base", d["configurations"]["base"], render.Library([LIB]))
    names = render.config_names(d, states)
    assert set(names) == set(states) and len(names) == 42
    assert names["outlet-a1"] == "A1" and names["outlet-a2"] == "A2" and names["outlet-f42"] == "F42"
    for target in ("netbox", "nautobot"):
        exported = load_yaml(ROOT / "library/exports" / target / "device-types/Eaton/EVMA8365X.yaml")
        assert sorted(names.values()) == sorted(o["name"] for o in exported["power-outlets"] if o["name"] in set(names.values()))
        assert set(names.values()) <= {o["name"] for o in exported["power-outlets"]}, target
    # a part no rule names has no entry, and a device with no rules has none
    assert render.config_names(d, {"outlet-a1": ["on", "off"], "psu-1": ["on", "off"]}) == {"outlet-a1": "A1"}
    assert render.config_names({}, states) == {}


def test_a_per_lamp_mapping_is_not_a_state_vocabulary_of_its_part():
    """The mapping form on a real device: the AIS2001 gives each lamp of a jack
    its own vocabulary, `{led-a: [...], led-b: [...]}`. Those keys are element
    ids. Read as a list they were published as state names."""
    path = next(LIB.glob("devices/**/ais2001/device.yaml"))
    d = load_yaml(path)
    placed = manifest.device_placements(d)
    mapped = [k for k, p in placed.items() if isinstance(p.get("states"), dict)]
    assert mapped, "the AIS2001 no longer states a per-lamp mapping: pick another device"
    lib = render.Library([LIB])
    for name, cfg in d["configurations"].items():
        got = render.config_states(d, name, cfg, lib)
        assert not set(mapped) & set(got), sorted(set(mapped) & set(got))
        names = {n for v in got.values() for n in v}
        elements = {el for k in mapped for el in placed[k]["states"]}
        assert not names & elements, f"element ids published as state names: {sorted(names & elements)}"


def test_no_device_publishes_an_element_id_or_a_lamp_under_states():
    """Every device: no lamp is listed, and every name is a state name a
    placement, its group or its part declares as a list."""
    lib = render.Library([LIB])
    listed = devices = 0
    for path in sorted(LIB.glob("devices/**/device.yaml")):
        d = load_yaml(path)
        placed = manifest.device_placements(d)
        groups = d.get("groups") or {}
        for name, cfg in (d.get("configurations") or {}).items():
            got = render.config_states(d, name, cfg, lib)
            devices += 1
            for pid, names in got.items():
                p = placed[pid]
                contract, _ = lib.resolve(p["ref"])
                assert contract.get("class") != "led", (path.parent.name, pid)
                want = p.get("states") or (groups.get(p.get("group")) or {}).get("states") or contract.get("states")
                assert isinstance(want, list) and names == render.state_names(want), (path.parent.name, pid)
                listed += 1
    assert devices > 250 and listed >= 42, (devices, listed)


def test_the_evmi2130x_lists_no_outlet_and_meters_its_branches():
    d = load_yaml(EVMI)
    assert render.config_states(d, "base", d["configurations"]["base"], render.Library([LIB])) == {}
    assert manifest.pdu_class(d) == "metered-branch"


def test_a_placement_states_win_over_its_group_and_its_group_over_its_part(tmp_path):
    d, lib = _bracket(tmp_path)
    d["groups"] = {"outlets": {"states": [{"name": "on", "color": "#22c55e"}, {"name": "off"}]}}
    p = d["views"]["front"]["components"]["placements"]
    p[0].update(group="outlets")
    p[1].update(group="outlets", states=["on", "off", "standby"])
    assert render.config_states(d, "front", {}, lib) == {"slot-1": ["on", "off"], "slot-2": ["on", "off", "standby"]}
    # a placement only one configuration draws is listed only there
    p[2].update(states=["open"])
    assert "slot-3" not in render.config_states(d, "front", {}, lib)
    assert render.config_states(d, "side", {}, lib)["slot-3"] == ["open"]
    # the part states its own: the group still wins over it, and it is what an ungrouped placement has
    part = tmp_path / "components/fixture/keyhole/v1/contract.yaml"
    part.write_text(KEYHOLE + "states: [shut, open]\n")
    lib = render.Library([tmp_path, LIB])
    p[2].pop("states")
    got = render.config_states(d, "side", {}, lib)
    assert got == {"slot-1": ["on", "off"], "slot-2": ["on", "off", "standby"], "slot-3": ["shut", "open"]}
    # the mapping form names lamps inside the part, and a lamp is not a part a rack entry sets
    p[0]["states"] = {"led-a": ["on", "off"]}
    assert "slot-1" not in render.config_states(d, "front", {}, lib)
    part.write_text(KEYHOLE.replace("class: mount", "class: led") + "states: [shut, open]\n")
    assert render.config_states(d, "side", {}, render.Library([tmp_path, LIB])) == {}


def test_the_built_configs_json_carries_slots_and_states():
    """The build, not the function: `main()` writes both keys on every
    configuration of every device. Reads library/dist, as the suite does."""
    import json
    dist = LIB / "dist"
    assert (dist / "evma8365x.configs.json").is_file(), "no library/dist: run ./build.sh first (the suite reads the build)"
    files = sorted(dist.glob("*.configs.json"))
    assert len(files) > 250
    for f in files:
        for c in json.loads(f.read_text())["configs"]:
            assert isinstance(c.get("slots"), list) and isinstance(c.get("states"), dict), f.name
            # `names` is for the parts of `states` alone, each a name that is not its path
            assert isinstance(c.get("names"), dict) and set(c["names"]) <= set(c["states"]), f.name
            assert all(isinstance(v, str) and v and v != k for k, v in c["names"].items()), f.name
    evma = json.loads((dist / "evma8365x.configs.json").read_text())["configs"][0]
    outlets = {k: v for k, v in evma["states"].items() if k.startswith("outlet-")}
    assert len(outlets) == 42 and outlets["outlet-a1"] == ["on", "off"] and evma["slots"] == []
    # the lamps beside the outlets are listed too, by their own path (P-0041)
    assert "led-a1" in evma["states"] and "led-f42" in evma["states"]
    assert len(evma["names"]) == 42 and evma["names"]["outlet-a2"] == "A2"
    evmi = json.loads((dist / "evmi2130x.configs.json").read_text())
    assert evmi["pdu-class"] == "metered-branch"
    assert not any(k.startswith("outlet-") for k in evmi["configs"][0]["states"])
    # and the key stays small enough to fetch with the parts list
    biggest = max(len(json.dumps(c["states"])) for f in files for c in json.loads(f.read_text())["configs"])
    assert biggest < 30_000, biggest


def _face(*rows):
    return {"elements": [dict(zip(("path", "states"), r)) for r in rows]}


def test_drawn_states_adds_every_lamp_the_drawing_declares_and_keeps_the_placements_own():
    """P-0041: a lamp, a seated module's lamp and a port's lamp are
    `data-states` on a `data-path` of the face, and a placement's own answer
    for its path wins."""
    placed = {"outlet-a1": ["on", "off"]}
    got = render.drawn_states(placed, [
        _face(("outlet-a1", ["off", "on", "x"]), ("led-sys", ["off", "ok"]), ("rear/psu-0/status", ["off", "ok", "fail"]),
              ("chassis", None), ("", ["off"])),
        _face(("led-sys", ["off", "fault"]), ("led-port-0", ["off", "up"]))])
    assert got == {"led-port-0": ["off", "up"], "led-sys": ["off", "ok", "fault"], "outlet-a1": ["on", "off"],
                   "rear/psu-0/status": ["off", "ok", "fail"]}
    assert list(got) == sorted(got)
    assert placed == {"outlet-a1": ["on", "off"]}, "the argument is not changed"
    assert render.drawn_states({}, []) == {}
