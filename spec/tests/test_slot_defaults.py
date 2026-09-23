"""The shipped default: what a slot holds when no configuration says otherwise
(B3, docs/pluggables-caps-design.md "The shipped default", decisions 4-5).

A slot's default is declared on the part that presents it: `default:` on a
`parts:` entry for a composed bore, or a top-level `default:` on a component
for its own presented slot. Precedence, lowest first (P5):
  1. the slot part's own declaration (a component's top-level `default:`);
  2. a composer's `parts:` entry `default:`, which overrides the placed
     component's TOP-LEVEL default only - never a grandchild's;
  3. a configuration's `occupants:` (`""` empties the slot);
  4. the explorer.
A default is the product's shipped state, so it seats in EVERY configuration
unless that configuration's `occupants:` overrides it.

Every test writes throwaway contracts into a tmp_path library searched BEFORE
the real one, and seats on a copy of a real device. The real adapters ship
caps since B3 task 8 (test_shipped_caps.py); a throwaway copied from one has
them removed first (`_unshipped`), and the caps the rest of a copied device
ships are left out of what is compared (`SHIPPED_CAPS`). `generic/lc-plug@2`
stands in for a dust cap, as it did before the caps landed (Task 5);
`test/other-plug@1` is a second `mates: lc` part.
"""
import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest
import yaml

from test_nested_occupants import (LIB, SPEC, assert_same_turn, by_path,
                                   device_point, is_inside)

from portrayal import lint
from portrayal.manifest import presented_interface
from portrayal.render import (Library, _connector_registry, _pluggable_candidates,
                              _pluggable_families, component_cages)

PLUG = "generic/lc-plug@2"
OTHER = "test/other-plug@1"
CASSETTE = "fs/fhd-1mtp24-lc-os2-a"
V_ADAPTER = "common/lc-duplex-v-adapter"     # what the cassette composes (@5)
H_ADAPTER = "common/lc-duplex-adapter"       # what dcp-r-34d-cs places (@5)


# --- the throwaway library ---------------------------------------------------------

def _copy(lib, src, major, name, edit):
    """library/components/<src>/v<major> copied to test/<name>/v1, its contract
    renamed and passed through `edit`."""
    dst = lib / "components" / "test" / name / "v1"
    shutil.copytree(LIB / "components" / src / f"v{major}", dst)
    f = dst / "contract.yaml"
    c = yaml.safe_load(f.read_text())
    c["name"] = name
    c["version"] = "1.0.0"
    c.pop("superseded-by", None)
    edit(c)
    f.write_text(yaml.safe_dump(c, sort_keys=False, allow_unicode=True))
    return f


def _unshipped(edit):
    """`edit`, applied to a copy of a REAL adapter with the caps it ships
    removed first. Those defaults are the product's (common/lc-duplex-v-adapter@5
    ships a duplex cap on its own slot, common/lc-duplex-adapter@5 a cap in each
    bore - test_shipped_caps.py), and every throwaway here is built to exercise
    ONE default at a time, which a second, shipped one would collide with
    (L111) or mask."""
    def wrapped(c):
        c.pop("default", None)
        for q in c.get("parts") or []:
            q.pop("default", None)
        edit(c)
    return wrapped


def _part(c, pid):
    return next(q for q in c["parts"] if q["id"] == pid)


def _set(**kw):
    def edit(c):
        c.update(kw)
    return edit


