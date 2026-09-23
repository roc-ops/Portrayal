"""The duplex host: a duplex LC adapter is itself a slot, and that slot and its
two bores are mutually exclusive (B3, docs/pluggables-caps-design.md, "The
duplex host").

`lc-duplex` is a connector interface in spec/schemas/connectors.yaml that SPANS
two `lc` bores: one duplex connector - a duplex dust cap, a duplex plug - is a
single moulding with two ferrules at the 6.25 pitch, so it fills both bores at
once. The two adapters present it at the midpoint of their bores, and the build
and lint each refuse a build in which the adapter's own slot and one of its
bores are both filled.

The figures here are all COMPUTED FROM THE CONTRACTS - the bores' composed mate
points through `manifest.seat_point`, the pitch from spec/schemas/standards.yaml
via the registry - so a test cannot agree with a stale copy of a number.

Nothing in the library ships a duplex occupant yet (Task 5 lands the caps), so
`test/duplex-plug@1` - a `mates: lc-duplex` copy of `generic/lc-plug@2` - stands
in for one, and `generic/lc-plug@2` is the simplex part in a bore.
"""
import math
import shutil
import subprocess
import sys

import pytest
import yaml

from test_nested_occupants import LIB, SPEC, by_path, device_point, is_inside
from test_slot_defaults import (_copy, _lib, _part, build, face, fhd,
                                occupants_drawn, run)

from portrayal import lint
from portrayal.manifest import (CANONICAL_SPAN_AXIS, presented_interface,
                                seat_point, spanned_slots, spanning_axis)
from portrayal.render import (_connector_registry, _pluggable_candidates,
                              _pluggable_families, component_cages)

ADAPTER = "common/lc-duplex-adapter"        # side by side; dcp-r-34d-cs places it
V_ADAPTER = "common/lc-duplex-v-adapter"    # stacked; the FHD cassette composes it
MAJOR = {ADAPTER: 4, V_ADAPTER: 5}
CASSETTE = "fs/fhd-1mtp24-lc-os2-a@3"
PLUG = "generic/lc-plug@2"                  # mates lc - one bore
DUPLEX = "test/duplex-plug@1"               # mates lc-duplex - the pair


# --- the throwaway library ----------------------------------------------------------

@pytest.fixture
def lib(tmp_path):
    root = tmp_path / "lib"

    def duplex(c):
        c["mates"] = "lc-duplex"
    _copy(root, "generic/lc-plug", 2, "duplex-plug", duplex)
    return root


def contract(root, ref):
    return _lib(root).resolve(ref)[0]


def resolver(root):
    lib_ = _lib(root)

    def _res(ref):
        try:
            return lib_.resolve(ref)[0]
        except (FileNotFoundError, ValueError, KeyError):
            return None
    return _res


def bore_mates(root, ref):
    """{part id: composed mate point} for the adapter's two bores, through each
    placement's own rotation - the figures the contract actually states."""
    _res = resolver(root)
    c = _res(ref)
    out = {}
    for q in c["parts"]:
        core = _res(q["ref"])
        out[q["id"]] = seat_point(q["at"], core["size"], q.get("rotate"),
                                  core["connection-points"]["mate"]["at"])
    return out


# STANDARDS IS EMPTY ON A PLAIN IMPORT: lint.py fills it inside main(), so a
# rule called directly finds no entry and L112's pitch arm would pass
# VACUOUSLY - the shape of failure this suite has been bitten by before. Load
# it once, the way main does.
lint.STANDARDS.update(
    lint.load_yaml(SPEC / "schemas/standards.yaml")["standards"])


def standards():
    return dict(lint.STANDARDS)


def test_the_pitch_registry_is_loaded():
    """The guard on every L112 pitch assertion below: an empty registry makes
    the rule skip in silence and every "clean" answer meaningless."""
    assert standards().get("lc-duplex-receptacle", {}).get("pitch")


def duplex_pitch():
    """The pitch `lc-duplex` is, read the way the linter reads it: the
    interface's own standard in spec/schemas/standards.yaml."""
    std = _connector_registry()["lc-duplex"]["standard"]
    entry = standards()[std]
    assert entry["pitch-confidence"] == "verified", entry
    return float(entry["pitch"])


