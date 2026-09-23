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
`test/duplex-plug@1` - a `mates: lc-duplex` copy of `generic/lc-plug@1` - stands
in for one, and `generic/lc-plug@1` is the simplex part in a bore.
"""
import math
import shutil
import subprocess
import sys

import pytest
import yaml

from test_nested_occupants import LIB, SPEC
from test_slot_defaults import (_copy, _lib, _part, build, face, fhd,
                                occupants_drawn, run)

from portrayal import lint
from portrayal.manifest import presented_interface, seat_point, spanned_slots
from portrayal.render import (_connector_registry, _pluggable_candidates,
                              _pluggable_families, component_cages)

ADAPTER = "common/lc-duplex-adapter"        # side by side; dcp-r-34d-cs places it
V_ADAPTER = "common/lc-duplex-v-adapter"    # stacked; the FHD cassette composes it
MAJOR = {ADAPTER: 4, V_ADAPTER: 4}
CASSETTE = "fs/fhd-1mtp24-lc-os2-a@3"
PLUG = "generic/lc-plug@1"                  # mates lc - one bore
DUPLEX = "test/duplex-plug@1"               # mates lc-duplex - the pair


# --- the throwaway library ----------------------------------------------------------

@pytest.fixture
def lib(tmp_path):
    root = tmp_path / "lib"

    def duplex(c):
        c["mates"] = "lc-duplex"
    _copy(root, "generic/lc-plug", 1, "duplex-plug", duplex)
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
