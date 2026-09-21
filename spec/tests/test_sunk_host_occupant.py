"""A seated part sinks with a host that stands `in:` a well (pluggables D, Task 5).

A placement that says `in: <well>` is sunk by the well's floor: draw_placement
calls `sink(g, floor_of(well))`, which writes `data-z-lift = -floor` on the
placement's group and pulls every `data-z-out` in it down by `floor`.
relief.js sums data-z-lift up the ANCESTOR chain and reads data-z-out as an
absolute distance from the panel, so both halves are needed and each is read
once.

A `mate-to` occupant is NOT inside its host's group - it is a top-level
sibling - so the host's sink never reached it. The occupant was drawn at the
panel (or at the host's presented lift) while the host face it sits on was
`floor` millimetres further down. The fix carries the host's sink into the
occupant's `host-lift` at resolution time, the same way the host's own seat
lift is already carried, so the draw_placement trio (z_inset, z_group_lift,
data-z-lift) applies it: a negative seat lift is a sink, in the same terms
`sink()` writes.

THE LIBRARY SHIPS NO FITTED DEVICE, and the Task 5 census found no seat on a
sunk host anywhere in it (task-5-report.md). So this seats on a COPY of
s9510-28dc in tmp_path (the spec/tests/test_occupants.py idiom) and gives the
host a well: a std/db9@1 placement, whose `size.d` of 6.73 is its floor under
the aperture rule (not a module, no `behaviour`). The number is chosen for being
unlike any seat lift in the chain, so a term counted twice or dropped shows.
"""
import pathlib
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[2]
SPEC, LIB = ROOT / "spec", ROOT / "library"
SRC = LIB / "devices/ufispace/s9510-28dc"
WELL_REF = "std/db9@1"


def _contract(path):
    return yaml.safe_load((LIB / "components" / path / "contract.yaml").read_text())


def _out_of(contract, node):
    return float(next(f["out"] for f in contract["relief"]["features"] if f["node"] == node))


# Read from the contracts, not restated, so a later contract change moves the
# expectation with it instead of failing for the wrong reason.
FLOOR = float(_contract("std/db9/v1")["size"]["d"])
PLUG_BODY = _out_of(_contract("generic/lc-plug/v1"), "body")
BOOT_BODY = _out_of(_contract("common/lc-boot/v1"), "body")
# generic/sfp-lc-simplex@2 composes std/lc-bore@3 at `lift: 10.0`; written here
# (as test_seat_depth does) because nothing in this task may move it.
OPTIC_PRESENTS = 10.0


def _render(tmp_path, occupants, *, port_in=True, extra=()):
    d = yaml.safe_load((SRC / "device.yaml").read_text())
    for cfg in d["configurations"].values():
        cfg["occupants"] = occupants
    placements = d["views"]["front"]["components"]["placements"]
    if port_in:
        placements.append({"ref": WELL_REF, "id": "well", "at": [120.0, 30.0]})
        port = next(q for q in placements if q.get("id") == "port-4")
        port["in"] = "well"
    placements.extend(extra)
    tmp_path.mkdir(parents=True, exist_ok=True)
    dev = tmp_path / "device.yaml"
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    out = tmp_path / "o"
    out.mkdir()
    r = subprocess.run(
        [sys.executable, str(SPEC / "tools/portrayal/render.py"), str(dev),
         "--library", str(LIB), "--out", str(out)],
        capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-800:]
    root = ET.parse(out / "s9510-28dc.dc.front.svg").getroot()
    return root, {el.get("id"): el for el in root.iter() if el.get("id")}


def _effective_lift(root, target_id):
    """relief.js's `liftOf`: data-z-lift summed from a node up to the root."""
    parents = {c: p for p in root.iter() for c in p}
    node = next(el for el in root.iter() if el.get("id") == target_id)
    total = 0.0
    while node is not None:
        if node.get("data-z-lift") is not None:
            total += float(node.get("data-z-lift"))
        node = parents.get(node)
    return total


def _outs(group):
    return {el.get("id"): float(el.get("data-z-out"))
            for el in group.iter() if el.get("data-z-out") is not None and el.get("id")}


CHAIN = {
    "port-4": "generic/sfp-lc-simplex@2",
    "port-4-occupant": "generic/lc-plug@1",
    "port-4-occupant-occupant": "common/lc-boot@1",
}


def test_the_host_is_sunk_by_the_well_floor(tmp_path):
    """The premise, measured: the fixture really does sink the cage."""
    root, by_id = _render(tmp_path, CHAIN)
    assert FLOOR == pytest.approx(6.73)
    assert by_id["port-4"].get("data-in") == "well"
    assert float(by_id["port-4"].get("data-z-lift")) == pytest.approx(-FLOOR)
    assert _effective_lift(root, "port-4") == pytest.approx(-FLOOR)


def test_every_link_of_a_chain_on_a_sunk_cage_sinks_with_it(tmp_path):
    """Hand arithmetic, floor 6.73. The cage is flush (presents 0) and sunk:
    the optic stands at 0 - 6.73 = -6.73; the plug on the optic at the optic's
    10.0 plus the optic's -6.73 = 3.27; the boot on the plug at the plug body's
    12.5 plus the plug's 3.27 = 15.77. Each link carries the sink ONCE - the
    chain inherits it through host-lift, it is not re-added per link."""
    root, by_id = _render(tmp_path, CHAIN)
    optic = -FLOOR
    plug = OPTIC_PRESENTS + optic
    boot = PLUG_BODY + plug
    assert (optic, plug, boot) == pytest.approx((-6.73, 3.27, 15.77))
    for oid, want in (("port-4-occupant", optic),
                      ("port-4-occupant-occupant", plug),
                      ("port-4-occupant-occupant-occupant", boot)):
        assert float(by_id[oid].get("data-z-lift")) == pytest.approx(want), oid
        # a top-level sibling: its own attribute IS its effective lift
        assert _effective_lift(root, oid) == pytest.approx(want), oid
    # the boot's rear face, where its cable leaves: absolute, lift + length
    assert float(by_id["port-4-occupant-occupant-occupant--body"].get("data-z-out")) \
        == pytest.approx(boot + BOOT_BODY)