# --- the presented interface --------------------------------------------------------

@pytest.mark.parametrize("name", [ADAPTER, V_ADAPTER])
def test_an_adapter_presents_lc_duplex_at_the_midpoint_of_its_bores(lib, name):
    ref = f"{name}@{MAJOR[name]}"
    c = contract(lib, ref)
    mates = bore_mates(lib, ref)
    assert len(mates) == 2, mates
    mid = [sum(v) / 2 for v in zip(*mates.values())]

    iface, at, lift = presented_interface(c, resolver(lib))
    assert iface == "lc-duplex"
    assert [round(v, 4) for v in at] == [round(v, 4) for v in mid], (at, mid)
    # AND AT THE DEPTH THE BORES ARE. Each bore is lifted onto the adapter's
    # raised bezel by the part's own `lift`; a connector spanning both stands
    # on that same face, so the presented lift is the bezel's `out`.
    bezel = {f["node"]: f["out"] for f in c["relief"]["features"]}["bezel"]
    assert lift == pytest.approx(bezel)
    assert {q.get("lift") for q in c["parts"]} == {bezel}


@pytest.mark.parametrize("name", [ADAPTER, V_ADAPTER])
def test_an_adapter_sits_its_bores_at_the_duplex_pitch(lib, name):
    mates = bore_mates(lib, f"{name}@{MAJOR[name]}")
    (a, b) = mates.values()
    assert math.dist(a, b) == pytest.approx(duplex_pitch(), abs=1e-9)


@pytest.mark.parametrize("name", [ADAPTER, V_ADAPTER])
def test_an_adapter_names_the_bores_its_own_slot_spans(lib, name):
    c = contract(lib, f"{name}@{MAJOR[name]}")
    assert spanned_slots(c, resolver(lib), _connector_registry()) == ["tx", "rx"]


# --- the published entries ----------------------------------------------------------

def cages(root, ref):
    lib_ = _lib(root)
    roots = [str(root), str(LIB)]
    return {e["id"]: e for e in component_cages(
        lib_.resolve(ref)[0], lib_, _pluggable_families(),
        _pluggable_candidates(roots), _connector_registry())}


def test_the_adapter_slot_is_published_with_the_bores_it_spans(lib):
    entry = cages(lib, CASSETTE)["lc01"]
    assert entry["kind"] == "connector"
    assert entry["interface"] == "lc-duplex"
    assert entry["bores"] == ["tx", "rx"]
    assert DUPLEX in entry["accepts"] and PLUG not in entry["accepts"]


def test_an_adapter_declaring_its_own_interface_still_publishes_its_bores(lib):
    """P2 is about FORWARDING: a component presenting its own interface
    forwards nothing, so every part it composes is still a slot of its own."""
    got = cages(lib, f"{V_ADAPTER}@{MAJOR[V_ADAPTER]}")
    assert sorted(got) == ["rx", "tx"]
    for e in got.values():
        assert e["kind"] == "connector" and e["interface"] == "lc"
        assert PLUG in e["accepts"] and DUPLEX not in e["accepts"]
        assert e["bores"] == []         # a bore spans nothing


def test_a_cage_entry_carries_an_empty_bores_list(lib):
    """The key is always published, for the reason `accepts` always is: a cage
    spans nothing, and "spans nothing" has to be tellable from "not a question
    this entry answers"."""
    got = cages(lib, "casa/csc-8x10g@1")
    assert got, "the fixture composes no slots any more"
    assert all(e["kind"] == "cage" and e["bores"] == [] for e in got.values()), got


def test_every_adapter_a_module_composes_names_its_bores(lib):
    """A module holding both kinds: its duplex adapters name their bores and
    its SFP cages name none, in one published list."""
    got = cages(lib, "smartoptics/dcp-f-a22@1")
    spanning = {i: e["bores"] for i, e in got.items()
                if e["interface"] == "lc-duplex"}
    assert spanning and all(b == ["tx", "rx"] for b in spanning.values()), got
    assert [e["bores"] for i, e in got.items() if i not in spanning] == \
        [[] for i in got if i not in spanning]