@pytest.fixture
def lib(tmp_path):
    root = tmp_path / "lib"

    # a bore default on a composed part: tx ships plugged, rx does not
    def capped(c):
        _part(c, "tx")["default"] = PLUG
    _copy(root, V_ADAPTER, 5, "capped-adapter", _unshipped(capped))

    def cassette_with(ref):
        def edit(c):
            _part(c, "lc01")["ref"] = ref
        return edit
    _copy(root, CASSETTE, 3, "capped-cassette", cassette_with("test/capped-adapter@1"))

    _copy(root, "generic/lc-plug", 2, "other-plug", lambda c: None)

    # a component's own presented slot, defaulted at the top level
    _copy(root, "std/lc-bore", 3, "defaulted-bore", _set(default=PLUG))

    # an adapter that IS a slot (top-level default) and whose bores are slots
    # with defaults of their own: tx overridden by this adapter's parts entry,
    # rx left to the bore's own top-level default
    def self_adapter(c):
        c["interface"] = "lc"
        c["default"] = PLUG
        c.setdefault("connection-points", {})["mate"] = {"at": [4.64, 6.875],
                                                         "direction": "front"}
        tx, rx = _part(c, "tx"), _part(c, "rx")
        tx["ref"] = rx["ref"] = "test/defaulted-bore@1"
        tx["default"] = OTHER
    _copy(root, V_ADAPTER, 5, "self-adapter", _unshipped(self_adapter))

    # the composer: lc01 overrides the adapter's own default, lc02 leaves it,
    # lc03 empties it
    def composer(c):
        for pid, extra in (("lc01", {"default": OTHER}), ("lc02", {}),
                           ("lc03", {"default": ""})):
            p = _part(c, pid)
            p["ref"] = "test/self-adapter@1"
            p.pop("default", None)
            p.update(extra)
    _copy(root, CASSETTE, 3, "composer-cassette", composer)

    # the same adapter shape at device level, for dcp-r-34d-cs's port-1510
    def h_adapter(c):
        c["interface"] = "lc"
        c["default"] = PLUG
        c.setdefault("connection-points", {})["mate"] = {"at": [6.6, 5.5],
                                                         "direction": "front"}
    _copy(root, H_ADAPTER, 5, "self-hadapter", _unshipped(h_adapter))
    return root


def _lib(root):
    return Library([str(root), str(LIB)])


def _contract(root, ref):
    return _lib(root).resolve(ref)[0]


# --- devices -----------------------------------------------------------------------

def fhd(tmp_path, cassette, occupants=None, every_config=True):
    """fs/fhd-1ufce with `cassette` in bay-1 of EVERY configuration, and
    `occupants` on the base configuration only."""
    dev = shutil.copytree(LIB / "devices/fs/fhd-1ufce", tmp_path / "fhd-1ufce") / "device.yaml"
    d = yaml.safe_load(dev.read_text())
    for name, cfg in d["configurations"].items():
        if every_config or name == "base":
            cfg["bays"] = {**(cfg.get("bays") or {}), "bay-1": cassette}
    if occupants is not None:
        d["configurations"]["base"]["occupants"] = occupants
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    return dev, list(d["configurations"])


def dcp(tmp_path, occupants=None):
    """smartoptics/dcp-r-34d-cs with port-1510 placing test/self-hadapter@1."""
    dev = shutil.copytree(LIB / "devices/smartoptics/dcp-r-34d-cs",
                          tmp_path / "dcp-r-34d-cs") / "device.yaml"
    d = yaml.safe_load(dev.read_text())
    n = 0
    for view in d["views"].values():
        for p in ((view or {}).get("components") or {}).get("placements") or []:
            if p.get("id") == "port-1510":
                p["ref"] = "test/self-hadapter@1"
                n += 1
    assert n == 1, "port-1510 is no longer placed once"
    if occupants is not None:
        assert not d.get("configurations")
        d["configurations"] = {"default": {"kind": "base", "default": True,
                                           "occupants": occupants}}
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    return dev


def run(dev, out, root):
    return subprocess.run([sys.executable, str(SPEC / "tools/portrayal/render.py"), str(dev),
                           "--library", str(root), "--library", str(LIB),
                           "--out", str(out)],
                          capture_output=True, text=True)


def build(dev, out, root):
    r = run(dev, out, root)
    assert r.returncode == 0, r.stderr[-800:]
    return out


def face(out, name, config, view="front"):
    root = ET.parse(out / f"{name}.{config}.{view}.svg").getroot()
    return root, {c: p for p in root.iter() for c in p}


# THE CAPS THE REAL ADAPTERS SHIP (test_shipped_caps.py). Every device these
# tests copy also places real adapters the throwaways do not replace - the
# other cassettes of a configuration, the DCP's other ports - and those draw
# their shipped caps. They are the product's, not the mechanism under test,
# so they are left out of what these tests compare; no throwaway here ships one.
SHIPPED_CAPS = {"common/lc-dust-cap@1", "common/lc-duplex-dust-cap@2",
                "common/sc-dust-cap@1", "common/mpo-dust-cap@2"}


