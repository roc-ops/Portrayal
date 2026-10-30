"""DC power, step 2: the build publishes each DC port a part states.

A part states its DC ports in a `dc` block (spec/schemas/component.schema.json),
and a device placement may override what differs. The build publishes them as
`dc-ports`, beside `cages`:

  - on a component's entry in components.json, relative to the part;
  - on each configuration of a device's configs.json, with the placements'
    overrides applied and every path a drawing addresses.

Both are omitted when there is nothing to say, as `cages` is. The tests build a
temporary library of synthetic parts and devices and run the indexers the build
runs over it, because no library part states a `dc` block yet; the last two
tests hold that the real library still publishes nothing.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

import onebuild

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "spec/tools/portrayal"
LIB = ROOT / "library"
DIST = LIB / "dist"

POST = "fixture/dc-post@1"
SUPPLY, TWIN, UNSTATED, PLAIN = ("fixture/dc-supply@1", "fixture/dc-twin@1",
                                 "fixture/dc-unstated@1", "fixture/dc-plain@1")

SKIN = ('<svg xmlns="http://www.w3.org/2000/svg" width="{w}mm" height="{h}mm" '
        'viewBox="0 0 {w} {h}"><rect id="body" x="0" y="0" width="{w}" height="{h}" fill="#ccc"/></svg>\n')


def _part(name, w, h, parts=(), dc=None, kind="module", cls="psu"):
    doc = {"format": 1, "kind": kind, "name": name, "version": "1.0.0", "class": cls,
           "description": "A synthetic part for the DC publication tests.",
           "size": {"w": w, "h": h},
           "provenance": {"size": "invented for a test", "terminals": "invented for a test"}}
    if parts:
        doc["parts"] = [{"ref": POST, "id": i, "at": [x, 20]} for i, x in parts]
    if dc:
        doc["dc"] = dc
    return doc


def _port(pid, poles, **keys):
    return {"id": pid, "direction": "input", "poles": [{"role": r, "slot": s} for r, s in poles],
            "source": {"poles": "terminals"}, **keys}


PARTS = {
    "dc-post": _part("dc-post", 8, 8, kind="component", cls="inlet"),
    "dc-plain": _part("dc-plain", 50, 40),
    "dc-supply": _part("dc-supply", 50, 40, [("terminal-rtn", 10), ("terminal-48v", 30)], {"ports": [
        _port("input", [("rtn", "terminal-rtn"), ("batt", "terminal-48v")],
              voltage={"nominal": -48, "range": [-44, -65]}, **{"rating-a": 18}, awg=[12], side="a")]}),
    "dc-twin": _part("dc-twin", 80, 40,
                     [("a-rtn", 5), ("a-batt", 20), ("b-rtn", 40), ("b-batt", 55)], {"ports": [
        _port("a", [("rtn", "a-rtn"), ("batt", "a-batt")], voltage={"nominal": -48}, side="a"),
        _port("b", [("rtn", "b-rtn"), ("batt", "b-batt")], voltage={"nominal": -48}, side="b")]}),
    "dc-unstated": _part("dc-unstated", 50, 40, [("terminal-1", 10), ("terminal-2", 30)], {"ports": [{
        "id": "input", "direction": "input", "voltage": {"nominal": -48},
        "poles": [{"role": "unstated", "slot": "terminal-1", "stand-in": {"order": "left-to-right"}},
                  {"role": "unstated", "slot": "terminal-2", "stand-in": {"order": "left-to-right"}}]}]}),
}

OVERRIDE = {"input": {"side": "b", "voltage": {"nominal": -60, "range": [-40.5, -72]},
                      "rating-a": 30, "poles": {"terminal-48v": "neg"}, "source": "a test"}}


def _device(name, placements=(), bays=(), configurations=None):
    return {"format": 1, "kind": "device", "name": name, "version": "1.0.0", "maturity": "draft",
            "manufacturer": "Fixture", "model": name.upper(), "description": "A synthetic box.",
            "chassis": {"width": 440, "height": 44, "depth": 300, "ru": 1},
            "provenance": {"size": "invented for a test"},
            "views": {"rear": {"size": {"w": 440, "h": 44},
                               "components": {"placements": list(placements), "bays": list(bays)}}},
            "configurations": configurations or {"base": {"default": True, "kind": "base"}}}


def _place(pid, ref, x, **keys):
    return {"id": pid, "ref": ref, "at": [x, 2], **keys}


DEVICES = {
    "placed-box": _device("placed-box", [
        _place("feed-a", SUPPLY, 10, dc=OVERRIDE),
        _place("feed-t", TWIN, 70),
        _place("feed-u", UNSTATED, 160),
        _place("feed-p", PLAIN, 220)]),
    "bayed-box": _device(
        "bayed-box", bays=[{"id": "psu-0", "at": [10, 2], "size": {"w": 80, "h": 40},
                            "accepts": [SUPPLY, TWIN, PLAIN], "default": SUPPLY}],
        configurations={"fitted": {"default": True, "kind": "base"},
                        "twin": {"kind": "orderable", "bays": {"psu-0": TWIN}},
                        "bare": {"kind": "orderable", "bays": {"psu-0": PLAIN}}}),
    "plain-box": _device("plain-box", [_place("feed-p", PLAIN, 10)]),
    # one part each and no override, so a change to the part is the whole change
    "supply-box": _device("supply-box", [_place("feed-a", SUPPLY, 10)]),
    "twin-box": _device("twin-box", [_place("feed-t", TWIN, 10)]),
}


def write_library(root, parts=None, devices=None):
    """A library of the synthetic parts and devices on `root`, returned."""
    for name, doc in (parts or PARTS).items():
        d = Path(root) / "components/fixture" / name / "v1"
        (d / "skins").mkdir(parents=True, exist_ok=True)
        (d / "contract.yaml").write_text(yaml.safe_dump(doc, sort_keys=False))
        (d / "skins/default.svg").write_text(SKIN.format(**doc["size"]))
    for name, doc in (devices or DEVICES).items():
        d = Path(root) / "devices/fixture" / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "device.yaml").write_text(yaml.safe_dump(doc, sort_keys=False))
    return Path(root)


def _run(*args):
    r = subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True,
                       env={**os.environ, "PYTHONPATH": str(ROOT / "spec/tools")})
    assert r.returncode == 0, r.stdout + r.stderr


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    """(components by ref, configs by device name) from the indexers the build
    runs over the synthetic library."""
    base = tmp_path_factory.mktemp("dc-published")
    lib = write_library(base / "lib")
    out = base / "dist"
    _run(TOOLS / "components_index.py", "--library", lib, "--out", out)
    comps = {f"{e['ns']}/{e['name']}@{e['major'][1:]}": e
             for e in json.loads((out / "components.json").read_text())["components"]}
    configs = {}
    for name in DEVICES:
        _run(TOOLS / "render.py", lib / "devices/fixture" / name / "device.yaml",
             "--library", lib, "--out", out)
        configs[name] = json.loads((out / f"{name}.configs.json").read_text())
    return comps, configs


def _config(configs, device, name):
    return next(c for c in configs[device]["configs"] if c["name"] == name)


def _ports(entry):
    return {p["path"]: p for p in entry["dc-ports"]}


# --- components.json -------------------------------------------------------------------------

def test_a_component_with_a_two_pole_port_publishes_it_with_its_figures_and_poles(built):
    comps, _ = built
    assert comps[SUPPLY]["dc-ports"] == [{
        "id": "input", "path": "", "direction": "input",
        "voltage": {"nominal": -48, "range": [-44, -65]}, "rating-a": 18, "awg": [12], "side": "a",
        "poles": [{"role": "rtn", "slot": "terminal-rtn"}, {"role": "batt", "slot": "terminal-48v"}]}]


def test_a_component_with_two_ports_publishes_each_with_its_id_in_its_path(built):
    comps, _ = built
    ports = comps[TWIN]["dc-ports"]
    assert [(p["id"], p["path"]) for p in ports] == [("a", "a"), ("b", "b")]
    assert [p["side"] for p in ports] == ["a", "b"]
    assert [q["slot"] for q in ports[1]["poles"]] == ["b-rtn", "b-batt"]


def test_a_figure_a_part_does_not_state_is_published_as_null(built):
    comps, _ = built
    port = comps[TWIN]["dc-ports"][0]
    assert port["rating-a"] is None and port["awg"] is None
    assert port["voltage"] == {"nominal": -48}


def test_a_component_with_no_dc_block_has_no_dc_ports_key(built):
    """A guard: it passes before this change as well as after."""
    comps, configs = built
    assert "dc-ports" not in comps[PLAIN] and "dc-ports" not in comps[POST]
    assert all("dc-ports" not in c for c in configs["plain-box"]["configs"])


def test_the_source_of_a_port_is_not_published(built):
    comps, configs = built
    assert all("source" not in p for p in comps[SUPPLY]["dc-ports"])
    assert all("source" not in p for c in configs["placed-box"]["configs"] for p in c["dc-ports"])


# --- configs.json ---------------------------------------------------------------------------------

def test_a_placed_part_publishes_its_port_with_the_placements_override_applied(built):
    _, configs = built
    port = _ports(_config(configs, "placed-box", "base"))["feed-a"]
    assert port["id"] == "input" and port["ref"] == SUPPLY
    assert (port["side"], port["rating-a"]) == ("b", 30)
    assert port["voltage"] == {"nominal": -60, "range": [-40.5, -72]}
    assert port["awg"] == [12]
    assert port["poles"] == [{"role": "rtn", "slot": "feed-a/terminal-rtn"},
                             {"role": "neg", "slot": "feed-a/terminal-48v"}]


def test_a_placement_with_no_override_publishes_what_its_part_states(built):
    _, configs = built
    ports = _ports(_config(configs, "placed-box", "base"))
    assert sorted(ports) == ["feed-a", "feed-t/a", "feed-t/b", "feed-u"]
    assert ports["feed-t/b"]["side"] == "b"
    assert [p["slot"] for p in ports["feed-t/b"]["poles"]] == ["feed-t/b-rtn", "feed-t/b-batt"]


def test_the_ports_are_ascending_by_path(built):
    _, configs = built
    paths = [p["path"] for p in _config(configs, "placed-box", "base")["dc-ports"]]
    assert paths == sorted(paths)


def test_a_part_seated_in_a_bay_publishes_under_the_configurations_that_seat_it(built):
    _, configs = built
    fitted = _ports(_config(configs, "bayed-box", "fitted"))
    assert list(fitted) == ["psu-0/module"]
    assert fitted["psu-0/module"]["poles"][1]["slot"] == "psu-0/module/terminal-48v"
    assert fitted["psu-0/module"]["ref"] == SUPPLY
    twin = _ports(_config(configs, "bayed-box", "twin"))
    assert sorted(twin) == ["psu-0/module/a", "psu-0/module/b"]
    assert {p["ref"] for p in twin.values()} == {TWIN}


def test_a_configuration_that_seats_another_part_does_not_carry_the_port(built):
    _, configs = built
    assert "dc-ports" not in _config(configs, "bayed-box", "bare")
    assert all("dc-ports" in _config(configs, "bayed-box", n) for n in ("fitted", "twin"))


def test_a_bays_default_is_not_published_for_a_configuration_that_replaces_it(built):
    _, configs = built
    assert not any(p["ref"] == SUPPLY for p in _config(configs, "bayed-box", "twin")["dc-ports"])


def test_an_unstated_pole_publishes_unstated_and_its_stand_in(built):
    comps, configs = built
    want = [{"role": "unstated", "slot": "terminal-1", "stand-in": {"order": "left-to-right"}},
            {"role": "unstated", "slot": "terminal-2", "stand-in": {"order": "left-to-right"}}]
    assert comps[UNSTATED]["dc-ports"][0]["poles"] == want
    got = _ports(_config(configs, "placed-box", "base"))["feed-u"]["poles"]
    assert got == [{**q, "slot": f"feed-u/{q['slot']}"} for q in want]


def test_a_pole_with_a_stated_role_carries_no_stand_in(built):
    comps, _ = built
    assert all("stand-in" not in q for q in comps[SUPPLY]["dc-ports"][0]["poles"])


# --- the real library ---------------------------------------------------------------------------------

def test_no_component_of_the_real_library_publishes_dc_ports_today():
    """Passes before this change as well as after: no part states a `dc` block."""
    doc = json.loads((onebuild.components_index() / "components.json").read_text())
    assert doc["components"]
    assert [e["name"] for e in doc["components"] if "dc-ports" in e] == []
    stating = [str(p.relative_to(LIB)) for p in (LIB / "components").glob("*/*/v*/contract.yaml")
               if "\ndc:" in "\n" + p.read_text()]
    assert stating == []


def test_no_configs_json_of_the_real_library_carries_dc_ports_today():
    """Passes before this change as well as after. It reads library/dist, so it
    holds after a build."""
    files = sorted(DIST.glob("*.configs.json"))
    assert files, "build the library first: ./build.sh"
    assert [f.name for f in files if "dc-ports" in f.read_text()] == []