# --- the build refuses both levels --------------------------------------------------

def capped_cassette(root):
    """A cassette copy whose lc01 is an adapter shipping a cap on its tx bore,
    so that bore is filled with no configuration saying so."""
    def capped(c):
        _part(c, "tx")["default"] = PLUG
    _copy(root, V_ADAPTER, MAJOR[V_ADAPTER], "capped-adapter", capped)

    def swap(c):
        _part(c, "lc01")["ref"] = "test/capped-adapter@1"
    _copy(root, CASSETTE.split("@")[0], 3, "capped-cassette", swap)
    return "test/capped-cassette@1"


def dcp(tmp_path, occupants):
    """smartoptics/dcp-r-34d-cs as it stands - port-1510 places the side-by-side
    adapter - with one configuration carrying `occupants`."""
    dev = shutil.copytree(LIB / "devices/smartoptics/dcp-r-34d-cs",
                          tmp_path / "dcp-r-34d-cs") / "device.yaml"
    d = yaml.safe_load(dev.read_text())
    placed = [p for v in d["views"].values()
              for p in ((v or {}).get("components") or {}).get("placements") or []
              if p.get("id") == "port-1510"]
    assert len(placed) == 1 and placed[0]["ref"] == f"{ADAPTER}@{MAJOR[ADAPTER]}"
    assert not d.get("configurations")
    d["configurations"] = {"default": {"kind": "base", "default": True,
                                       "occupants": occupants}}
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    return dev


def refuses(dev, tmp_path, lib_root, key, bore):
    r = run(dev, tmp_path / "o", lib_root)
    assert r.returncode != 0, r.stdout[-400:]
    want = f"occupants/{key}:"
    assert want in r.stderr and f"its bore {bore} cannot both be filled" in r.stderr, \
        r.stderr[-800:]


def test_a_composed_adapter_refuses_its_slot_and_a_bore(tmp_path, lib):
    dev, _ = fhd(tmp_path, CASSETTE,
                 {"bay-1/lc01": DUPLEX, "bay-1/lc01/tx": PLUG})
    refuses(dev, tmp_path, lib, "bay-1/lc01", "tx")


def test_a_placed_adapter_refuses_its_slot_and_a_bore(tmp_path, lib):
    dev = dcp(tmp_path, {"port-1510": DUPLEX, "port-1510/rx": PLUG})
    refuses(dev, tmp_path, lib, "port-1510", "rx")


def test_a_shipped_bore_counts_as_filled(tmp_path, lib):
    """After defaults resolve: nothing keys the bore, the adapter ships a cap
    in it, and the configuration fills the adapter's own slot."""
    dev, _ = fhd(tmp_path, capped_cassette(lib), {"bay-1/lc01": DUPLEX})
    refuses(dev, tmp_path, lib, "bay-1/lc01", "tx")


def test_emptying_the_shipped_bore_lets_the_duplex_connector_seat(tmp_path, lib):
    dev, _ = fhd(tmp_path, capped_cassette(lib),
                 {"bay-1/lc01": DUPLEX, "bay-1/lc01/tx": ""})
    root, _ = face(build(dev, tmp_path / "o", lib), "fhd-1ufce", "base")
    assert occupants_drawn(root) == {"bay-1/module/lc01-occupant": DUPLEX}


# --- one level at a time still builds -----------------------------------------------

def test_filling_only_the_adapter_slot_builds(tmp_path, lib):
    dev, _ = fhd(tmp_path, CASSETTE, {"bay-1/lc01": DUPLEX})
    root, _ = face(build(dev, tmp_path / "o", lib), "fhd-1ufce", "base")
    assert occupants_drawn(root) == {"bay-1/module/lc01-occupant": DUPLEX}


