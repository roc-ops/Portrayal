"""`cages[]` in `<device>.configs.json`: what the library could seat, derived.

A device's compiled index gains one entry per placement that presents a
pluggable interface, each carrying an `accepts` list computed from THREE
inputs that have each been wrong in this project before: a part's `mates`, a
wrapper's presented interface (`manifest.presented_interface`), and a port's
declared `media` - read from the placement first, then from its group, which
is the precedence L18 has applied since long before this. Nothing consumes this list until spec C2 - the same
shape spec B1 shipped a kit accessor in, tested only against hand-built
fakes, where a latent defect survived until B2 became its first real
consumer (docs/... the C1 plan says so directly). These tests are what stands
in for that consumer here, so they run against the REAL library and REAL
built `configs.json`, never a fixture.

THE THREE DEVICES ARE PICKED BY CHECKING THEIR DECLARED MEDIA, not by
trusting a name - that assumption has been wrong repeatedly on this project
(docs/visio-stencils-are-simplifications.md is the same lesson one level
down, about a datasheet instead of a device name):

  - edgecore/csr310, placement `m1-0`: `groups.sfp28.attrs.media == sfp28`,
    ref `std/sfp-ganged@1`, which presents interface `sfp` - the `sfp` family
    on the ladder, ceiling `sfp28`.
  - edgecore/dcs510, placement `port-1`: `groups.qsfpdd-400g.attrs.media ==
    qsfp-dd`, ref `std/qsfp-dd@1`, interface `qsfp-dd` - the ONLY case in this
    library that exercises `also-accepts` (`qsfp-dd` also-accepts `qsfp`).
  - edgecore/ais800-32o, placement `port-1`: `groups.osfp800.attrs.media ==
    osfp`, ref `std/osfp@1`, interface `osfp` - one of four families (osfp,
    xfp, cfp, cfp2) with a cage in the library and no component that mates
    it, so its accept list is legitimately `[]`.

Checked directly, once, in `spec/tools/portrayal/render.py`:

    grep -n "ref: std/sfp-ganged@1" library/devices/edgecore/csr310/device.yaml
    grep -n "ref: std/qsfp-dd@1" library/devices/edgecore/dcs510/device.yaml
    grep -n "ref: std/osfp@1" library/devices/edgecore/ais800-32o/device.yaml

all resolve to placements inside a `groups:` entry carrying the media named
above.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

SPEC = Path(__file__).resolve().parents[1]
LIB = SPEC.parent / "library"
RENDER = SPEC / "tools/portrayal/render.py"

from portrayal import libwalk
from portrayal import render as render_mod

CSR310 = LIB / "devices/edgecore/csr310/device.yaml"
DCS510 = LIB / "devices/edgecore/dcs510/device.yaml"
AIS800_32O = LIB / "devices/edgecore/ais800-32o/device.yaml"


def _build(device_yaml, tmp_path):
    r = subprocess.run([sys.executable, str(RENDER), str(device_yaml),
                        "--library", str(LIB), "--out", str(tmp_path)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    name = yaml.safe_load(device_yaml.read_text())["name"]
    return json.loads((tmp_path / f"{name}.configs.json").read_text())


def _cage(idx, view, cage_id):
    return next(c for c in idx["cages"][view] if c["id"] == cage_id)


# --- the three real cages ------------------------------------------------

def test_an_sfp28_cage_accepts_exactly_the_two_sfp_generics(tmp_path):
    idx = _build(CSR310, tmp_path)
    cage = _cage(idx, "front", "m1-0")
    assert cage["interface"] == "sfp"
    assert cage["media"] == "sfp28"
    assert cage["group"] == "sfp28"
    # ORDER IS PART OF THE CONTRACT - generics first, alphabetical - so a
    # wrong-but-nonempty list (the failure mode an unordered `set()` compare
    # would hide) fails loudly here.
    assert cage["accepts"] == ["generic/sfp-lc-simplex@1", "generic/sfp-lc@1"]


def test_a_qsfp_dd_cage_accepts_its_own_generic_and_the_also_accepted_qsfp_one(tmp_path):
    """The ONLY case in this library exercising `also-accepts`:
    `generic/qsfp-lc@1` (`mates: qsfp`) reaches this cage through
    `qsfp-dd`'s `also-accepts: [qsfp]`, not through its own family. If
    `also-accepts` were silently dropped, this list would still be
    non-empty (`generic/qsfp-dd-lc@1` alone) - an easy defect to miss without
    an exact-list assertion, which is why this checks both members and the
    order together rather than membership alone."""
    idx = _build(DCS510, tmp_path)
    cage = _cage(idx, "front", "port-1")
    assert cage["interface"] == "qsfp-dd"
    assert cage["media"] == "qsfp-dd"
    assert cage["group"] == "qsfpdd-400g"
    assert cage["accepts"] == ["generic/qsfp-dd-lc@1", "generic/qsfp-lc@1"]


def test_an_osfp_cage_accepts_nothing_but_says_so_explicitly(tmp_path):
    """Four families - osfp, xfp, cfp, cfp2 - have a cage in the library and
    no component that mates one. `[]`, EMPTY, NOT ABSENT: a consumer has to
    be able to tell "the library offers nothing here" from "this placement
    is not a cage at all", and those are different facts only if the key is
    always present."""
    idx = _build(AIS800_32O, tmp_path)
    cage = _cage(idx, "front", "port-1")
    assert cage["interface"] == "osfp"
    assert "accepts" in cage
    assert cage["accepts"] == []


def test_a_cage_entry_carries_the_documented_shape(tmp_path):
    idx = _build(CSR310, tmp_path)
    cage = _cage(idx, "front", "m1-0")
    assert set(cage) == {"id", "at", "interface", "media", "group", "rel-pos",
                          "rotate", "accepts", "occupant",
                          "mate", "lift", "occupant-attrs"}
    assert cage["rel-pos"] == 0
    assert cage["rotate"] is None
    # AFTER SPEC A NO SHIPPED DEVICE SEATS ONE - this is the honest value for
    # every real device today, and is checked as a fact about the corpus
    # below rather than assumed here.
    assert cage["occupant"] is None


def test_a_group_with_no_media_has_no_ceiling(tmp_path):
    """`media` is the port GROUP's declared media - the cage's ceiling on its
    family's ladder. A group with no `media` declares none, so the cage
    accepts every rate of its family rather than nothing: checked on a copy
    of csr310 with `groups.sfp28.attrs.media` removed. The accept list is
    unchanged from the media-bearing case (nothing in the library declares a
    rate yet, so no ceiling has anything to exclude either way) - what this
    proves is that a missing `media` reads as `None` and does not make the
    derivation empty or raise, which a `.get("media")` typo could do
    silently."""
    dev = tmp_path / "src" / "csr310" / "device.yaml"
    shutil.copytree(CSR310.parent, dev.parent)
    d = yaml.safe_load(dev.read_text())
    del d["groups"]["sfp28"]["attrs"]["media"]
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))

    idx = _build(dev, tmp_path / "out")
    cage = _cage(idx, "front", "m1-0")
    assert cage["group"] == "sfp28"
    assert cage["media"] is None
    assert cage["accepts"] == ["generic/sfp-lc-simplex@1", "generic/sfp-lc@1"]


# --- the configured occupant, read from the manifest, not hardcoded ------

SFP_SRC = LIB / "devices/ufispace/s9510-28dc"


def test_the_configured_occupant_is_read_from_the_default_configuration(tmp_path):
    """No shipped device seats one (spec A), so this is the one place the
    field is proven live rather than merely absent everywhere: a real device,
    copied to a scratch path and given a real `occupants:` entry in its
    DEFAULT configuration (`dc`, `default: true`) - the same idiom
    test_occupants.py uses, because the library ships no fitted device by
    policy (docs/pluggables-design.md decision 2) and a corpus other tests
    read is not a scratch pad."""
    dev = tmp_path / "src" / "s9510-28dc" / "device.yaml"
    shutil.copytree(SFP_SRC, dev.parent)
    d = yaml.safe_load(dev.read_text())
    assert d["configurations"]["dc"].get("default") is True
    d["configurations"]["dc"]["occupants"] = {"port-4": "generic/sfp-lc@1"}
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))

    idx = _build(dev, tmp_path / "out")
    seated = _cage(idx, "front", "port-4")
    empty = _cage(idx, "front", "port-5")
    assert seated["occupant"] == "generic/sfp-lc@1"
    assert empty["occupant"] is None


def test_a_non_default_configurations_occupants_reach_configs(tmp_path):
    """`occupants:` is a PER-CONFIGURATION key, so `cages[].occupant` - a
    view-static entry - can only ever report one configuration's answer, and
    it reports the default's. Every configuration's own map is published
    beside its `bays`, as `configs[].occupants`.

    The failure this pins is not hypothetical: a device offering a bare and a
    fitted configuration (the downstream export docs/pluggables-slotting-
    design.md names, and spec C2's first consumer) published the default's
    occupants and dropped every other configuration's on the floor, with
    nowhere else in the file to look. `s9510-28dc`'s `ac` is a real
    non-default configuration."""
    dev = tmp_path / "src" / "s9510-28dc" / "device.yaml"
    shutil.copytree(SFP_SRC, dev.parent)
    d = yaml.safe_load(dev.read_text())
    assert d["configurations"]["dc"].get("default") is True
    assert not d["configurations"]["ac"].get("default")
    d["configurations"]["ac"]["occupants"] = {"port-4": "generic/sfp-lc@1"}
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))

    idx = _build(dev, tmp_path / "out")
    by_name = {c["name"]: c for c in idx["configs"]}
    assert by_name["ac"]["occupants"] == {"port-4": "generic/sfp-lc@1"}
    # THE DEFAULT SEATS NOTHING, and says so as an empty map rather than by
    # omitting the key - the same "empty is not absent" rule `accepts` keeps.
    assert by_name["dc"]["occupants"] == {}
    # AND THE VIEW-LEVEL FIELD IS UNCHANGED: it answers for `dc`, the
    # default, which seats nothing. A consumer holding `ac` must read
    # `configs[].occupants`, which is the whole point of the pair.
    assert _cage(idx, "front", "port-4")["occupant"] is None


def test_no_shipped_device_seats_an_occupant():
    """The corpus-wide fact `test_a_cage_entry_carries_the_documented_shape`
    pins one example of: after spec A, `occupants:` is empty on every
    configuration this library ships (docs/pluggables-design.md decision 2)."""
    seated = []
    for man in libwalk.iter_devices([LIB]):
        d = yaml.safe_load(man.read_text())
        for name, cfg in (d.get("configurations") or {}).items():
            if (cfg or {}).get("occupants"):
                seated.append(f"{man.parent.name}:{name}")
    assert not seated, seated


# --- what never reaches an accept list, checked directly against the whole
# library rather than one device at a time - the corpus B1's kit accessor
# did not have, and the reason its defect survived to B2. ----------------

def test_superseded_parts_are_real_but_excluded_from_every_candidate_pool():
    """`common/sfp-lc-duplex@1` and `common/qsfp-transceiver@1` are not
    hypothetical - they are real, live contracts in this library, checked
    here so the exclusion below is not vacuous (the exact failure mode a
    silently-empty `iter_components` walk would produce)."""
    dup = yaml.safe_load((LIB / "components/common/sfp-lc-duplex/v1/contract.yaml").read_text())
    assert dup["mates"] == "sfp" and dup.get("superseded-by") == "generic/sfp-lc@1"
    qxc = yaml.safe_load((LIB / "components/common/qsfp-transceiver/v1/contract.yaml").read_text())
    assert qxc["mates"] == "qsfp" and qxc.get("superseded-by") == "generic/qsfp-lc@1"

    candidates = render_mod._pluggable_candidates([LIB])
    all_refs = {ref for entries in candidates.values() for ref, _c in entries}
    assert "common/sfp-lc-duplex@1" not in all_refs
    assert "common/qsfp-transceiver@1" not in all_refs
    # NOT VACUOUS the other way either: real, live candidates for the same two
    # interfaces ARE in the pool, so the exclusion is `superseded-by` at work
    # and not an empty table passing every check by having nothing to check.
    assert any(ref == "generic/sfp-lc@1" for ref, _c in candidates.get("sfp", []))
    assert any(ref == "generic/qsfp-lc@1" for ref, _c in candidates.get("qsfp", []))


def test_a_boot_never_reaches_an_accept_list():
    """`common/lc-boot@1` (`mates: lc-plug`) and `common/rj45-boot@1`
    (`mates: rj45-plug`) pass `behaviour: occupies` and carry no
    `superseded-by` - they are real candidates in the pool, exactly like a
    transceiver. The ONLY reason neither ever seats in a cage is that
    `lc-plug`/`rj45-plug` name no family's `interface` in
    spec/schemas/pluggables.yaml, so no cage's derivation can ever draw from
    either bucket - checked directly against the registry rather than by
    grepping every device's rendered `accepts` list for the two refs."""
    candidates = render_mod._pluggable_candidates([LIB])
    assert any(ref == "common/lc-boot@1" for ref, _c in candidates.get("lc-plug", []))
    assert any(ref == "common/rj45-boot@1" for ref, _c in candidates.get("rj45-plug", []))

    families = render_mod._pluggable_families()
    family_interfaces = {fam["interface"] for fam in families.values()}
    assert "lc-plug" not in family_interfaces
    assert "rj45-plug" not in family_interfaces


def test_the_registry_load_is_not_vacuous():
    """A registry that failed to parse would pass every check above by
    having nothing to check - test_pluggable_ladder.py's own vacuity test,
    one file over, for the same reason."""
    families = render_mod._pluggable_families()
    assert len(families) >= 8
    assert render_mod._family_by_interface(families, "sfp")[0] == "sfp"
    assert render_mod._family_by_interface(families, "not-a-real-interface") is None


# --- fix round 1: the group's media governs when it disagrees with the -----
# cage's presented interface ---------------------------------------------
#
# The accept list derivation surfaced a real corpus fact: 78 ports across six
# devices (edgecore/as7946-30xb, as7946-74xksb, csr440, dcs240, dcs511,
# ufispace/s9510-28dc) declare `media: qsfp-dd` on their port group while
# being modelled with `std/qsfp-ganged@1`, a QSFP aperture, not a QSFP-DD
# one. QSFP-DD and QSFP share a face opening and differ mainly in depth, so
# the DRAWING may be correct - which family should govern the accept list is
# Jason's ruling, not something this code derives: the group's media, because
# the group says what the port IS and the aperture only says what it looks
# like. `spec/tools/portrayal/lint.py`'s L104
# (`lint_device_cage_media_disagreement`) flags every one of the 78 so the
# modelling question - aperture wrong, or group media wrong - stays visible;
# `spec/tests/test_ladder_lint.py` pins that count and the exact six devices.
# This is the other half: that render.py's derivation actually serves the
# RIGHT optic once the two disagree, checked against a real device rather
# than the six being taken on faith.
#
# edgecore/csr440, placement `port-2`: `groups.qsfp-dd.attrs.media ==
# qsfp-dd`, ref `std/qsfp-ganged@1`, which presents interface `qsfp` - one of
# the 78, checked directly:
#
#     grep -n "ref: std/qsfp-ganged@1" library/devices/edgecore/csr440/device.yaml
#
# resolves to `port-2`, inside the `qsfp-dd` group.

CSR440 = LIB / "devices/edgecore/csr440/device.yaml"


def test_a_qsfp_shaped_cage_with_qsfp_dd_media_offers_the_qsfp_dd_optic(tmp_path):
    idx = _build(CSR440, tmp_path)
    cage = _cage(idx, "front", "port-2")
    # THE DRAWING FACT IS UNCHANGED - this really is a QSFP-shaped aperture,
    # and the entry says so honestly.
    assert cage["interface"] == "qsfp"
    assert cage["media"] == "qsfp-dd"
    assert cage["group"] == "qsfp-dd"
    # THE ACCEPT LIST FOLLOWS THE MEDIA, NOT THE APERTURE: the qsfp-dd
    # family's own generic, plus generic/qsfp-lc@1 through qsfp-dd's
    # `also-accepts: [qsfp]` - exactly what a genuine std/qsfp-dd@1 cage with
    # this same media would offer (test_a_qsfp_dd_cage_accepts_its_own_generic_
    # and_the_also_accepted_qsfp_one, above, on edgecore/dcs510).
    assert cage["accepts"] == ["generic/qsfp-dd-lc@1", "generic/qsfp-lc@1"]


# --- final review F1: the media is read from the PLACEMENT first, then its --
# group ------------------------------------------------------------------
#
# The corpus declares a port's media in TWO places and lint.py has read them
# in this order since L18 (`(p.get("attrs") or {}).get("media") or
# gattrs.get("media")`); L22 makes a placement/group contradiction an ERROR,
# so the two can never disagree and the placement is simply the more specific
# answer. 83 cage placements across 22 devices declare a media their group
# does not, and on exactly ONE of them it changes the accept list:
#
# smartoptics/dcp-sc-28p, placement `port-probe`:
#
#     grep -n "id: port-probe" library/devices/smartoptics/dcp-sc-28p/device.yaml
#
# resolves to `{ref: std/qsfp-ganged@1, id: port-probe, attrs: {media:
# qsfp-dd, role: probe}, group: probe}` - a QSFP aperture whose `probe` group
# declares NO media of its own, only the description "the QSFP-DD probe
# port". Read from the group alone this cage published `media: null` and
# offered `generic/qsfp-lc@1` only, omitting the QSFP-DD optic that actually
# belongs in it - quietly wrong rather than empty, which is the failure mode
# the whole precedence rule exists to prevent.

DCP_SC_28P = LIB / "devices/smartoptics/dcp-sc-28p/device.yaml"


def test_a_placement_declared_media_governs_when_the_group_declares_none(tmp_path):
    idx = _build(DCP_SC_28P, tmp_path)
    cage = _cage(idx, "front", "port-probe")
    # THE DRAWING FACT IS UNCHANGED, exactly as on csr440 above: a QSFP-shaped
    # aperture, reported honestly.
    assert cage["interface"] == "qsfp"
    assert cage["group"] == "probe"
    # READ FROM THE PLACEMENT. `null` here - the value a group-only read
    # published - is the defect this pins.
    assert cage["media"] == "qsfp-dd"
    assert cage["accepts"] == ["generic/qsfp-dd-lc@1", "generic/qsfp-lc@1"]


def test_the_probe_group_itself_declares_no_media(tmp_path):
    """NOT VACUOUS: the assertion above would pass unchanged if `probe` had
    quietly gained an `attrs.media` of its own, which would make it a copy of
    the csr440 case rather than the placement-declared one. Read from the
    manifest, so it fails the day that changes."""
    d = yaml.safe_load(DCP_SC_28P.read_text())
    assert "media" not in ((d["groups"]["probe"].get("attrs")) or {})
    placement = next(p for p in d["views"]["front"]["components"]["placements"]
                     if p["id"] == "port-probe")
    assert placement["attrs"]["media"] == "qsfp-dd"


def test_a_qsfp_shaped_cage_with_agreeing_media_is_unaffected(tmp_path):
    """The precedence rule only fires on a disagreement. `port-1` on the same
    device is in the plain `qsfp28` group - QSFP media on a QSFP aperture,
    the ordinary case everywhere else in this suite - and must not be
    touched by the code path the 78 disagreeing ports exercise."""
    idx = _build(CSR440, tmp_path)
    cage = _cage(idx, "front", "port-1")
    assert cage["interface"] == "qsfp"
    assert cage["media"] == "qsfp28"
    assert cage["accepts"] == ["generic/qsfp-lc@1"]


# --- C2 Task 1: where an occupant mates, published --------------------------
#
# Three keys let the kit seat an optic without re-deriving the build: `mate`
# (the cage's presented mate point in the DEVICE frame, rotation applied),
# `lift` (its presented lift, the build's `host-lift`) and `occupant-attrs`
# (what the build writes on a seated occupant from the host's side). Checked
# against the build's own seat - test_seat_rotation.py measures the two
# S9510-28DC ports this pins - and across the whole library.

def _fitted_s9510(tmp_path):
    dev = tmp_path / "src" / "s9510-28dc" / "device.yaml"
    shutil.copytree(SFP_SRC, dev.parent)
    d = yaml.safe_load(dev.read_text())
    d["configurations"]["dc"]["occupants"] = {"port-0": "generic/qsfp-lc@1",
                                              "port-2": "generic/qsfp-lc@1"}
    dev.write_text(yaml.safe_dump(d, sort_keys=False, allow_unicode=True))
    return dev


def test_every_entry_says_where_and_how_to_seat(tmp_path):
    idx = _build(_fitted_s9510(tmp_path), tmp_path / "out")
    entries = [c for v in idx["cages"].values() for c in v]
    assert entries, "no cages - the checks below would pass vacuously"
    for c in entries:
        assert isinstance(c["mate"], list) and len(c["mate"]) == 2, c
        assert all(isinstance(v, (int, float)) for v in c["mate"]), c
        assert isinstance(c["lift"], float), c
        assert isinstance(c["occupant-attrs"], dict), c
        assert all(isinstance(k, str) and k.startswith("data-") and isinstance(v, str)
                   for k, v in c["occupant-attrs"].items()), c


def test_the_published_mate_is_where_the_build_seats(tmp_path):
    """The device-frame mate points test_seat_rotation.py measures off the
    build's own transforms: port-0 upright, port-2 at rotate 180. port-2's is
    NOT `at + mate` - that would be [239.625, 14.19], the upright answer."""
    idx = _build(_fitted_s9510(tmp_path), tmp_path / "out")
    assert _cage(idx, "front", "port-0")["mate"] == [187.225, 31.59]
    assert _cage(idx, "front", "port-2")["rotate"] == 180
    assert _cage(idx, "front", "port-2")["mate"] == [239.475, 13.59]


def test_occupant_attrs_are_what_the_build_wrote_from_the_host(tmp_path):
    """Every `occupant-attrs` entry appears, with that value, on the build's
    own seated occupant - and it carries the host group's media, overriding
    the optic's contract `media: fiber`."""
    import re
    dev = _fitted_s9510(tmp_path)
    idx = _build(dev, tmp_path / "out")
    svg = (tmp_path / "out" / "s9510-28dc.dc.front.svg").read_text()
    for port, media in (("port-0", "qsfp-dd"), ("port-2", "qsfp28")):
        attrs = _cage(idx, "front", port)["occupant-attrs"]
        assert attrs["data-media"] == media
        assert attrs["data-group-role"] == "traffic"
        tag = re.search(rf'<g id="{port}-occupant"[^>]*>', svg).group(0)
        for k, v in attrs.items():
            assert f'{k}="{v}"' in tag, (port, k, v, tag)


def test_the_lift_census():
    """RECORDS the published lift across every cage in the library, computed
    by the same `cage_entries` main() writes. 3,326 cages at this writing, and
    NONE presents a lift: no cage wrapper composes its aperture with a `lift`
    today. The day one does, this count moves and the kit's data-z-lift path
    stops being dead code - which is the point of pinning it."""
    lib = render_mod.Library([str(LIB)])
    families = render_mod._pluggable_families()
    candidates = render_mod._pluggable_candidates([LIB])
    total = nonzero = 0
    for man in libwalk.iter_devices([LIB]):
        d = render_mod.load_yaml(man)
        for v in d.get("views") or {}:
            for c in render_mod.cage_entries(d, v, lib, families, candidates, {}):
                total += 1
                nonzero += bool(c["lift"])
    assert total >= 3000, total
    assert nonzero == 0, nonzero
