"""The seats of a placed part are slots of its device.

A part placed straight on a device face that composes two or more connector parts
(the Casa C40G's three ground studs, a DC terminal block's lugs, an AC inlet panel's
four C14 inlets) presents no slot of its own: `manifest.forwarded_part` answers only
when exactly one composed part qualifies. Its seats were published in the part's
entry in `components.json` and nowhere in the device's `cages[]`, so the catalogue
the Rack Builder reads offered no end there. `render.nested_seat_entries` lists each
seat in `cages[view]` under `<placement>/<part>`, the key `occupants:` and
`seat-turns` already use.

Run against the real library, with the functions the build calls. Nothing here counts
the seats of the library: the tests hold the rule, and a named list of devices holds
that the rule is exercised.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from portrayal import libwalk
from portrayal import render as render_mod
from portrayal.manifest import seat_point

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"
SCRIPT = SPEC / "tests/js/placed-part-seats.mjs"

CASA_TERMINAL = "casa/c40g-ground-studs@1"
# device -> view -> the ids its index must list: each seat of a placed part, under its placement
NAMED = {
    "c40g": {"rear": {"ground-studs-rear/stud-tr", "ground-studs-rear/stud-bl", "ground-studs-rear/stud-br",
                      "ac-inlet-panel/inlet-psu1", "ac-inlet-panel/inlet-psu2",
                      "ac-inlet-panel/inlet-psu3", "ac-inlet-panel/inlet-psu4"}},
    "7010tx-48": {"rear-dc": {"dc-ps1/lug-1", "dc-ps1/lug-2", "dc-ps2/lug-1", "dc-ps2/lug-2"}},
    "csr180": {"front": {"psu1-input/lug-1", "psu1-input/lug-2", "psu1-input/lug-3",
                         "psu2-input/lug-1", "psu2-input/lug-2", "psu2-input/lug-3"}},
    "csr200": {"front": {"psu1-input/lug-1", "psu1-input/lug-2", "psu1-input/lug-3",
                         "psu2-input/lug-1", "psu2-input/lug-2", "psu2-input/lug-3"}},
    "ex3300-24t": {"rear": {"dc-terminal/lug-1", "dc-terminal/lug-2", "dc-terminal/lug-3", "dc-terminal/lug-4"}},
    "sr-1-dc": {"rear": {"dc-input/a-neg", "dc-input/a-rtn", "dc-input/b-neg", "dc-input/b-rtn"}},
}


@pytest.fixture(scope="module")
def tools():
    return (render_mod.Library([str(LIB)]), render_mod._pluggable_families(),
            render_mod._pluggable_candidates([str(LIB)]), render_mod._connector_registry())


@pytest.fixture(scope="module")
def library(tools):
    """Every view of every device, as the build publishes it: `views` maps (device, view) to its `cages[]`,
    and `rows` holds one row per placement that sits on a face with a ref - whether the device lists a slot
    under the placement's own id, the seats the placed part composes (components.json's answer), and the ids
    of every placement and bay of the device."""
    lib, families, candidates, connectors = tools
    views, rows = {}, []
    for man in libwalk.iter_devices([LIB]):
        device = render_mod.load_yaml(man)
        taken = set()
        for view in (device.get("views") or {}).values():
            parts = render_mod.view_parts(view or {})
            taken.update(p["id"] for p in parts["placements"] if p.get("id"))
            taken.update(b["id"] for b in parts["bays"] if b.get("id"))
        for name in device.get("views") or {}:
            published = render_mod.cage_entries(device, name, lib, families, candidates, {}, connectors=connectors)
            views[(device["name"], name)] = published
            ids = [c["id"] for c in published]
            for p in render_mod.view_parts(device["views"][name] or {})["placements"]:
                if "at" not in p or not p.get("ref"):
                    continue
                seats = render_mod.component_cages(lib.resolve(p["ref"])[0], lib, families, candidates, connectors)
                rows.append({"device": device["name"], "view": name, "placement": p["id"], "seats": seats,
                             "own": p["id"] in ids, "published": published, "taken": taken})
    return views, rows


@pytest.fixture(scope="module")
def survey(library):
    return library[1]


def test_every_named_device_lists_the_seats_of_its_placed_parts(library):
    views = library[0]
    for name, by_view in NAMED.items():
        for view, want in by_view.items():
            got = {c["id"] for c in views[(name, view)]}
            assert want <= got, (name, view, sorted(want - got))


def test_the_casa_studs_and_inlets_are_connector_slots_that_take_a_lug_and_a_plug(library):
    cages = {c["id"]: c for c in library[0][("c40g", "rear")]}
    # the terminal is not itself a slot: its seats are
    assert "ground-studs-rear" not in cages and "ac-inlet-panel" not in cages
    for key in NAMED["c40g"]["rear"]:
        assert cages[key]["kind"] == "connector", key
    for stud in ("stud-tr", "stud-bl", "stud-br"):
        c = cages[f"ground-studs-rear/{stud}"]
        assert c["interface"] == "terminal-stud" and c["accepts"] == ["generic/ring-lug@1"], stud
    for n in (1, 2, 3, 4):
        c = cages[f"ac-inlet-panel/inlet-psu{n}"]
        assert c["interface"] == "iec-c14" and c["accepts"] == ["generic/c13-plug@1"], n
        assert c["only-in"] == ["ac-power"], "the placement's configurations reach its seats"


@pytest.mark.heavy
def test_every_seat_of_a_placed_part_with_no_slot_of_its_own_is_published_once(survey):
    checked = 0
    for r in survey:
        if r["own"] or not r["seats"]:
            continue
        ids = [c["id"] for c in r["published"]]
        for seat in r["seats"]:
            key = f"{r['placement']}/{seat['id']}"
            where = (r["device"], r["view"], key)
            assert ids.count(key) == 1, where
            got = next(c for c in r["published"] if c["id"] == key)
            # the answer components.json carries for the part, re-keyed
            for k in ("interface", "kind", "accepts", "media", "turns", "bores"):
                assert got.get(k) == seat.get(k), (where, k)
            checked += 1
    assert checked > 0, "no placed part composes seats any more: the rule is not exercised"


def test_a_placement_that_presents_a_slot_of_its_own_gets_no_second_key(survey):
    """A duplex adapter, a cage wrapper and a pair of studs list their one opening once, under the
    placement's id; a key for a composed seat as well is what manifest.slot_in_slot refuses."""
    checked = 0
    for r in survey:
        if not (r["own"] and r["seats"]):
            continue
        checked += 1
        under = [c["id"] for c in r["published"] if c["id"].startswith(r["placement"] + "/")]
        assert not under, (r["device"], r["view"], r["placement"], under)
    assert checked > 100, "the adapters, wrappers and pairs that compose seats are no longer placed"