def occupants_drawn(root):
    """{data-path: occupant ref} for every seated occupant in a drawing, bar
    the real adapters' shipped caps (SHIPPED_CAPS)."""
    return {n.get("data-path"): n.get("data-ref").rsplit(":", 1)[0]
            for n in root.iter()
            if (n.get("data-path") or "").endswith("-occupant")
            and n.get("data-ref").rsplit(":", 1)[0] not in SHIPPED_CAPS}


def assert_seated(root, parents, holder_path, host_id, host_ref, root_lib):
    """The occupant is inside the holder's group, names its host, and lands its
    own mate on the host's to 1e-6, turned with it."""
    holder = by_path(root, holder_path)
    host = by_path(root, f"{holder_path}/{host_id}")
    occ = by_path(root, f"{holder_path}/{host_id}-occupant")
    assert is_inside(parents, occ, holder)
    assert occ.get("data-for") == f"{holder_path}/{host_id}"
    lib_ = _lib(root_lib)
    _, hm, _lift = presented_interface(lib_.resolve(host_ref)[0],
                                       lambda r: lib_.resolve(r)[0])
    hx, hy = device_point(parents, host, hm)
    occ_ref = occ.get("data-ref").rsplit(":", 1)[0]
    ox, oy = device_point(parents, occ,
                          lib_.resolve(occ_ref)[0]["connection-points"]["mate"]["at"])
    assert abs(hx - ox) < 1e-6 and abs(hy - oy) < 1e-6, ((hx, hy), (ox, oy))
    assert_same_turn(parents, occ, host)


# --- a bore's default ----------------------------------------------------------------

def test_an_unconfigured_bore_draws_its_default_in_every_configuration(tmp_path, lib):
    dev, configs = fhd(tmp_path, "test/capped-cassette@1")
    assert len(configs) > 1, "every configuration needs more than one"
    out = build(dev, tmp_path / "o", lib)
    for cfg in configs:
        root, parents = face(out, "fhd-1ufce", cfg)
        assert occupants_drawn(root) == {"bay-1/module/lc01/tx-occupant": PLUG}, cfg
        assert_seated(root, parents, "bay-1/module/lc01", "tx", "std/lc-bore@3", lib)


def test_an_empty_string_empties_a_default(tmp_path, lib):
    dev, _ = fhd(tmp_path, "test/capped-cassette@1", {"bay-1/lc01/tx": ""})
    root, _ = face(build(dev, tmp_path / "o", lib), "fhd-1ufce", "base")
    by_path(root, "bay-1/module/lc01/tx")           # the bore is drawn,
    assert occupants_drawn(root) == {}              # and nothing seated on it


def test_a_configured_occupant_replaces_a_default(tmp_path, lib):
    dev, _ = fhd(tmp_path, "test/capped-cassette@1", {"bay-1/lc01/tx": OTHER})
    out = build(dev, tmp_path / "o", lib)
    root, parents = face(out, "fhd-1ufce", "base")
    assert occupants_drawn(root) == {"bay-1/module/lc01/tx-occupant": OTHER}
    assert_seated(root, parents, "bay-1/module/lc01", "tx", "std/lc-bore@3", lib)
    # the override is the configuration's alone: the other one ships the default
    root, _ = face(out, "fhd-1ufce", "populated")
    assert occupants_drawn(root) == {"bay-1/module/lc01/tx-occupant": PLUG}


def test_a_configured_chain_seats_on_a_default(tmp_path, lib):
    """A boot keyed on the default plug's produced id seats on it."""
    dev, _ = fhd(tmp_path, "test/capped-cassette@1",
                 {"bay-1/lc01/tx-occupant": "common/lc-boot@1"})
    root, _ = face(build(dev, tmp_path / "o", lib), "fhd-1ufce", "base")
    assert occupants_drawn(root) == {
        "bay-1/module/lc01/tx-occupant": PLUG,
        "bay-1/module/lc01/tx-occupant-occupant": "common/lc-boot@1"}


# --- precedence (P5) -----------------------------------------------------------------