def test_the_occupant_moves_by_the_floor_and_nothing_else(tmp_path):
    """The same chain with and without the well: every data-z-lift and every
    data-z-out in each occupant differs by exactly -floor. That is the other
    half of the trio - z_inset carried the sink into the absolute `out`
    figures, not only into the attribute (the attribute alone double-counts
    nothing here but leaves every raised feature at the panel)."""
    _, sunk = _render(tmp_path / "sunk", CHAIN)
    _, flat = _render(tmp_path / "flat", CHAIN, port_in=False)
    measured = 0
    for oid in ("port-4-occupant", "port-4-occupant-occupant",
                "port-4-occupant-occupant-occupant"):
        a = float(sunk[oid].get("data-z-lift") or 0)
        b = float(flat[oid].get("data-z-lift") or 0)
        assert a - b == pytest.approx(-FLOOR), oid
        so, fo = _outs(sunk[oid]), _outs(flat[oid])
        assert so.keys() == fo.keys() and so, oid
        for k in so:
            assert so[k] - fo[k] == pytest.approx(-FLOOR), (oid, k)
            measured += 1
    assert measured >= 3


def test_a_sunk_host_that_presents_a_lift_takes_both_terms_once(tmp_path):
    """A hand-written plug seated on the optic AND standing in the well: it is
    itself sunk by sink() (data-z-lift = -6.73 + its seat 10.0 = 3.27), and a
    boot on it stands at the plug body's 12.5 + the plug's seat 10.0 + the
    plug's sink -6.73 = 15.77. Presented lift, inherited seat and the host's
    own floor - each once."""
    root, by_id = _render(
        tmp_path, {"port-4": "generic/sfp-lc-simplex@2"}, port_in=False,
        extra=[{"ref": WELL_REF, "id": "well", "at": [120.0, 30.0]},
               {"ref": "generic/lc-plug@1", "id": "plug",
                "mate-to": "port-4-occupant", "in": "well"},
               {"ref": "common/lc-boot@1", "id": "boot", "mate-to": "plug"}])
    assert by_id["plug"].get("data-in") == "well"
    assert float(by_id["plug"].get("data-z-lift")) == pytest.approx(OPTIC_PRESENTS - FLOOR)
    want = PLUG_BODY + OPTIC_PRESENTS - FLOOR
    assert want == pytest.approx(15.77)
    assert float(by_id["boot"].get("data-z-lift")) == pytest.approx(want)
    assert _effective_lift(root, "boot") == pytest.approx(want)
    assert float(by_id["boot--body"].get("data-z-out")) == pytest.approx(want + BOOT_BODY)


def test_a_host_in_no_well_seats_exactly_as_before(tmp_path):
    """No `in:`, no change: the Task 4 numbers, 0 / 10.0 / 22.5."""
    _, by_id = _render(tmp_path, CHAIN, port_in=False)
    assert by_id["port-4-occupant"].get("data-z-lift") is None
    assert float(by_id["port-4-occupant-occupant"].get("data-z-lift")) == OPTIC_PRESENTS
    assert float(by_id["port-4-occupant-occupant-occupant"].get("data-z-lift")) == \
        pytest.approx(OPTIC_PRESENTS + PLUG_BODY)


def test_a_sunk_cage_publishes_its_sink_as_its_lift(tmp_path):
    """`cages[].lift` is documented as what the mate-to resolution carries as
    `host-lift`, so a cage in a well publishes -floor: a consumer seating an
    optic there (the kit refuses any non-zero lift) declines it rather than
    seating it at the panel. A cage in no well still publishes 0.0."""
    import json
    _render(tmp_path, {})
    cages = {c["id"]: c for c in json.loads(
        (tmp_path / "o" / "s9510-28dc.configs.json").read_text())["cages"]["front"]}
    assert cages["port-4"]["lift"] == pytest.approx(-FLOOR)
    assert cages["port-5"]["lift"] == 0.0


def test_an_occupant_that_stands_in_its_sunk_hosts_well_is_refused(tmp_path):
    """The host's sink already reaches its occupant through host-lift, so an
    `in:` on the occupant as well would sink it twice: measured -3.46 where
    3.27 is right (final review I2). Refused, naming both, the way a rotate
    that disagrees with the host is refused."""
    d = yaml.safe_load((SRC / "device.yaml").read_text())
    for cfg in d["configurations"].values():
        cfg["occupants"] = {"port-4": "generic/sfp-lc-simplex@2"}
    placements = d["views"]["front"]["components"]["placements"]
    placements.append({"ref": WELL_REF, "id": "well", "at": [120.0, 30.0]})
    next(q for q in placements if q.get("id") == "port-4")["in"] = "well"
    placements.append({"ref": "generic/lc-plug@1", "id": "plug",
                       "mate-to": "port-4-occupant", "in": "well"})
    dev = tmp_path / "device.yaml"
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    out = tmp_path / "o"
    out.mkdir()
    r = subprocess.run(
        [sys.executable, str(SPEC / "tools/portrayal/render.py"), str(dev),
         "--library", str(LIB), "--out", str(out)],
        capture_output=True, text=True)
    assert r.returncode != 0
    assert "plug" in r.stderr and "'port-4-occupant'" in r.stderr, r.stderr[-800:]
    assert "sinks with its host" in r.stderr, r.stderr[-800:]