def test_filling_only_the_bores_builds(tmp_path, lib):
    dev, _ = fhd(tmp_path, CASSETTE,
                 {"bay-1/lc01/tx": PLUG, "bay-1/lc01/rx": PLUG})
    root, _ = face(build(dev, tmp_path / "o", lib), "fhd-1ufce", "base")
    assert occupants_drawn(root) == {"bay-1/module/lc01/tx-occupant": PLUG,
                                     "bay-1/module/lc01/rx-occupant": PLUG}


def test_emptying_the_adapter_slot_is_not_filling_it(tmp_path, lib):
    dev, _ = fhd(tmp_path, CASSETTE, {"bay-1/lc01": "", "bay-1/lc01/tx": PLUG})
    root, _ = face(build(dev, tmp_path / "o", lib), "fhd-1ufce", "base")
    assert occupants_drawn(root) == {"bay-1/module/lc01/tx-occupant": PLUG}


# --- L111 ---------------------------------------------------------------------------

def l111_device(dev, root):
    data = yaml.safe_load(dev.read_text())
    with lint.collecting() as got:
        lint.lint_device_spanned_exclusion(dev, data, [str(root), str(LIB)])
    return [e for e in got.errors if "[L111]" in e]


def l111_component(root, ref):
    ns, rest = ref.split("/", 1)
    name, major = rest.split("@")
    f = root / "components" / ns / name / f"v{major}" / "contract.yaml"
    with lint.collecting() as got:
        lint.lint_component_spanned_exclusion(f, yaml.safe_load(f.read_text()),
                                              [str(root), str(LIB)])
    return [e for e in got.errors if "[L111]" in e]


def test_l111_reports_a_configuration_filling_both_levels(tmp_path, lib):
    dev, _ = fhd(tmp_path, CASSETTE,
                 {"bay-1/lc01": DUPLEX, "bay-1/lc01/tx": PLUG})
    got = l111_device(dev, lib)
    assert got and "bay-1/lc01" in got[0] and "bay-1/lc01/tx" in got[0], got


def test_l111_reports_a_placed_adapter_too(tmp_path, lib):
    dev = dcp(tmp_path, {"port-1510": DUPLEX, "port-1510/rx": PLUG})
    got = l111_device(dev, lib)
    assert got and "port-1510/rx" in got[0], got


def test_l111_reports_a_configured_bore_over_a_shipped_adapter_slot(tmp_path, lib):
    """The other direction: the adapter's own slot ships a duplex cap and the
    configuration fills a bore. Neither key names both levels; both are filled."""
    def ships(c):
        c["default"] = DUPLEX
    _copy(lib, V_ADAPTER, MAJOR[V_ADAPTER], "capped-duplex", ships)

    def swap(c):
        _part(c, "lc01")["ref"] = "test/capped-duplex@1"
    _copy(lib, CASSETTE.split("@")[0], 3, "duplex-cassette", swap)
    dev, _ = fhd(tmp_path, "test/duplex-cassette@1", {"bay-1/lc01/tx": PLUG})
    got = l111_device(dev, lib)
    assert got and "bay-1/lc01/tx" in got[0], got
    # and the build says the same thing
    refuses(dev, tmp_path, lib, "bay-1/lc01", "tx")


def test_l111_is_clean_for_one_level_at_a_time(tmp_path, lib):
    for occ in ({"bay-1/lc01": DUPLEX},
                {"bay-1/lc01/tx": PLUG, "bay-1/lc01/rx": PLUG},
                {"bay-1/lc01": "", "bay-1/lc01/tx": PLUG}):
        dev, _ = fhd(tmp_path / str(abs(hash(str(occ)))), CASSETTE, occ)
        assert l111_device(dev, lib) == [], occ


def test_l111_reports_a_contract_shipping_both_levels(lib):
    def both(c):
        c["default"] = DUPLEX
        _part(c, "tx")["default"] = PLUG
    _copy(lib, V_ADAPTER, MAJOR[V_ADAPTER], "greedy-adapter", both)
    got = l111_component(lib, "test/greedy-adapter@1")
    assert got and "tx" in got[0], got