EXPECTED_COMPOSED = {
    # lc01: the composer's parts entry overrides the adapter's top-level default
    "bay-1/module/lc01-occupant": OTHER,
    # lc02: the adapter's own top-level default
    "bay-1/module/lc02-occupant": PLUG,
    # lc03: the composer's "" empties it - no lc03-occupant
    # and on every adapter, the composer does NOT reach its bores: tx is the
    # adapter's parts entry (OTHER), rx is the bore's own top-level default
    **{f"bay-1/module/lc0{n}/{b}-occupant": want
       for n in (1, 2, 3) for b, want in (("tx", OTHER), ("rx", PLUG))},
}


def test_a_composer_overrides_the_top_level_default_only(tmp_path, lib):
    dev, _ = fhd(tmp_path, "test/composer-cassette@1")
    root, parents = face(build(dev, tmp_path / "o", lib), "fhd-1ufce", "base")
    assert occupants_drawn(root) == EXPECTED_COMPOSED
    assert_seated(root, parents, "bay-1/module", "lc01", "test/self-adapter@1", lib)
    assert_seated(root, parents, "bay-1/module/lc02", "rx", "test/defaulted-bore@1", lib)


def test_a_configuration_reaches_a_grandchild_default(tmp_path, lib):
    dev, _ = fhd(tmp_path, "test/composer-cassette@1",
                 {"bay-1/lc01/rx": "", "bay-1/lc03": OTHER})
    root, _ = face(build(dev, tmp_path / "o", lib), "fhd-1ufce", "base")
    want = dict(EXPECTED_COMPOSED)
    del want["bay-1/module/lc01/rx-occupant"]
    want["bay-1/module/lc03-occupant"] = OTHER
    assert occupants_drawn(root) == want


# --- device level -------------------------------------------------------------------

def test_a_placed_slots_top_level_default_seats_at_device_level(tmp_path, lib):
    out = build(dcp(tmp_path), tmp_path / "o", lib)
    root, parents = face(out, "dcp-r-34d-cs", "default")
    assert occupants_drawn(root) == {"port-1510-occupant": PLUG}
    occ = by_path(root, "port-1510-occupant")
    assert occ.get("data-for") == "port-1510"


@pytest.mark.parametrize("occ, want", [
    ({"port-1510": ""}, {}),
    ({"port-1510": OTHER}, {"port-1510-occupant": OTHER}),
])
def test_a_configuration_overrides_a_device_level_default(tmp_path, lib, occ, want):
    out = build(dcp(tmp_path, occ), tmp_path / "o", lib)
    root, _ = face(out, "dcp-r-34d-cs", "default")
    assert occupants_drawn(root) == want


# --- the published slot entries --------------------------------------------------------

def _cages(root, ref):
    lib_ = _lib(root)
    cands = _pluggable_candidates([str(root), str(LIB)])
    return {e["id"]: e for e in component_cages(lib_.resolve(ref)[0], lib_,
                                                  _pluggable_families(), cands,
                                                  _connector_registry())}


def test_components_json_publishes_the_resolved_default(lib):
    capped = _cages(lib, "test/capped-adapter@1")
    assert {k: e["default"] for k, e in capped.items()} == {"tx": PLUG, "rx": None}
    assert PLUG in capped["tx"]["accepts"]
    self_ = _cages(lib, "test/self-adapter@1")
    assert {k: e["default"] for k, e in self_.items()} == {"tx": OTHER, "rx": PLUG}
    comp = _cages(lib, "test/composer-cassette@1")
    got = {k: comp[k]["default"] for k in ("lc01", "lc02", "lc03")}
    assert got == {"lc01": OTHER, "lc02": PLUG, "lc03": None}
    # every other adapter on it is the stock one, which is a slot of its own
    # since B3 task 4 and ships FS's duplex cap since B3 task 8
    assert set(comp) == {f"lc{n:02d}" for n in range(1, 13)}
    assert all(comp[k]["default"] == "common/lc-duplex-dust-cap@2"
               for k in comp if k not in got)


def test_configs_json_publishes_the_resolved_default(tmp_path, lib):
    out = build(dcp(tmp_path), tmp_path / "o", lib)
    idx = json.loads((out / "dcp-r-34d-cs.configs.json").read_text())
    entries = [e for es in idx["cages"].values() for e in es]
    assert entries, "the device publishes no slots"
    assert all("default" in e for e in entries)
    got = {e["id"]: e["default"] for e in entries if e["id"] == "port-1510"}
    assert got == {"port-1510": PLUG}
    assert sum(1 for e in entries if e["default"] is None) > 0