def test_no_seat_key_is_the_id_of_a_placement_a_bay_or_another_slot(survey):
    nested = 0
    for r in survey:
        ids = [c["id"] for c in r["published"]]
        for i in {i for i in ids if "/" in i}:
            nested += 1
            assert i not in r["taken"], (r["device"], r["view"], i)
            assert ids.count(i) == 1, (r["device"], r["view"], i)
    assert nested > 0


@pytest.mark.parametrize("rotate, mirror", [(None, False), (90, False), (None, True)])
def test_the_seats_are_carried_through_the_placement(tools, rotate, mirror):
    lib, families, candidates, connectors = tools
    p = {"id": "t", "ref": CASA_TERMINAL, "at": [10.0, 20.0], "only-in": ["dc"]}
    if rotate:
        p["rotate"] = rotate
    if mirror:
        p["mirror"] = True
    device = {"views": {"rear": {"components": {"placements": [p]}}}}
    got = render_mod.cage_entries(device, "rear", lib, families, candidates, {}, connectors=connectors)
    contract = lib.resolve(CASA_TERMINAL)[0]
    seats = render_mod.component_cages(contract, lib, families, candidates, connectors)
    assert [c["id"] for c in got] == [f"t/{s['id']}" for s in seats] and len(seats) == 3
    size = render_mod._xy_size(contract["size"])
    for c, s in zip(got, seats):
        want = seat_point(p["at"], size, p.get("rotate"), s["mate"])
        assert c["mate"] == pytest.approx(want), c["id"]
        if not rotate:
            # a placement that is not turned only moves the seat
            assert c["mate"] == pytest.approx([10.0 + s["mate"][0], 20.0 + s["mate"][1]]), c["id"]
        assert (c["rotate"] or 0) == (s["rotate"] or 0) + (rotate or 0), c["id"]
        assert c["mirror"] is mirror and c["only-in"] == ["dc"], c["id"]
        assert c["occupant"] is None and c["group"] is None


def test_a_default_occupant_of_a_seat_key_is_published_on_the_seat(tools):
    lib, families, candidates, connectors = tools
    p = {"id": "t", "ref": CASA_TERMINAL, "at": [10.0, 20.0]}
    device = {"views": {"rear": {"components": {"placements": [p]}}}}
    got = render_mod.cage_entries(device, "rear", lib, families, candidates,
                                  {"t/stud-tr": {"ref": "generic/ring-lug@1"}}, connectors=connectors)
    assert {c["id"]: c["occupant"] for c in got} == {
        "t/stud-tr": "generic/ring-lug@1", "t/stud-bl": None, "t/stud-br": None}


def _run(mode):
    if shutil.which("node") is None:
        pytest.skip("node not installed")
    p = subprocess.run(["node", str(SCRIPT), mode], capture_output=True, text=True, cwd=str(SCRIPT.parent))
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout.strip().splitlines()[-1])


def test_the_explorer_lists_a_seat_the_index_and_the_drawing_both_give_once():
    out = _run("once")
    assert out["every"] == ["port-1", "studs/stud-a", "studs/stud-b"]
    assert out["offered"] == out["every"]
    # the entry kept is the drawing's, which names the part and the carrier a swap seats through
    assert out["carriers"] == ["test/studs@1", "test/studs@1"] and out["modulePaths"] == ["studs", "studs"]
    assert out["keptDevice"] and out["at"] == {"id": "studs/stud-b", "carrier": "test/studs@1"}
    assert out["deviceAfter"] == ["port-1", "studs/stud-a", "studs/stud-b"]


def test_a_seat_only_the_index_lists_stays_and_a_seat_only_the_drawing_yields_is_found():
    out = _run("alone")
    assert out["half"] == ["port-1", "studs/stud-c", "studs/stud-a", "studs/stud-b"]
    assert out["halfCarriers"] == [None, None, "test/studs@1", "test/studs@1"]
    assert out["bare"] == ["port-1", "studs/stud-a", "studs/stud-b"]
    assert out["none"] == ["port-1", "studs/stud-a", "studs/stud-b", "studs/stud-c"]