def test_l111_reports_a_composer_shipping_over_shipped_bores(lib):
    capped_cassette(lib)                # test/capped-adapter@1 ships a cap on tx

    def over(c):
        p = _part(c, "lc01")
        p["ref"], p["default"] = "test/capped-adapter@1", DUPLEX
    _copy(lib, CASSETTE.split("@")[0], 3, "greedy-cassette", over)
    got = l111_component(lib, "test/greedy-cassette@1")
    assert got and "lc01" in got[0], got


def test_l111_is_clean_for_the_library_adapters(lib):
    for name in (ADAPTER, V_ADAPTER):
        assert l111_component(LIB, f"{name}@{MAJOR[name]}") == []


# --- L112 ---------------------------------------------------------------------------

def l112(root, ref):
    ns, rest = ref.split("/", 1)
    name, major = rest.split("@")
    f = root / "components" / ns / name / f"v{major}" / "contract.yaml"
    with lint.collecting() as got:
        lint.lint_component_spanned_geometry(f, yaml.safe_load(f.read_text()),
                                             [str(root), str(LIB)])
    return [e for e in got.errors if "[L112]" in e]


@pytest.mark.parametrize("name", [ADAPTER, V_ADAPTER])
def test_l112_is_clean_for_the_library_adapters(lib, name):
    assert l112(LIB, f"{name}@{MAJOR[name]}") == []


def test_l112_reports_bores_off_the_duplex_pitch(lib):
    """The defect the rule exists for: an adapter drawn to a vendor stencil
    rather than to the interface standard."""
    def narrow(c):
        rx = _part(c, "rx")
        rx["at"] = [rx["at"][0], round(_part(c, "tx")["at"][1] + 6.0, 4)]
    _copy(lib, V_ADAPTER, MAJOR[V_ADAPTER], "narrow-adapter", narrow)
    got = l112(lib, "test/narrow-adapter@1")
    assert got and "6.0" in got[0] and str(duplex_pitch()) in got[0], got


def test_l112_reports_a_mate_off_the_midpoint(lib):
    def moved(c):
        c["connection-points"]["mate"]["at"] = [1.0, 1.0]
    _copy(lib, ADAPTER, MAJOR[ADAPTER], "askew-adapter", moved)
    got = l112(lib, "test/askew-adapter@1")
    assert got and "midpoint" in got[0], got


def test_l112_reports_the_wrong_number_of_bores(lib):
    def one(c):
        c["parts"] = [_part(c, "tx")]
    _copy(lib, ADAPTER, MAJOR[ADAPTER], "lonely-adapter", one)
    got = l112(lib, "test/lonely-adapter@1")
    assert got and "spans 2" in got[0], got


def test_l112_leaves_a_non_spanning_interface_alone(lib):
    """A transceiver composing two bores is not a duplex host: its own
    interface spans nothing, and its bores are its own."""
    assert l112(LIB, "common/sfp-lc-duplex@1") == []
    assert l112(LIB, "std/lc-bore@3") == []


# --- the axis the pair runs on ------------------------------------------------------
#
# A duplex connector is one moulding with two ferrules on an axis and cannot
# turn itself: a seated part takes its host's rotation. The two adapters do not
# agree about that axis - the Smartoptics one puts its bores side by side, the
# FS one stacks them - so a spanning slot publishes the turn that carries the
# canonical drawing axis onto its own pair, and the build seats its occupant at
# that turn. Everything below is computed from the two contracts' own bore
# placements; nothing here reads a name or a ref to decide which way round a
# pair runs.

CAP = "common/lc-duplex-dust-cap@2"         # drawn ACROSS, the canonical axis
REAL_PLUG = "generic/lc-duplex-plug@2"      # likewise
CARD = "smartoptics/dcp-f-a22@1"            # composes two side-by-side adapters


def bore_axis(root, ref):
    """Which way round this adapter's pair runs, read off the two composed
    mate points here rather than taken from the code under test: the right
    angle the first-to-last direction lies nearest."""
    (a, b) = bore_mates(root, ref).values()
    dx, dy = b[0] - a[0], b[1] - a[1]
    assert abs(dx) > 1e-9 or abs(dy) > 1e-9, (a, b)
    if abs(dx) >= abs(dy):
        return 0 if dx >= 0 else 180
    return 90 if dy > 0 else 270