# --- L110 ----------------------------------------------------------------------------

def l110(root, ref):
    ns, rest = ref.split("/", 1)
    name, major = rest.split("@")
    f = root / "components" / ns / name / f"v{major}" / "contract.yaml"
    data = yaml.safe_load(f.read_text())
    with lint.collecting() as got:
        lint.lint_component_slot_defaults(f, data, [str(root), str(LIB)])
    return [e for e in got.errors if "[L110]" in e]


@pytest.mark.parametrize("ref", ["test/capped-adapter@1", "test/defaulted-bore@1",
                                 "test/self-adapter@1", "test/composer-cassette@1",
                                 "test/self-hadapter@1"])
def test_lint_the_throwaway_defaults_are_clean(lib, ref):
    assert l110(lib, ref) == []


def test_lint_a_default_the_slot_does_not_accept(lib):
    def bad(c):
        _part(c, "tx")["default"] = "common/lc-boot@1"      # mates lc-plug
    _copy(lib, V_ADAPTER, 5, "bad-adapter", _unshipped(bad))
    got = l110(lib, "test/bad-adapter@1")
    assert got and "tx" in got[0] and "common/lc-boot@1" in got[0], got


def test_lint_a_top_level_default_the_slot_does_not_accept(lib):
    _copy(lib, "std/lc-bore", 3, "bad-bore", _set(default="common/lc-boot@1"))
    got = l110(lib, "test/bad-bore@1")
    assert got and "common/lc-boot@1" in got[0], got


def test_lint_a_default_on_a_part_that_is_no_slot(lib):
    def bad(c):
        # a splice tray presents no interface, so nothing can seat on it - the
        # stock adapter is a slot of its own since B3 task 4 and no longer
        # answers this question
        p = _part(c, "lc01")
        p["ref"], p["default"] = "common/fibre-splice@1", PLUG
    _copy(lib, CASSETTE, 3, "bad-cassette", bad)
    got = l110(lib, "test/bad-cassette@1")
    assert got and "lc01" in got[0] and "no slot" in got[0], got


def test_lint_a_top_level_default_on_a_component_that_is_no_slot(lib):
    # the CASSETTE, which presents no interface of its own and composes twelve
    # apertures rather than one, so it forwards nothing either
    _copy(lib, CASSETTE, 3, "bad-self", _set(default=PLUG))
    got = l110(lib, "test/bad-self@1")
    assert got and "no slot" in got[0], got


# --- a default on a part that got there some other way -------------------------------

BOOT = "common/lc-boot@1"


@pytest.fixture
def booted(lib):
    """A plug whose contract ships a boot on its own rear slot, and an adapter
    whose bore ships that plug."""
    _copy(lib, "generic/lc-plug", 2, "booted-plug", _set(default=BOOT))

    def capped(c):
        _part(c, "tx")["default"] = "test/booted-plug@1"
    _copy(lib, V_ADAPTER, 5, "booted-adapter", _unshipped(capped))
    _copy(lib, CASSETTE, 3, "booted-cassette",
          lambda c: _part(c, "lc01").update({"ref": "test/booted-adapter@1"}))
    return lib


def test_a_configured_occupant_brings_its_own_default(tmp_path, booted):
    """The occupant path: a plug seated by a configuration ships its boot,
    whatever seated the plug (the nested seat, inside the cassette)."""
    dev, _ = fhd(tmp_path, "test/capped-cassette@1",
                 {"bay-1/lc01/tx": "test/booted-plug@1"})
    root, _ = face(build(dev, tmp_path / "o", booted), "fhd-1ufce", "base")
    assert occupants_drawn(root) == {
        "bay-1/module/lc01/tx-occupant": "test/booted-plug@1",
        "bay-1/module/lc01/tx-occupant-occupant": BOOT}


def test_a_default_occupant_brings_its_own_default(tmp_path, booted):
    """And a plug seated as the BORE's default ships the same boot: two
    defaults, one on the other, neither configured."""
    dev, _ = fhd(tmp_path, "test/booted-cassette@1")
    root, _ = face(build(dev, tmp_path / "o", booted), "fhd-1ufce", "base")
    assert occupants_drawn(root) == {
        "bay-1/module/lc01/tx-occupant": "test/booted-plug@1",
        "bay-1/module/lc01/tx-occupant-occupant": BOOT}