# 270 FOR THE STACKED ADAPTER, NOT 90 - and 270 is the right answer. Since
# common/lc-duplex-v-adapter@5 the LOWER bore is composed first (`tx`, the port
# FS prints as odd), so the first-to-last direction runs UP the plate, and the
# turn that carries the canonical across axis onto it is 270. That turn puts a
# duplex part's half `a` in the lower bore (port 1) and swings its latch, drawn
# up, to the LEFT - the side each bore's own latch tongue faces (std/lc-bore@3
# draws it down; the adapter turns every bore 90). @3 composed the upper bore
# first and derived 90, which drew the duplex plug turned the wrong way round.
AXIS = {ADAPTER: 0, V_ADAPTER: 270}


@pytest.mark.parametrize("name", [ADAPTER, V_ADAPTER])
def test_the_two_adapters_pairs_run_different_ways(lib, name):
    """THE PREMISE OF EVERY TEST BELOW, asserted rather than assumed, and it is
    also what makes the axis worth publishing: one part cannot be drawn right
    for both hosts."""
    assert bore_axis(lib, f"{name}@{MAJOR[name]}") == AXIS[name]
    assert len(set(AXIS.values())) == 2, AXIS


@pytest.mark.parametrize("name", [ADAPTER, V_ADAPTER])
def test_an_adapter_derives_its_axis_from_its_bores(lib, name):
    """`manifest.spanning_axis` answers the turn that carries the canonical
    axis onto the adapter's own, which for a canonical host is 0."""
    c = contract(lib, f"{name}@{MAJOR[name]}")
    got = spanning_axis(c, resolver(lib), _connector_registry())
    assert got == (bore_axis(lib, f"{name}@{MAJOR[name]}") - CANONICAL_SPAN_AXIS) % 360
    assert got == AXIS[name]


def test_a_contract_that_hosts_no_spanning_slot_has_no_axis(lib):
    """None, not 0: "drawn upright" and "not a question this contract answers"
    have to be tellable apart, for the reason `bores: []` is always published."""
    _res, reg = resolver(lib), _connector_registry()
    for ref in ("std/lc-bore@3", "common/sfp-lc-duplex@1", "casa/csc-8x10g@1"):
        assert spanning_axis(contract(lib, ref), _res, reg) is None, ref


SPANNING = [(CASSETTE, "lc01", V_ADAPTER), (CARD, "edfa", ADAPTER)]


@pytest.mark.parametrize("composer,slot,adapter", SPANNING)
def test_a_spanning_slot_publishes_the_axis_its_bores_lie_on(lib, composer, slot,
                                                             adapter):
    """The published entry carries the turn, so a consumer seating a duplex
    part turns it the way the build does.

    NOTHING DECLARES IT: the placement carries no `rotate` of its own, which is
    checked here, so a published one can only have come from the bores."""
    placement = next(q for q in contract(lib, composer)["parts"]
                     if q["id"] == slot)
    assert placement.get("rotate") is None
    assert placement["ref"] == f"{adapter}@{MAJOR[adapter]}"
    entry = cages(lib, composer)[slot]
    assert entry["bores"] == ["tx", "rx"]
    assert entry["rotate"] == AXIS[adapter]


def test_a_slot_that_spans_nothing_still_publishes_its_placements_rotate(lib):
    """The axis is added to a SPANNING slot and to nothing else: a cage keeps
    publishing exactly what its placement declares, `None` included."""
    got = cages(lib, "casa/csc-8x10g@1")
    assert got, "the fixture composes no slots any more"
    for pid, e in got.items():
        q = next(p for p in contract(lib, "casa/csc-8x10g@1")["parts"]
                 if p["id"] == pid)
        assert e["bores"] == [] and e["rotate"] == q.get("rotate"), pid


# --- seated on a real build: the part covers both bores ------------------------------