def test_a_configuration_empties_a_chained_default(tmp_path, booted):
    """The chained default stays addressable: the produced id empties it."""
    dev, _ = fhd(tmp_path, "test/booted-cassette@1",
                 {"bay-1/lc01/tx-occupant": ""})
    root, _ = face(build(dev, tmp_path / "o", booted), "fhd-1ufce", "base")
    assert occupants_drawn(root) == {
        "bay-1/module/lc01/tx-occupant": "test/booted-plug@1"}


def test_a_device_level_occupant_brings_its_own_default(tmp_path, booted):
    """The same on the device-level path, where the occupant is expanded into
    a mate-to placement."""
    out = build(dcp(tmp_path, {"port-1510": "test/booted-plug@1"}),
                tmp_path / "o", booted)
    root, _ = face(out, "dcp-r-34d-cs", "default")
    assert occupants_drawn(root) == {"port-1510-occupant": "test/booted-plug@1",
                                     "port-1510-occupant-occupant": BOOT}


def test_a_device_level_chained_default_is_addressable(tmp_path, booted):
    out = build(dcp(tmp_path, {"port-1510": "test/booted-plug@1",
                               "port-1510-occupant": ""}),
                tmp_path / "o", booted)
    root, _ = face(out, "dcp-r-34d-cs", "default")
    assert occupants_drawn(root) == {"port-1510-occupant": "test/booted-plug@1"}


def test_a_device_level_default_brings_its_own_default(tmp_path, booted):
    """The placed slot's own default ships its boot too: port-1510 defaults to
    the plug (test/self-hplug@1 below is the same adapter, defaulted)."""
    def h_adapter(c):
        c["interface"] = "lc"
        c["default"] = "test/booted-plug@1"
        c.setdefault("connection-points", {})["mate"] = {"at": [6.6, 5.5],
                                                         "direction": "front"}
    _copy(booted, H_ADAPTER, 5, "booted-hadapter", _unshipped(h_adapter))
    dev = dcp(tmp_path)
    d = yaml.safe_load(dev.read_text())
    for view in d["views"].values():
        for p in ((view or {}).get("components") or {}).get("placements") or []:
            if p.get("id") == "port-1510":
                p["ref"] = "test/booted-hadapter@1"
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    root, _ = face(build(dev, tmp_path / "o", booted), "dcp-r-34d-cs", "default")
    assert occupants_drawn(root) == {"port-1510-occupant": "test/booted-plug@1",
                                     "port-1510-occupant-occupant": BOOT}


# --- a bay module's own default has no key, and is refused -----------------------------

def test_a_bay_module_shipping_a_default_is_an_error(tmp_path, lib):
    """A module seated in a BAY may not ship an occupant on its own slot: a
    bay module's slot has no `occupants:` key, so nothing could empty it.
    Refused by name rather than dropped in silence (B3)."""
    dev, _ = fhd(tmp_path, "test/self-adapter@1")
    r = run(dev, tmp_path / "o", lib)
    assert r.returncode != 0
    assert "test/self-adapter@1 ships holding generic/lc-plug@2" in r.stderr, r.stderr[-800:]
    assert "bay-1" in r.stderr and "no slot key" in r.stderr


def test_a_module_in_a_nested_bay_is_refused_the_same_way(tmp_path, lib):
    """The same refusal one level down, where a card's own bay seats it."""
    dev = shutil.copytree(LIB / "devices/cisco/asr-9010",
                          tmp_path / "asr-9010") / "device.yaml"
    d = yaml.safe_load(dev.read_text())
    cfg = d["configurations"]["ac"]
    cfg["bays"] = {**(cfg.get("bays") or {}), "slot-0": "cisco/a9k-mod160-tr@1",
                   "slot-0/bay-0": "test/self-adapter@1"}
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    r = run(dev, tmp_path / "o", lib)
    assert r.returncode != 0
    assert "test/self-adapter@1 ships holding generic/lc-plug@2" in r.stderr, r.stderr[-800:]
    assert "slot-0/module/bay-0" in r.stderr