def dcp2(tmp_path, occupants):
    """smartoptics/dcp-2 in its ILA-node configuration - a dcp-f-a22 in
    `slot-1`, which composes two `common/lc-duplex-adapter@4` on a raised
    block - with one configuration carrying `occupants`. `slot-1/edfa` is the
    first adapter's own spanning slot, three levels down."""
    dev = shutil.copytree(LIB / "devices/smartoptics/dcp-2",
                          tmp_path / "dcp-2") / "device.yaml"
    d = yaml.safe_load(dev.read_text())
    cfg = d["configurations"]["ila-node"]
    assert cfg["bays"]["slot-1"] == CARD, cfg["bays"]
    cfg["occupants"] = occupants
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    return dev


# (which builder, the device slug, the configuration, the occupant key, the
#  path the build draws the host at, which adapter that host is). The two
#  reach a spanning slot by different routes - a cassette in a bay, and a card
#  in a bay whose adapters stand on a raised block at lift 44 - and between
#  them they cover both axes.
SEATS = [
    ("fhd", "fhd-1ufce", "base", "bay-1/lc01", "bay-1/module/lc01", V_ADAPTER),
    ("dcp2", "dcp-2", "ila-node", "slot-1/edfa", "slot-1/module/edfa", ADAPTER),
]


def seat_duplex(tmp_path, lib_root, where, name, config, key, ref):
    if where == "fhd":
        dev, _ = fhd(tmp_path, CASSETTE, {key: ref})
    else:
        dev = dcp2(tmp_path, {key: ref})
    return face(build(dev, tmp_path / "o", lib_root), name, config)


def outline(parents, el, size):
    """An instance's own outline in the DEVICE frame, composed through every
    ancestor: the four corners of its `size` box. Axis-aligned, because every
    turn in this corpus is a right angle."""
    pts = [device_point(parents, el, p)
           for p in ([0, 0], [size["w"], 0], [size["w"], size["h"]],
                     [0, size["h"]])]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def covers(box, pt):
    x0, y0, x1, y1 = box
    return x0 - 1e-6 <= pt[0] <= x1 + 1e-6 and y0 - 1e-6 <= pt[1] <= y1 + 1e-6


def turn_about(pt, centre, deg):
    """`pt` turned about `centre` by `deg`, in whatever frame both are in."""
    dx, dy = pt[0] - centre[0], pt[1] - centre[1]
    rad = math.radians(deg)
    c, s = round(math.cos(rad), 12), round(math.sin(rad), 12)
    return (centre[0] + dx * c - dy * s, centre[1] + dx * s + dy * c)


def bore_points(root, parents, host_path, adapter_ref, lib_root):
    """Each bore's own mate point in the DEVICE frame, through the adapter's
    placement and every ancestor above it."""
    host = by_path(root, host_path)
    return {bid: device_point(parents, host, p)
            for bid, p in bore_mates(lib_root, adapter_ref).items()}


def seated_duplex(tmp_path, lib_root, seat, ref):
    """Build one seating and return (the bores' device points, the occupant's
    device-frame outline, the occupant's device-frame mate point)."""
    where, name, config, key, path, adapter = seat
    root, parents = seat_duplex(tmp_path, lib_root, where, name, config, key, ref)
    occ = by_path(root, f"{path}-occupant")
    assert occ.get("data-ref").rsplit(":", 1)[0] == ref
    # THE OCCUPANT AND ITS HOST ARE IN THE SAME FRAME, which is what makes the
    # two device-frame figures below comparable at all: an occupant is drawn
    # as a SIBLING of its slot, inside whatever group holds them both.
    assert is_inside(parents, occ, parents[by_path(root, path)])
    part = contract(lib_root, ref)
    bores = bore_points(root, parents, path, f"{adapter}@{MAJOR[adapter]}",
                        lib_root)
    assert len(bores) == 2, bores
    return (bores, outline(parents, occ, part["size"]),
            device_point(parents, occ,
                         part["connection-points"]["mate"]["at"]))


@pytest.mark.parametrize("ref", [CAP, REAL_PLUG])
@pytest.mark.parametrize("seat", SEATS, ids=[s[5].split("/")[1] for s in SEATS])
def test_a_duplex_part_covers_both_bores_of_either_adapter(tmp_path, lib, ref, seat):
    """THE ASSERTION THIS TASK EXISTS FOR, on a real build and composed through
    every ancestor: the part seated on a spanning slot lies over BOTH of the
    bores it fills, on the side-by-side adapter and on the stacked one alike.

    Coverage rather than a mate-point equality, because that is the claim a
    cap makes - it is one moulding over two ports and nothing inside it is
    addressable - and it is the claim a reader of the drawing can check."""
    bores, box, _ = seated_duplex(tmp_path, lib, seat, ref)
    for bid, pt in bores.items():
        assert covers(box, pt), (ref, seat[3], bid, pt, box)


@pytest.mark.parametrize("deg", [90, 270])
@pytest.mark.parametrize("ref", [CAP, REAL_PLUG])
@pytest.mark.parametrize("seat", SEATS, ids=[s[5].split("/")[1] for s in SEATS])
def test_the_coverage_check_fails_on_a_mutated_published_rotate(tmp_path, lib,
                                                                ref, seat, deg):
    """NON-VACUITY, by mutating the one number this task publishes.

    CHANGING A SPANNING SLOT'S `rotate` BY d MOVES ITS OCCUPANT IN EXACTLY ONE
    WAY, and that is arithmetic rather than a guess: `render.seat_at` re-solves
    the occupant's `at` so its own `mate` stays on the slot's point whatever
    the turn is, so the whole outline turns about that point by d and nothing
    else about the drawing changes. So the mutation is applied here to the
    outline the build produced, about the occupant's own mate point, and no
    second build is needed to know what a different published rotate would
    have drawn.

    A HALF TURN IS NOT TESTED, and the reason is a real limit of this check: a
    duplex part is a pair on an axis, so turning it 180 maps the pair onto
    itself and leaves both bores covered. What 180 changes is WHICH half lands
    on which bore - tx against rx - and coverage cannot see that. The order is
    held instead by `spanning_axis` reading the bores in declaration order and
    by the plug's halves being checked against the bores by name in
    spec/tests/test_fibre_plugs.py."""
    bores, box, mate = seated_duplex(tmp_path, lib, seat, ref)
    turned = [turn_about(c, mate, deg) for c in
              ((box[0], box[1]), (box[2], box[1]), (box[2], box[3]),
               (box[0], box[3]))]
    xs, ys = [p[0] for p in turned], [p[1] for p in turned]
    mutated = (min(xs), min(ys), max(xs), max(ys))
    assert not all(covers(mutated, pt) for pt in bores.values()), \
        (ref, seat[3], deg, mutated, bores)


# --- L112: a spanning part is drawn on the canonical axis ----------------------------

@pytest.mark.parametrize("ref", [CAP, REAL_PLUG])
def test_l112_is_clean_for_the_librarys_duplex_parts(lib, ref):
    assert l112(LIB, ref) == []


@pytest.mark.parametrize("ref", [CAP, REAL_PLUG])
def test_l112_reports_a_duplex_part_drawn_on_the_wrong_axis(lib, ref):
    """The fault the arm exists for, and it is the state both parts were in
    before this task from one side or the other: a part drawn STACKED. Its
    outline is transposed here - width for height, and every element with it -
    which is exactly the drawing turned onto the other axis."""
    def stacked(c):
        c["size"] = {"w": c["size"]["h"], "h": c["size"]["w"]}
        m = c["connection-points"]["mate"]["at"]
        c["connection-points"]["mate"]["at"] = [m[1], m[0]]
    _copy(lib, ref.split("@")[0], int(ref.split("@")[1]), "tall-duplex", stacked)
    got = l112(lib, "test/tall-duplex@1")
    assert got and "lc-duplex" in got[0] and "across" in got[0].lower(), got


def test_l112_leaves_a_simplex_part_alone(lib):
    """A part mating an interface that spans nothing is not held to any axis:
    it fills one bore and has no pair to line up."""
    for ref in (PLUG, "common/lc-dust-cap@1", "common/lc-boot@1"):
        assert l112(LIB, ref) == [], ref