def test_a_bay_module_whose_parts_ship_defaults_is_fine(tmp_path, lib):
    """Only the module's OWN slot is refused: the defaults declared inside it,
    on its `parts:`, seat as they do anywhere else - which is the whole of the
    cassette case above."""
    dev, _ = fhd(tmp_path, "test/capped-cassette@1")
    root, _ = face(build(dev, tmp_path / "o", lib), "fhd-1ufce", "base")
    assert occupants_drawn(root) == {"bay-1/module/lc01/tx-occupant": PLUG}


# --- two slots shipping the same part, and a real cycle ---------------------------------

def test_sibling_slots_shipping_the_same_default_each_ship_its_chain(tmp_path, booted):
    """THE GUARD IS THE CHAIN, NOT THE REF. Both bores of an adapter ship the
    same plug, and that plug ships a boot: two plugs and TWO boots. A guard
    that deduped by ref value would seat the second plug and drop its boot."""
    def both(c):
        for pid in ("tx", "rx"):
            _part(c, pid)["default"] = "test/booted-plug@1"
    _copy(booted, V_ADAPTER, 5, "twice-booted-adapter", _unshipped(both))
    _copy(booted, CASSETTE, 3, "twice-booted-cassette",
          lambda c: _part(c, "lc01").update({"ref": "test/twice-booted-adapter@1"}))
    dev, _ = fhd(tmp_path, "test/twice-booted-cassette@1")
    root, _ = face(build(dev, tmp_path / "o", booted), "fhd-1ufce", "base")
    assert occupants_drawn(root) == {
        "bay-1/module/lc01/tx-occupant": "test/booted-plug@1",
        "bay-1/module/lc01/tx-occupant-occupant": BOOT,
        "bay-1/module/lc01/rx-occupant": "test/booted-plug@1",
        "bay-1/module/lc01/rx-occupant-occupant": BOOT}


def test_sibling_placements_shipping_the_same_default_each_ship_its_chain(tmp_path, booted):
    """The same on the device-level path: two ports shipping one plug."""
    def h_adapter(c):
        c["interface"] = "lc"
        c["default"] = "test/booted-plug@1"
        c.setdefault("connection-points", {})["mate"] = {"at": [6.6, 5.5],
                                                         "direction": "front"}
    _copy(booted, H_ADAPTER, 5, "booted-hadapter", _unshipped(h_adapter))
    dev = dcp(tmp_path)
    d = yaml.safe_load(dev.read_text())
    n = 0
    for view in d["views"].values():
        for p in ((view or {}).get("components") or {}).get("placements") or []:
            if p.get("id") in ("port-1510", "port-line"):
                p["ref"] = "test/booted-hadapter@1"
                n += 1
    assert n == 2, "the two ports are no longer placed once each"
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    root, _ = face(build(dev, tmp_path / "o", booted), "dcp-r-34d-cs", "default")
    assert occupants_drawn(root) == {
        "port-1510-occupant": "test/booted-plug@1",
        "port-1510-occupant-occupant": BOOT,
        "port-line-occupant": "test/booted-plug@1",
        "port-line-occupant-occupant": BOOT}


@pytest.fixture
def looping(lib):
    """A plug whose own default is itself - a cycle of one link."""
    _copy(lib, "generic/lc-plug", 2, "loop-plug", _set(default="test/loop-plug@1"))
    _copy(lib, V_ADAPTER, 5, "looping-adapter",
          _unshipped(lambda c: _part(c, "tx").update({"default": "test/loop-plug@1"})))
    _copy(lib, CASSETTE, 3, "looping-cassette",
          lambda c: _part(c, "lc01").update({"ref": "test/looping-adapter@1"}))
    return lib


def test_a_default_that_loops_back_on_one_seat_is_an_error(tmp_path, looping):
    dev, _ = fhd(tmp_path, "test/looping-cassette@1")
    r = run(dev, tmp_path / "o", looping)
    assert r.returncode != 0
    assert "test/loop-plug@1 is a cycle" in r.stderr, r.stderr[-800:]
    assert "bay-1/module/lc01/tx" in r.stderr


def test_a_device_level_default_that_loops_is_an_error(tmp_path, looping):
    r = run(dcp(tmp_path, {"port-1510": "test/loop-plug@1"}), tmp_path / "o", looping)
    assert r.returncode != 0
    assert "test/loop-plug@1 is a cycle" in r.stderr, r.stderr[-800:]
    assert "port-1510" in r.stderr
